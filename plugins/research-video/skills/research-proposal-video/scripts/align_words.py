#!/usr/bin/env python3
"""Get word timestamps for one voice-only audio file, either by forced alignment or by ASR.

Two back ends:
  qwen    - Qwen3-ForcedAligner-0.6B aligns the approved script itself to the audio (needs
            --script and `pip install qwen-asr`). The words are exactly the script's, so nothing is
            misheard ("ten to fifteen" stays words, names stay spelled), results are repeatable, and
            onsets were about twice as close as Whisper's in testing. Up to 5 minutes of audio.
  whisper - faster-whisper transcribes and times the words; --script then lists where it heard
            something different. Use it when there is no approved script or no qwen-asr.

Run it on the voice-only track, never on a mix with music. Both back ends miss some onsets after
pauses (Whisper starts early, inside the silence; the aligner sometimes starts late, inside the
word). Each start is snapped to where the voice actually begins, never past the neighbouring word
(--no-refine keeps the raw times).

The default (--aligner auto) uses qwen when --script and --language are given and qwen-asr is
installed, and Whisper otherwise; the choice is printed and stored in words.json.

  python align_words.py work/voice.wav work/words.json --language en --script work/script.txt
  python align_words.py work/voice.wav work/words.json --aligner whisper --language en   # no script
"""
import argparse
import difflib
import json
import re
import subprocess
from pathlib import Path

CJK = "\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uac00-\ud7af"
# Latin words/numbers as one token each; every CJK character as its own token.
TOKEN = re.compile(f"[{CJK}]|[^\\W{CJK}]+")


def tokens(text):
    return TOKEN.findall(text.casefold())


def report_mismatch(approved, recognized, limit=12):
    """Print where ASR differs from the approved script, so names/terms can be fixed by hand."""
    diffs = [op for op in difflib.SequenceMatcher(None, approved, recognized, autojunk=False).get_opcodes()
             if op[0] != "equal"]
    if not diffs:
        return
    print(f"WARNING: ASR differs from the approved script in {len(diffs)} place(s). Check names and terms; "
          "fix words.json or anchor on nearby words before rendering.")
    for tag, a1, a2, b1, b2 in diffs[:limit]:
        context = " ".join(approved[max(0, a1 - 3):a1])
        print(f"  after '{context}': script '{' '.join(approved[a1:a2])}' -> heard '{' '.join(recognized[b1:b2])}'")
    if len(diffs) > limit:
        print(f"  ... and {len(diffs) - limit} more")


def refine_starts(audio, words, offset, threshold_db=-35.0, ffmpeg="ffmpeg", min_gap=12, max_back=60):
    """Snap word starts onto voice onsets (10 ms frames).

    A start in silence moves forward to the first voiced frame inside the word. A start inside
    speech that follows a gap after the previous word moves back to where that stretch of speech
    begins (a silence of at least min_gap frames; shorter gaps between words do not count), at most max_back frames and never before the
    previous word's end, so starts inside continuous speech are left alone.
    """
    import numpy as np
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32)
    n = len(x) // 160
    db = 10 * np.log10((x[:n * 160].reshape(n, 160) ** 2).mean(axis=1) + 1e-10)
    voiced = db > np.percentile(db, 95) + threshold_db
    moved = 0
    prev_end = 0
    for w in words:
        a, b = round((w["start"] - offset) * 100), round((w["end"] - offset) * 100)
        if 0 < a < n:
            lo_s, hi_s = a, a              # the run of silent frames around the start, if any
            while lo_s > 0 and not voiced[lo_s - 1]:
                lo_s -= 1
            while hi_s < n and not voiced[hi_s]:
                hi_s += 1
            if hi_s - lo_s >= min_gap:     # start sits in a real pause: move to the first voiced frame
                hits = np.nonzero(voiced[a:max(a + 1, b - 2)])[0]
                if len(hits) and hits[0]:
                    w["start"] = round(offset + (a + hits[0]) / 100, 3)
                    moved += 1
            elif a - prev_end >= min_gap:  # start inside speech after a gap: back to where it begins
                k, run, lo = a, 0, max(prev_end, a - max_back)
                while k > lo:
                    k -= 1
                    run = 0 if voiced[k] else run + 1
                    if run >= min_gap:
                        if k + run < a:
                            w["start"] = round(offset + (k + run) / 100, 3)
                            moved += 1
                        break
        prev_end = max(prev_end, round((w["end"] - offset) * 100))
    return moved


QWEN_LANG = {"en": "English", "zh": "Chinese", "yue": "Cantonese", "fr": "French", "de": "German",
             "it": "Italian", "ja": "Japanese", "ko": "Korean", "pt": "Portuguese", "ru": "Russian",
             "es": "Spanish"}


_QWEN_MODELS = {}


def qwen_align(audio, script_text, language, device, ffmpeg="ffmpeg"):
    """Force-align the script to the audio with Qwen3-ForcedAligner; returns [(text, start, end)]."""
    import subprocess as sp
    import numpy as np
    import torch
    from qwen_asr import Qwen3ForcedAligner
    x = np.frombuffer(sp.run([ffmpeg, "-v", "error", "-i", str(audio), "-ac", "1", "-ar", "16000",
                              "-f", "f32le", "-"], capture_output=True, check=True).stdout, dtype=np.float32)
    if len(x) > 300 * 16000:
        raise SystemExit("Qwen3-ForcedAligner handles up to 5 minutes; split the audio and use --offset")
    if device is None:
        device = "mps" if torch.backends.mps.is_available() else ("cuda:0" if torch.cuda.is_available() else "cpu")
    if device not in _QWEN_MODELS:  # kept, so a batch of files loads the model once
        _QWEN_MODELS[device] = Qwen3ForcedAligner.from_pretrained("Qwen/Qwen3-ForcedAligner-0.6B",
                                                                  dtype=torch.float32, device_map=device)
    result = _QWEN_MODELS[device].align(audio=(x, 16000), text=script_text, language=language)[0]
    return [(item.text, float(item.start_time), float(item.end_time)) for item in result]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--aligner", choices=("auto", "whisper", "qwen"), default="auto",
                        help="qwen: force-align --script with Qwen3-ForcedAligner (recommended when a script exists); "
                             "auto: qwen when --script, --language and qwen-asr are all there, else whisper")
    parser.add_argument("--model", default="small", help="Whisper model size")
    parser.add_argument("--device", help="Default: cpu for Whisper; mps/cuda when available for qwen")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", help="ISO language code; omit for detection")
    parser.add_argument("--offset", type=float, default=0, help="Position of this clip in the full film, seconds")
    parser.add_argument("--script", type=Path, help="Approved script; report where ASR differs from it")
    parser.add_argument("--no-refine", action="store_true", help="Keep the back end's word starts as they are")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    if args.offset < 0:
        parser.error("--offset must be nonnegative")
    if args.aligner == "auto":
        import importlib.util
        args.aligner = ("qwen" if args.script and args.language and importlib.util.find_spec("qwen_asr")
                        else "whisper")
        print(f"Aligner: {args.aligner}")
    if args.aligner == "qwen":
        if not args.script:
            parser.error("--aligner qwen needs --script (the text to align)")
        language = QWEN_LANG.get((args.language or "").lower(), args.language)
        if not language:
            parser.error("--aligner qwen needs --language, e.g. en or zh")
        try:
            raw = qwen_align(args.audio, args.script.read_text(encoding="utf-8"), language, args.device, args.ffmpeg)
        except ImportError:
            parser.error("Install qwen-asr in the chosen Python environment (pip install qwen-asr)")
    else:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            parser.error("Install faster-whisper in the chosen Python environment")
        model = WhisperModel(args.model, device=args.device or "cpu", compute_type=args.compute_type)
        segments, info = model.transcribe(str(args.audio), language=args.language, word_timestamps=True, beam_size=5)
        language = info.language
        raw = [(word.word.strip(), word.start, word.end) for segment in segments for word in segment.words or []]
    words = []
    for text, start, end in raw:
        start = round(args.offset + start, 3)
        words.append({
            "id": f"w{len(words) + 1:04d}",
            "text": text,
            "start": start,
            # Both back ends can return zero-length words; give them 20 ms so timelines validate.
            "end": max(round(args.offset + end, 3), round(start + .02, 3)),
        })
    if not args.no_refine:
        moved = refine_starts(args.audio, words, args.offset, ffmpeg=args.ffmpeg)
        if moved:
            print(f"Moved {moved} word start(s) out of silence onto the voice onset")
    result = {"source": str(args.audio), "aligner": args.aligner, "language": language, "words": words}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.script and args.aligner == "whisper":
        approved = tokens(args.script.read_text(encoding="utf-8"))
        recognized = [part for w in words for part in tokens(w["text"])]
        report_mismatch(approved, recognized)
    print(f"Wrote {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()

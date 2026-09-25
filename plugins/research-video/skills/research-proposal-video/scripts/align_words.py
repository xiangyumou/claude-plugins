#!/usr/bin/env python3
"""Transcribe one audio file to word timestamps and compare them with the approved script.

  python align_words.py work/voice.wav work/words.json --language en --script work/script.txt
"""
import argparse
import difflib
import json
import re
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="small")
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--language", help="ISO language code; omit for detection")
    parser.add_argument("--offset", type=float, default=0, help="Position of this clip in the full film, seconds")
    parser.add_argument("--script", type=Path, help="Approved script; report where ASR differs from it")
    args = parser.parse_args()
    if args.offset < 0:
        parser.error("--offset must be nonnegative")
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        parser.error("Install faster-whisper in the chosen Python environment")
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    segments, info = model.transcribe(str(args.audio), language=args.language, word_timestamps=True, beam_size=5)
    words = []
    for segment in segments:
        for word in segment.words or []:
            words.append({
                "id": f"w{len(words) + 1:04d}",
                "text": word.word.strip(),
                "start": round(args.offset + word.start, 3),
                "end": round(args.offset + word.end, 3),
            })
    result = {"source": str(args.audio), "language": info.language, "words": words}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.script:
        approved = tokens(args.script.read_text(encoding="utf-8"))
        recognized = [part for w in words for part in tokens(w["text"])]
        report_mismatch(approved, recognized)
    print(f"Wrote {len(words)} words to {args.output}")


if __name__ == "__main__":
    main()

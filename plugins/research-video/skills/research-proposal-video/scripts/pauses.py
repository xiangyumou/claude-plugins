#!/usr/bin/env python3
"""Measure the pauses in a voice track by the punctuation before them, and optionally reset them.

Every gap between two words in words.json is classed by what the approved script has after
the first word: a sentence end (. ! ? and CJK equivalents), a comma-like break (, ; : dash) or
none. Without an output file the script only reports, per class, how many pauses there are and
their median and longest length, plus the speaking rate without pauses - run it on the TTS voice
and on a real recording of the speaker and compare.

With an output file it rewrites the pauses: --sentence sets sentence pauses to that length
(longer or shorter), --comma and --none cap the other two classes. A pause is shortened by
cutting out its middle (both edges and the breath next to the words stay) with a short
crossfade, and lengthened by inserting silence in the middle. Nothing after the last word or
before the first one is touched. --words-out writes words.json with the times moved to match;
align the new track again anyway before building the timeline.

  python pauses.py work/voice.wav work/voice_words.json work/script.txt          # measure
  python pauses.py work/voice.wav work/voice_words.json work/script.txt work/voice_paced.wav \\
      --sentence 0.55 --comma 0.3 --none 0.1 --words-out work/voice_paced_words.json

Run it on the TTS narration with its own words.json, before place_audio.py builds the full voice
track, or limit it with --from/--to. The script may use {shown|spoken} markup.
"""
import argparse
import difflib
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
from align_words import TOKEN, spoken, tokens  # noqa: E402
from make_subtitles import sentences  # noqa: E402

RATE = 48000
COMMA = re.compile(r"[,;:](?:\s|$)|[，；：、—]|\s[–-]\s")


def classes(script, words):
    """For each word but the last: 'sentence', 'comma' or 'none', from the script's punctuation
    after the script token matched to the word's last token (sentences split as in make_subtitles,
    so "Dr. Lee" or "3.5" is not a sentence end)."""
    script_toks, kind = [], []
    for paragraph in script.split("\n"):
        for sentence in sentences(" ".join(paragraph.split())):
            text = spoken(sentence).casefold()
            found = list(TOKEN.finditer(text))
            for k, m in enumerate(found):
                gap = text[m.end():found[k + 1].start()] if k + 1 < len(found) else ""
                script_toks.append(m.group())
                kind.append("sentence" if k + 1 == len(found) else "comma" if COMMA.search(gap) else "none")
    heard = [(w, t) for w, word in enumerate(words) for t in tokens(word["text"])]
    last_tok = {}
    for k, (w, _) in enumerate(heard):
        last_tok[w] = k
    matcher = difflib.SequenceMatcher(None, [t for _, t in heard], script_toks, autojunk=False)
    to_script = {}
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            to_script[a + k] = b + k
    return [kind[to_script[last_tok[w]]] if last_tok.get(w, -1) in to_script else "none"
            for w in range(len(words) - 1)]


def load(path, ffmpeg):
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).reshape(-1, 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("audio", type=Path, help="Voice-only track the words were timed on")
    parser.add_argument("words", type=Path, help="words.json for that track (align_words.py)")
    parser.add_argument("script", type=Path, help="Approved script, for the punctuation")
    parser.add_argument("output", type=Path, nargs="?", help="Paced WAV (48 kHz stereo); omit to only measure")
    parser.add_argument("--sentence", type=float, help="Set pauses after a sentence end to this (s)")
    parser.add_argument("--comma", type=float, help="Cap pauses after a comma-like break at this (s)")
    parser.add_argument("--none", type=float, help="Cap pauses with no punctuation at this (s), e.g. 0.1")
    parser.add_argument("--from", dest="t0", type=float, default=0, help="Only change pauses after this time (s)")
    parser.add_argument("--to", dest="t1", type=float, default=float("inf"), help="... and before this time (s)")
    parser.add_argument("--fade", type=float, default=.01, help="Crossfade at each cut (s)")
    parser.add_argument("--words-out", type=Path, help="words.json with times moved to the new track")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    data = json.loads(args.words.read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    if len(words) < 2:
        parser.error("need at least two words")
    kinds = classes(args.script.read_text(encoding="utf-8"), words)
    gaps = [max(0.0, words[k + 1]["start"] - words[k]["end"]) for k in range(len(words) - 1)]

    speech = words[-1]["end"] - words[0]["start"] - sum(gaps)
    print(f"{len(words)} words, {len(words) / max(speech, 1e-6):.2f} words/s without pauses "
          f"({speech:.1f} s of speech, {sum(gaps):.1f} s of pauses)")
    for kind in ("sentence", "comma", "none"):
        these = [g for g, c in zip(gaps, kinds) if c == kind]
        long = [g for g in these if g >= .05]
        if these:
            print(f"  {kind:8s} {len(these):4d} gaps, {len(long):4d} over 50 ms; median {np.median(these):.2f} s, "
                  f"longest {max(these):.2f} s")
    if not args.output:
        return

    target = {"sentence": args.sentence, "comma": args.comma, "none": args.none}
    x = load(args.audio, args.ffmpeg)
    fade = max(1, round(args.fade * RATE))
    parts, pos, shift, shifts, changed = [], 0, 0.0, [0.0], 0
    for k, (gap, kind) in enumerate(zip(gaps, kinds)):
        want, a = target[kind], words[k]["end"]
        if want is None or not args.t0 <= a <= args.t1 or gap <= 0:
            shifts.append(shift)
            continue
        new = want if kind == "sentence" else min(gap, want)
        delta = round((new - gap) * RATE)
        if abs(delta) < round(.01 * RATE):
            shifts.append(shift)
            continue
        mid = round((a + gap / 2) * RATE)
        if delta > 0:                                    # lengthen: silence in the middle
            parts += [x[pos:mid], np.zeros((delta, 2), np.float32)]
            pos = mid
        else:                                            # shorten: cut the middle, crossfade the edges
            cut = -delta
            lo, hi = mid - cut // 2, mid - cut // 2 + cut
            ramp = np.linspace(0, 1, fade, dtype=np.float32)[:, None]
            lo = max(lo, pos + fade)
            parts += [x[pos:lo - fade], x[lo - fade:lo] * ramp[::-1] + x[hi - fade:hi] * ramp]
            pos = hi
        shift += delta / RATE
        shifts.append(shift)
        changed += 1
    parts.append(x[pos:])
    y = np.concatenate(parts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([args.ffmpeg, "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-",
                    "-c:a", "pcm_s24le", str(args.output)], input=y.tobytes(), check=True)
    print(f"{args.output}: {changed} pause(s) changed, {len(x) / RATE:.2f} s -> {len(y) / RATE:.2f} s")
    if args.words_out:
        moved = [dict(w, start=round(w["start"] + s, 3), end=round(w["end"] + s, 3)) for w, s in zip(words, shifts)]
        out = dict(data, words=moved, source=str(args.output)) if isinstance(data, dict) else moved
        args.words_out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote shifted words to {args.words_out}; align the new track again before building the timeline")


if __name__ == "__main__":
    main()

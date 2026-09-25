#!/usr/bin/env python3
"""Time the approved script's text to the voice using ASR word timestamps, and write SRT.

Subtitle text always comes from the approved script (names and terms stay correct); only the
timing comes from words.json. Every sentence starts a new cue; a long sentence is split into
the fewest even cues of at most --max-chars, preferring breaks at commas.

  python make_subtitles.py work/script.txt work/words.json work/subtitles.srt
"""
import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from align_words import CJK, tokens  # noqa: E402

SENTENCE = re.compile(r"(?<=[.!?。！？；;])\s*")
CLAUSE_END = re.compile(r"[,，、:：;；.!?。！？]\s*$")
# A CJK character with any closing punctuation, or a run of other text with its trailing spaces.
UNIT = re.compile(f"[{CJK}][，。、！？；：”’）》]*|[^\\s{CJK}]+\\s*")


def pack(sentence, max_chars):
    """Split one sentence into the fewest cues of at most max_chars, as even as possible,
    preferring breaks after commas and other clause punctuation."""
    units = UNIT.findall(sentence) or [sentence]
    n = len(units)
    best = [(0, 0.)] + [None] * n       # best[i] = (cues, cost) for units[:i]
    back = [0] * (n + 1)
    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            piece = "".join(units[j:i]).strip()
            if len(piece) > max_chars and i - j > 1:
                break
            if best[j] is None:
                continue
            slack = max(0, max_chars - len(piece))
            penalty = 0 if i == n or CLAUSE_END.search(units[i - 1]) else max_chars
            score = (best[j][0] + 1, best[j][1] + slack * slack + penalty * penalty / 4)
            if best[i] is None or score < best[i]:
                best[i], back[i] = score, j
    cues, i = [], n
    while i:
        cues.append("".join(units[back[i]:i]).strip())
        i = back[i]
    return cues[::-1]


def srt_time(t):
    ms = round(max(0., t) * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("script", type=Path, help="Approved narration text (UTF-8)")
    parser.add_argument("words", type=Path, help="words.json from align_words.py")
    parser.add_argument("output", type=Path, help=".srt, or .json for render_video.py cue lists")
    parser.add_argument("--max-chars", type=int, help="Per cue; default 42 (Latin) or 20 (CJK)")
    parser.add_argument("--min-duration", type=float, default=1.0)
    parser.add_argument("--gap", type=float, default=.08, help="Seconds between consecutive cues")
    args = parser.parse_args()
    script = args.script.read_text(encoding="utf-8")
    data = json.loads(args.words.read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    if not words:
        parser.error("words.json has no words")
    max_chars = args.max_chars or (20 if re.search(f"[{CJK}]", script) else 42)

    texts = []
    for paragraph in script.split("\n"):
        for sentence in SENTENCE.split(" ".join(paragraph.split())):
            if sentence.strip():
                # Subtitles drop a trailing comma (and, in CJK text, a trailing full stop).
                texts += [re.sub(r"[,，、；：。]+$" if re.search(f"[{CJK}]", t) else r",+$", "", t)
                          for t in pack(sentence.strip(), max_chars)]
    cue_tokens = [tokens(t) for t in texts]

    # Align script tokens to recognised tokens; each recognised token remembers its word.
    script_toks = [(c, tok) for c, toks in enumerate(cue_tokens) for tok in toks]
    heard_toks = [(w, tok) for w, word in enumerate(words) for tok in tokens(word["text"])]
    matcher = difflib.SequenceMatcher(None, [t for _, t in script_toks], [t for _, t in heard_toks], autojunk=False)
    matched = [[] for _ in texts]
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            matched[script_toks[a + k][0]].append(heard_toks[b + k][0])

    times = [(words[m[0]]["start"], words[m[-1]]["end"]) if m else None for m in matched]
    # Cues with no matched word get the time between their neighbours, shared by token count.
    i = 0
    while i < len(texts):
        if times[i]:
            i += 1
            continue
        j = i
        while j < len(texts) and not times[j]:
            j += 1
        lo = times[i - 1][1] if i else words[0]["start"]
        hi = times[j][0] if j < len(texts) else words[-1]["end"]
        weights = [max(1, len(cue_tokens[k])) for k in range(i, j)]
        t = lo
        for k, weight in zip(range(i, j), weights):
            step = (hi - lo) * weight / sum(weights)
            times[k] = (t, t + step)
            t += step
        i = j

    cues = []
    for k, (start, end) in enumerate(times):
        next_start = times[k + 1][0] if k + 1 < len(times) else float("inf")
        end = min(max(end, start + args.min_duration), next_start - args.gap)
        if cues:
            start = max(start, cues[-1]["end"] + args.gap)
        cues.append({"start": round(start, 3), "end": round(max(end, start + .2), 3), "text": texts[k]})

    weak = [(k, len(m), len(cue_tokens[k])) for k, m in enumerate(matched) if len(m) < .6 * len(cue_tokens[k])]
    for k, got, total in weak:
        print(f"WARNING: cue {k + 1} matched {got}/{total} tokens ({srt_time(cues[k]['start'])}): "
              f"{texts[k]!r}; check its timing.", file=sys.stderr)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.suffix.lower() == ".json":
        args.output.write_text(json.dumps({"subtitles": cues}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    else:
        args.output.write_text("".join(
            f"{k + 1}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n\n" for k, c in enumerate(cues)),
            encoding="utf-8")
    print(f"Wrote {len(cues)} cues to {args.output}")


if __name__ == "__main__":
    main()

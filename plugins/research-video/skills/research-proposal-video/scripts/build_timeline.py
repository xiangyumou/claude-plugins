#!/usr/bin/env python3
"""Build timeline.json from a short scene plan: each cut is placed on a spoken word.

Instead of typing start/end times, name the word each scene should begin on. The dissolve is
centred on that word's start, the previous scene ends where the dissolve ends, the first scene
starts at 0 and the last one runs to the last word plus a tail. Other scene keys (zoom,
center_x/y, title, clip_in, ...) are copied through. The result is checked with
check_timeline.py before it is written.

  python build_timeline.py work/plan.json work/timeline.json

plan.json:
  {"words": "words.json", "word_offset": 0, "transition": 0.36, "tail": 2.8,
   "video": {"width": 1920, "height": 1080, "fps": 30, "fade_in": 0.3},
   "asset_pattern": "cards/out/{id}.png",       # used when a scene has no "asset"
   "scenes": [
     {"id": "intro", "asset": "../src/presenter.mp4", "clip_in": 0.9},
     {"id": "problem", "at": 8.0, "transition": 0.4},  # cut centred at 8.0 s
     {"id": "stats", "word": "It", "after": 11},       # first "It" starting at/after 11 s
     {"id": "clinic", "word": "clinic", "after": 30, "asset": "photos/clinic.jpg", "zoom": 0.03}]}  # photos only

Word times are word-file times plus word_offset (use it when words.json was timed on an audio
file that starts later in the film). A missing word stops the build and lists the nearest words
actually spoken after `after`, which catches US/UK spellings and ASR mishearings.
"""
import argparse
import difflib
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from check_timeline import load_words, validate  # noqa: E402

PLAN_KEYS = {"word", "after", "at", "transition", "anchor_tolerance"}


def norm(text):
    return "".join(c for c in text.casefold() if c.isalnum())


def find_word(words, text, after, offset):
    for w in words:
        if w["start"] + offset >= after - 1e-6 and norm(w["text"]) == norm(text):
            return w
    later = [w for w in words if w["start"] + offset >= after - 1e-6]
    spoken = [norm(w["text"]) for w in later]
    close = difflib.get_close_matches(norm(text), spoken, n=3, cutoff=0.5)
    hints = [f"'{w['text']}' at {w['start'] + offset:.2f}s" for w in later if norm(w["text"]) in close][:3]
    nearby = " ".join(w["text"] for w in later[:8])
    raise SystemExit(f"'{text}' is not spoken at or after {after}s. "
                     + (f"Close: {', '.join(hints)}. " if hints else "")
                     + f"Next words: {nearby}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    plan_dir, out_dir = args.plan.resolve().parent, args.output.resolve().parent
    offset = float(plan.get("word_offset", 0))
    words, word_rel = None, None
    if plan.get("words"):
        word_path = plan_dir / plan["words"]
        words = load_words(word_path)
        word_rel = os.path.relpath(word_path, out_dir)
    default_t = float(plan.get("transition", 0.36))
    tolerance = float(plan.get("anchor_tolerance", 0.25))
    specs = plan["scenes"]

    cuts = [None]                        # (centre, transition, word) for each scene after the first
    for spec in specs[1:]:
        t = float(spec.get("transition", default_t))
        if "at" in spec:
            cuts.append((float(spec["at"]), t, None))
        elif "word" in spec:
            if words is None:
                raise SystemExit(f"scene {spec['id']}: 'word' needs a words file in the plan")
            w = find_word(words, spec["word"], float(spec.get("after", 0)), offset)
            cuts.append((w["start"] + offset, t, w))
        else:
            raise SystemExit(f"scene {spec['id']}: give 'word' (with optional 'after') or 'at' seconds")
    if "duration" in plan:
        duration = float(plan["duration"])
    elif words:
        duration = round(words[-1]["end"] + offset + float(plan.get("tail", 2.5)), 3)
    else:
        raise SystemExit("give 'duration' when the plan has no words file")

    scenes = []
    for i, spec in enumerate(specs):
        scene = {k: v for k, v in spec.items() if k not in PLAN_KEYS}
        if "asset" not in scene and plan.get("asset_pattern"):
            scene["asset"] = plan["asset_pattern"].format(id=spec["id"])
        if "asset" in scene:   # asset paths are relative to the plan; the timeline may live elsewhere
            scene["asset"] = os.path.relpath(plan_dir / scene["asset"], out_dir)
        start = 0.0 if i == 0 else round(cuts[i][0] - cuts[i][1] / 2, 3)
        end = duration if i == len(specs) - 1 else round(cuts[i + 1][0] + cuts[i + 1][1] / 2, 3)
        scene.update(start=start, end=end)
        if i:
            scene["transition_in"] = cuts[i][1]
            w = cuts[i][2]
            if w is not None:
                scene["speech_anchor"] = ({"word_id": w["id"], "tolerance": tolerance} if "id" in w else
                                          {"word": w["text"], "occurrence": 1 + sum(
                                              norm(x["text"]) == norm(w["text"]) for x in words
                                              if x["start"] < w["start"]), "tolerance": tolerance})
        scenes.append(scene)
        cue = f"'{cuts[i][2]['text']}'" if i and cuts[i][2] else ("fixed" if i else "start")
        print(f"{spec['id']:>14}  {start:7.2f} - {end:7.2f}  ({end - start:5.2f}s)  {cue}")

    timeline = {"duration": duration, "video": plan.get("video", {"width": 1920, "height": 1080, "fps": 30}),
                "scenes": scenes}
    if word_rel:
        timeline["word_file"] = word_rel
        if offset:
            timeline["word_offset"] = offset
    errors = validate(timeline, out_dir, words)
    if errors:
        raise SystemExit("Timeline problems (nothing written):\n  " + "\n  ".join(errors))
    args.output.write_text(json.dumps(timeline, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{args.output}  {duration:.2f}s, {len(scenes)} scenes, checked")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Validate a scene timeline, declared dissolves, video-clip scenes, and optional word cues.

Word cues are compared with word start times plus the timeline's optional `word_offset`
(seconds), for word files timed against an audio file that starts later in the film.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
from align_words import CJK  # noqa: E402

EPS = .002
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


def clip_length(path):
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None
    try:
        out = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except (ValueError, subprocess.CalledProcessError):
        return None


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def load_words(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    words = data.get("words") if isinstance(data, dict) else data
    if not isinstance(words, list):
        raise ValueError("words must be a list or an object with a words list")
    ids, previous = set(), 0.0
    for i, word in enumerate(words):
        if not isinstance(word, dict) or not isinstance(word.get("text"), str):
            raise ValueError(f"word {i + 1} needs text, start, and end")
        start, end = word.get("start"), word.get("end")
        if not number(start) or not number(end) or start < 0 or end <= start:
            raise ValueError(f"word {i + 1} has invalid start/end")
        if start + EPS < previous:
            raise ValueError(f"word {i + 1} is out of order")
        previous = start
        if "id" in word:
            if not isinstance(word["id"], str) or not word["id"] or word["id"] in ids:
                raise ValueError(f"word {i + 1} has an invalid or duplicate id")
            ids.add(word["id"])
    return words


def norm(text):
    return "".join(c for c in text.casefold() if c.isalnum())


def can_span(text):
    """A CJK word or a phrase ("explainable AI", "AI-driven") may cover several word entries;
    a single Latin word may not, so "into" never matches "in to"."""
    return bool(re.search(f"[{CJK}]", text) or re.search(r"\w\W+\w", text.strip()))


def spoken_at(words, i, text):
    """True when `text` is spoken starting at words[i]: as that entry, or, when can_span(text),
    across the next entries too (Chinese and Japanese are often timed per character: 超声 = 超 + 声)."""
    target, said = norm(text), ""
    if not target or not norm(words[i]["text"]):     # a match starts on a spoken word, not on punctuation
        return False
    if not can_span(text):
        return norm(words[i]["text"]) == target
    for w in words[i:]:
        said += norm(w["text"])
        if said == target:
            return True
        if not target.startswith(said):
            return False
    return False


def resolve_word(anchor, words):
    if "word_id" in anchor:
        hits = [w for w in words if w.get("id") == anchor["word_id"]]
    elif isinstance(anchor.get("word"), str) and anchor["word"].strip():
        hits = [w for i, w in enumerate(words) if spoken_at(words, i, anchor["word"])]
    else:
        return None, "speech_anchor needs word_id or word"
    occurrence = anchor.get("occurrence", 1)
    if not isinstance(occurrence, int) or isinstance(occurrence, bool) or occurrence < 1:
        return None, "occurrence must be a positive integer"
    if len(hits) < occurrence:
        return None, "referenced word was not found"
    return hits[occurrence - 1], None


def validate(data, base, words=None):
    if not isinstance(data, dict):
        return ["Root must be an object."]
    errors = []
    duration, scenes = data.get("duration"), data.get("scenes")
    if not number(duration) or duration <= 0:
        errors.append("duration must be finite and positive.")
    if not isinstance(scenes, list) or not scenes:
        return errors + ["scenes must be a non-empty list."]
    word_offset = data.get("word_offset", 0)
    if not number(word_offset):
        errors.append("word_offset must be a number.")
        word_offset = 0
    video = data.get("video", {})
    for key in ("fade_in", "fade_out"):
        if key in video and (not number(video[key]) or video[key] < 0):
            errors.append(f"video.{key} must be a nonnegative number of seconds.")
    ids, previous, before_previous = set(), None, None
    for i, scene in enumerate(scenes):
        label = f"Scene {i + 1}"
        if not isinstance(scene, dict):
            errors.append(f"{label}: must be an object.")
            continue
        identity = scene.get("id")
        if not isinstance(identity, str) or not identity.strip():
            errors.append(f"{label}: missing string id.")
        elif identity in ids:
            errors.append(f"{label}: duplicate id {identity}.")
        else:
            ids.add(identity)
        start, end, transition = scene.get("start"), scene.get("end"), scene.get("transition_in", 0)
        if not number(start) or not number(end) or start < 0 or end <= start:
            errors.append(f"{label}: invalid start/end.")
            previous = None
            continue
        if not number(transition) or transition < 0:
            errors.append(f"{label}: transition_in must be nonnegative.")
            transition = 0
        if i == 0:
            if abs(start) > EPS or transition > EPS:
                errors.append(f"{label}: first scene must start at 0 without a transition.")
        elif previous:
            expected = previous["end"] - transition
            if abs(start - expected) > EPS:
                errors.append(f"{label}: gap or overlap differs from transition_in; expected start {expected:.3f}, got {start:.3f}.")
            if transition >= min(previous["end"] - previous["start"], end - start) - EPS:
                errors.append(f"{label}: transition_in consumes a whole scene.")
            if before_previous and start < before_previous["end"] - EPS:
                errors.append(f"{label}: three scenes overlap; split or shorten a transition.")
        asset = scene.get("asset")
        if asset is not None:
            if not isinstance(asset, str) or not asset.strip():
                errors.append(f"{label}: asset must be a non-empty local path.")
            elif not (base / asset).is_file():
                errors.append(f"{label}: asset not found: {asset}")
            elif Path(asset).suffix.lower() in VIDEO_EXT:
                clip_in = scene.get("clip_in", 0)
                if not number(clip_in) or clip_in < 0:
                    errors.append(f"{label}: clip_in must be a nonnegative number of seconds.")
                else:
                    length = clip_length(base / asset)
                    if length is not None and clip_in + (end - start) > length + .05:
                        errors.append(f"{label}: clip needs {clip_in + end - start:.2f}s of {asset} "
                                      f"but it lasts {length:.2f}s; the last frame would freeze.")
        if "clip_in" in scene and not (isinstance(asset, str) and Path(asset).suffix.lower() in VIDEO_EXT):
            errors.append(f"{label}: clip_in only applies to a video asset.")
        zoom = scene.get("zoom", 0)
        if not number(zoom) or not 0 <= zoom <= .5:
            errors.append(f"{label}: zoom must be between 0 and 0.5.")
        for key in ("center_x", "center_y"):
            value = scene.get(key, .5)
            if not number(value) or not 0 <= value <= 1:
                errors.append(f"{label}: {key} must be between 0 and 1.")
        anchor = scene.get("speech_anchor")
        if number(anchor):
            if not start <= anchor < end:
                errors.append(f"{label}: numeric speech_anchor must lie within the scene.")
        elif isinstance(anchor, dict):
            if words is None:
                errors.append(f"{label}: word-cued speech_anchor requires --words or word_file.")
            else:
                word, error = resolve_word(anchor, words)
                if error:
                    errors.append(f"{label}: {error}.")
                else:
                    tolerance, offset = anchor.get("tolerance", .35), anchor.get("offset", 0)
                    if not number(tolerance) or tolerance < 0 or not number(offset):
                        errors.append(f"{label}: invalid speech_anchor tolerance/offset.")
                    elif abs((start + transition / 2) - (word["start"] + word_offset + offset)) > tolerance + EPS:
                        errors.append(f"{label}: visual transition midpoint {start + transition / 2:.3f}s misses '{word['text']}' at {word['start'] + word_offset + offset:.3f}s by more than {tolerance:.3f}s.")
        elif anchor is not None:
            errors.append(f"{label}: speech_anchor must be a number or word cue object.")
        before_previous, previous = previous, scene
    if previous and number(duration) and abs(previous["end"] - duration) > EPS:
        errors.append(f"Last scene ends at {previous['end']}, not duration {duration}.")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("--words", type=Path, help="Word timestamps JSON; overrides timeline word_file")
    args = parser.parse_args()
    try:
        data = json.loads(args.timeline.read_text(encoding="utf-8"))
        base = args.timeline.resolve().parent
        word_path = args.words or (base / data["word_file"] if isinstance(data, dict) and data.get("word_file") else None)
        errors = validate(data, base, load_words(word_path) if word_path else None)
    except (OSError, ValueError, KeyError) as exc:
        errors = [str(exc)]
    print(json.dumps({"ok": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

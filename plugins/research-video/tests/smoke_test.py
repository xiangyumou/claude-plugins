#!/usr/bin/env python3
"""Smoke test for the research-proposal-video scripts, on synthetic media (no models, no network).

Checks a few pure functions and check_timeline's errors, then runs the default pipeline on a
made-up 13-second film: place_audio --lufs -> make_subtitles -> build_timeline -> render_video
-> check_output --ref, and requires check_output to pass with the voice within 10 ms. Then
sync_to_footage lays a recording onto "footage" spoken slower and later, and must land every
phrase within 40 ms, and pauses.py must reset each pause by its punctuation. shoot_cards runs too when Playwright is installed. Needs Python 3, NumPy,
Pillow and FFmpeg.

  python3 plugins/research-video/tests/smoke_test.py
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "research-proposal-video" / "scripts"
sys.dont_write_bytecode = True
sys.path.insert(0, str(SCRIPTS))
from align_words import spoken  # noqa: E402
from build_timeline import find_word  # noqa: E402
from check_timeline import spoken_at, validate  # noqa: E402
from make_subtitles import is_cjk, sentences  # noqa: E402

RATE = 48000
SCRIPT = ("Accuracy rose to {3.5%|three point five percent} with Dr. Lee at U.K. sites. "
          "The team will test it in clinics next year.")
SPOKEN = ("Accuracy rose to three point five percent with Dr Lee at U K sites. "
          "The team will test it in clinics next year.")


def words_of(texts, start=0.0):
    return [{"id": f"w{k + 1:04d}", "text": t, "start": start + k, "end": start + k + .5} for k, t in enumerate(texts)]


def unit_checks():
    assert sentences(SCRIPT) == [SCRIPT.split(" The")[0], "The" + SCRIPT.split(" The")[1]], sentences(SCRIPT)
    assert sentences("第一句。第二句！") == ["第一句。", "第二句！"]
    assert sentences("He said no. Then left.") == ["He said no.", "Then left."]
    assert sentences("See No. 5 first. Then go.") == ["See No. 5 first.", "Then go."]
    assert spoken(SCRIPT).startswith("Accuracy rose to three point five percent with Dr. Lee")
    assert not is_cjk("An interview with 李明 about the lab") and is_cjk("我们用 AI 看超声")
    w = words_of("look in to the rapist into 超 声".split())
    assert [i for i in range(len(w)) if spoken_at(w, i, "into")] == [5]
    assert not any(spoken_at(w, i, "therapist") for i in range(len(w)))
    assert [i for i in range(len(w)) if spoken_at(w, i, "超声")] == [6]
    try:
        find_word(words_of("我 们 用 朝 声 看".split()), "超声", 0, 0)
        raise AssertionError("found a word that is not there")
    except SystemExit as e:
        assert "朝声" in str(e), e


def timeline_checks(d):
    Image.new("RGB", (64, 36)).save(d / "a.png")
    words = words_of(["one", "two", "three"])
    good = {"duration": 4, "scenes": [
        {"id": "a", "asset": "a.png", "start": 0, "end": 2.2},
        {"id": "b", "asset": "a.png", "start": 1.8, "end": 4, "transition_in": .4,
         "speech_anchor": {"word": "three", "tolerance": .1}}]}
    assert validate(good, d, words) == [], validate(good, d, words)
    bad = json.loads(json.dumps(good))
    bad["scenes"][1].update(start=2.0, asset="missing.png", speech_anchor={"word": "four"})
    bad["duration"] = 5
    errors = " ".join(validate(bad, d, words))
    for expected in ("expected start 1.800", "asset not found", "not found", "not duration 5"):
        assert expected in errors, errors
    (d / "bad.json").write_text(json.dumps(bad))
    result = subprocess.run([sys.executable, str(SCRIPTS / "check_timeline.py"), str(d / "bad.json")],
                            capture_output=True, text=True)
    assert result.returncode == 1 and not json.loads(result.stdout)["ok"], result.stdout


def write_wav(path, x):
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(RATE)
        f.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


def syllables(words, length):
    """A voice-like track: a harmonic burst with a pitch glide for every word, silence between."""
    x = np.zeros(round(length * RATE))
    rng = np.random.default_rng(1)
    for w in words:
        a, b = round(w["start"] * RATE), round(w["end"] * RATE)
        t = np.arange(b - a) / RATE
        f0 = rng.uniform(110, 220) * (1 + .2 * t)
        phase = 2 * np.pi * np.cumsum(f0) / RATE
        x[a:b] = sum(np.sin(h * phase) / h for h in range(1, 6)) * np.sin(np.pi * t / t[-1]) * .3
    return x


def run(*args):
    result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise SystemExit(f"FAILED: {' '.join(map(str, args))}\n{result.stdout}\n{result.stderr}")
    return result


def pipeline(d):
    texts = [t.strip(".") for t in SPOKEN.split()]
    intro = [{"text": t, "start": k * 1.0, "end": k * 1.0 + .5} for k, t in enumerate(texts[:4])]   # "presenter"
    narration = [{"text": t, "start": .2 + k * .4, "end": .5 + k * .4} for k, t in enumerate(texts[4:])]
    write_wav(d / "intro.wav", syllables(intro, 4))
    write_wav(d / "voice.wav", syllables(narration, 8))
    words = [dict(w, id=f"w{k + 1:04d}", start=round(w["start"] + (.5 if k < 4 else 4.8), 3),
                  end=round(w["end"] + (.5 if k < 4 else 4.8), 3)) for k, w in enumerate(intro + narration)]
    (d / "words.json").write_text(json.dumps({"words": words}))
    (d / "script.txt").write_text(SCRIPT)
    t = np.arange(14 * RATE) / RATE
    write_wav(d / "music.wav", .1 * (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 277 * t)))
    for k, name in enumerate(["intro", "team", "clinic"]):
        Image.new("RGB", (1920, 1080), (40 + 70 * k, 90, 160 - 40 * k)).save(d / f"{name}.png")
    plan = {"words": "words.json", "transition": .36, "tail": 1.5,
            "video": {"width": 640, "height": 360, "fps": 24, "fade_in": .3}, "asset_pattern": "{id}.png",
            "scenes": [{"id": "intro"}, {"id": "team", "word": "team"}, {"id": "clinic", "word": "clinics"}]}
    (d / "plan.json").write_text(json.dumps(plan))

    run(SCRIPTS / "place_audio.py", d / "voice_full.wav", "--lufs", -16,          # ends with the last piece
        f"{d / 'intro.wav'}@0.5", f"{d / 'voice.wav'}@4.8")
    run(SCRIPTS / "make_subtitles.py", d / "script.txt", d / "words.json", d / "subtitles.srt")
    srt = (d / "subtitles.srt").read_text()
    assert "|" not in srt and "three point" not in srt and "3.5%" in srt and "Dr. Lee" in srt, srt
    run(SCRIPTS / "build_timeline.py", d / "plan.json", d / "timeline.json")
    render = run(SCRIPTS / "render_video.py", d / "timeline.json", d / "film.mp4", "--voice", d / "voice_full.wav",
                 "--music", d / "music.wav", "--subtitles", d / "subtitles.srt")
    assert "WARNING" not in render.stderr, render.stderr
    check = [sys.executable, SCRIPTS / "check_output.py", d / "film.mp4", "--max-duration", 120, "--max-mb", 50,
             "--ref", d / "voice_full.wav"]
    report = json.loads(subprocess.run(list(map(str, check)), capture_output=True, text=True).stdout)
    assert report["ok"] and report["sync"], report
    assert all(abs(c["offset_ms"]) <= 10 for c in report["sync"]), report["sync"]

    sync(d)
    paced(d)
    if importlib.util.find_spec("playwright"):
        (d / "cards.html").write_text(
            "<style>body{margin:0}.card{width:1920px;height:1080px;font:80px sans-serif}</style>"
            "<div class=card id=c></div><script>const SCENES=['a','b'];"
            "function render(id){document.getElementById('c').textContent='Card '+id}</script>")
        run(SCRIPTS / "shoot_cards.py", d / "cards.html", d / "cards")
        assert sorted(p.name for p in (d / "cards").glob("*.png")) == ["a.png", "b.png"]
        return "pipeline ok (with shoot_cards)"
    return "pipeline ok (shoot_cards skipped: no Playwright)"


def sync(d):
    """A clean recording (with trailing silence) laid onto footage spoken 8 % slower, 0.4 s later,
    with longer pauses; every phrase onset must land within 40 ms of the footage's."""
    rec = [{"start": s, "end": s + .3} for s in (.3, .7, 1.1, 1.5, 2.4, 2.8, 3.2, 4.1, 4.5, 4.9)]
    foot = [{"start": .4 + 1.08 * w["start"] + .25 * (w["start"] > 2) + .15 * (w["start"] > 4),
             "end": .4 + 1.08 * w["end"] + .25 * (w["start"] > 2) + .15 * (w["start"] > 4)} for w in rec]
    rng = np.random.default_rng(2)
    write_wav(d / "note.wav", syllables(rec, 6.5))
    write_wav(d / "take.wav", syllables(foot, 7) + .003 * rng.standard_normal(7 * RATE))
    result = run(SCRIPTS / "sync_to_footage.py", d / "take.wav", d / "note.wav", d / "synced.wav", "--clip-out", 7)
    assert "WARNING" not in result.stderr, result.stderr
    report = json.loads((d / "synced.sync.json").read_text())
    onsets = sorted(p["clip_onset"] for p in report["phrases"])
    expected = [w["start"] for w, r in zip(foot, rec) if any(abs(r["start"] - p["rec_speech"][0]) < .02
                                                             for p in report["phrases"])]
    assert len(onsets) == len(expected) >= 3, (onsets, expected)
    assert all(abs(a - b) < .04 for a, b in zip(onsets, expected)), (onsets, expected)


def paced(d):
    """pauses.py: set sentence pauses, cap comma and unpunctuated ones; the words must still sit
    on the sound in the new track."""
    times = [(.2, .5), (.9, 1.2), (1.3, 1.6), (1.8, 2.1), (2.5, 2.8), (3.3, 3.6), (3.7, 4.0)]
    words = [{"id": f"w{k + 1:04d}", "text": t, "start": a, "end": b}
             for k, (t, (a, b)) in enumerate(zip("one two three four five six seven".split(), times))]
    (d / "p_words.json").write_text(json.dumps({"words": words}))
    (d / "p_script.txt").write_text("One two three. Four five, six seven.")
    write_wav(d / "p_voice.wav", syllables(words, 4.3))
    run(SCRIPTS / "pauses.py", d / "p_voice.wav", d / "p_words.json", d / "p_script.txt", d / "p_paced.wav",
        "--sentence", .5, "--comma", .3, "--none", .1, "--words-out", d / "p_paced.json")
    new = json.loads((d / "p_paced.json").read_text())["words"]
    gaps = [round(b["start"] - a["end"], 3) for a, b in zip(new, new[1:])]
    assert gaps == [.1, .1, .5, .1, .3, .1], gaps
    x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(d / "p_paced.wav"), "-ac", "1", "-f", "f32le",
                                      "-ar", str(RATE), "-"], capture_output=True, check=True).stdout, np.float32)
    assert abs(len(x) / RATE - 3.8) < .002, len(x) / RATE
    rms = lambda a, b: float(np.sqrt(np.mean(x[round(a * RATE):round(b * RATE)] ** 2)))
    assert all(rms(w["start"] + .05, w["end"] - .05) > .05 for w in new), [rms(w["start"], w["end"]) for w in new]
    assert all(rms(a["end"] + .01, b["start"] - .01) < .001 for a, b in zip(new, new[1:]))


def main():
    unit_checks()
    print("unit checks ok")
    with tempfile.TemporaryDirectory() as tmp:
        timeline_checks(Path(tmp))
        print("check_timeline errors ok")
        print(pipeline(Path(tmp)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Smoke test for the research-proposal-video scripts, on synthetic media (no models, no network).

Checks a few pure functions, then runs the default pipeline on a made-up 14-second film:
place_audio --lufs -> make_subtitles -> build_timeline -> render_video -> check_output --ref,
and requires check_output to pass with the voice within 10 ms. shoot_cards runs too when
Playwright is installed. Needs Python 3, NumPy, Pillow and FFmpeg.

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
from build_timeline import find_word  # noqa: E402
from check_timeline import spoken_at  # noqa: E402
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

    run(SCRIPTS / "place_audio.py", d / "voice_full.wav", "--duration", 14, "--lufs", -16,
        f"{d / 'intro.wav'}@0.5", f"{d / 'voice.wav'}@4.8")
    run(SCRIPTS / "make_subtitles.py", d / "script.txt", d / "words.json", d / "subtitles.srt")
    srt = (d / "subtitles.srt").read_text()
    assert "|" not in srt and "three point" not in srt and "3.5%" in srt and "Dr. Lee" in srt, srt
    run(SCRIPTS / "build_timeline.py", d / "plan.json", d / "timeline.json")
    run(SCRIPTS / "render_video.py", d / "timeline.json", d / "film.mp4", "--voice", d / "voice_full.wav",
        "--music", d / "music.wav", "--subtitles", d / "subtitles.srt")
    check = [sys.executable, SCRIPTS / "check_output.py", d / "film.mp4", "--max-duration", 120, "--max-mb", 50,
             "--ref", d / "voice_full.wav"]
    report = json.loads(subprocess.run(list(map(str, check)), capture_output=True, text=True).stdout)
    assert report["ok"] and report["sync"], report
    assert all(abs(c["offset_ms"]) <= 10 for c in report["sync"]), report["sync"]

    if importlib.util.find_spec("playwright"):
        (d / "cards.html").write_text(
            "<style>body{margin:0}.card{width:1920px;height:1080px;font:80px sans-serif}</style>"
            "<div class=card id=c></div><script>const SCENES=['a','b'];"
            "function render(id){document.getElementById('c').textContent='Card '+id}</script>")
        run(SCRIPTS / "shoot_cards.py", d / "cards.html", d / "cards")
        assert sorted(p.name for p in (d / "cards").glob("*.png")) == ["a.png", "b.png"]
        return "pipeline ok (with shoot_cards)"
    return "pipeline ok (shoot_cards skipped: no Playwright)"


def main():
    unit_checks()
    print("unit checks ok")
    with tempfile.TemporaryDirectory() as tmp:
        print(pipeline(Path(tmp)))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Lay a separate recording of the same words onto on-camera footage, phrase by phrase, in lip sync.

Typical case: the presenter's on-camera take has bad audio (room echo, music bed, noise) but they
also sent a clean voice note of the same sentences. The recording is split into phrases at its
pauses; an MFCC + DTW map from the recording to the footage's own audio gives, for each phrase,
where its first and last speech sound on camera; each phrase is then time-stretched (atempo,
clamped) to span the same stretch and placed at an exact sample offset. A second DTW pass
measures the remaining offset at every phrase; --asr-check adds an independent check that compares
Whisper word start times in the footage and in the result, word by word.

  python sync_to_footage.py presenter.mp4 note.opus work/intro_voice.wav \
      --clip-in 0.9 --clip-out 9.1 --rec-out 6.75 --lufs -16 --asr-check
  # phrases are split at long pauses, then further wherever one tempo cannot follow the lips;
  # to override, give cut points (recording seconds) yourself:
  python sync_to_footage.py presenter.mp4 note.opus out.wav --clip-in 0.9 --clip-out 9.1 --splits 1.1,2.6,5.36

The output WAV lasts exactly clip_out - clip_in and starts at the clip's first frame, so it lines
up with a video cut made with the same in/out points. Mute the footage's own audio in the edit.
A JSON plan (pieces, tempos, residual offsets) is written next to the output; the pieces can be
re-placed by hand with place_audio.py. Needs only NumPy and FFmpeg.
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
from place_audio import place  # noqa: E402

SR, HOP, WIN = 16000, 160, 400   # 10 ms hop, 25 ms window


def load(path, start=0.0, end=None, ffmpeg="ffmpeg"):
    import subprocess
    cmd = [ffmpeg, "-v", "error", "-ss", str(start), "-i", str(path)]
    if end is not None:
        cmd += ["-t", str(end - start)]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def frames(x):
    n = 1 + max(0, (len(x) - WIN) // HOP)
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    return np.pad(x, (0, WIN))[idx] * np.hanning(WIN)


def mel_bank(n_mels=40, n_fft=512, fmin=80, fmax=7600):
    mel = lambda f: 2595 * np.log10(1 + f / 700)
    inv = lambda m: 700 * (10 ** (m / 2595) - 1)
    pts = inv(np.linspace(mel(fmin), mel(fmax), n_mels + 2))
    bins = np.fft.rfftfreq(n_fft, 1 / SR)
    bank = np.zeros((n_mels, len(bins)))
    for i in range(n_mels):
        lo, mid, hi = pts[i:i + 3]
        bank[i] = np.clip(np.minimum((bins - lo) / (mid - lo), (hi - bins) / (hi - mid)), 0, None)
    return bank


def features(x):
    """Cepstral-mean-normalised MFCC 1-19 plus deltas, one row per 10 ms."""
    spec = np.abs(np.fft.rfft(frames(x), 512)) ** 2
    logmel = np.log(spec @ mel_bank().T + 1e-8)
    k = np.arange(logmel.shape[1])
    dct = np.cos(np.pi / logmel.shape[1] * (k[None, :] + .5) * np.arange(20)[:, None])
    c = (logmel @ dct.T)[:, 1:]
    c -= c.mean(axis=0)
    d = np.gradient(c, axis=0)
    f = np.hstack([c, 2 * d])
    return f / (np.linalg.norm(f, axis=1, keepdims=True) + 1e-8)


def energy_db(x):
    e = 10 * np.log10((frames(x) ** 2).mean(axis=1) + 1e-10)
    return e - np.percentile(e, 95)


def dtw_path(a, b):
    """DTW on cosine distance with the symmetric2 step pattern (a diagonal step costs twice a
    horizontal or vertical one), so the stretch of `b` with no match in `a` - room tone, a music
    bed, a breath before the first word - is absorbed by cheap horizontal runs instead of bending
    the whole path. Row-vectorised; returns (i, j) index pairs from (0, 0) to the ends."""
    cost = 1 - a @ b.T
    n, m = cost.shape
    acc = np.empty((n, m))
    acc[0] = np.cumsum(cost[0])
    for i in range(1, n):
        prev = acc[i - 1]
        diag = np.concatenate([[np.inf], prev[:-1]])
        best = np.minimum(prev + cost[i], diag + 2 * cost[i])      # up, or diagonal at double weight
        csum = np.cumsum(cost[i])
        acc[i] = np.minimum.accumulate(best - csum) + csum         # then runs to the right
    i, j, path = n - 1, m - 1, [(n - 1, m - 1)]
    while i or j:
        if not i:
            j -= 1
        elif not j:
            i -= 1
        else:
            _, i, j = min((acc[i - 1, j - 1] + 2 * cost[i, j], i - 1, j - 1),
                          (acc[i - 1, j] + cost[i, j], i - 1, j), (acc[i, j - 1] + cost[i, j], i, j - 1))
        path.append((i, j))
    return np.array(path[::-1])


def mapper(path):
    """Function: time in the first signal -> time in the second, via the DTW path (median per frame)."""
    xs = np.unique(path[:, 0])
    ys = np.array([np.median(path[path[:, 0] == x, 1]) for x in xs])
    return lambda t: float(np.interp(t * SR / HOP, xs, ys)) * HOP / SR


def speech_bounds(db, threshold):
    on = np.nonzero(db > threshold)[0]
    return (on[0] * HOP / SR, (on[-1] + 1) * HOP / SR) if len(on) else (None, None)


def pauses(db, threshold, min_pause):
    """(middle, length) in seconds of every quiet run of at least min_pause between speech."""
    speech = db > threshold
    found, run = [], 0
    for k in range(int(np.argmax(speech)), len(speech)):
        if not speech[k]:
            run += 1
            continue
        if run * HOP / SR >= min_pause:
            found.append(((k - run / 2) * HOP / SR, run * HOP / SR))
        run = 0
    return found


def fit_phrase(a, b, db, threshold, to_foot, tempo_range):
    """Fit one phrase: its speech onset lands on the matching onset on camera, and one atempo best
    follows the DTW map through the rest of it. Returns None for a silent piece."""
    seg = db[int(a * SR / HOP):int(b * SR / HOP)]
    on, off = speech_bounds(seg, -99 if not (seg > threshold).any() else threshold)
    if on is None or not (seg > threshold).any():
        return None
    on, off = a + on, a + off
    von = to_foot(on)
    # Fit on voiced frames only: inside pauses the DTW map is arbitrary.
    ts = np.array([t for t in np.arange(on, off, .02) if db[min(len(db) - 1, int(t * SR / HOP))] > threshold])
    dv = np.array([to_foot(t) for t in ts]) - von
    dt = ts - on
    slope = float((dt * dv).sum() / max((dt * dt).sum(), 1e-9))          # clip s per recording s
    wanted = 1 / max(slope, 1e-3)
    tempo = round(min(tempo_range[1], max(tempo_range[0], wanted)), 3)
    deviation = float(np.percentile(np.abs(dt / tempo - dv), 90)) if len(ts) else 0.0
    return {"a": a, "b": b, "on": on, "off": off, "von": von, "voff": to_foot(off), "wanted": wanted,
            "tempo": tempo, "start": von - (on - a) / tempo, "deviation": deviation}


def plan_phrases(db, threshold, to_foot, tempo_range, length, coarse_pause, min_pause, min_phrase, max_dev):
    """Split at long pauses, then keep splitting any phrase that drifts more than max_dev from the
    footage at its best internal pause (the presenter paused on camera where the recording did not,
    or spoke a stretch faster); returns fitted phrases."""
    quiet = pauses(db, threshold, min_pause)
    cuts = [c for c, n in quiet if n >= coarse_pause and min_phrase <= c <= length - min_phrase]
    edges, done = [0.0] + cuts + [length], []
    todo = [(a, b) for a, b in zip(edges, edges[1:])]
    while todo:
        a, b = todo.pop(0)
        fit = fit_phrase(a, b, db, threshold, to_foot, tempo_range)
        if fit is None:
            continue
        if fit["deviation"] > max_dev:
            options = []
            for c, _ in quiet:
                if a + min_phrase <= c <= b - min_phrase:
                    left, right = (fit_phrase(a, c, db, threshold, to_foot, tempo_range),
                                   fit_phrase(c, b, db, threshold, to_foot, tempo_range))
                    if left and right:
                        options.append((max(left["deviation"], right["deviation"]), c))
            if options and min(options)[0] < fit["deviation"] - .01:
                c = min(options)[1]
                todo[:0] = [(a, c), (c, b)]
                continue
        done.append(fit)
    return sorted(done, key=lambda f: f["a"])


def asr_check(foot, out, model_name, language=None):
    """Word-by-word start-time differences (result - footage) from faster-whisper; None if unavailable."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("WARNING: --asr-check needs faster-whisper in this Python; skipped", file=sys.stderr)
        return None
    model = WhisperModel(model_name, compute_type="int8")
    norm = lambda w: "".join(c for c in w.lower() if c.isalnum())

    def words(x):
        segments, _ = model.transcribe(x, word_timestamps=True, language=language)
        return [(norm(w.word), w.start) for seg in segments for w in seg.words if norm(w.word)]
    a, b = words(foot), words(out)
    # Pair words in order, skipping over the odd mis-heard word on either side.
    pairs, j = [], 0
    for text, start in a:
        k = next((k for k in range(j, min(j + 3, len(b))) if b[k][0] == text), None)
        if k is not None:
            pairs.append((text, round(start, 2), round(b[k][1] - start, 2)))
            j = k + 1
    if not pairs:
        print("ASR check: no words matched; listen to the result", file=sys.stderr)
        return {"matched": 0}
    diffs = np.array([d for *_, d in pairs])
    late = [f"{t} {d:+.2f}s" for t, _, d in pairs if abs(d) > .12]
    print(f"ASR check: {len(pairs)}/{len(a)} words matched, median {np.median(diffs):+.2f}s, "
          f"worst {diffs[np.argmax(np.abs(diffs))]:+.2f}s" + (f"; over 0.12 s: {', '.join(late)}" if late else ""))
    print("  (one outlier on a single word is usually Whisper, not the edit; several in a row is a real drift)")
    return {"matched": len(pairs), "of": len(a), "median_s": round(float(np.median(diffs)), 3),
            "words": [{"word": t, "footage_start": s0, "diff_s": d} for t, s0, d in pairs]}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("footage", type=Path, help="On-camera video (or its audio)")
    parser.add_argument("recording", type=Path, help="Separate recording of the same words")
    parser.add_argument("output", type=Path, help="WAV, exactly clip_out - clip_in seconds")
    parser.add_argument("--clip-in", type=float, default=0.0, help="Footage in point used in the edit (s)")
    parser.add_argument("--clip-out", type=float, required=True, help="Footage out point used in the edit (s)")
    parser.add_argument("--rec-in", type=float, default=0.0, help="Recording in point (s)")
    parser.add_argument("--rec-out", type=float, help="Recording out point (s); default: end")
    parser.add_argument("--splits", help="Comma-separated phrase cut points in recording seconds (overrides auto)")
    parser.add_argument("--coarse-pause", type=float, default=0.2, help="Pause (s) that always starts a new phrase")
    parser.add_argument("--min-pause", type=float, default=0.04, help="Shortest pause (s) a drifting phrase may be cut at")
    parser.add_argument("--min-phrase", type=float, default=0.5, help="Shortest phrase (s)")
    parser.add_argument("--max-drift", type=float, default=0.06,
                        help="Split a phrase further if one atempo leaves its voiced frames more than this (s) off (90th pct)")
    parser.add_argument("--threshold", type=float, default=-32, help="Speech level (dB below the 95th percentile)")
    parser.add_argument("--tempo-range", default="0.85,1.2", help="Allowed atempo (min,max)")
    parser.add_argument("--lufs", type=float, help="Level the result to this integrated loudness")
    parser.add_argument("--asr-check", nargs="?", const="small", metavar="MODEL",
                        help="Independent check: compare faster-whisper word starts in the footage and the result")
    parser.add_argument("--language", help="Spoken language code for --asr-check (e.g. en); default: detect")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    tempo_range = tuple(map(float, args.tempo_range.split(",")))
    clip_len = args.clip_out - args.clip_in
    if clip_len <= 0:
        parser.error("--clip-out must be after --clip-in")

    foot = load(args.footage, args.clip_in, args.clip_out, args.ffmpeg)
    rec = load(args.recording, args.rec_in, args.rec_out, args.ffmpeg)
    rec_end = args.rec_in + len(rec) / SR
    rec_db = energy_db(rec)
    foot_feat = features(foot)
    # The recording's speech span (plus a margin) is matched against the whole clip.
    r0, r1 = speech_bounds(rec_db, args.threshold)
    if r0 is None:
        parser.error("no speech found in the recording; lower --threshold or check --rec-in/--rec-out")
    r0, r1 = max(0, r0 - .1), min(len(rec) / SR, r1 + .1)
    ra, rb = int(r0 * SR / HOP), int(r1 * SR / HOP)
    to_foot_local = mapper(dtw_path(features(rec)[ra:rb], foot_feat))
    to_foot = lambda t: to_foot_local(t - r0)               # recording-local s -> clip s

    length = len(rec) / SR
    if args.splits:
        edges = [0.0] + [float(c) - args.rec_in for c in args.splits.split(",")] + [length]
        fits = [f for a, b in zip(edges, edges[1:]) if (f := fit_phrase(a, b, rec_db, args.threshold, to_foot, tempo_range))]
    else:
        fits = plan_phrases(rec_db, args.threshold, to_foot, tempo_range, length, args.coarse_pause,
                            args.min_pause, args.min_phrase, args.max_drift)
    pieces, plan, prev_end = [], [], 0.0
    for f in fits:
        a, start = f["a"], f["start"]
        if start < 0:
            a, start = a - start * f["tempo"], 0.0     # trim leading silence rather than start before the clip
        if start < prev_end - 0.05:
            print(f"WARNING: phrase at {a + args.rec_in:.2f}s overlaps the previous one by "
                  f"{prev_end - start:.2f}s; consider --splits", file=sys.stderr)
        prev_end = start + (f["b"] - a) / f["tempo"]
        pieces.append({"path": args.recording, "start": round(start, 4), "in": round(a + args.rec_in, 3),
                       "out": round(f["b"] + args.rec_in, 3), "tempo": f["tempo"], "gain": 0.0, "fade": 0.01})
        plan.append({"rec": [round(a + args.rec_in, 3), round(f["b"] + args.rec_in, 3)],
                     "rec_speech": [round(f["on"] + args.rec_in, 3), round(f["off"] + args.rec_in, 3)],
                     "clip_speech": [round(f["von"], 3), round(f["voff"], 3)],
                     "tempo": f["tempo"], "tempo_wanted": round(f["wanted"], 3), "clip_start": round(start, 4),
                     "clip_onset": round(start + (f["on"] - a) / f["tempo"], 3),
                     "max_drift_s": round(f["deviation"], 3)})
    if not pieces:
        parser.error("no phrases found")
    place(pieces, clip_len, args.output, ffmpeg=args.ffmpeg, quiet=True, mix_lufs=args.lufs)

    # Verify: map the result back onto the footage and measure each phrase's remaining offset.
    out = load(args.output, ffmpeg=args.ffmpeg)
    o0, o1 = speech_bounds(energy_db(out), args.threshold)
    o0, o1 = max(0, o0 - .1), min(clip_len, o1 + .1)
    back_local = mapper(dtw_path(features(out)[int(o0 * SR / HOP):int(o1 * SR / HOP)], foot_feat))
    back = lambda t: back_local(t - o0)
    worst = 0.0
    for p in plan:
        on_clip = p["clip_onset"]
        residual = back(on_clip) - on_clip
        p["residual_s"] = round(residual, 3)
        worst = max(worst, abs(residual))
        clamp = "" if p["tempo"] == p["tempo_wanted"] else f" (wanted {p['tempo_wanted']}, clamped)"
        print(f"rec {p['rec'][0]:6.2f}-{p['rec'][1]:6.2f} -> clip {p['clip_start']:6.3f}  "
              f"speech on camera {p['clip_speech'][0]:.2f}-{p['clip_speech'][1]:.2f}  "
              f"atempo {p['tempo']}{clamp}  drift {p['max_drift_s'] * 1000:.0f} ms  onset check {residual * 1000:+.0f} ms")
    asr = asr_check(foot, out, args.asr_check, args.language) if args.asr_check else None
    spec = [f"{args.recording}@{p['start']}:in={p['in']},out={p['out']},tempo={p['tempo']}" for p in pieces]
    report = {"footage": str(args.footage), "clip_in": args.clip_in, "clip_out": args.clip_out,
              "recording": str(args.recording), "rec_range": [args.rec_in, round(rec_end, 3)],
              "phrases": plan, "worst_residual_s": round(worst, 3), "asr_check": asr,
              "place_audio_pieces": spec}
    Path(args.output).with_suffix(".sync.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{args.output}  {clip_len:.3f} s  worst residual {worst * 1000:.0f} ms"
          + ("  -> CHECK: over 80 ms; try --splits or watch the lips" if worst > .08 else ""))


if __name__ == "__main__":
    main()

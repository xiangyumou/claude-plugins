#!/usr/bin/env python3
"""Check a finished MP4 before it is delivered.

Reports per-stream durations (a video and audio track that differ by more than a frame or two is
the usual sign of a mis-placed voice track), file size and duration limits, codec/pixel format,
integrated loudness and true peak, and when the audio first becomes audible. With --ref, it also
cross-correlates a reference voice file against the film's audio at several points, which catches
a constant sync offset (the whole film early/late) or drift that a quick look will miss.

  python check_output.py outputs/film.mp4 --max-duration 120 --max-mb 50
  # the narration WAV was laid in at 7.8 s; confirm it is still there, sample-accurate:
  python check_output.py outputs/film.mp4 --ref work/voice.wav --ref-offset 7.8
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np

SR = 8000


def probe(path, ffprobe):
    out = subprocess.run([ffprobe, "-v", "error", "-show_entries",
                          "format=duration,size:stream=codec_type,codec_name,width,height,pix_fmt,"
                          "r_frame_rate,duration,sample_rate,channels", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def pcm(path, ffmpeg, start=0.0, duration=None):
    cmd = [ffmpeg, "-v", "error", "-ss", str(start), "-i", str(path)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += ["-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32)


def loudness(path, ffmpeg):
    err = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-vn", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", summary)
    return (float(i.group(1)) if i else None), (float(tp.group(1)) if tp and tp.group(1) != "-inf" else None)


def first_sound(x, threshold_db=-40.0):
    """Seconds until a 20 ms window first exceeds threshold_db RMS."""
    hop = SR // 50
    n = len(x) // hop
    if not n:
        return None
    rms = np.sqrt((x[:n * hop].reshape(n, hop) ** 2).mean(axis=1) + 1e-12)
    loud = np.nonzero(20 * np.log10(rms) > threshold_db)[0]
    return round(float(loud[0] * hop / SR), 2) if len(loud) else None


def lag_ms(ref, film, max_lag):
    """Lag (ms) of ref inside film: film[k] ~ ref[k - lag]; film is ref's window padded by max_lag each side."""
    ref = ref - ref.mean()
    film = film - film.mean()
    n = 1 << (len(ref) + len(film)).bit_length()
    corr = np.fft.irfft(np.fft.rfft(film, n) * np.conj(np.fft.rfft(ref, n)), n)
    k = int(np.argmax(corr[:len(film) - len(ref) + 1]))
    peak = corr[k] / (np.linalg.norm(ref) * np.linalg.norm(film[k:k + len(ref)]) + 1e-12)
    return round((k - max_lag) * 1000 / SR), round(float(peak), 2)


def sync_check(film, ref_path, offset, ffmpeg, points=6, window=4.0, max_lag=2.5):
    """Up to `points` windows spread over the part of ref that lies inside the film (shorter windows
    in a short film); silent windows are skipped. The film is padded with silence, so windows at
    its very start and end are compared too."""
    ref = pcm(ref_path, ffmpeg)
    lo, hi = max(0., -offset), min(len(ref) / SR, len(film) / SR - offset)
    window = min(window, hi - lo)
    if window < 1.0:
        return []
    pad = np.zeros(round(max_lag * SR), dtype=film.dtype)
    film = np.concatenate([pad, film, pad])
    results = []
    for t in np.linspace(lo, hi - window, points):
        a = round(t * SR)
        r = ref[a:a + round(window * SR)]
        if np.sqrt((r ** 2).mean()) < 0.01:   # skip silent windows
            continue
        b = round((t + offset) * SR)           # = film time - max_lag, in the padded film
        f = film[b:b + len(r) + 2 * len(pad)]
        lag, peak = lag_ms(r, f, len(pad))
        results.append({"ref_time": round(float(t), 1), "film_time": round(float(t + offset), 1),
                        "offset_ms": lag, "match": peak})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("video", type=Path)
    parser.add_argument("--max-duration", type=float, help="Seconds")
    parser.add_argument("--max-mb", type=float, help="Megabytes (10^6 bytes)")
    parser.add_argument("--lufs", type=float, default=-16.0, help="Target integrated loudness (warn beyond +/-2 LU)")
    parser.add_argument("--ref", type=Path, help="Voice file that should appear in the film's audio")
    parser.add_argument("--ref-offset", type=float, default=0.0, help="Where --ref starts in the film (s)")
    parser.add_argument("--sync-tolerance-ms", type=float, default=40)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    ffprobe = shutil.which("ffprobe") or str(Path(args.ffmpeg).with_name("ffprobe"))
    info = probe(args.video, ffprobe)
    fmt = info["format"]
    video = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    audio = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    errors, warnings = [], []
    report = {"file": str(args.video), "duration": round(float(fmt["duration"]), 3),
              "size_mb": round(int(fmt["size"]) / 1e6, 2)}
    if not video or not audio:
        errors.append("missing a video or an audio stream")
    else:
        num, den = map(int, video["r_frame_rate"].split("/"))
        fps = num / den
        vd, ad = float(video.get("duration", fmt["duration"])), float(audio.get("duration", fmt["duration"]))
        report.update(video=f"{video['codec_name']} {video['width']}x{video['height']} {video['pix_fmt']} {fps:.3g} fps",
                      audio=f"{audio['codec_name']} {audio.get('sample_rate')} Hz {audio.get('channels')} ch",
                      video_duration=round(vd, 3), audio_duration=round(ad, 3))
        if abs(vd - ad) > max(2 / fps, 0.05):
            errors.append(f"audio ({ad:.3f}s) and video ({vd:.3f}s) durations differ by {abs(vd - ad):.3f}s; "
                          "a track was dropped, padded or mis-placed")
        if video["codec_name"] != "h264" or video["pix_fmt"] != "yuv420p":
            warnings.append("not H.264/yuv420p; some players and assessment tools will refuse it")
        if audio["codec_name"] != "aac":
            warnings.append("audio is not AAC")
    if args.max_duration and report["duration"] > args.max_duration:
        errors.append(f"duration {report['duration']}s exceeds {args.max_duration}s")
    if args.max_mb and report["size_mb"] > args.max_mb:
        errors.append(f"size {report['size_mb']} MB exceeds {args.max_mb} MB")
    if audio:
        lufs, peak = loudness(args.video, args.ffmpeg)
        report.update(integrated_lufs=lufs, true_peak_dbfs=peak)
        if lufs is not None and abs(lufs - args.lufs) > 2:
            warnings.append(f"loudness {lufs} LUFS is far from the {args.lufs} LUFS target")
        if peak is not None and peak > -0.5:
            warnings.append(f"true peak {peak} dBFS is above -0.5 dBFS; lower the limiter ceiling")
        film = pcm(args.video, args.ffmpeg)
        report["audio_first_sound_s"] = first_sound(film)
        if args.ref:
            checks = sync_check(film, args.ref, args.ref_offset, args.ffmpeg)
            report["sync"] = checks
            if not checks:
                warnings.append("sync check found no usable windows; check --ref-offset")
            for c in checks:
                if c["match"] < 0.3:
                    errors.append(f"voice not found near film {c['film_time']}s (r={c['match']}): missing, "
                                  f"replaced, or more than 2.5 s off; check --ref-offset")
                elif abs(c["offset_ms"]) > args.sync_tolerance_ms:
                    errors.append(f"voice is {c['offset_ms']:+d} ms off at film {c['film_time']}s")
    report.update(ok=not errors, errors=errors, warnings=warnings)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(1 if errors else 0)


if __name__ == "__main__":
    main()

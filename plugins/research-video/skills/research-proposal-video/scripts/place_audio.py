#!/usr/bin/env python3
"""Place audio pieces on one timeline at exact sample offsets and write a single WAV.

Use this instead of an FFmpeg adelay+amix graph for building voice tracks: such graphs can
silently drop the shared leading silence, shifting everything early (a 1.15 s lip-sync error in
practice) while the file still "looks" fine. Each piece is decoded by FFmpeg, optionally trimmed,
time-stretched and loudness-matched, then summed into the buffer at round(start * rate).

  python place_audio.py work/voice_full.wav --duration 111 \
      work/intro_voice.wav@0 work/voice.wav@7.8
  # a slice of a recording, sped up 5 %, levelled to the narration:
  python place_audio.py out.wav --duration 9 "note.opus@1.2:in=0.05,out=1.1,tempo=1.05" --lufs -16
  # two different sources, each levelled to the narration before mixing:
  python place_audio.py out.wav --duration 30 "clip.wav@0:lufs=-16" "tts.wav@8:lufs=-16"

Piece syntax: PATH@START[:key=value,...] with keys in, out (seconds in the source), tempo
(FFmpeg atempo, 0.5-2), gain (dB), fade (edge fade seconds, default 0.01) and lufs (level this
piece on its own; only for whole takes from different sources - never for phrases of one
recording, where short pieces would be pumped up). --lufs levels the finished mix and applies a
-1 dBFS limiter. Output: 48 kHz stereo 24-bit WAV.
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

RATE = 48000


def parse_piece(spec):
    path_part, sep, rest = spec.rpartition("@")
    if not sep:
        raise ValueError(f"piece needs PATH@START: {spec}")
    start, _, opts = rest.partition(":")
    piece = {"path": Path(path_part), "start": float(start), "in": None, "out": None,
             "tempo": 1.0, "gain": 0.0, "fade": 0.01, "lufs": None}
    for item in filter(None, opts.split(",")):
        key, _, value = item.partition("=")
        if key not in ("in", "out", "tempo", "gain", "fade", "lufs"):
            raise ValueError(f"unknown option {key!r} in {spec}")
        piece[key] = float(value)
    if piece["start"] < 0 or not 0.5 <= piece["tempo"] <= 2:
        raise ValueError(f"start must be >= 0 and tempo within 0.5-2: {spec}")
    return piece


def measure_lufs(filters, path, ffmpeg="ffmpeg"):
    err = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-af", ",".join(filters + ["ebur128"]),
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    found = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    return float(found[-1]) if found else None


def decode(piece, ffmpeg="ffmpeg"):
    """Return float32 stereo samples for one piece after trim, tempo, level and edge fades."""
    filters = []
    if piece["in"] is not None or piece["out"] is not None:
        a = piece["in"] or 0
        filters.append(f"atrim=start={a}" + (f":end={piece['out']}" if piece["out"] is not None else ""))
        filters.append("asetpts=PTS-STARTPTS")
    filters += [f"aresample={RATE}", "aformat=sample_fmts=flt:channel_layouts=stereo"]
    if piece["tempo"] != 1:
        filters.append(f"atempo={piece['tempo']}")
    gain, lufs = piece["gain"], piece.get("lufs")
    if lufs is not None:
        measured = measure_lufs(filters, piece["path"], ffmpeg)
        if measured is None or measured < -70:
            print(f"WARNING: could not measure loudness of {piece['path']}; no levelling", file=sys.stderr)
        else:
            gain += lufs - measured
            piece["levelled_by_db"] = round(lufs - measured, 2)
    if gain:
        filters.append(f"volume={gain}dB")
    raw = subprocess.run([ffmpeg, "-v", "error", "-i", str(piece["path"]), "-af", ",".join(filters),
                          "-f", "f32le", "-ac", "2", "-ar", str(RATE), "-"], capture_output=True, check=True).stdout
    x = np.frombuffer(raw, dtype=np.float32).reshape(-1, 2).copy()
    n = min(len(x) // 2, round(piece["fade"] * RATE))
    if n:
        ramp = np.linspace(0, 1, n, dtype=np.float32)[:, None]
        x[:n] *= ramp
        x[-n:] *= ramp[::-1]
    return x


def place(pieces, duration, out_path, ffmpeg="ffmpeg", quiet=False, mix_lufs=None):
    """Mix pieces into a buffer of `duration` seconds; returns per-piece placement info."""
    buf = np.zeros((round(duration * RATE), 2), dtype=np.float32)
    report = []
    for p in pieces:
        x = decode(p, ffmpeg)
        k = round(p["start"] * RATE)
        if k >= len(buf):
            raise ValueError(f"{p['path']} starts after the end ({p['start']} s >= {duration} s)")
        if k + len(x) > len(buf):
            print(f"WARNING: {p['path']} is cut at the end by {(k + len(x) - len(buf)) / RATE:.2f} s", file=sys.stderr)
            x = x[:len(buf) - k]
        buf[k:k + len(x)] += x
        info = {"path": str(p["path"]), "start": p["start"], "end": round(p["start"] + len(x) / RATE, 3)}
        if "levelled_by_db" in p:
            info["levelled_by_db"] = p["levelled_by_db"]
        report.append(info)
        if not quiet:
            print(f"{p['path'].name}: {info['start']:.3f}-{info['end']:.3f} s" +
                  (f"  level {p['levelled_by_db']:+.1f} dB" if "levelled_by_db" in p else ""))
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    post = []
    if mix_lufs is not None:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-",
                            "-c:a", "pcm_f32le", tmp.name], input=buf.tobytes(), check=True)
            measured = measure_lufs([], tmp.name, ffmpeg)
        if measured is not None and measured > -70:
            post = [f"volume={mix_lufs - measured:.2f}dB", "alimiter=limit=0.89:level=false"]
            if not quiet:
                print(f"mix {measured} LUFS -> {mix_lufs} LUFS ({mix_lufs - measured:+.1f} dB, -1 dBFS limiter)")
    else:
        peak = float(np.abs(buf).max()) if len(buf) else 0.0
        if peak > 0.999:
            print(f"WARNING: summed peak {20 * np.log10(peak):+.1f} dBFS clips; lower a piece's gain", file=sys.stderr)
    # apad+atrim keep the exact sample count through the filters.
    post += ["apad", f"atrim=end_sample={len(buf)}"]
    subprocess.run([ffmpeg, "-v", "error", "-y", "-f", "f32le", "-ar", str(RATE), "-ac", "2", "-i", "-",
                    "-af", ",".join(post), "-c:a", "pcm_s24le", str(out_path)], input=buf.tobytes(), check=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output", type=Path)
    parser.add_argument("pieces", nargs="+", help="PATH@START[:in=,out=,tempo=,gain=,fade=]")
    parser.add_argument("--duration", type=float, required=True, help="Output length in seconds (exact)")
    parser.add_argument("--lufs", type=float, help="Level the finished mix to this integrated loudness")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    try:
        pieces = [parse_piece(s) for s in args.pieces]
    except ValueError as exc:
        parser.error(str(exc))
    for p in pieces:
        if not p["path"].is_file():
            parser.error(f"not found: {p['path']}")
    place(pieces, args.duration, args.output, args.ffmpeg, mix_lufs=args.lufs)
    print(f"{args.output}  {args.duration:.3f} s")


if __name__ == "__main__":
    main()

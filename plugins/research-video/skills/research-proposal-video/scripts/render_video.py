#!/usr/bin/env python3
"""Render a narrated MP4 from a validated scene timeline of images and video clips.

Image frames are resampled from the original with float affine coordinates (no stepped
jitter). An image scene is still unless it sets `zoom` (a slow push-in, e.g. 0.03 for photos;
keep text and chart cards at 0); consecutive scenes on one image share a motion clock. A scene whose asset is a video
(.mp4/.mov/.m4v/.webm/.mkv) plays that clip from its `clip_in` second, scaled to cover the frame
(its own sound is not used: put it, or a synced replacement, in the voice track with
place_audio.py / sync_to_footage.py). Dissolves are blended before subtitles are drawn, so
presenter footage and slides share one subtitle style; music fades in and out and ducks under
the voice; the output is H.264/yuv420p + AAC with faststart.

  python render_video.py work/timeline.json outputs/film.mp4 --voice work/voice.wav \
      --music work/music.wav --subtitles work/subtitles.srt
  # real presenter intro (a video scene) + image body in one pass, one music bed, one subtitle style:
  #   timeline scene 1: {"id": "intro", "asset": "../src/presenter.mp4", "clip_in": 0.9, "start": 0, "end": 8.2}
  # preview one changed passage with the real mix and fades:
  python render_video.py work/timeline.json work/preview.mp4 --voice work/voice.wav \
      --music work/music.wav --subtitles work/subtitles.srt --start 40 --end 55
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
from check_timeline import load_words, validate  # noqa: E402

CJK = "\u3000-\u303f\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff00-\uffef\uac00-\ud7af"
HAS_CJK = re.compile(f"[{CJK}]")
# One CJK character, one run of other non-space text, or one run of spaces.
WRAP_UNITS = re.compile(f"[{CJK}]|[^\\s{CJK}]+|\\s+")
LATIN_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]
CJK_FONTS = [
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
]


def find_font(need_cjk):
    """First installed font that covers the text; fc-match as a last resort."""
    for path in CJK_FONTS if need_cjk else LATIN_FONTS + CJK_FONTS:
        if Path(path).is_file():
            return path
    if shutil.which("fc-match"):
        query = "sans-serif:lang=zh-cn" if need_cjk else "sans-serif"
        found = subprocess.run(["fc-match", "-f", "%{file}", query], capture_output=True, text=True).stdout
        if found and Path(found).is_file():
            return found
    return None


def media_duration(path, ffmpeg):
    ffprobe = shutil.which("ffprobe") or str(Path(ffmpeg).with_name("ffprobe"))
    try:
        out = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                              "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
        return float(out.stdout.strip())
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None


VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm", ".mkv", ".avi"}


class ClipReader:
    """Sequential frames of one video scene, scaled to cover width x height at the film's fps.
    Opened lazily at the first requested time; requests must not go backwards."""

    def __init__(self, path, clip_in, width, height, fps, ffmpeg):
        self.args = (path, clip_in, width, height, fps, ffmpeg)
        self.proc, self.pos, self.frame, self.size = None, None, None, width * height * 3

    def get(self, local_t):
        path, clip_in, width, height, fps, ffmpeg = self.args
        k = round(local_t * fps)
        if self.proc is None:
            self.pos = k - 1
            vf = (f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=increase,"
                  f"crop={width}:{height},setsar=1,format=rgb24")
            self.proc = subprocess.Popen([ffmpeg, "-v", "error", "-ss", f"{clip_in + k / fps:.4f}", "-i", str(path),
                                          "-an", "-vf", vf, "-f", "rawvideo", "-"],
                                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        while self.pos < k:
            raw = self.proc.stdout.read(self.size)
            if len(raw) < self.size:      # clip ran out: hold the last frame
                break
            self.frame, self.pos = raw, self.pos + 1
        if self.frame is None:
            raise SystemExit(f"could not read frames from {path} at {clip_in + local_t:.2f}s")
        return self.frame

    def close(self):
        if self.proc:
            self.proc.stdout.close()
            self.proc.kill()
            self.proc.wait()


def subtitle_time(value):
    h, m, rest = value.replace(",", ".").split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def load_subtitles(path):
    if not path:
        return []
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        cues = data.get("subtitles") if isinstance(data, dict) else data
        return [(float(c["start"]), float(c["end"]), c["text"]) for c in cues]
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        lines = block.splitlines()
        idx = next((i for i, line in enumerate(lines) if "-->" in line), None)
        if idx is None:
            continue
        start, end = [subtitle_time(x.strip()) for x in lines[idx].split("-->")]
        cues.append((start, end, "\n".join(lines[idx + 1:])))
    return cues


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("timeline", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--voice", type=Path, required=True)
    parser.add_argument("--music", type=Path)
    parser.add_argument("--subtitles", type=Path, help="SRT or JSON subtitle cues")
    parser.add_argument("--font", type=Path, help="TTF/OTF/TTC; default: an installed system font, "
                        "a CJK one when titles or subtitles contain CJK text")
    parser.add_argument("--music-volume", type=float, default=.28,
                        help="Linear music gain before ducking (0.28 is about -11 dB)")
    parser.add_argument("--music-fade-in", type=float, default=1.5, help="Seconds")
    parser.add_argument("--music-fade-out", type=float, default=2.5, help="Seconds, ending at the film's end")
    parser.add_argument("--start", type=float, default=0, help="Preview: first second to render")
    parser.add_argument("--end", type=float, help="Preview: last second to render (default: film end)")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--crf", type=int, default=20)
    args = parser.parse_args()
    if not 0 <= args.music_volume <= 1:
        parser.error("--music-volume must be between 0 and 1")
    if args.music_fade_in < 0 or args.music_fade_out < 0:
        parser.error("music fades must be nonnegative")
    if not args.voice.is_file() or args.music and not args.music.is_file():
        parser.error("voice/music input not found")
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        parser.error("Install Pillow in the chosen Python environment")
    data = json.loads(args.timeline.read_text(encoding="utf-8"))
    base = args.timeline.resolve().parent
    words = load_words(base / data["word_file"]) if data.get("word_file") else None
    errors = validate(data, base, words)
    if errors:
        parser.error("Invalid timeline: " + "; ".join(errors))
    video = data.get("video", {})
    width, height, fps = int(video.get("width", 1920)), int(video.get("height", 1080)), int(video.get("fps", 30))
    if min(width, height, fps) <= 0 or width % 2 or height % 2:
        parser.error("video width/height must be positive even integers; fps must be positive")
    duration, scenes = float(data["duration"]), data["scenes"]
    if any(not s.get("asset") for s in scenes):
        parser.error("render_video.py requires an image or video asset for every scene")
    is_clip = [Path(s["asset"]).suffix.lower() in VIDEO_EXT for s in scenes]
    start = args.start
    end = duration if args.end is None else args.end
    if not 0 <= start < end <= duration + 1e-6:
        parser.error(f"--start/--end must satisfy 0 <= start < end <= {duration}")
    subtitles = load_subtitles(args.subtitles)
    texts = [c[2] for c in subtitles] + [str(s.get("title", "")) for s in scenes]
    font_path = args.font or find_font(any(HAS_CJK.search(t) for t in texts))
    sub_px, title_px = max(16, round(height * .037)), max(20, round(height * .05))
    if font_path:
        subtitle_font = ImageFont.truetype(str(font_path), sub_px)
        title_font = ImageFont.truetype(str(font_path), title_px)
    else:
        print("WARNING: no system font found; using Pillow's built-in Latin font. Pass --font.", file=sys.stderr)
        subtitle_font, title_font = ImageFont.load_default(sub_px), ImageFont.load_default(title_px)
    images, readers = {}, {}
    for i, scene in enumerate(scenes):
        path = base / scene["asset"]
        if is_clip[i]:
            readers[i] = ClipReader(path, float(scene.get("clip_in", 0)), width, height, fps, args.ffmpeg)
            continue
        if path not in images:
            with Image.open(path) as raw:
                rgba = raw.convert("RGBA")
                bg = Image.new("RGBA", rgba.size, "white")   # transparent logos go on white, not black
                images[path] = Image.alpha_composite(bg, rgba).convert("RGB")

    # Consecutive uses of one image share a single motion clock (a new title doesn't restart it).
    spans = []
    for i, scene in enumerate(scenes):
        if is_clip[i]:
            spans.append(None)
            continue
        first, last = i, i
        while first and scenes[first - 1]["asset"] == scene["asset"]:
            first -= 1
        while last + 1 < len(scenes) and scenes[last + 1]["asset"] == scene["asset"]:
            last += 1
        spans.append((scenes[first]["start"], scenes[last]["end"], first))

    def text_box(draw, text, font):
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        return left, top, right - left, bottom - top

    def scene_frame(i, t):
        scene = scenes[i]
        if is_clip[i]:
            frame = Image.frombytes("RGB", (width, height), readers[i].get(t - scene["start"]))
            return draw_title(frame, scene)
        src = images[base / scene["asset"]]
        span_start, span_end, motion_scene = spans[i]
        p = max(0., min(1., (t - span_start) / (span_end - span_start)))
        ease = p * p * (3 - 2 * p)   # smoothstep ease-in-out
        motion = scenes[motion_scene]
        zoom = float(motion.get("zoom", 0))
        factor = max(width / src.width, height / src.height) * (1 + zoom * ease)
        visible_w, visible_h = width / factor, height / factor
        cx = src.width * float(motion.get("center_x", .5))
        cy = src.height * float(motion.get("center_y", .5))
        cx = max(visible_w / 2, min(src.width - visible_w / 2, cx))
        cy = max(visible_h / 2, min(src.height - visible_h / 2, cy))
        frame = src.transform(
            (width, height), Image.Transform.AFFINE,
            (1 / factor, 0, cx - width / (2 * factor), 0, 1 / factor, cy - height / (2 * factor)),
            resample=Image.Resampling.BICUBIC, fillcolor="white")
        return draw_title(frame, scene)

    def draw_title(frame, scene):
        if scene.get("title"):
            draw = ImageDraw.Draw(frame)
            text = str(scene["title"])
            left, top, w, h = text_box(draw, text, title_font)
            pad_x, pad_y = round(title_px * .6), round(title_px * .4)
            x, y = round(width * .045) + pad_x, round(height * .06) + pad_y
            draw.rounded_rectangle((x - pad_x, y - pad_y, x + w + pad_x, y + h + pad_y),
                                   radius=round(title_px * .35), fill=(12, 37, 48))
            draw.text((x - left, y - top), text, font=title_font, fill="white")
        return frame

    def wrap(draw, text, max_width):
        # Latin breaks at spaces; CJK may break between any two characters.
        lines, current = [], ""
        for unit in WRAP_UNITS.findall(text):
            trial = current + unit
            if current.strip() and not unit.isspace() and text_box(draw, trial.strip(), subtitle_font)[2] > max_width:
                lines.append(current.strip())
                current = unit
            else:
                current = trial
        return [line for line in lines + [current.strip()] if line]

    def balanced(draw, text, max_width):
        # as few lines as fit max_width, then the narrowest width that keeps that many lines,
        # so a two-line cue is split near the middle instead of leaving one word on line two
        lines = wrap(draw, text, max_width)
        lo, hi = max_width / (len(lines) + 1), max_width
        while len(lines) > 1 and hi - lo > 4:
            mid = (lo + hi) / 2
            lo, hi = (lo, mid) if len(wrap(draw, text, mid)) == len(lines) else (mid, hi)
        return wrap(draw, text, hi) if len(lines) > 1 else lines

    def add_subtitle(frame, t):
        cue = next((x for x in subtitles if x[0] <= t < x[1]), None)
        if not cue:
            return frame
        draw = ImageDraw.Draw(frame)
        # a line break written in the cue is kept; longer lines wrap, balanced, within 70% of the frame
        lines = [line for part in cue[2].splitlines() for line in balanced(draw, " ".join(part.split()), width * .7)]
        if not lines:
            return frame
        line_h, pad = round(sub_px * 1.45), round(sub_px * .45)
        bottom = height - round(height * .05)
        top = bottom - len(lines) * line_h - 2 * pad
        widest = max(text_box(draw, line, subtitle_font)[2] for line in lines)
        draw.rounded_rectangle(((width - widest) / 2 - 2 * pad, top, (width + widest) / 2 + 2 * pad, bottom),
                               radius=round(sub_px * .3), fill=(9, 30, 42))
        for j, line in enumerate(lines):
            left, ttop, w, h = text_box(draw, line, subtitle_font)
            y = top + pad + j * line_h + (line_h - h) / 2 - ttop
            draw.text(((width - w) / 2 - left, y), line, font=subtitle_font, fill="white")
        return frame

    fade_in, fade_out = float(video.get("fade_in", 0)), float(video.get("fade_out", 0))
    black = Image.new("RGB", (width, height))
    # Audio is mixed over the whole film and then trimmed, so a preview hears the real fades and ducking.
    window = f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS"
    voice_len = media_duration(args.voice, args.ffmpeg)
    if voice_len is not None and voice_len > duration + .05:
        print(f"WARNING: the voice ({voice_len:.2f}s) is longer than the timeline ({duration:.2f}s); "
              f"its last {voice_len - duration:.2f}s are cut. Lengthen the timeline or trim the voice.", file=sys.stderr)
    voice = f"[1:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=duration={duration}"
    cmd = [args.ffmpeg, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-i", str(args.voice)]
    if args.music:
        music_len = media_duration(args.music, args.ffmpeg)
        if music_len is not None and music_len < duration:
            print(f"WARNING: music ({music_len:.1f}s) is shorter than the film ({duration:.1f}s) and will loop "
                  "with an audible seam; use a longer track or a prepared seamless loop.", file=sys.stderr)
        cmd += ["-stream_loop", "-1", "-i", str(args.music)]
        filt = (
            f"{voice},asplit=2[voice][key];"
            f"[2:a]aresample=48000,aformat=channel_layouts=stereo,volume={args.music_volume},"
            f"atrim=duration={duration},afade=t=in:d={args.music_fade_in},"
            f"afade=t=out:st={max(0., duration - args.music_fade_out)}:d={args.music_fade_out}[music];"
            "[music][key]sidechaincompress=threshold=0.018:ratio=6:attack=30:release=350[duck];"
            f"[voice][duck]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.89:level=false:latency=1,{window}[a]"
        )
    else:
        filt = f"{voice},{window}[a]"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    cmd += ["-filter_complex", filt, "-map", "0:v:0", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-t", str(end - start), "-movflags", "+faststart", str(args.output)]
    with tempfile.TemporaryFile() as log:   # a file, not a pipe, so FFmpeg can never block on stderr
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=log)
        try:
            for frame_no in range(round(start * fps), round(end * fps)):
                t = frame_no / fps
                i = max(j for j, scene in enumerate(scenes) if scene["start"] <= t)
                scene = scenes[i]
                frame = scene_frame(i, t)
                transition = scene.get("transition_in", 0)
                if i and transition and t < scene["start"] + transition:
                    previous = scene_frame(i - 1, t)
                    frame = Image.blend(previous, frame, (t - scene["start"]) / transition)
                shade = min(1., t / fade_in if fade_in else 1., (duration - t) / fade_out if fade_out else 1.)
                if shade < 1:
                    frame = Image.blend(black, frame, max(0., shade))
                proc.stdin.write(add_subtitle(frame, t).tobytes())
                for j in [j for j in readers if scenes[j]["end"] <= t]:   # finished clips
                    readers.pop(j).close()
        except BrokenPipeError:
            pass   # FFmpeg exited early; its log below says why
        finally:
            for reader in readers.values():
                reader.close()
            try:
                proc.stdin.close()
            except BrokenPipeError:
                pass
        code = proc.wait()
        if code:
            log.seek(0)
            raise SystemExit("FFmpeg failed:\n" + log.read().decode(errors="replace"))
    print(args.output)

if __name__ == "__main__":
    main()

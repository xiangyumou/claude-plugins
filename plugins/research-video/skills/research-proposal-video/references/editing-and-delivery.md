# 剪辑、配乐与交付

## 工具链

下面是新项目的默认方案。faster-whisper 和 Qwen3-ForcedAligner 只用于识别/对齐和词级时间戳，不是配音模型；配音方案按 [voice.md](voice.md) 选择并记录。

| 工作 | 默认 | 换用条件 |
|---|---|---|
| 词级时间戳 | `align_words.py`：有定稿、`--language` 且装了 qwen-asr 时自动用 Qwen3-ForcedAligner-0.6B 按定稿强制对齐 | 没有定稿时自动用 faster-whisper。Qwen 一次最多对齐 5 分钟：更长的人声在停顿处切段，各段用 `--offset` 对齐后合并（不切段时自动改用 Whisper）。两者都要人工抽查 |
| 字幕 | `make_subtitles.py --lines`：手工分条的字幕稿（`{显示\|口播}`）+ 词时间，见 [subtitles.md](subtitles.md) | 已有人工校对的字幕 |
| 拼人声轨 | `place_audio.py`（采样点精确） | 不用 adelay+amix |
| 真人画面换成干净录音 | `sync_to_footage.py`（DTW 分句对口型），见 [presenter-footage.md](presenter-footage.md) | 自动结果仍不自然时，按 `.sync.json` 手调各段再用 `place_audio.py` |
| 时间线 | `build_timeline.py` 由词生成，`check_timeline.py` 检查 | 现有剪辑工程有更完整的检查时沿用 |
| 图片/视频镜头、溶解、逐帧字幕、混音、MP4 | `render_video.py`（Pillow + FFmpeg） | 大量实拍、多轨复杂剪辑时用现有 NLE/FFmpeg 工程 |
| 成片检查 | `check_output.py` | 必做，不可替代 |

安装：

- 基本：`pip install numpy Pillow`，另装 FFmpeg。
- 卡片截图：`pip install playwright && playwright install chromium`；论文首页截图用 poppler 的 `pdftoppm`。
- 词时间：`pip install qwen-asr`（强制对齐，可放单独的虚拟环境；首次运行下载约 1.7 GB 模型；Apple 芯片用 MPS，NVIDIA 用 CUDA）；没有定稿时用 `pip install faster-whisper`。WhisperX 只在逐词精度确实不够时用。
- 工具能力当场查，不要对不存在的滤镜反复试错。例如有些 FFmpeg 没有 libass/subtitles 滤镜：`render_video.py` 逐帧自己画字幕，不依赖它；需要软字幕时另交 SRT。

## 口播、画面、字幕共用一条时间轴

先定稿和干声，再按下面的顺序做（`$S` 是本 skill 的 `scripts/` 目录的绝对路径）：

- 用 `place_audio.py` 拼出从 0 秒开始的整条人声轨（开场真人段 + 旁白；长度默认到最后一段结束，不必与成片等长），`--lufs -16` 做整体响度。渲染器不再归一响度，`check_output.py` 按 −16 LUFS 检查。
- 在这条纯人声轨上生成 `words.json`，不对混了音乐的音轨做。单独识别某一段时，用 `align_words.py --offset` 传入该段在全片中的起点，词时间就在全片时间上，不需要 `word_offset`。
- ASR 只建议时间，不改认可稿的文字。人名、机构名、一词对多词和语音起止点要对照原声核实。
- 调停顿用 `pauses.py`（见 [voice.md](voice.md)）。改了语速、静音或重新合成后必须重新取时间戳；只做保持时长的音量/音高处理可以沿用，但要检查边界。转换采样率不能改变时长，不要把 24 kHz 的文件当 48 kHz 解释。

    python3 $S/place_audio.py work/voice_full.wav --lufs -16 \
        work/intro_voice.wav@0 work/voice.wav@7.8
    python3 $S/align_words.py work/voice_full.wav work/words.json --language en --script work/script.txt
    python3 $S/make_subtitles.py work/subtitles.txt work/words.json work/subtitles.srt --lines
    python3 $S/build_timeline.py work/plan.json work/timeline.json
    python3 $S/render_video.py work/timeline.json outputs/film.mp4 \
        --voice work/voice_full.wav --music work/music.wav --subtitles work/subtitles.srt
    python3 $S/check_output.py outputs/film.mp4 --max-duration 120 --max-mb 50 --ref work/voice_full.wav

关于词时间：

- `align_words.py` 默认在有 `--script`、`--language`、装了 qwen-asr 且音频不超过 5 分钟时用 Qwen 强制对齐，否则用 Whisper，并打印所选的方式。
- `--script` 给认可稿，和 `make_subtitles.py` 用同一份即可：`{显示|口播}` 按口播部分对齐。稿子要写声音实际读出的词，不要给为了 TTS 读音改拼写的合成文本（写 Qwen，不写 Chwen）。
- Qwen 对齐的词和稿子逐字一致（计划里的 `word` 按稿子拼写，harmonised 而非 harmonized），同一音频两次结果完全相同。它偶尔把句首词起点放晚到词中（或把一个词的时间给下一个词），脚本会在前面至少 120 ms 的静音处找回起音。
- Whisper 常把停顿后第一个词提前 0.4–1 秒（脚本会推到真正出声处），偶尔给零时长的词（已修正），重跑时同一词可能差 0.3 秒以上，所以用 `after` 的计划要留余量。`--script` 会列出识别与认可稿不一致的每一处（例如 script 'growth' -> heard 'gross'），逐条判断是识别错还是真的读错。
- 中文、日文常按字给时间，计划里的“超声”这类词会跨几个字去匹配；英文单词只和单个词匹配（into 不会命中 in to），带空格或连字符的短语可以跨词。

字幕的写法和生成见 [subtitles.md](subtitles.md)。

### 时间线格式

每个 scene 的 start/end 是它参与合成的区间。`transition_in` 是与上一镜头重叠溶解的秒数，所以后一个 start = 前一个 end − transition_in，0 表示硬切。转场中点 = start + transition_in/2。

`speech_anchor` 把转场中点对准一个词：用 `words.json` 的 `word_id`，或用 `word` 加 `occurrence`（第几次出现）。检查器比较词的起点和转场中点，默认容差 0.35 秒；`offset` 表示希望画面相对词起点提前（负）或延后（正）。数值型 speech_anchor 只检查它落在镜头区间内，核对不了语词。检查器只验证时序，画面含义要人核对。

    {
      "duration": 4.0,
      "video": {"width": 1280, "height": 720, "fps": 24},
      "word_file": "words.json",
      "scenes": [
        {"id": "need", "start": 0.0, "end": 2.15, "asset": "need.jpg", "title": "The need"},
        {"id": "scan", "start": 1.85, "end": 4.0, "transition_in": 0.3,
         "asset": "scan.jpg", "zoom": 0.035, "center_x": 0.6,
         "speech_anchor": {"word_id": "w0042", "tolerance": 0.25}}
      ]
    }

若 w0042 从 2.00 秒开始，第二个镜头的转场中点正好是 2.00 秒。时间线顶层的 `word_offset` 会加到所有词时间上（`words.json` 是在后来才进入成片的音轨上取的时候用；字幕同样要加，见 subtitles.md）。不写 `video` 时默认 1920×1080、30 fps。`video` 里可设 `fade_in`/`fade_out`（从黑/到黑的秒数）。

视频镜头：`asset` 是 .mp4/.mov 等时，按 `clip_in` 秒开始播放，铺满画面，不用它自带的声音（声音放进人声轨）。检查器会核对片段够不够长。

一般不手写时间，而是写一份计划，让 `build_timeline.py` 算：

    {"words": "words.json", "transition": 0.36, "tail": 2.6,
     "video": {"width": 1280, "height": 720, "fps": 24, "fade_in": 0.3},
     "asset_pattern": "cards/{id}.png",
     "scenes": [
       {"id": "intro", "asset": "../src/presenter.mp4", "clip_in": 0.9, "zoom": 0},
       {"id": "need", "at": 8.0, "transition": 0.4},
       {"id": "scan", "word": "ultrasound", "after": 20, "zoom": 0.03},
       {"id": "team", "word": "team", "occurrence": 2}]}

- 每个镜头从 `after` 秒之后第 `occurrence` 次（默认第 1 次）说到 `word` 时开始，或用 `at` 指定秒数；转场中点对准该词起点，时长和 speech_anchor 自动生成并检查。第一个镜头总是从 0 开始，写了 `word`/`at` 会被忽略并警告。
- 找不到词会停下，列出相近的实际读音（例如 harmonised → harmonized，超声 → 朝声）。
- `after` 是某一条人声轨上的秒数，要比预期早约 1 秒写，换了配音就不再对。全部用 `word` + `occurrence` 的计划与声音无关：`build_timeline.py plan.json B/timeline.json --words B/words.json` 按另一条人声切出同样的镜头。
- 素材路径相对于计划文件，写出的时间线里换算成相对于时间线文件。
- `title` 画在左上角，只在图的左上有留白时使用。字幕写在 SRT 或 JSON 里，TTS 的专名发音拼写不能进字幕。

## 按语义切画面

每个镜头记录 start、end、asset、含义、触发它的短句和 speech_anchor。先标出关键短句，再填中间镜头，不要平均分配图片。一个镜头不必等于一页 PPT，一段配音也可以对应多个镜头。

每个关键短句找一个看得见的对应物：说到研究方法就出现相应的实验、检查或计算场景；说到国家或合作方出现对应的标志或地图；说到团队、指导出现真实的人；数字出现对应的数据卡；致谢句对应致谢画面。

0.25–0.4 秒的短溶解是合适的起点。让关键词落在转场中点，也就是画面在关键词前约半个转场时长开始溶入。不能只检查全片总时长对得上。

## 平滑运动与画质

整数像素反复缩放/裁切会产生台阶状抖动。每帧都从原图用浮点仿射采样加 bicubic 重采样，不要在上一帧缩小后的图上再放大；帧率保持恒定。

`zoom` 默认 0，画面静止：

- 只给照片和场景图设缓慢推近，从全镜头 2–4% 开始，按观感调整。
- 文字卡、图表卡保持 0：推近不增加信息，只让字和线条轻微游动。
- 逐步显示的卡片（同一版式先灰后实、逐项点亮的几张图）必须是 0：每张是不同的图，换图时运动进度归零，溶解时元素会跳一下，看起来像抖动。
- 静止画面编码也省得多：以卡片为主的片子去掉推近后，文件可以小到原来的三分之一左右。

进度 p 限制在 [0,1]，缓入缓出 e = p·p·(3−2p)，缩放 = 1 + zoom·e。人物不在中间时调 `center_x/center_y`，渲染器会保证画面不越界。同一张图跨连续几个镜头（例如换了标题）时，运动进度按整段计算，不因标题变化归零；换图才重置。不要加随机晃动来模拟镜头感。

透明 logo 要先按实际背景做 alpha 合成再转 RGB（渲染器合成到白底）。用联系表检查脸、标题、logo 和裁切；但静态联系表证明不了运动顺滑，要看动态片段。

## BGM 与混音

用有相应用途许可的音乐或原创音乐，在状态记录里写明来源和许可。用户喜欢参考片，不代表可以用它的音轨。普通的原创配乐不需要额外找用户确认。

说话段落下，音乐可以从比人声 RMS 低约 12–18 dB 开始，最终值由频谱和听感决定，这不是固定的验收阈值。用户说音乐太小时，相对当前版本提高 2–3 dB，做出听得出的变化，不要同时偷偷压低人声。`--music-volume` 是线性增益：+3 dB 约 ×1.41，−3 dB 约 ×0.71。

音乐开头淡入、结尾淡出（`--music-fade-in` 默认 1.5 秒，`--music-fade-out` 默认 2.5 秒，结束于片尾），说话时由人声侧链平滑压低，停顿时自然回升。避免泵动、突然起落或音乐盖住辅音。使命句处可以略有推进，致谢后留一段短尾声：让时间线的 duration 比最后一句多 2–3 秒。音乐比成片短时渲染器会警告，循环接缝通常听得出来，换更长的曲子或事先做好无缝循环。

保留干声的动态。渲染器最后用 alimiter 限峰，但 PCM 不削波不等于 AAC 编码后没有 intersample peak，有条件时检查最终编码结果。响度数值不能代替试听；不要把固定增益说成专业母带标准。

## 预览、验证与交付

先对改动的镜头和声音接点做短预览：`render_video.py` 加 `--start 40 --end 55` 只渲染这一段，混音和淡入淡出与完整片完全相同。实际看、听口型、运动、字幕和音乐闪避是否自然；静态抽帧、ASR 和峰值数值代替不了看和听。

完整片的最低检查是跑 `check_output.py`，加上提交限制和 `--ref`（人声轨在片中的起点用 `--ref-offset`）：

- 它报告音视频时长是否一致、时长和大小、编码、整体响度和真峰值、第一次出声的时间。
- 它在全片最多 6 处用互相关核对人声的位置（短片会缩短窗口，静音处跳过）；整体偏移超过 40 ms 或找不到人声都算错误。只有它通过才算“时序没问题”。
- 机器检查之外还要：看完结尾，看过新增画面和所有改过的转场，核对相关口播和字幕，听过音乐与人声的关系。环境无法实际播放时，明确说明验证到了哪一步。

编码按提交规范选择；兼容性最好的是 MP4/H.264、yuv420p、AAC、faststart（渲染器的默认输出）。默认 1920×1080/30；要更小更快时在时间线的 `video` 里改成 720p/24，文件太大时提高 `--crf`。

`work/` 保留原图、干声、音乐、字幕、时间线、来源清单和历史版本，方便下次只改必要的部分；不擅自删除历史版本。新一版放进新目录（例如 `work/pipeline_v6/`、`cards/out_v6/`），只复制要改的输入，旧版本和已交付的成品保持原样，状态记录里写明每版改了什么，让用户对比后再决定用哪版。

### 只换配音的 A/B 版

几个候选声音都过了试听、各有取舍时，做两部只差配音的完整成片让用户（或导师）选，比两段试听更接近最终观感。除了人声轨，其余全部相同：开场、卡片、运动、配乐、字幕文字。

- 每个声音各拼一条整轨人声（开场段相同、旁白起点相同），各自取词时间。开场段两版用同一份词时间，免得对齐抖动让开场的切点不同。
- 时间线计划用 `word` + `occurrence`，两版共用一份，分别用 `--words` 生成时间线。旧计划只有 `after` 时，先按当前声音的词时间把每个镜头换算成 `occurrence`。配乐里按时间写的推进点、音乐尾声也跟着对应的词走。
- 字幕共用一份字幕稿，两版分别生成 SRT（见 [subtitles.md](subtitles.md) 最后一段）。
- 放在 `work/pipeline_vN/A/`、`B/`，文件名写明差别（例如 `film_A_<声音名>.mp4`），两版都跑 `check_output.py`（`--ref` 各用自己的人声轨）。发给用户时说清“除了配音完全一样”，状态记录写明两版唯一的差别。

### 选定之后

用户选定一版后才更新交付目录：原来的成品挪进 `work/` 下的归档目录（例如 `work/outputs_archive_v2/`），不删除；把选中的成片和它自己的 SRT 按交付文件名复制进 `outputs/`；核对逐字稿、录音稿是否仍与这一版的口播一致；对 `outputs/` 里的文件再跑一遍 `check_output.py`；状态记录写明选了哪版、谁选的、来源路径和检查结果。没选中的版本留在 `work/`。

某些客户端（例如手机、远程控制）对聊天附件的大小有上限（遇到过约 30 MB）。成片超过这个大小时，另做一个预览发过去（例如 `ffmpeg -i film.mp4 -c:v libx264 -preset slow -crf 26 -c:a aac -b:a 160k -movflags +faststart preview.mp4`），说明它只是压缩预览，完整片在哪个路径。外发目录只放用户需要的完整成片，以及用户要的 PPTX、逐字稿或 SRT；短预览另附，不代替完整片。

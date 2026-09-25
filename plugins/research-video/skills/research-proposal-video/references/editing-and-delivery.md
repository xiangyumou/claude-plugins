# 剪辑、配乐与交付

## 工具链

下面是新项目的默认方案。faster-whisper 和 Qwen3-ForcedAligner 只用于识别/对齐和词级时间戳，不是配音模型；配音方案按 [voice.md](voice.md) 选择并记录。

| 工作 | 默认 | 换用条件 |
|---|---|---|
| 词级时间戳 | `align_words.py --aligner qwen`（Qwen3-ForcedAligner-0.6B，按定稿强制对齐） | 没有定稿、或音频超过 5 分钟时用默认的 faster-whisper；两者都要人工抽查 |
| 字幕 | `make_subtitles.py`：认可稿文字 + ASR 时间 | 已有人工校对的字幕 |
| 拼人声轨 | `place_audio.py`（采样点精确） | 不用 adelay+amix |
| 真人画面换成干净录音 | `sync_to_footage.py`（DTW 分句对口型） | 自动结果仍不自然时，按 `.sync.json` 手调各段再用 `place_audio.py` |
| 时间线 | `build_timeline.py` 由词生成，`check_timeline.py` 检查 | 现有剪辑工程有更完整的检查时沿用 |
| 图片/视频镜头、溶解、逐帧字幕、混音、MP4 | `render_video.py`（Pillow + FFmpeg） | 大量实拍、多轨复杂剪辑时用现有 NLE/FFmpeg 工程 |
| 成片检查 | `check_output.py` | 必做，不可替代 |

安装：`pip install Pillow faster-whisper`，强制对齐另装 `pip install qwen-asr`（单独的虚拟环境即可，首次运行下载约 1.7 GB 模型；Apple 芯片用 MPS，有 NVIDIA 显卡用 CUDA），FFmpeg 另装。WhisperX 环境更复杂，只在逐词精度确实不够时用。工具能力当场查：有些 Mac 上的 FFmpeg 没有 libass/subtitles 滤镜，`render_video.py` 逐帧自己画字幕，不依赖它；需要软字幕时另交 SRT。不要对不存在的滤镜反复试错。

## 口播、画面、字幕共用一条时间轴

先定稿和干声，用 `place_audio.py` 拼出从 0 秒开始、与成片等长的整条人声轨（开场真人段 + 旁白），再在这条轨上生成 `words.json`。识别只对纯人声做，不对混了音乐的音轨做。整条音轨识别时偏移为 0；单独识别某段时，用 `--offset` 传入该段在全片中的起点。ASR 只建议时间，不改认可稿的文字。人名、机构名、一词对多词和语音起止点要对照原声核实。改了语速、静音或重新合成后必须重新取时间戳；只做保持时长的音量/音高处理可以沿用原时间，但要检查边界。转换采样率不能改变时长，不要把 24 kHz 的文件当 48 kHz 解释。

    python3 scripts/place_audio.py work/voice_full.wav --duration 111 \
        work/intro_voice.wav@0 work/voice.wav@7.8
    python3 scripts/align_words.py work/voice_full.wav work/words.json --aligner qwen --language en --script work/script.txt
    python3 scripts/make_subtitles.py work/script.txt work/words.json work/subtitles.srt
    python3 scripts/build_timeline.py work/plan.json work/timeline.json
    python3 scripts/render_video.py work/timeline.json outputs/film.mp4 \
        --voice work/voice_full.wav --music work/music.wav --subtitles work/subtitles.srt
    python3 scripts/check_output.py outputs/film.mp4 --max-duration 120 --max-mb 50 --ref work/voice_full.wav

`align_words.py` 会把落在静音里的词起点推到真正出声的地方（Whisper 常把停顿后第一个词提前 0.4–1 秒），并修正零时长的词。同一段音频重跑 ASR，个别词的时间也可能差 0.3 秒以上，所以时间线计划要留余量。Qwen 强制对齐同一音频两次结果完全相同；它偶尔把句首词起点放晚到词中（也会把一个词的时间给下一个词），`align_words.py` 会在前面至少 120 ms 的静音处找回起音。对齐结果的词和稿子逐字一致，计划里的 `word` 要按稿子的拼写写（harmonised 而非 harmonized）。

`align_words.py --script` 会列出 ASR 与认可稿不一致的每一处（例如 script 'growth' -> heard 'gross'），逐条判断是识别错还是真的读错。`make_subtitles.py` 的字幕文字全部来自认可稿：每句另起一条，长句拆成数量最少、长度均匀的几条（默认英文不超过 42 字符、中文不超过 20 字），优先在逗号处断开；中文字幕去掉句末标点。对不上的条目会报警告，要人工核对时间。

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

若 w0042 从 2.00 秒开始，第二个镜头的转场中点正好是 2.00 秒。时间线顶层的 `word_offset` 会加到所有词时间上（`words.json` 是在后来才进入成片的音轨上取的时候用）。`video` 里可设 `fade_in`/`fade_out`（从黑/到黑的秒数）。

视频镜头：`asset` 是 .mp4/.mov 等时，按 `clip_in` 秒开始播放，铺满画面，不用它自带的声音（声音放进人声轨）。检查器会核对片段够不够长。

一般不手写时间，而是写一份计划，让 `build_timeline.py` 算：

    {"words": "words.json", "transition": 0.36, "tail": 2.6,
     "video": {"width": 1280, "height": 720, "fps": 24, "fade_in": 0.3},
     "asset_pattern": "cards/{id}.png",
     "scenes": [
       {"id": "intro", "asset": "../src/presenter.mp4", "clip_in": 0.9, "zoom": 0},
       {"id": "need", "at": 8.0, "transition": 0.4},
       {"id": "scan", "word": "ultrasound", "after": 20, "zoom": 0.03}]}

每个镜头从 `after` 秒之后第一次出现的 `word` 开始（或用 `at` 指定秒数），转场中点对准该词起点，时长和 speech_anchor 自动生成并检查。找不到词会停下并列出相近的实际读音（例如 harmonised → harmonized）。`after` 比预期早约 1 秒写，给 ASR 抖动留余量；同一个词在附近出现多次时，靠 `after` 区分。路径相对于时间线文件。`title` 画在左上角，只在图的左上有留白时使用；字幕写在 SRT 或 JSON 里，TTS 的专名发音拼写不能进字幕。

## 按语义切画面

每个镜头记录 start、end、asset、含义、触发它的短句和 speech_anchor。先标出关键短句，再填中间镜头，不要平均分配图片。一个镜头不必等于一页 PPT，一段配音也可以对应多个镜头。

常见对应：说到超声就出现检查画面；说国家名出现多国地图；说 stakeholder engagement 出现讨论；说 women's health 出现患者；说 mentoring/next generation 出现指导场景；致谢句对应致谢画面。

0.25–0.4 秒的短溶解是合适的起点。让关键词落在转场中点，也就是画面在关键词前约半个转场时长开始溶入。不能只检查全片总时长对得上。

字幕在转场合成之后绘制，所以跨镜头的字幕不会出现双影；字幕跨过切镜是允许的。底部留安全边距，按短句分组，一屏不塞太多字。

## 平滑运动与画质

整数像素反复缩放/裁切会产生台阶状抖动。每帧都从原图用浮点仿射采样加 bicubic 重采样，不要在上一帧缩小后的图上再放大；帧率保持恒定。

`zoom` 默认 0，画面静止。只给照片和场景图设缓慢推近，从全镜头 2–4% 开始，按观感调整。文字卡、图表卡保持 0：推近不增加信息，只让字和线条轻微游动。逐步显示的卡片（同一版式先灰后实、逐项点亮的几张图）必须是 0：每张是不同的图，换图时运动进度归零，前后两张的缩放不同，溶解时元素会跳一下，看起来像抖动。静止画面编码也省得多：一部 110 秒、以卡片为主的片子去掉推近后从 34 MB 降到 12 MB。

进度 p 限制在 [0,1]，缓入缓出 e = p·p·(3−2p)，缩放 = 1 + zoom·e。人物不在中间时调 `center_x/center_y`，渲染器会保证画面不越界。同一张图跨连续几个镜头（例如换了标题）时，运动进度按整段计算，不因标题变化归零；换图才重置。不要加随机晃动来模拟镜头感。

透明 logo 要先按实际背景做 alpha 合成再转 RGB（渲染器合成到白底）。用联系表检查脸、标题、logo 和裁切；但静态联系表证明不了运动顺滑，要看动态片段。

## BGM 与混音

用有相应用途许可的音乐或原创音乐，在状态记录里写明来源和许可。用户喜欢参考片，不代表可以用它的音轨。普通的原创配乐不需要额外找用户确认。

说话段落下，音乐可以从比人声 RMS 低约 12–18 dB 开始，最终值由频谱和听感决定，这不是固定的验收阈值。用户说音乐太小时，相对当前版本提高 2–3 dB，做出听得出的变化，不要同时偷偷压低人声。`--music-volume` 是线性增益：+3 dB 约 ×1.41，−3 dB 约 ×0.71。

音乐开头淡入、结尾淡出（`--music-fade-in` 默认 1.5 秒，`--music-fade-out` 默认 2.5 秒，结束于片尾），说话时由人声侧链平滑压低，停顿时自然回升。避免泵动、突然起落或音乐盖住辅音。使命句处可以略有推进，致谢后留一段短尾声：让时间线的 duration 比最后一句多 2–3 秒。音乐比成片短时渲染器会警告，循环接缝通常听得出来，换更长的曲子或事先做好无缝循环。

保留干声的动态。渲染器最后用 alimiter 限峰，但 PCM 不削波不等于 AAC 编码后没有 intersample peak，有条件时检查最终编码结果。响度数值不能代替试听；不要把固定增益说成专业母带标准。

## 旧真人视频和新旁白

研究者想露面又来不及重拍时，看旧视频能否提供一段完整、清楚、与本次提案相符的自我介绍。核对身份、姓名、职务是否仍然准确；旧项目的专有说法、过时数据或本次提案没有的承诺，不能因为画面好看就带进来。记录源文件和选用的起止时间（clip_in/clip_out），不覆盖源片。不是每部研究片都必须露脸。

在完整句后、自然停顿处切。真人片段作为时间线里的一个视频镜头，和图片镜头一起用 `render_video.py` 一次渲染：同一条配乐、同一种字幕样式，开场字幕也来自认可稿。不要把真人段单独渲染后再拼接。

真人段的声音按情况三选一：

1. **原声可用**：`place_audio.py "presenter.mp4@0:in=0.9,out=9.1"` 把原声放进人声轨，和画面用同样的起止点。
2. **原声不可用（混响、底噪、旧配乐），但研究者另录了同样的句子**：`sync_to_footage.py presenter.mp4 note.opus work/intro_voice.wav --clip-in 0.9 --clip-out 9.1 --lufs -16 --asr-check --language en`。它在停顿处把录音切成短句，用 DTW 找到每句在画面里的位置，逐句轻微变速（0.85–1.2）后精确放置；残差大的句子会在内部停顿处继续拆分。看 `--asr-check` 的逐词差（±0.1 秒内属于 ASR 噪声），再看预览里的嘴型。原声里有音乐底时也能用，因为 DTW 比的是整段的音色轨迹。
3. **只能用克隆或别人的声音**：嘴部可见时不要配上去，改用肖像或资料画面。

旧视频自带的配乐必须去掉（它不进人声轨），全片只用一条配乐。不要在嘴部可见时冻结画面或另配口播。想用这位研究者的声音生成新台词时，先按 voice.md 核对授权；复用视频不等于授权克隆声音。

真实录音紧挨着克隆旁白时，音色差异会被放大。差异明显时如实告诉用户，最可靠的办法是请本人按稿录一遍（给出逐句稿）。轻度均衡、降噪和连续的配乐只能缓和接缝。新增片段会改变全片时间轴：重拼人声轨，重新取词时间、字幕和时间线。

## 预览、验证与交付

先对改动的镜头和声音接点做短预览：`render_video.py` 加 `--start 40 --end 55` 只渲染这一段，混音和淡入淡出与完整片完全相同。实际看、听口型、运动、字幕和音乐闪避是否自然；静态抽帧、ASR 和峰值数值代替不了看和听。长片渲染放后台运行，完成后再检查。

完整片的最低检查是跑 `check_output.py`，加上提交限制和 `--ref`（人声轨在片中的起点用 `--ref-offset`）。它报告音视频时长是否一致、时长和大小、编码、整体响度和真峰值、第一次出声的时间，并在全片 6 处用互相关核对人声的位置：整体偏移超过 40 ms 或找不到人声都算错误。只有它通过才算“时序没问题”。此外还要看完结尾；看过新增画面和所有改过的转场；核对相关口播和字幕；听过音乐与人声的关系。环境无法实际播放时，明确说明验证到了哪一步。

编码按提交规范选择；兼容性最好的是 MP4/H.264、yuv420p、AAC、faststart（渲染器的默认输出）。720p/24fps 是轻量的选择，不是所有项目的默认值；按要求改时间线里的 `video`，文件太大时提高 `--crf`。

`work/` 保留原图、干声、音乐、字幕、时间线、来源清单和历史版本，方便下次只改必要的部分；不擅自删除历史版本。新一版放进新目录（例如 `work/pipeline_v6/`、`cards/out_v6/`），只复制要改的输入，旧版本和已交付的成品保持原样，状态记录里写明每版改了什么，让用户对比后再决定用哪版。

用户在手机上或通过远程控制看进度时，聊天里发送的文件大约超过 30 MB 就收不到。成片超过这个大小时，另做一个预览发过去（例如 `ffmpeg -i film.mp4 -c:v libx264 -preset slow -crf 26 -c:a aac -b:a 160k -movflags +faststart preview.mp4`），说明它只是压缩预览，完整片在哪个路径。外发目录只放用户需要的完整成片，以及用户要的 PPTX、逐字稿或 SRT；短预览另附，不代替完整片。

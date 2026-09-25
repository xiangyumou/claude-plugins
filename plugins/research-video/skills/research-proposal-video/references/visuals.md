# 参考视频、素材与生成图

## 不止是给 PPT 配音乐

看用户给的实际参考视频或页面，观察开头、正文、过渡和结尾：人物、照片、图表各占多少，镜头多长，字幕、旁白、音乐怎么进出，品牌怎么收尾。没听过音轨就不要猜音乐。

“内容对，但无聊”通常要改呈现方式：把论点变成相关的场景、动作、研究工作或示意图，减少长时间的文字页。BGM 代替不了视觉叙事。不要直接复制参考片的音乐或受保护的画面。

## 素材处理

内部清单记录每个文件的来源、内容、对应的口播短句、真实性和使用限制。优先用真实的团队、论文、标志和产品素材，生成图补充情境。拿不到的产品不能用虚构截图冒充真实演示。

文字卡片（标题、数据、流程、团队）可以用 HTML/CSS 排版，再用 Playwright 按成片分辨率截图，比在 Pillow 里画字更好调，也便于统一字体和配色。用 `scripts/shoot_cards.py` 截图：页面定义 `SCENES`（卡片 id 列表）和 `render(id)`，脚本逐张截图，同时检查文字是否超出卡片或画面、两段文字是否叠在一起、曲线/坐标轴/网格线是否穿过文字，有问题时返回非零。标签压线、坐标轴刻度出界、标签被裁掉这类问题，在缩略图上很难看出来，用户在成片里却一眼就看到。有意让装饰线穿过标题时，给那个元素加 `data-allow-overlap`。检查只管几何，配色、层次和信息是否正确仍要看截图。逐步显示的卡片保持同一版式、只改颜色或透明度，并且不加推近（见 editing-and-delivery.md）。

机构和合作方标志优先取官网或 Wikimedia Commons 的原始文件（SVG/透明 PNG），记下 URL；https 失败时可以试 http 或官方的其它镜像，但不绕过验证码或登录。论文元数据（题名、作者、期刊、年份、DOI）用 Crossref API 查（常带摘要）；PubMed 网页出验证码时改用 E-utilities（`esearch.fcgi`/`efetch.fcgi`，返回题录和摘要）；开放获取的全文和图在 PMC。出版社页面挡住时请用户提供 PDF，不绕过验证码或付费墙。用 `pdftoppm` 渲染首页，裁出题名和作者区，配上“期刊 · 年份”标签，这就是真实的“代表作”画面。

按文件名模式查找用户给的文件，不要假定时间戳完全一致。做联系表（contact sheet）检查构图、手部、器械、人物连续性和标题位置。优先用原图，不用带边框的截图。按故事需要用图，不为凑数量打乱节奏。

## 数据图

数据图画面上的每条曲线、每根柱子都是一个事实主张，和口播里的数字同样要有出处。先找真实数据：公认的参考标准（例如胎儿体重百分位表），团队已发表论文的表格和图（准确率、病例的特征贡献），公开的统计数据。原文只有图时，可以按像素读数：先用两个已知刻度确定比例，从零线量柱长或点位，在事实表里注明“从图中读取、近似值”。

找不到数据就换一种画面：研究设计（比较哪些人群、哪些时间点）、流程、时间轴或概念图，不带数字和假的坐标。不要画一张看起来像结果的“示意”数据图，再贴上 illustrative、示意、未验证之类的小字：观众记住的是图形，看不到小字，评审会把它当成结果或当成造假。出处记在事实表和状态记录里；画面上要不要标注，按用户或主办方的要求。

## 由用户生成图片

每条提示词都要独立完整，包含用途、动作、构图、光线、色调、画幅和限制。写 “matching the attached image” 时，必须说明要上传哪张参考图；没有参考图也要给出完整描述。需要人物连续时，写明人物、服装和环境特征。

为当前项目确定统一的画幅、摄影或插画风格、主色和人物连续性，不沿用上一个项目的配色或场景。例如：16:9、纪实摄影感、柔和自然光、克制的主色、真实的人体比例、符合项目所在地；不要每张都是同一人物的同一坐姿。每条提示词写明对应的口播、主体动作、场景、给标题留的空白、光线和真实度。生成的人物只作情境图，不标成真实团队。

下面是一个孕产研究项目的示例，按当前项目改写地点、人物、配色和留白方向，不要照搬：

> Create a photorealistic editorial image for an academic prenatal-care research video, landscape 16:9. In a contemporary Malaysian antenatal consultation room, a fictional Southeast Asian female obstetrician in her forties listens attentively to a seated pregnant woman. Use a medium-wide, eye-level composition, realistic hands and anatomy, soft window light, restrained teal furnishings and warm neutral colours. Place the people toward the right, leaving calm space on the left for a title added later. Keep documents and screens unreadable. No text, logos, watermarks, diagnostic claims or identifiable real people.

需要同一人物时追加一句，例如 “Use the uploaded pregnancy portrait as the visual reference for the same fictional patient, including clothing, headscarf and lighting”，并告诉用户上传哪张已认可的图。

提示词数量由镜头节奏决定，不设固定张数。一部 1–2 分钟的片子常见 8–12 条，每条绑定一句口播，覆盖问题、研究方法、检查或实验、跨学科讨论、示意解释、多样人群、沟通、科研指导和有希望感的收尾。这是一个参考范围，不是所有学科的清单。每条都能单独复制使用，不依赖前一条的隐含描述。

根据每幅图决定标题位置，避开脸、手和关键操作；图里没有留白就少放标题，不强行遮挡。演讲者的姓名和头衔只放在对应的真实人物画面上。

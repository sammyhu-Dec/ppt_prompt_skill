# PPT Prompt Skill

`ppt_prompt_skill` 是一个把企业介绍类 PowerPoint 自动转成视频策划素材的本地 Python 项目。它的核心目标不是简单地把 PPT 页面逐页改写成视频，而是建立一条清晰的内容生产链路：先抽取 PPT 信息，再形成语义中间态，再从“讲故事”的角度决定取舍、合并和节奏，最后生成分镜脚本和可复制到文生视频工具里的 Prompt。

当前项目已经支持两种运行方式：

- `mock`：不调用大模型，用规则和模板生成示例结果，适合验证流程。
- `openai`：调用 OpenAI 兼容接口，适合使用真实大模型生成高质量内容。

## 当前核心流程

```text
PPTX
  ↓
extracted_slides.json      PPT 文本抽取结果
  ↓
psd.json                   PPT 语义中间态文档
  ↓
story_plan.json            故事策划：决定讲什么、合并什么、跳过什么、每段多久
  ↓
storyboard.json            分镜脚本
  ↓
video_prompts.json         文生视频 Prompt JSON
video_prompts.md           方便复制使用的 Markdown
```

最重要的设计变化是新增了 `story_plan.json`。项目不再默认“一页 PPT = 一个分镜”，而是在 PSD 之后先理解整份介绍的故事主线，然后决定哪些内容要讲、哪些内容可以浓缩、哪些内容可以不讲，再生成分镜。

## 解决的问题

企业介绍 PPT 通常信息密度很高，包含公司介绍、发展历程、团队、产品、技术路线、生态伙伴、应用场景、荣誉资质等内容。直接逐页转成视频会带来几个问题：

- 分镜数量和 PPT 页数强绑定，视频节奏僵硬。
- 每个分镜时长容易固定为 6-7 秒，缺少节奏变化。
- 细碎数据、名单、地址、荣誉容易被逐条复述，视频表达会变得冗长。
- 观众看到的是信息罗列，而不是一个完整的企业故事。

当前项目用 `story_plan` 阶段解决这些问题：先决定叙事主线和内容取舍，再进入分镜和 Prompt 生成。

## 示例说明

公开仓库只保留一个轻量示例文件：

```text
input/demo.pptx
```

真实企业介绍 PPT、Web 上传缓存和历史输出结果不提交到仓库。你可以把自己的 `.pptx` 文件放到 `input/` 目录，然后按 README 的命令运行。生成结果会写入 `output/`，该目录也会被 Git 忽略。

## 项目结构

```text
ppt_prompt_skill/
├── README.md
├── requirements.txt
├── main.py
├── web_app.py
├── config.py
├── .env.example
│
├── input/
│   ├── demo.pptx
│   └── .gitkeep
│
├── output/
│   └── .gitkeep
│
├── app/
│   ├── extractor/
│   │   └── ppt_extractor.py
│   ├── agents/
│   │   ├── base_llm.py
│   │   ├── psd_agent.py
│   │   ├── story_plan_agent.py
│   │   ├── storyboard_agent.py
│   │   └── prompt_agent.py
│   ├── schemas/
│   │   └── models.py
│   ├── prompts/
│   │   ├── psd_prompt.txt
│   │   ├── story_plan_prompt.txt
│   │   ├── storyboard_prompt.txt
│   │   └── video_prompt.txt
│   ├── pipeline/
│   │   └── skill_pipeline.py
│   ├── utils/
│   │   ├── duration_utils.py
│   │   ├── file_utils.py
│   │   ├── json_utils.py
│   │   └── markdown_utils.py
│   └── web/
│       ├── static/
│       └── templates/
│
└── tests/
    └── test_extractor.py
```

## 入口脚本

入口文件是 `main.py`。

命令格式：

```bash
python main.py \
  --input input/demo.pptx \
  --output output/demo_openai \
  --provider openai
```

参数说明：

- `--input` / `-i`：输入 PPTX 文件路径，必填。
- `--output` / `-o`：输出目录，默认读取 `config.OUTPUT_DIR`。
- `--provider`：生成模式，可选 `mock` 或 `openai`。

运行成功后会打印输出目录和生成文件列表。

## 环境变量

配置文件是 `config.py`，会通过 `python-dotenv` 读取 `.env`。

`.env.example` 提供了模板：

```env
LLM_PROVIDER=mock

OPENAI_API_KEY=
OPENAI_BASE_URL=
OPENAI_TIMEOUT=180
OPENAI_MODEL=gpt-4o-mini

OUTPUT_DIR=output
DEBUG=true
```

字段说明：

- `LLM_PROVIDER`：默认 provider，可设为 `mock` 或 `openai`。
- `OPENAI_API_KEY`：OpenAI 兼容接口的 API Key。
- `OPENAI_BASE_URL`：OpenAI 兼容服务地址，例如内网 LiteLLM / vLLM / 代理服务。
- `OPENAI_TIMEOUT`：请求超时时间，单位秒。大 PPT 和慢模型建议调大。
- `OPENAI_MODEL`：模型名称，例如 `ext-general`。
- `OUTPUT_DIR`：默认输出目录。
- `DEBUG`：调试开关，目前主要作为配置保留。

注意：不要把真实 `.env` 里的 API Key 写入文档或提交到仓库。

## 安装依赖

```bash
cd /path/to/ppt_prompt_skill
pip install -r requirements.txt
```

主要依赖：

- `python-pptx`：读取 `.pptx` 文件。
- `pydantic`：定义和校验结构化中间数据。
- `python-dotenv`：读取 `.env`。
- `openai`：调用 OpenAI 兼容接口。
- `pytest`：测试。

## 运行方式

### 1. Mock 模式

Mock 模式不调用真实大模型，适合快速确认流程是否能跑通。

```bash
python main.py \
  --input input/demo.pptx \
  --output output/demo_mock \
  --provider mock
```

Mock 模式会使用规则和模板生成：

- PPT 页面语义
- 故事策划
- 分镜脚本
- 视频 Prompt

它的结果不代表最终文案质量，但适合测试文件路径、依赖和输出结构。

### 2. 真实大模型模式

真实大模型模式使用 OpenAI 兼容接口。

```bash
python main.py \
  --input input/demo.pptx \
  --output output/demo_openai \
  --provider openai
```

真实模式下，项目会进行多次小颗粒模型调用，而不是一次性让模型生成整份超长 JSON。这样做是为了降低超时和 JSON 格式错误概率。



## Web 前端工作台

项目提供一个轻量 Web UI，用于上传 PPT、查看各阶段中间结果、编辑 `story_plan.json`，并导出最终视频 Prompt。

启动方式：

```bash
cd /path/to/ppt_prompt_skill
python web_app.py
```

默认地址：

```text
http://127.0.0.1:7860
```

页面能力：

- 上传 `.pptx` 文件并选择 `mock` 或 `openai` provider。
- 自动运行完整 pipeline。
- 上传后显示转换进度条，阶段包括 Extract、PSD、Story Plan、Storyboard、Prompts。
- 查看 `extracted_slides.json`、`psd.json`、`story_plan.json`、`storyboard.json`、`video_prompts.json`、`video_prompts.md`。
- 在页面中编辑 `story_plan.json`。
- 保存 Story Plan 后，从 story plan 阶段重新生成 storyboard 和 video prompts。
- 复制 Markdown Prompt。
- 下载 `video_prompts.md` 或 `video_prompts.json`。

Web 相关文件：

```text
web_app.py
app/web/templates/index.html
app/web/static/styles.css
app/web/static/app.js
```

真实大模型模式会同步等待模型返回，完整 PPT 可能需要数分钟。快速验证建议先选择 `mock`。

### Web 访问和部署说明

默认 `WEB_HOST=127.0.0.1` 时，网站只监听本机回环地址，通常只有运行服务的这台机器自己能打开：

```text
http://127.0.0.1:7860
```

如果服务进程还在运行，即使浏览器页面关掉，下次再打开这个地址仍然可以访问；如果机器重启、进程被 kill、终端会话结束导致服务退出，就需要重新启动。

如果希望同一局域网内的电脑或手机访问，可以让 Flask 监听所有网卡：

```bash
WEB_HOST=0.0.0.0 WEB_PORT=7860 python web_app.py
```

然后在手机或其他电脑上访问运行服务器的局域网 IP，例如：

```text
http://192.168.x.x:7860
```

长期运行建议使用 `systemd`、Docker、Supervisor 或 Nginx 反向代理，而不是手动开一个终端。公网随时访问时，不建议使用 GitHub Pages，因为本项目需要 Python 后端、PPT 上传、文件处理、大模型 API Key 和本地输出目录；GitHub Pages 只能托管静态网页，不能运行这类后端服务。

更合适的长期部署方式：

- 局域网长期使用：服务器上用 `systemd` 守护 Flask/Gunicorn，`WEB_HOST=0.0.0.0`，手机连同一 Wi-Fi 访问服务器 IP。
- 外网安全访问：使用 Tailscale、ZeroTier、WireGuard 或 Cloudflare Tunnel，把本机服务安全暴露给自己的设备。
- 公网正式服务：部署到云服务器/VPS，用 Gunicorn + Nginx + HTTPS + 登录鉴权。
- 如果仍使用内网模型地址，例如 `192.168.20.64:4000/v1`，云服务器必须能访问该模型服务；否则需要把模型服务也部署到公网可达环境，或通过 VPN/专线/Tunnel 打通。

## 各阶段说明

### 1. PPT 文本抽取

实现文件：`app/extractor/ppt_extractor.py`

输入：`.pptx`

输出：`extracted_slides.json`

主要工作：

- 使用 `python-pptx` 读取 PPT。
- 遍历每页 slide 的 shapes。
- 提取文本框文本。
- 支持组合形状的递归文本提取。
- 去重但保留原始顺序。
- 统计每页图片数量。
- 以每页第一个非空文本作为粗略标题。

输出结构示例：

```json
{
  "file_name": "demo.pptx",
  "slide_count": 3,
  "slides": [
    {
      "page": 1,
      "title": "Demo Title",
      "raw_text": "...",
      "image_count": 2,
      "notes": ""
    }
  ]
}
```

当前边界：

- 不做 OCR。
- 不解析图片内容。
- 不理解版式视觉布局。
- 不深度解析图表。
- 不读取 speaker notes。

### 2. PSD 语义中间态

实现文件：`app/agents/psd_agent.py`

Prompt 文件：`app/prompts/psd_prompt.txt`

输入：`extracted_slides.json`

输出：`psd.json`

PSD 指 `Presentation Semantic Document`，用于把 PPT 的原始文本整理成结构化语义。

主要字段：

- `deck_title`：整份 PPT 标题。
- `deck_type`：PPT 类型。
- `core_message`：核心信息。
- `target_style`：目标视频风格。
- `slides`：每页语义列表。

每页语义包含：

- `page`：页码。
- `slide_type`：页面类型，如 `cover`、`company_intro`、`product`、`technology`、`application`、`summary`、`other`。
- `title`：页面标题。
- `raw_text`：页面原始文本。
- `key_points`：关键信息。
- `narrative_role`：该页在视频叙事中的作用。
- `visual_direction`：适合被视频化表达成什么画面。

真实大模型模式下，PSD 生成采用“小颗粒调用”：

1. 先根据整份 PPT 的标题列表生成 deck summary。
2. 再逐页生成 `SlideSemantic`。
3. 最后由 Python 组装成完整 `PresentationSemanticDocument`。

这样比一次性生成完整 PSD 更稳定。

### 3. Story Plan 故事策划

实现文件：`app/agents/story_plan_agent.py`

Prompt 文件：`app/prompts/story_plan_prompt.txt`

输入：`psd.json`

输出：`story_plan.json`

这是当前项目最关键的一步。它的职责不是写最终分镜，而是先决定“整支视频应该怎么讲”。

Story Plan 会输出：

- `story_title`：故事标题。
- `narrative_arc`：整支视频的叙事主线。
- `target_total_duration`：目标总时长。
- `selected_slides`：决定保留讲述的 PPT 页。
- `skipped_slides`：决定跳过或不单独讲述的 PPT 页。
- `skip_reason`：跳过原因。
- `segments`：故事段落列表。

每个故事段落包含：

- `segment_id`：故事段编号。
- `source_slides`：参考的 PPT 页，可以是一页、多页，也可以为空。
- `title`：段落标题。
- `key_message`：该段要传达的核心信息。
- `story_role`：该段在叙事中的作用。
- `include_reason`：为什么保留这一段。
- `visual_strategy`：适合的视频化表达策略。
- `duration`：建议分镜时长。

当前时长规则：

- 所有段落控制在 `2-8s` 左右。
- 快速过渡、Logo、地点、荣誉闪回：`2-3s`。
- 普通说明：`4-5s`。
- 核心能力、产品、技术、关键成果：`6-8s`。
- 不鼓励所有分镜都固定为 `6s` 或 `7s`。

代码中通过 `app/utils/duration_utils.py` 对模型输出的时长做归一化：

- `1s` 会被拉到 `2s`。
- `9s` 会被压到 `8s`。
- `6秒` 会规范为 `6s`。

### 4. Storyboard 分镜脚本

实现文件：`app/agents/storyboard_agent.py`

Prompt 文件：`app/prompts/storyboard_prompt.txt`

输入：`psd.json` + `story_plan.json`

输出：`storyboard.json`

Storyboard 不再按 PPT 页生成，而是按 `story_plan.segments` 生成。

每个分镜包含：

- `scene_id`：分镜编号。
- `source_slides`：参考 PPT 页。
- `duration`：继承 story plan 的 `2-8s` 节奏。
- `scene_goal`：分镜目标。
- `visual_content`：画面内容。
- `camera`：运镜方式。
- `shot_type`：镜头类型。
- `transition`：转场方式。
- `subtitle`：字幕。
- `voiceover`：旁白。

真实大模型模式下，项目会逐个故事段落生成单个分镜，避免一次性生成大量 JSON。

### 5. Video Prompt 生成

实现文件：`app/agents/prompt_agent.py`

Prompt 文件：`app/prompts/video_prompt.txt`

输入：`storyboard.json`

输出：

- `video_prompts.json`
- `video_prompts.md`

每条视频 Prompt 包含：

- `scene_id`：对应分镜编号。
- `duration`：继承 storyboard 的 `2-8s` 时长。
- `prompt`：适合文生视频模型使用的中文画面描述。
- `negative_prompt`：负面提示词。

`video_prompts.md` 是为了方便复制到文生视频工具中，内容和 JSON 对应。

## LLM 调用机制

实现文件：`app/agents/base_llm.py`

当前项目封装了一个 `OpenAIJsonClient`，用于调用 OpenAI 兼容接口。

它做了几件重要的稳定性处理：

1. 支持 `OPENAI_BASE_URL`

   可以连接 OpenAI 官方接口，也可以连接内网 LiteLLM、vLLM 或其他兼容服务。

2. 支持 `OPENAI_TIMEOUT`

   大模型响应慢时可以调整超时时间。

3. 优先使用 JSON mode

   请求会优先带上：

   ```python
   response_format={"type": "json_object"}
   ```

4. 自动兼容不支持 `response_format` 的模型

   如果模型服务返回不支持 `response_format`，客户端会自动降级为普通 chat completion。

5. 解析 Markdown 包裹的 JSON

   如果模型返回 ```json 代码块，客户端会先剥离 Markdown fence。

6. 自动修复非法 JSON

   如果模型返回的 JSON 语法不合法，客户端会再调用模型做一次 JSON 修复。

7. 校验必要字段

   每个 agent 会传入 `expected_keys`，防止模型返回一个合法但业务字段不对的 JSON。

## 输出文件说明

### `extracted_slides.json`

PPT 文本抽取结果，是最接近原始 PPT 的结构化数据。

### `psd.json`

PPT 语义中间态，负责把页面文本变成可供策划使用的语义信息。

### `story_plan.json`

故事策划结果，是当前项目的关键产物。建议优先检查它，因为它决定后续视频是否“像一个故事”。

重点检查：

- `narrative_arc` 是否清晰。
- `selected_slides` 是否合理。
- `skipped_slides` 是否符合预期。
- `segments` 是否完成了合并、浓缩和取舍。
- `duration` 是否有节奏变化。

### `storyboard.json`

分镜脚本结果。它应该服务 `story_plan`，而不是机械对应 PPT 页。

重点检查：

- 每个分镜是否只表达一个核心信息。
- 运镜、镜头类型、转场是否适合该段时长。
- 字幕和旁白是否简洁。

### `video_prompts.json`

结构化视频 Prompt，适合程序消费或后续接视频生成 API。

### `video_prompts.md`

Markdown 版视频 Prompt，适合人工复制到文生视频工具。

## 输入输出目录

仓库包含：

```text
input/demo.pptx
input/.gitkeep
output/.gitkeep
```

运行后会生成：

```text
output/<run_name>/
├── extracted_slides.json
├── psd.json
├── story_plan.json
├── storyboard.json
├── video_prompts.json
└── video_prompts.md
```

`output/`、`input/uploads/` 和本地真实 PPT 文件会被 Git 忽略，避免提交生成结果、上传缓存或私有素材。

## 推荐检查顺序

每次跑完完整 PPT 后，建议按这个顺序看结果：

1. `extracted_slides.json`

   确认 PPT 文本有没有抽取完整。

2. `psd.json`

   确认每页类型、关键点、叙事作用是否合理。

3. `story_plan.json`

   重点检查。确认模型是否真的理解了整份 PPT，并做了合理取舍。

4. `storyboard.json`

   看分镜是否按故事段落展开，时长是否在 `2-8s`，镜头是否有节奏。

5. `video_prompts.md`

   最后检查可复制的文生视频 Prompt。

## 开发和测试

语法检查：

```bash
python -m compileall app main.py web_app.py config.py
```

运行测试：

```bash
pytest
```

当前测试较轻，主要是 extractor 层的基础测试。后续可以补充：

- duration 归一化测试。
- mock pipeline 端到端测试。
- JSON 修复和 expected_keys 校验测试。
- story_plan 是否生成 2-8s 时长的测试。

## 当前限制

当前版本仍然是文本驱动的 v1：

- 只读取 PPTX 文本，不看页面截图。
- 不做 OCR，所以图片里的文字不会被识别。
- 不理解复杂图表和版式关系。
- 不读取演讲者备注。
- 不直接调用视频生成平台 API。
- 输出质量依赖模型能力和 prompt 质量。
- 真实大模型模式会多次调用模型，完整 19 页 PPT 可能耗时较长。

## 后续升级方向

建议下一阶段可以做：

1. PPT 每页转图片

   把每页转成图片，作为后续 VLM 输入。

2. OCR 与视觉理解

   识别图片中的文字、图表、结构图和产品图。

3. VLM 页面理解

   让模型理解页面布局、视觉重点和图文关系。

4. Story Plan 可编辑

   允许用户手动修改 `story_plan.json` 后，从该阶段继续生成 storyboard 和 prompt。

5. 视频生成 API 对接

   将 `video_prompts.json` 直接发送给视频生成平台。

6. 模板化企业宣传片风格

   提供“科技企业介绍”“产品发布”“融资路演”“行业解决方案”等不同叙事模板。

## 一句话总结

`ppt_prompt_skill` 当前是一条面向企业介绍 PPT 的视频策划流水线：它先把 PPT 变成语义文档，再从故事角度做内容取舍和节奏规划，最后生成 2-8 秒节奏变化的分镜脚本和文生视频 Prompt。

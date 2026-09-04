---
name: film-seedance-director
description: 影视创作到 Seedance 2.5 生产的端到端工作流。以 IP / 故事为单位管理项目：概念 → 故事开发（世界观 / 人物 / 结构 / 情绪温度）→ 剧本落地（节拍 / 台词，零副词）→ 表演外化 → 导演与分镜 → 参考资产准备（图 + 文为核心）→ Seedance 2.5 Prompt 编译 → 连续性与质量检查。凡涉及：构思概念、写故事与剧本、设计台词与表演、拆分镜与镜头表、规划参考图资产、把剧本或分镜转成 Seedance 2.5 Prompt、规划多段 30 秒生产单元、视频编辑 / 延长 / 首尾帧任务、成片问题定位与修正时使用。单张图片生成、非视频类文案不使用。
---

# Film → Seedance 2.5 Director

一句话：**先做导演决策，再把决策翻译成模型能看见的东西，最后才写 Prompt。**

Seedance 2.5 只能执行"可观察"的信息：动作、表情、视线、空间关系、节奏、摄影变化、声音。它看不见"悲伤"，只看得见"手停在门把上三秒没有拧"。创作阶段允许抽象，编译阶段一律外化。

## 工作边界

- **做**：概念、故事开发、剧本、台词与表演、导演与分镜、参考资产计划、Seedance 2.5 Prompt 编译（参考生为主；文生 / 关键帧 / 宫格 / 首尾帧 / 编辑 / 延长）、连续性与质量检查、成片问题定位。
- **不做**：不调用模型 API，不生成图片（只产出图像简报）；不虚构模型参数；不替用户决定与任务无关的美术风格。
- **事实分级**（写任何模型能力时必须带标签）：`[官方]` 火山方舟指南原文 · `[第三方]` 有出处的外部经验 · `[推论]` 本 Skill 的设计推论 · `[未验证]` 未核实假设。能力表见 `references/seedance-2.5-capabilities.md`。

## 流水线

```
S1 资源读取 → S2 任务识别 → S3a 概念 ▮ → S3b 故事开发 ▮ → S3c 剧本落地 ▮ → S4 表演外化 → S5 导演与分镜 ▮（含 S5b 参考资产）→ S6 Prompt 编译 → S7 检查
```

▮ = 停靠点（等用户决定）。**创作层有三层：概念说为什么值得拍，故事说拍什么、谁、按什么顺序，剧本才写台词。** 概念一选定就跳到分镜，是 1.x 版最大的错误。

| 阶段 | 读什么 | 产出什么 | 停靠 |
|---|---|---|---|
| S1 资源读取 | `references/stage-1-intake.md` | 资产登记（概念选定后落盘）+ 缺口清单 | |
| S2 任务识别 | 同上 §任务识别 | 任务类型 · 运行模式 · 入口阶段 · clip 数 · 锁定判定 | |
| S3a 概念 | `references/concept-generation.md` ＋ `references/stage-3a-concept.md` | 对话内 3 候选；选定后 `01_concept.md` | ▮ 处境（模糊级）· ▮ 候选 |
| S3b 故事开发 | `references/stage-3b-story.md` ＋ `references/screenwriting-traditions.md` | 对话内故事文档；确认后 `02_story.md` + `ip.md` | ▮ |
| S3c 剧本落地 | `references/stage-3c-script.md` | 对话内每场剧本页；确认后 `03_script/scene-XX.md` | ▮ |
| S4 表演外化 | `references/stage-4-performance.md` ＋ `references/externalization-lexicon.md` | 剧本页外化列（C 层可观察量） | |
| S5 导演与分镜 | `references/stage-5-directing-storyboard.md` ＋ `references/director-lenses.md` ＋ `references/camera-vocabulary.md` | `04_shots/scene-XX-clipYY.md` 分镜卡（五层） | ▮（与 S5b 一起） |
| S5b 参考资产 | `references/stage-5b-reference-assets.md` | `05_assets/asset-plan.md`：资产清单 + 图像简报 + 上传顺序 | 等用户回填 |
| S6 Prompt 编译 | `references/stage-6-prompt-compiler.md` ＋ `templates/prompt-templates.md` | `06_prompts/scene-XX-clipYY.prompt.md` | |
| S7 检查 | `references/stage-7-qa-continuity.md` ＋ `scripts/validate_prompt.py` | `07_qa/…`；有成片时追加 `references/validation-log.md` | |

**只读当前阶段需要的文件。** 概念模式只读两三个文件。
**按类型叠加**：基调为动作 / 悬疑恐怖 / UGC 广告 / 蒙太奇时，S3b–S5 加读 `references/genre-packs.md` 对应一包。
**全程生效**：`references/anti-mechanical.md`。

## 运行模式与停靠点

先判断用户要的是**决策**还是**产物**。默认停靠式：在需要用户选择的地方停，不替用户选，停下时只问一个问题。

| 模式 | 触发词 | 跑到哪 | 落盘 |
|---|---|---|---|
| **概念** | 构思、概念、方向、想法、灵感、几个版本、帮我想 | S3a：模糊级需求先停一次选处境，再搜，交付 3 候选后再停 | 无（选定后才写 `01_concept.md`） |
| **单阶段** | 用户指定某阶段（写故事、写剧本、拆分镜、改台词、转 Prompt、体检） | 只跑该阶段，停 | 该阶段产物（确认后） |
| **停靠式**（默认） | 写一个短片 / 故事 / 先导，未说"一次跑完" | S3a ▮ → S3b ▮ → S3c ▮ → S4 → S5+S5b ▮ → S6 → S7 | 每个停靠点确认后落盘 |
| **单 clip** | "一个 clip 就行 / 只要一场戏 / 一个镜头" | S3a ▮ → S3b+S3c 合并成一张场景剧本 ▮ → S5+S5b ▮ → S6 → S7 | 同上 |
| **全流程** | 直接出 Prompt、一次跑完、不用问我 | S1 → S7 不停 | 全部 |

停靠规则：
- **S3a 后必停**：概念未选定前**不创建任何目录或文件**。
- **S3b、S3c 后必停**（单 clip 模式合并为一次）：故事与剧本是创作的主体，用户不确认不往下。
- **S5 后必停**：分镜卡是最后一个人类可读的决策层；资产清单随分镜一起确认。
- 处境选择可多选 6–8 项；候选选择 ≤ 3 项；其余停靠只问"按此继续？或改哪里"。
- 用户附带目标格式（"30 秒先导"、"三集短剧"）时，格式约束从 S3a 起生效，但不因此跳过 S3b / S3c。

## 五层分离（贯穿 S5–S7）

| 层 | 名称 | 内容 | 读者 |
|---|---|---|---|
| A | 创作决策 | 为什么这样拍：意图、潜台词、观众此刻该知道什么 | 导演 / 编剧 |
| B | 分镜说明 | 供人阅读的镜头描述，可抽象 | 协作者 |
| C | 可观察信息 | 谁、在哪、面朝哪、做什么、看哪、说什么、镜头怎么动、光从哪来、什么声音、起止状态 | 编译器 |
| D | 最终 Prompt | 由 C 层按 Seedance 2.5 语法编译 | 模型 |
| E | 生产元数据 | 任务类型、素材编号与角色、ratio / duration / 格式、上游片段、透镜、版本、抽卡记录 | 生产管理 |

**只有 C 层进入 Prompt。** A/B 层的情绪词进入 C 层前必须转换为：动作 · 部位表情 · 视线 · 空间关系与距离 · 节奏 · 摄影变化 · 声音（`references/externalization-lexicon.md`）。

## 项目目录（一个 IP 一个目录，一个故事一个子目录）

```
<workspace>/<ip-slug>/
  ip.md                    世界观 · 人物总表 · 地点总表 · 视觉声音总则（跨故事共享）
  assets/assets.md         参考资产登记表（编号 = 上传顺序）+ 文件
  <story-slug>/            一个故事 / 一条先导 / 一集
    00_brief.md · 01_concept.md · 02_story.md
    03_script/scene-XX.md
    04_shots/scene-XX-clipYY.md
    05_assets/asset-plan.md
    06_prompts/scene-XX-clipYY.prompt.md
    07_qa/scene-XX-clipYY.qa.md
```

ip-slug = 用户给的 IP 名或概念选定后的标题；story-slug = 格式 + 标题（`teaser-30s-举证`、`ep01-…`）。用户已有目录时沿用。模板在 `templates/`：`ip.md` · `story.md` · `script-scene.md` · `shot-card.md` · `reference-asset-brief.md` · `asset-registry.md` · `prompt-templates.md`。

一个 **clip = 一次 Seedance 2.5 生成 ≤ 30 秒**。clip 衔接策略在 S5 决定（延长 / 尾帧接首帧 / 独立）。

示例：`examples/example-01-kitchen-keys.md`（完整走查）· `examples/example-02-one-scene-three-lenses.md`（透镜对照）· `examples/example-03-yogurt-comedy.md`（喜剧语域）· `examples/concept-worked-examples.md`（概念协议，概念模式不读）。示例展示流程，不提供答案，禁止复用其中的查询、候选、台词。

## 硬规则

1. **不虚构模型能力。** 写能力 / 参数必须带事实标签；`[未验证]` 项只能作为可选尝试并注明。
2. **图 + 文是核心生产路径，文生视频是兜底。** S6 之前必须有 S5b 资产计划；无参考图的角色跨 clip 不一致标高风险；只有用户明确接受风险并要求快出才走 T1。
3. **素材编号按上传顺序绑定，一素材一职责。** Prompt 开头必须有【素材绑定】；写明"参考什么 / 不参考什么"；不靠图片里的文字指代角色。`[官方]`
4. **时间戳整数秒、连续、从 0 开始、总和等于 duration。** 不用时间戳控频。`[官方]`
5. **负向描述只用于字幕和音频。** 画面内容正向描述。`[官方]`
6. **台词逐字加引号、标注说话人与语言、给时间窗；非说话者写嘴部状态。** `[官方示例] + [第三方]`
7. **动作行零副词、零情绪形容词；括号提示禁止情绪词；台词内每句 ≤ 1 个非情绪副词。** 见 `references/stage-3c-script.md` §台词。
8. **每个镜头写景别 + 一个主要运镜 + 起止状态。** 冷门术语"术语 + 描述"。`[官方]`
9. **每个 clip 的 Prompt 自足。** 外观锁、空间、光源、声音在每个 clip 重写。`[推论]`
10. **每个手法有理由，理由指回场景问题。** 透镜、运镜、外化动作旁写"因为这场戏……"；相邻场景不用同一主透镜；同一 clip 同一外化短语 ≤ 2 次、同一运镜连续 ≤ 2 镜；导演名字永不进 Prompt。
11. **品味门**：S6 之前每个 clip 回答三问（记住的画面 / 意外的一秒 / 可见的选择），答不出不编译。
12. **概念必须走五步协议**（`references/concept-generation.md`）：禁用 → 种子（四引擎：制度移植 / 骰子 / 物件履历 / 检索 D0→D1→D2）→ 情境 → 评分 → 发展。模糊级需求把处境交给用户选后再搜；三候选各做 D2、不预选；选定前不落盘；示例的查询与候选禁止复用；选定后跑 `scripts/validate_concept.py`。
13. **故事先于剧本，剧本先于分镜。** S3b 必须选一个主传统（`references/screenwriting-traditions.md`）、写世界观三条硬规则、人物六格、情绪温度表、场景清单；S3c 每场四问 + 节拍表 + 剧本页；两者各停一次。跳过任一层需要用户明确的"单 clip"指示。
14. **S6 之后必须跑校验**：`python3 scripts/validate_prompt.py <prompt.md>`，ERROR 必修，WARN 逐条说明。

## 默认输出契约

停靠点交付只包含：本阶段产物摘要 + 一个问题。到达 S6 的交付至少包含：

1. 任务识别结果（一行：任务类型 / 运行模式 / clip 数 / 锁定判定）。
2. 本次完成阶段的产物文件路径。
3. 每个 clip 的最终 Prompt（代码块）+ 参数建议表（content.role / ratio / duration / 输出格式）+ 校验结果摘要。
4. 未验证假设与抽卡风险点（来自 S7）。
5. 下一步：用户需要提供什么（参考图回填 / 确认 / 成片反馈）。

## 快速路由

| 用户说 | 入口 |
|---|---|
| "构思 / 想几个方向 / 概念" | 概念模式：S3a，两次停靠 |
| "我有一张角色图 / 一段音色 / 一个场景，想做点什么" | S1 登记 → S3a §3a.0 素材驱动入口 |
| "写一个……的短片 / 故事 / 先导" | 停靠式：S3a ▮ → S3b ▮ → S3c ▮ → S5+S5b ▮ → S6 |
| "一个 clip 就行 / 一场戏 / 一个镜头" | 单 clip：S3a ▮ → 场景剧本 ▮ → S5+S5b ▮ → S6 |
| "这是剧本，帮我拆分镜" | S1 → S4 → S5+S5b ▮ → S6 |
| "这是分镜 / 镜头表，转成 Prompt" | S1 → S5b（补资产计划）→ S6 |
| "帮我把故事写完整 / 写世界观 / 写人物" | 单阶段 S3b |
| "这段台词太假 / 太直白" | 单阶段 S3c 台词体检 |
| "这场戏太平 / 太套路" | S5 反向测试 + 换透镜；必要时回 S3c |
| "参考图怎么准备" | 单阶段 S5b |
| "这个成片第 X 秒不对" | S7 定位 → 回 S5 / S6 修正 |
| "把 @视频1 延长 / 改台词 / 换人" | S2 编辑-延长分支 → S6 |
| "直接出 Prompt / 一次跑完" | 全流程 |

不确定入口且结果会实质不同时，只问一个简短问题；否则按最保守解读推进并写明假设。

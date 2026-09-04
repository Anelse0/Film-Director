# film-seedance-director

影视创作 → Seedance 2.5 生产的可运行工作流 Skill。调用：`/film-seedance-director` 或在对话中描述任务（写场景、拆分镜、转 Prompt、改成片）。

## 一句话

先做导演决策，再把决策翻译成模型能看见的东西，最后才写 Prompt。

## 流水线

```
S1 资源读取 → S2 任务识别 → S3a 概念 → S3b 故事与场景 → S4 台词与表演 → S5 导演与分镜 → S6 Prompt 编译 → S7 检查
```

可从任意阶段进入（有剧本从 S5，有分镜从 S6，改成片从 S7）。

## 文件地图

| 文件 | 何时读 |
|---|---|
| `SKILL.md` | 入口：路由、五层分离、硬规则、输出契约 |
| `references/seedance-2.5-capabilities.md` | 写任何模型能力/参数前；事实分级表 |
| `references/stage-1-intake.md` | S1 / S2 |
| `references/stage-2a-concept.md` | S3a 概念：前提 / 主控句 / 三问 / 反套路 |
| `references/stage-2-story-scene.md` | S3b |
| `references/director-lenses.md` | S3b / S5：14 个导演透镜（问题 → 可观察量 → 误用信号） |
| `references/anti-mechanical.md` | 全程：防机械套用规则与品味门 |
| `references/genre-packs.md` | 动作 / 悬疑恐怖 / UGC 广告 / 蒙太奇 四个类型包 |
| `references/validation-log.md` | 成片验证账本：把 [推论] 变成 [已验证] 或 [已推翻] |
| `references/stage-3-dialogue-performance.md` | S4 |
| `references/externalization-lexicon.md` | S4–S6 任何时候出现情绪词 |
| `references/stage-4-directing-storyboard.md` | S5 |
| `references/camera-vocabulary.md` | S5 / S6 写镜头语 |
| `references/stage-5-prompt-compiler.md` | S6 |
| `references/stage-6-qa-continuity.md` | S7 |
| `references/source-analysis.md` | 审计 / 更新来源时 |
| `templates/*.md` | 各阶段产物骨架 |
| `scripts/validate_prompt.py` | S6 之后必跑 |
| `examples/example-01-kitchen-keys*.md` | 完整走查 + 通过校验的 Prompt |
| `examples/example-02-one-scene-three-lenses.md` | 同一场戏三个透镜的对照，含一版通过校验的 Prompt |

## 校验脚本

```bash
python3 ~/.claude/skills/film-seedance-director/scripts/validate_prompt.py <prompt.md> [--duration N] [--json]
```

退出码 0 = 无 ERROR。检查项列表见脚本头部 docstring。传入多个 prompt 文件时额外做跨 clip 检查（相邻 clip 同一主透镜、外化短语跨 clip 重复）。

## 项目目录约定

```
<project>/00_brief.md · 01_bible/ · 02_script/ · 03_shots/ · 04_prompts/ · 05_qa/
```

## 事实来源

- `[官方]` 火山方舟《Doubao Seedance 2.5 提示词指南》（2026 版，38 页）
- `[第三方]` Higgsfield、fal.ai、rundiffusion、runware、the-decoder、mindstudio 等（见 `references/source-analysis.md`）
- 分辨率各来源不一致（480p/720p/1080p/4K），Skill 内标为"以平台为准"。

## 安装

```bash
git clone https://github.com/Anelse0/Film-Director.git ~/.claude/skills/film-seedance-director
```

更新：在该目录 `git pull`。目录名必须保持 `film-seedance-director`，与 `SKILL.md` 的 `name` 一致。

## 版本管理

- 语义化版本，记录在 `VERSION` 与 `CHANGELOG.md`。
  - **主版本**：流水线阶段或五层分离规则变化，旧项目目录需要迁移。
  - **次版本**：新增透镜 / 类型包 / 校验项 / 模板字段，向后兼容。
  - **修订**：措辞、示例、误报修复。
- 每次改动跑 `bash tests/run_tests.sh`；GitHub Actions 在 push 与 PR 时自动跑。
- 模型能力标签变更必须同时登记在 `references/validation-log.md` 的"标签变更登记"表。

## 维护

- 模型能力更新 → 只改 `references/seedance-2.5-capabilities.md`，并保留事实标签。
- 新任务类型 → 在 `templates/prompt-templates.md` 加骨架，在 `stage-1-intake.md` 判定树加分支，在校验脚本加触发词。
- 校验脚本回归：`examples/bad-example.prompt.md` 应报 ≥ 6 个 ERROR；`example-01-kitchen-keys.prompt.md` 应 0 ERROR。

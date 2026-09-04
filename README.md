# film-seedance-director

影视创作 → Seedance 2.5 生产的可运行工作流 Skill。调用：`/film-seedance-director` 或在对话中描述任务（写场景、拆分镜、转 Prompt、改成片）。

## 一句话

先做导演决策，再把决策翻译成模型能看见的东西，最后才写 Prompt。

## 流水线

```
S1 资源读取 → S2 任务识别 → S3a 概念 → S3b 故事与场景 → S4 台词与表演 → S5 导演与分镜 → S6 Prompt 编译 → S7 检查
```

可从任意阶段进入（有剧本从 S5，有分镜从 S6，改成片从 S7）。

交付原则：对话是默认，落盘只在停靠确认后或用户明确要求时。运行模式：**概念**（只到 S3a，对话里给 3 候选后停）、**单阶段**、**停靠式**（默认，S3a 与 S5 后停下等确认）、**全流程**（用户说"一次跑完"）。见 SKILL.md「运行模式与停靠点」。

## 文件地图

| 文件 | 何时读 |
|---|---|
| `SKILL.md` | 入口：路由、五层分离、硬规则、输出契约 |
| `references/seedance-2.5-capabilities.md` | 写任何模型能力/参数前；事实分级表 |
| `references/stage-1-intake.md` | S1 / S2：登记、任务树（R2V 核心）、项目目录 |
| `references/concept-generation.md` | S3a 概念模式契约 + 五步协议（含 D0/D1/D2 检索） |
| `references/stage-3a-concept.md` | S3a 概念长什么样：前提 / 主控句 / 三问 / 反套路 / 交付格式 |
| `references/stage-3b-story.md` | S3b 故事开发：主传统 / 世界观 / 人物六格 / 情绪温度表 / 场景清单 |
| `references/stage-3c-script.md` | S3c 剧本落地：四问 / 节拍表 / 剧本页 / 台词通用关与副词规则 |
| `references/scene-parameters.md` | 场景参数卡：六参数 → 台词 / 表演 / 分镜 / 结构 / 模型执行的规则取值；预设只是参数组合 |
| `references/screenwriting-traditions.md` | 好莱坞 · 欧洲 · 韩国 × 六维度；按格式选主传统；24 条可迁移规则 |
| `references/stage-4-performance.md` | S4 表演外化与台词的模型执行约束 |
| `references/stage-5-directing-storyboard.md` | S5 导演与分镜 |
| `references/stage-5b-reference-assets.md` | S5b 参考资产清单与图像简报（图 + 文核心） |
| `references/stage-6-prompt-compiler.md` | S6 |
| `references/stage-7-qa-continuity.md` | S7 |
| `references/source-analysis.md` | 审计 / 更新来源时 |
| `templates/*.md` | 各阶段产物骨架 |
| `scripts/validate_prompt.py` | S6 之后必跑 |
| `examples/example-01-kitchen-keys*.md` | 完整走查 + 通过校验的 Prompt |
| `examples/example-02-one-scene-three-lenses.md` | 同一场戏三个透镜的对照，含一版通过校验的 Prompt |
| `examples/example-03-yogurt-comedy*.md` | 喜剧走查（三拍 + 反讽落差），通过校验 |
| `examples/example-04-parameters-fight*.md` | 同一套规则，参数卡不同：高强度外放吵架，与示例 01 对照 |

## 校验脚本

```bash
python3 ~/.claude/skills/film-seedance-director/scripts/validate_prompt.py <prompt.md> [--duration N] [--json]
```

退出码 0 = 无 ERROR。检查项列表见脚本头部 docstring。传入多个 prompt 文件时额外做跨 clip 检查（相邻 clip 同一主透镜、外化短语跨 clip 重复）。

## 项目目录约定

```
<workspace>/<ip-slug>/ip.md · assets/ · <story-slug>/{00_brief, 01_concept, 02_story, 03_script/, 04_shots/, 05_assets/, 06_prompts/, 07_qa/}
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
- 校验脚本回归：`bash tests/run_tests.sh`。

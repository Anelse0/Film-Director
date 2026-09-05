# film-seedance-director

版本 **2.3.1**。影视创作 → Seedance 2.5 Prompt 的工作流 Skill；包含可直接使用的情绪表演库与强度/克制调节。调用：`/film-seedance-director` 或在对话中描述任务（写场景、拆分镜、转 Prompt、改成片）。

## 一句话

先做导演决策，再把决策翻译成模型能看见的东西，最后才写 Prompt。

## 流水线

```
S1 资源读取 → S2 任务识别 → S3a 概念 → S3b 故事 → S3c 剧本 → S4 表演 → S5 分镜与参考资产 → S6 Prompt → S7 检查
```

可从已有材料对应阶段进入。纯表演测试走共用 S4 模块，不强制故事、参考图或停靠。可直接说“10秒，从愤怒到委屈，最后忍住眼泪”或“原文直出 Crying”。

交付原则：对话是默认，落盘只在停靠确认后或用户明确要求时。运行模式：**概念**（只到 S3a，对话里给创作判断与候选后停，候选数量由任务定）、**单阶段**、**停靠式**（默认，概念、故事、剧本与分镜按需停靠）、**全流程**（用户说"一次跑完"）。见 SKILL.md「运行模式与停靠点」。

## 文件地图

| 文件 | 何时读 |
|---|---|
| `SKILL.md` | 入口：路由、五层分离、硬规则、输出契约 |
| `references/seedance-2.5-capabilities.md` | 写任何模型能力/参数前；事实分级表 |
| `references/stage-1-intake.md` | S1 / S2：登记、任务树（R2V 核心）、项目目录 |
| `references/concept-generation.md` | S3a 概念模式契约：创作判断 / 默认地图 / 入口 / 研究服务缺口 / 候选发展 / 试写 |
| `references/research-to-craft.md` | S3a–S4：研究材料如何进入创作（缺口 → 发现 / 可信范围 / 影响的决定） |
| `references/stage-3a-concept.md` | S3a 概念长什么样：前提 / 主控句 / 三问 / 反套路 / 交付格式 |
| `references/stage-3b-story.md` | S3b 故事开发：主传统 / 世界观 / 人物六格 / 情绪温度表 / 场景清单 |
| `references/stage-3c-script.md` | S3c 剧本落地：四问 / 节拍表 / 剧本页 / 台词通用关与副词规则 |
| `references/scene-parameters.md` | 场景参数卡：六参数 → 台词 / 表演 / 分镜 / 结构 / 模型执行的规则取值；预设只是参数组合 |
| `references/screenwriting-traditions.md` | 基于第一手编剧/导演资料，按场景问题选方法，不按地区或配额套写 |
| `references/emotion-performance.md` | 原文/微调/重组，强度与克制独立，高光时间编排及保真 |
| `references/performance-record.md` | 可选编译前记录与自动检查接口 |
| `scripts/emotion_library.py` | 按编号或关键词读取完整条目，`--list` 查看索引 |
| `examples/performance/acceptance.md` | 五组验收 Demo、取材/改动说明及成片观察点 |
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
cd <实际安装的Skill目录>
python3 scripts/validate_prompt.py <prompt.md> [--duration N] [--json]
python3 scripts/validate_prompt.py <fragment.md> --artifact performance --duration 10
python3 scripts/validate_prompt.py <fragment.md> --artifact performance --record <record.json>
python3 scripts/validate_prompt.py <original.txt> --artifact raw --entry-id 6
```

退出码 0 只代表无确定性错误，不代表表演或视频质量通过。JSON 单列格式、保真、语义待审阅与成片未验证。多文件默认按连续片段做提示，独立 A/B 对照加 `--batch independent`。Python 3.9+，基础脚本仅用标准库；真实媒体预检另需 PATH 中的 ffprobe（测试另用 ffmpeg）。

完整生产预检：

```bash
python3 scripts/validate_prompt.py <prompt.md> --production-record <production.json> --require-ready --json
```

接口与参数适配见 `references/production-workflow.md`。新版验收和30秒对照见 `examples/production/acceptance-2.3.1.md`；可直接测试 `examples/production/30s-fight-t2v.prompt.md`。原R2V案例需补真实素材；不会把虚构图号当就绪。

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
git clone https://github.com/Anelse0/Film-Director.git <skills目录>/Film-Director
```

更新：Git 安装在该目录拉取更新；目录可沿用现有 `Film-Director`，调用名保持 `film-seedance-director`。2.3.0 不迁移旧项目目录，不要求补写历史表演记录。

## 版本管理

- 语义化版本，记录在 `VERSION` 与 `CHANGELOG.md`。
  - **主版本**：流水线阶段或五层分离规则变化，旧项目目录需要迁移。
  - **次版本**：新增透镜 / 类型包 / 校验项 / 模板字段，向后兼容。
  - **修订**：措辞、示例、误报修复。
- 每次改动跑 `bash tests/run_tests.sh`（含原文完整性、表演记录、时间和验收 Demo 回归）；GitHub Actions 在 push 与 PR 时自动跑。
- 模型能力标签变更必须同时登记在 `references/validation-log.md` 的"标签变更登记"表。

## 维护

- 模型能力更新 → 只改 `references/seedance-2.5-capabilities.md`，并保留事实标签。
- 新任务类型 → 更新对应模板与路由；脚本只增加可确定核对的契约，不通过累积情绪关键词或固定动作组合模拟语义判断。
- 校验脚本回归：`bash tests/run_tests.sh`。

# Changelog

格式遵循 Keep a Changelog；版本号遵循语义化版本。

## [1.4.0] - 2026-09-04

修复实际使用中发现的问题：用户要"构思概念"，Skill 跑完全流程并提前创建了 bible 与 Prompt。

### Added
- SKILL.md「运行模式与停靠点」：概念 / 单阶段 / 停靠式（默认）/ 全流程四种模式，各自的触发词、读取范围、落盘范围、交付形式。
- 停靠点规则：S3a 后必停、S5 后必停（全流程除外）；停下只问一个问题。
- `stage-2a` §3a.4b 概念模式交付格式（对话内 3 候选 + 推荐 + "目标格式下拍什么"一行）；§3a.1 目标格式约束先行。
- `stage-1` §1.2b 概念模式轻量登记（不建 bible）。

### Changed
- 快速路由表拆分"构思 / 概念"、"写一个短片"、"直接出 Prompt"三行。

## [1.3.0] - 2026-09-04

基于 v1.2.0 评估的四项短板做定向补强。

### Added
- 透镜 L15 动能分层（Tony Scott / Michael Bay）、L16 节奏即镜头（Chazelle）、L17 色彩与情节剧（Almodóvar / Sirk）、L18 群戏（Altman），平衡库的克制偏向；速查表加"太冷 / 有拍子 / 人太多"三行与"库的偏向"规则。
- `stage-4` §5.10 群戏、追逐、大空间三种段落的地图先行拆镜规则。
- `stage-2a` §3a.0 素材驱动入口（对角色图 / 场景图 / 音色 / 动作视频各三问）与 §3a.0b 前提的三种失败。
- `examples/example-03-yogurt-comedy*.md`：喜剧语域走查与通过校验的 Prompt（L9 三拍 + L8 落差）。
- 校验 W18：外化词典示例短语逐字照抄；回归测试加 example-03 与 W18 断言。

### Changed
- SKILL.md 路由加"素材驱动"入口。

## [1.2.0] - 2026-09-04

### Added
- `references/genre-packs.md`：动作、悬疑恐怖、UGC 广告、蒙太奇四个类型包（难题 → 规则 → Seedance 约束 → 反套路）。
- `references/validation-log.md`：成片验证账本与待验证队列；标签变更登记表。
- `tests/run_tests.sh`：校验脚本回归测试（23 项断言）；GitHub Actions 工作流。
- `VERSION`、`CHANGELOG.md`、安装与版本管理说明。

## [1.1.0] - 2026-09-04

### Added
- S3a 概念阶段（`references/stage-2a-concept.md`）：三候选前提、主控句、三问、反套路否决表。
- `references/director-lenses.md`：14 个导演透镜（Hitchcock、Spielberg、Fincher、Haneke、Cuarón、Villeneuve、Lanthimos、Coen、Edgar Wright、Lumet、Mamet、Weston、Murch、Scorsese/Bergman），每条含"它回答的问题"与"误用信号"。
- `references/anti-mechanical.md`：理由指回场景、反向测试、多样性硬约束、名字不进 Prompt、品味门三问。
- S5 新增视觉方案、视点归属、节奏曲线、改变意义的声音、10 种调度模式库；coverage 降为兜底。
- S4 新增角色声音表、五种语域、可演的及物动词。
- 校验脚本 W13 导演名、W14 外化短语重复、W15 反套路组合、W16 跨 clip 透镜重复（多文件模式）、W17 运镜连续重复。
- `examples/example-02-one-scene-three-lenses.md` 与画外版 Prompt。

### Changed
- 流水线由 7 阶段改为 S1 / S2 / S3a / S3b / S4 / S5 / S6 / S7。
- 场景卡、分镜卡、Prompt 模板 E 层增加透镜 / 视点 / 品味门字段。

## [1.0.0] - 2026-09-04

### Added
- 初版：S1–S7 流水线、五层分离、事实分级能力表、六份阶段参考、外化词典、镜头语汇、五份模板、九种任务类型 Prompt 骨架、校验脚本（E01–E08、W01–W12）、示例〈钥匙〉。

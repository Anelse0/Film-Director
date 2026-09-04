# Changelog

格式遵循 Keep a Changelog；版本号遵循语义化版本。

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

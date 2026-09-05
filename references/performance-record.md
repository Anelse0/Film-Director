# 可选表演记录与检查接口

只在自动保真核对、落盘交接或验收时读本文件。普通对话测试不强制生成 sidecar。

## 格式

模板 `templates/performance-record.json`。顶层 `version: 1` 是记录格式版本，不是 Skill 版本；`mode` 为 raw/adapt/blend/free；`duration` 为 clip 总秒数。performance 的 `beats` 连续覆盖测试时长；production 中镜头时间线覆盖全片，`beats` 仅覆盖实际表演区间，可以有空镜间隔，不给无人镜头编表演。

每个节拍：

- `id`：记录内唯一标识，不与固定情绪或时间绑定。
- `actor`：本次角色标识；多人同步时写清涉及角色，正文分别给主语。
- `start/end`：clip 绝对秒数。
- `text`：S4 已确认的完整可观察正文，进入 D 层时保持原样。
- `entry_ids`：关联的内部库条目；free 模式为空。
- `keep`：本次关键细节，每项含 `text`（正文中的连续文本）及 `reason`（为什么重要）。不是固定通道配额；按本次选择。
- `changes`：相对条目的有意调整，含新增连接、翻译、末态变化；raw 必须为空。

模式控制的是整个记录；raw 每个节拍正文应是一个完整条目，记录中只能引用同一个条目。拼接不同条目用 blend。adapt 使用一个条目；blend 至少两个；free 不声称条目保真。原文直出不需要时间记录，直接使用 `--artifact raw --entry-id`。

`keep` 只能检查文本仍在，不能证明意思没变。完整 `text` 比较防止编译丢失/添加/重排；关系是否忠实仍须与条目和索引作语义审阅。脚本不会读取自报的“审阅通过”字段来自动放行。

## 调用（在 Skill 目录运行）

```bash
python3 scripts/validate_prompt.py fragment.prompt.md --artifact performance --duration 10
python3 scripts/validate_prompt.py fragment.prompt.md --artifact performance --record fragment.performance.json
python3 scripts/validate_prompt.py production.prompt.md --record production.performance.json
python3 scripts/validate_prompt.py original.txt --artifact raw --entry-id 6
python3 scripts/validate_prompt.py a.prompt.md b.prompt.md --batch independent
```

生产格式维持旧 CLI 默认。表演片段用 `节拍 标识（起-止s）：正文` 或独占一行的 `起–止秒：正文`；换段即下一节拍。可有一行镜头说明；完整生产 Prompt 可在 `镜头N（起-止s）` 内嵌同样节拍。段外条件不承载额外表演；相关动作全部进入节拍，防止绕开核对。

退出码 0 只代表无确定性错误；1 为检查错误；2 为调用/文件/格式错误。`--json` 分别给出 `format`、`fidelity`、`performance`、`render` 状态。`matched` 只表示已确认文本与输出一致，不能当成语义或成片通过。未提供记录时 `fidelity=not_checked`；脚本始终 `performance=needs_review`、`render=not_tested`。

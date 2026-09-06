# 实际生产交付契约（S5b → S6 → S7）

创作稿与生产包是不同交付。先沿用已有世界观、角色、场景、台词和视觉素材，完成 C 层分镜及表演；S6 只编译。缺少真实素材仍能给文本草稿，但标明缺口，不编造图号、不声称可直接提交。

## 每条 clip 的闭环

1. S1/S5b 读取实际素材：看图核对身份/服装/空间；音视频检查内容与时间，记录实际路径、用途和稳定资产 ID。
2. 按本条任务选最少必要素材，确定同类上传顺序：img1…、vid1…、aud1…。局部编号对应稳定资产 ID，不把 IP 的全部素材上传到每一条。
3. S4/S5 确认剧本、C 层有序表演和镜头可见性。先后与同步关系、台词原句、道具状态和高光末态都保留；调整回上游，不从 D 倒造“已确认”记录。
4. S6 按 T1–T9 生成 D 正文及 E 参数。台词用 `台词（角色，0-3s，中文普通话）："逐字"`；窗口为 clip 绝对时间。镜头、节拍和台词三轨不相加；无独立窗口会提示人工估时。
5. S7 完成下述预检，交付可复制正文、参数、上传清单与检查结果。上传/生成仍由用户执行，本 Skill 不调用生成 API。

## 参数适配

当前自动适配器 `ark-seedance-2.5-guide` 对应用户提供的火山方舟 Seedance 2.5 指南，不自动代替其他平台。Higgsfield 的提示结构可借鉴，上传限制/参数须按实际平台单独核实。

| task（E 层及记录） | 主要素材 role | 参数差异 |
|---|---|---|
| t2v | 无 | 自定 ratio、duration |
| r2v | reference_image/video/audio，按实际类型 | 自定 |
| motion | 实际动作/运镜参考 | 允许以参考内容承载时间结构，不强制伪造镜头段 |
| keyframe | reference_image | 首句声明有序关键帧；同类上传顺序一致 |
| storyboard | reference_image | 逐格补足运动、台词等图中没有的信息 |
| first_last | 一个 first_frame，至多一个 last_frame | ratio=adaptive；不同画幅的尾帧有拉伸风险 |
| edit | reference_video，可加替换目标参考 | ratio=adaptive、duration=-1 |
| extend | reference_video | ratio=adaptive、duration 为新增秒数 |
| transition | 至少两个 reference_video | 描述接续范围与可见过渡 |

编辑/延长的 MOV 是建议，不是禁用 MP4。当前本地生成契约为 1–30 整数秒；这是保守输出约定，不推断其他接口不支持其他时长。普通画幅范围 0.4–2.5，锁定任务用 adaptive。图像≤30、视频≤10且合计≤30秒、音频≤10且合计≤30秒、全部≤50；“图像主体 1–8 更稳”等经验范围不等于素材数量上限。

## 可复跑的记录

复制 `templates/production-record.json`，填写实际值。路径相对于记录文件；SHA-256 可用 `shasum -a 256 <文件>` 获取。哈希只绑定版本，不证明用户批准或表演优秀。不要自动把警告统一填“已接受”。

- `prompt_sha256` 绑定整个 Prompt 文件（含 E 表）。
- `assets` 按实际上传顺序，含 id/path/sha256/role/purpose；不得只给假路径。预检依赖 PATH 中的 `ffprobe`，读取实际类型、尺寸、时长；不可读取即失败。
- `upstream` 绑定编译前剧本/分镜文件。嵌入节拍时另给 `performance_record`，且把它列入 upstream。其结构见 `performance-record.md`。
- `reviews` 分 creative/performance/continuity，写审阅者及具体证据；不适用必须说明原因。它记录人工/模型审阅，不自动判断证据真实性。
- `warning_decisions` 每项保存完整 warning 文本及本次保留理由；否则严格预检不通过。风险接受不等于视频效果通过。

```bash
python3 scripts/validate_prompt.py clip.prompt.md --json
python3 scripts/validate_prompt.py clip.prompt.md --production-record clip.production.json --require-ready --json
```

基础命令保持旧稿兼容，只检查可解析文本；严格命令在生产记录、媒体、参数、上游或风险处理缺失时返回非零。不要为消除提示删已锁定台词或表演细节；先核对估时、并行关系，再调整上游或明确接受风险。

## 分层交付

分别写：格式；原文逐字/上游文本匹配；来源关系与表演语义审阅；素材参数预检；成片验证。C/D 匹配仅说明编译未改变文本，不能证明改编保留原作关系（例如呼气完成之后才笑）。脚本不会把内在强度或情绪词频当成艺术质量。

30 秒不必拆成两条 15 秒，也不强制留最后三秒反转。按实际对白、串行动作与同步表演估时，核对景别能看到高光，允许高潮持续到结束。只有真实生成并观看后才能写成片通过。

## 交流与连续性审阅的证据

`creative` 记录必要上下文、问题定位和保留项，不记自然度自评分；`continuity` 记录相关物件初态→实际转移→末态、指代与镜头可见性；`performance` 记录关键细节和发展/持续时间。不是每项都要另建表，但不能只写“C/D 一样，所以成立”。重叠对白、长句与精细动作的风险逐条处理；不能为严格预检方便自动拆轮次、提高语速、删台词或缩短高光。

W19 标点推意图检查已退役；W05 嘴部和 W07 声音/字幕提示只识别有限的引号外表达，不能证明所有听者的所有非说话时段均已覆盖。没有警告也要审阅角色与时间归属。参见 `character-scene-development.md` 与 S7。

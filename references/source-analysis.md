# 资源分析与研究记录

分析日期：2026-09-04。本文件是 Skill 的来源账本，生成流程不读它；审计或更新能力表时读。

## 资源一：Higgsfield《Seedance 2.5 Prompting Guide》

- URL：https://higgsfield.ai/blog/seedance-2-5-prompting-guide
- 性质：第三方平台博客（英文），面向该平台用户。
- 作用：提供一种"整块文本、九段标签"的 Prompt 结构和 8 个题材范本（戏剧外景 / 动作 / 商业产品 / 史诗风景 / 黑色电影 / 多角色 / 奇幻动作 / UGC 广告）。
- 可复用内容：
  - 九段结构：GLOBAL STYLE → SCENE → CHARACTERS → LOCATION → FIRST FRAME AND BLOCKING → Shot 1…N（每镜以 Hard cut 结束）→ OPTICS AND CAMERA → PHYSICS → LIGHTING / AUDIO。
  - "漏掉一段会以可预测的方式失败"；"地点写模糊是多镜序列漂移的最常见原因"。
  - 起始帧与站位锁定（谁在哪、面朝哪），甚至用画面百分比定位。
  - 连续性锁：地理关系逐镜保持、屏幕方向不翻转。
  - 光源哲学：一个真实光源；避免默认好莱坞黄金时刻。
  - 剪辑纪律：只用硬切，切点落在动作或对白节拍上。
  - 台词写法："exactly two scripted spoken lines, nothing else spoken"；"speaks on camera with accurate lip-sync"；"All speech ends by 25s"。
- 声称的参数：1080p、30s、9:16 到 21:9、50 个参考。→ 均标 `[第三方]`。
- 局限：不用 @image 编号语法（与官方相反）；范本大量使用画面负向词（No logos, no text）；有一个 24 快切范例与评测"抗拒快切"冲突；参数未标出处。

## 资源二：火山方舟《Doubao Seedance 2.5 提示词指南》（PDF，38 页）

- 路径：`/Users/leo/Downloads/火山方舟_Doubao Seedance 2.5 提示词指南_1786425487 (1).pdf`；工作目录内有同名 `.md` 转写，本次按转写通读全部 38 页。
- 性质：官方第一手文档。
- 作用：定义任务类型、锁定规则、素材上限、Prompt 结构、时间戳与负向控制规则，并给出白模 / 宫格分镜 / 关键帧 / 编辑 / 延长 / 一键成片 / 无缝转场 8 个案例。
- 可复用内容：已全部结构化进 `seedance-2.5-capabilities.md` §2–§4。最关键的三条：
  1. 有锁定 / 无锁定 决定 ratio、duration 参数与 content.role。
  2. 素材按上传顺序编号绑定，不靠图片内文字。
  3. 负向描述只用于字幕与音频。
- 官方范例揭示的写法：`台词 (角色): "…"` 逐镜绑定；镜头段落用【景别 运镜 构图】方括号开头；【严格排除】段（宫格案例中出现，属画面负向，是官方自己范例中的例外，本 Skill 视为"风格排除"而非"对象排除"，只允许用于风格/媒介层面）。
- 缺口：文中"主体/运动/音频/风格参考的使用方式与 Seedance 2.0 一致，可以参考 附录：提示词案例"——该附录不在本文档内（在 2.0 指南里）。因此 R2V 基础参考（单主体图参考、动作参考）的官方范例缺失，本 Skill 用 §4.2 的规则 + 第三方范例补齐，标注来源。
- 另一个缺口：文中推荐安装官方 `sd25-pe` skill（`npx skills add …`），本 Skill 未获取其内容，不假设其规则。

## 两份资源的关系

| 维度 | 资源一（Higgsfield） | 资源二（官方） | 本 Skill 的处理 |
|---|---|---|---|
| Prompt 结构 | 九段标签整块 | 素材指代 → 概述 → 情节（镜头 N / 时间戳）→ 贯穿细节 | 以官方四段为骨架，把九段中"起始站位 / 光学 / 物理 / 光源"并入"概述"和"贯穿细节"，"Shot N + Hard cut"用官方"镜头 N（a-bs）"表达 |
| 素材指代 | 描述性 | 编号绑定 | 编号绑定（官方） |
| 负向描述 | 大量画面负向 | 只支持字幕/音频 | 只用字幕/音频负向；画面排除改正向；英文 Prompt 结尾允许少量约束段并标注未验证 |
| 切镜密度 | 有 24 快切范例 | 未规定 | 保守：剧情 ≥2s/镜 |
| 台词 | 引号 + 时间点 | `台词 (角色): "…"` | 合并：说话人 + 引号 + 时间窗 + 语言 + 非说话时嘴部状态 |
| 参数 | 1080p 等 | 不谈分辨率 | 分辨率标"不统一" |

重复项：起始状态锁定、每镜一个运镜、光源方向、音效绑定动作——两者一致，采纳为规则。

## 外部研究（核实 Seedance 2.5）

| 来源 | 类型 | 采纳内容 |
|---|---|---|
| 搜狐 / 七牛 / 知乎 / CSDN 转载的发布稿 | 媒体 | 2026-06-23 展示、07-31 上线；30s、50 素材、10 余语言（与官方一致）；"原生 4K"（与其它来源冲突，不采纳为事实） |
| the-decoder | 媒体 | 30 图 / 10 视频 / 10 音频；音画一次生成；可多次延长 |
| fal.ai 指南 | 平台实践 | 因果先后、遮挡连续性、一素材一职责、台词时间窗、末帧续接、单变量迭代；T2V 4–30s；480p/720p |
| rundiffusion 指南 | 平台实践 | 主体→动作→镜头→风格；空泛形容词黑名单；故障对照表；人物审核限制 |
| runware / renderforest | 平台文档 | 台词加引号即生成口型与配音；在 Prompt 中点名语言 |
| mindstudio / novoads 评测 | 评测 | 快动作形变；文字渲染只"减少"；2.5 抗拒快切；Prompt 更长更结构化 |
| cutout.pro 2.0 音频指南 | 经验 | 2.0 技术报告承认多人口型同步未解决 |

## 外部研究（导演 / 分镜 / 台词方法）

采纳的通用方法（行业常识，不单独标注出处）：

- 场景单元 = 目标（objective）+ 阻力（obstacle）+ 策略（tactic）+ 转折（turn）；节拍四步：尝试 → 受阻 → 调整 → 代价。
- Show don't tell：情绪由动作、视觉与潜台词传达。"John 很紧张" → "John 摆弄衣领，瞟向门口"。
- 潜台词成立的三个条件：隐藏的欲望、阻止直说的压力、观众已知真实赌注。
- 台词：短、可说出口、每句有目的；回答"没被问的问题"；沉默是台词。
- 分镜：先定轴线与视线，再定景别阶梯（建立 → 关系 → 反应 → 细节），运镜必须有动机（信息、关系、空间或视点变化）。

## 外部研究（导演方法，2026-09-04 二次调研）

用于 `director-lenses.md`。全部为方法层面引用，标 `[第三方]`；转成 Seedance 可观察量的写法为本 Skill `[推论]`。

| 导演 / 作者 | 采纳的方法 | 来源类型 |
|---|---|---|
| Hitchcock | 悬念 vs 惊讶：桌下的炸弹；"只要有可能就让观众知道" | Hitchcock/Truffaut 访谈转述（nofilmschool、faroutmagazine） |
| Spielberg | 纵深调度 oner：摇、移、走位、焦点转移在一镜内完成多个构图；调度即潜台词 | studiobinder、nofilmschool 对 Hook / Jurassic Park / Close Encounters 的拆解 |
| Fincher | 镜头不动除非有角色理由；剪掉一切分散注意力的东西 | 访谈与评论（thefincheranalyst、nofilmschool、premiumbeat） |
| Haneke | 暴力在画外，声音承担事件；长静止镜头给观众"思考空间" | sensesofcinema、Criterion 论 Funny Games |
| Cuarón | 实时长镜头，危险从背景进入前景 | ASC、johnaugust、nofilmschool 论 Children of Men |
| Villeneuve | 尺度压缩人物 + 沉默特写停留 | talkhouse 视频论文、filmlifestyle |
| Lanthimos | 全景、几何阵列、冷面念白 | indiewire 访谈、birthmoviesdeath |
| Coen 兄弟 | 期待与结果的落差；反应比事件小一号 | 学术与评论（tandfonline、rogerebert） |
| Edgar Wright | 视觉喜剧：去而复返三拍、擦画转场、动作配音效 | 《How to Do Visual Comedy》视频论文及多篇拆解 |
| Lumet | "这片子讲什么"一句话裁决所有部门决定 | 《Making Movies》 |
| Mamet | 从目标推镜头表；无表情镜头并置产生意义 | 《On Directing Film》 |
| Weston | 给演员动词不给结果 | 《Directing Actors》 |
| Murch | 剪辑六律：情绪 > 故事 > 节奏 > 视线 > 2D > 3D | 《In the Blink of an Eye》 |
| Scorsese / Bergman | 视点归属；主观镜头；两张脸 | 通识 |

设计决定：不把这些做成"风格预设"，而做成"透镜 = 它回答的问题 + 误用信号"，并用 `anti-mechanical.md` 的多样性约束和校验脚本 W13/W14/W16/W17 防止套用。

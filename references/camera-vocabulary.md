# 镜头语汇（中英对照，Seedance 安全写法）

`[官方]`：通识术语与热门运镜可直接写；小众术语用"术语 + 描述性解释"。下表"直接写"列可原样进 Prompt；"需解释"列必须附解释。

## 景别

| 中文 | 英文 | 直接写 |
|---|---|---|
| 大远景 / 大全景 | extreme wide shot | ✅ |
| 全景 | wide shot / full shot | ✅ |
| 中景 | medium shot | ✅ |
| 中近景 | medium close-up | ✅ |
| 近景 | close-up | ✅ |
| 特写 | close-up（面部特写 face close-up） | ✅ |
| 大特写 | extreme close-up（眼睛 / 手部） | ✅ |

## 角度 / 机位

| 中文 | 英文 | 直接写 |
|---|---|---|
| 平视 | eye level | ✅ |
| 低角度仰拍 | low angle | ✅ |
| 高角度俯拍 | high angle | ✅ |
| 顶视 / 垂直俯拍 | top-down / overhead | ✅ |
| 第一人称 / 主观视角 | POV / first person | ✅ |
| 越肩 | over-the-shoulder | ✅（写清谁的肩） |
| 荷兰角 / 倾斜 | dutch angle | ⚠️ 加"画面微微倾斜" |

## 运镜

| 中文 | 英文 | 直接写 |
|---|---|---|
| 推 | push in / dolly in | ✅ |
| 拉 | pull back / dolly out | ✅ |
| 摇（左右） | pan | ✅ |
| 上摇 / 下摇 | tilt up / tilt down | ✅ |
| 横移 | truck / lateral move | ✅ |
| 跟拍 | tracking / follow | ✅ |
| 环绕 | orbit | ✅ |
| 升 / 降 | crane up / down | ✅ |
| 俯冲 | dive | ✅ |
| 手持 | handheld | ✅ |
| 固定机位 | locked / static | ✅ |
| 一镜到底 | one continuous take | ✅ |
| 希区柯克变焦 | dolly zoom | ✅（热门） |
| 航拍 | aerial / drone | ✅ |
| FPV | FPV | ✅ |
| 子弹时间 | bullet time | ✅ |
| 回弹变速 | speed ramp | ✅ |
| 移焦 | rack focus | ❌ 需解释："画面焦点平滑转变，前景清晰的 X 变模糊，背景的 Y 由模糊变清晰" |
| 甩镜 | whip pan | ⚠️ "快速横摇，画面短暂拖影" |
| 斯坦尼康 | steadicam | ❌ 写"平稳跟拍" |
| 变形宽银幕 | anamorphic | ⚠️ "横向椭圆光斑、画面略宽的电影镜头质感" |

## 构图位置（写给模型）

- "人物在画面左三分之一 / 右三分之一 / 中心"
- "前景是 A 的后背肩膀，焦点在 B 的面部"
- "人物占画面高度约一半"
- "保持 X 始终在画面内"

## 转场（写触发时间 + 方式）`[官方]`

- "第 5s 快速向左横移转场（向左擦除＋自然叠化）"
- "第 12s 硬切到镜头 4"
- "第 20s 画面渐黑 1 秒"

## 光

写光源 + 方向 + 质地：

- "唯一光源是画面左侧的窗，午后侧光，柔和"
- "头顶一盏钨丝灯，硬光，人物面部一半在阴影里"
- "夜，路灯从画面右上方打下来，冷白"

避免：只写"电影级光影"。

## 禁用空泛词（校验脚本会警告）

电影感、唯美、震撼、史诗感、高级感、氛围感、大片、cinematic、stunning、epic、beautiful、premium、dramatic（作为形容词单独出现时）。风格要写可见的东西：媒介（35mm 胶片 / 手机实拍 / 3D 动画）、光、色调、质地、颗粒、景深。

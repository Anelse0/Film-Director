#!/usr/bin/env python3
"""路由自检（film-seedance-director S2，2.5.5）。

用法: python3 route_check.py "<需求原文>" [--material idea|fragment|story|script|storyboard|footage] [--json]

只回答四件事：创作意图 / 入口成果 / 自主度 / 文件保存。目的是核对"同一请求换种说法"
不会改变工作范围、保存行为或审美要求。脚本按措辞与材料标记做确定性判断，不替代阅读需求；
不确定时输出"需确认"，由人判断。审美要求永远不由路由设定。
"""
import json
import re
import sys

INTENTS = [
    ("表演测试", ["原文", "憋哭", "调强度", "强度调", "表演测试", "情绪弧线", "秒表演", "秒的表演", "克制一点", "raw"]),
    ("局部改写", ["太假", "太平", "太直白", "太淡", "太套路", "没意思", "不可信", "改一下", "改这句", "改这段", "改改", "改结尾", "换个结尾", "重写这", "这句不对", "不喜欢这"]),
    ("进入生产", ["拆分镜", "分镜", "镜头表", "转成 prompt", "转 prompt", "转prompt", "出 prompt", "出prompt", "出一个 prompt", "参考图", "资产", "成片", "第 ", "延长", "编辑视频", "换人", "校验", "体检 prompt", "@视频"]),
    ("写完整剧本", ["写剧本", "写成剧本", "剧本写", "完整场景", "写成短片", "写一个", "写一部", "写个", "给我写", "短片", "先导", "一集", "一个 clip", "一场戏", "一个镜头", "完整故事"]),
    ("发展已有想法", ["发展", "展开", "写完整", "写世界观", "写人物", "我有个想法", "我有一个想法", "这个人物", "一句对白", "一句台词", "一个片段", "长成", "接着写", "补完"]),
    ("想故事", ["构思", "想几个", "几个方向", "方向", "概念", "灵感", "帮我想", "几个版本", "点子", "想做点什么", "能做什么"]),
]
MATERIAL_ENTRY = {
    None: "S3a 概念", "idea": "S3a 概念", "fragment": "S3b 故事（先试写最有生命力的部分）",
    "story": "S3c 剧本", "script": "S4 表演 → S5", "storyboard": "S6 Prompt", "footage": "S7 检查",
}
AUTONOMY_WORDS = ["一次跑完", "不用问我", "别问我", "全部落盘", "看一眼", "看看", "看下", "试一下", "试试", "先出一个", "直接出"]
PEEK_WORDS = ["看一眼", "看看", "看下", "试一下", "试试", "先出一个", "直接出"]
SAVE_WORDS = ["存", "落盘", "写进项目", "保存", "写到文件"]


def classify(text, material=None):
    t = text.lower()
    intent = None
    hits = {}
    for name, words in INTENTS:
        matched = [w for w in words if w.lower() in t]
        if matched:
            hits[name] = matched
    # 表演与局部改写优先级最高；有材料标记时，材料决定入口，措辞决定意图
    for name, _ in INTENTS:
        if name in hits:
            intent = name
            break
    if material in ("script", "storyboard", "footage") and intent in (None, "写完整剧本", "想故事"):
        intent = "进入生产"
    if material == "fragment" and intent in (None, "想故事", "写完整剧本"):
        intent = "发展已有想法"
    if material == "story" and intent in (None, "想故事", "发展已有想法"):
        intent = "写完整剧本"
    if intent is None:
        intent = "需确认"

    if intent == "表演测试":
        entry = "表演优先路由"
    elif intent == "想故事":
        entry = "S3a 概念"
    elif intent == "发展已有想法":
        entry = "S3b 故事（先试写最有生命力的部分）"
    elif intent == "局部改写":
        entry = "creative-loop §二 诊断层级 → 定点重写"
    elif intent == "进入生产":
        if material in ("script", "storyboard", "footage"):
            entry = MATERIAL_ENTRY[material]
        elif material in ("fragment", "story", "idea"):
            entry = "材料未成熟（有台词不等于剧本完成）：先按 §2.2 补齐 S3b/S3c，再进生产"
        else:
            entry = "S1 登记 → 按材料成熟度进入 S4/S5b/S6/S7"
    elif intent == "写完整剧本":
        entry = {None: "S3a 概念 ▮ → S3b 故事 ▮ → S3c 剧本 ▮", "idea": "S3a 概念 ▮ → S3b 故事 ▮ → S3c 剧本 ▮",
                 "fragment": "S3b 故事（先试写）▮ → S3c 剧本 ▮", "story": "S3c 剧本 ▮（故事不重停）",
                 "script": "S4 表演 → S5（剧本成熟则不重写）"}.get(material, "需确认")
    else:
        entry = "需确认"

    peek = any(w in t for w in PEEK_WORDS)
    autonomous = any(w in t for w in AUTONOMY_WORDS)
    if intent == "表演测试":
        autonomy = "直接交付"
    elif autonomous:
        autonomy = "自主到指定阶段" if peek or "一次跑完" in t or "不用问我" in t or "别问我" in t else "自主"
    else:
        autonomy = "停靠式"

    explicit_save = any(w in t for w in SAVE_WORDS)
    if explicit_save:
        save = "显式保存（用户说了存 / 落盘）"
    elif peek or intent in ("表演测试", "想故事", "局部改写"):
        save = "不落盘（对话内交付）"
    else:
        save = "停靠确认后写该阶段产物"

    return {"text": text, "material": material, "intent": intent, "entry": entry,
            "autonomy": autonomy, "save": save, "aesthetic": "由场景参数与用户锁定项决定，不由路由设定",
            "matched": hits}


def main(argv):
    args = [a for a in argv if not a.startswith("--")]
    material = None
    if "--material" in argv:
        material = argv[argv.index("--material") + 1]
        args = [a for a in args if a != material]
    if not args:
        print(__doc__); return 2
    r = classify(args[0], material)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        for k in ("intent", "entry", "autonomy", "save", "aesthetic"):
            print(f"{k:10s} {r[k]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

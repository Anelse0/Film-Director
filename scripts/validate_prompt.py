#!/usr/bin/env python3
"""Seedance 2.5 Prompt 静态校验器（film-seedance-director S7）。

用法:
    python3 validate_prompt.py <prompt.md> [--duration N] [--json]

只依赖标准库。读取编译后的 Prompt 文件（中文或英文骨架），做确定性检查：
  ERROR  违反官方规则或结构缺失，必须修
  WARN   风险项，需逐条说明保留理由
  INFO   统计信息

检查项（编号对应 SKILL.md 硬规则 / 各 reference）:
  E01 缺少【素材绑定】/REFERENCES 段
  E02 时间戳非整数秒
  E03 时间戳不连续 / 首镜不从 0 开始
  E04 末镜结束秒 != 声明时长（--duration 或【总述】中的"N秒"）
  E05 引用了未在【素材绑定】声明的素材编号
  E06 clip 总时长 > 30s
  E07 编辑任务缺少触发关键词 / 延长任务缺少触发关键词
  E08 关键帧任务首句不是"以图片x至图片y的顺序作为关键帧"
  W01 画面级负向描述（只允许字幕/音频负向）
  W02 空泛风格词
  W03 情绪抽象词未见外化（同一镜头段落内无动作/部位/视线词）
  W04 单镜 < 1.5s 或 30s 内镜头数 > 8
  W05 台词密度：某镜台词字数 / 镜头秒数 过高，或总台词估时 > 2/3
  W06 台词出现在引号外（"说了一句…"）
  W07 缺少"不要字幕"或声音策略
  W08 缺少镜头段落的景别标注【…】/[...]
  W09 时间戳控频（"N秒内…N次"）
  W10 镜头段落含 2 个以上运镜词
  W11 多说话人同一镜头（可能同框同时说话）
  W12 缺少起始状态段
  W13 Prompt 正文出现导演/影片/摄影师名字（名字不是可观察量）
  W14 同一外化短语在一个 clip 内出现 ≥ 3 次
  W15 反套路组合（缓慢推近+泪/悲伤；黄金时刻；雨夜霓虹；背影望远）——需要理由
  W16 多文件模式：相邻 clip 同一主透镜 / 某透镜占比 > 1/3
  W17 同一运镜连续 ≥ 3 镜

多文件用法:
    python3 validate_prompt.py clip01.prompt.md clip02.prompt.md ...
    按传入顺序视为相邻 clip；每个文件末尾 E 层表的「透镜」行用于 W16。
"""
import json
import re
import sys
from pathlib import Path

# ---------- 词表 ----------
VAGUE_WORDS = [
    "电影感", "唯美", "震撼", "史诗感", "高级感", "氛围感", "大片感", "大片",
    "cinematic", "stunning", "epic", "beautiful", "premium", "breathtaking",
]
EMOTION_WORDS = [
    "悲伤", "难过", "伤心", "愤怒", "生气", "紧张", "恐惧", "害怕", "释然", "犹豫",
    "羞耻", "轻蔑", "惊讶", "疲惫", "尴尬", "深情", "冷漠", "温柔", "痛苦", "绝望",
    "喜悦", "开心", "幸福", "焦虑", "不舍", "感伤", "怅然",
    "sad", "angry", "nervous", "afraid", "anxious", "relieved", "hesitant",
    "ashamed", "surprised", "exhausted", "awkward", "tender", "cold", "desperate",
]
OBSERVABLE_HINTS = [
    "手", "指", "眉", "眼", "嘴", "唇", "下颌", "下巴", "肩", "吞咽", "眨", "视线", "看向", "看着",
    "盯", "转身", "后退", "靠近", "低头", "抬头", "停", "秒", "呼吸", "泪", "拳", "握", "放下",
    "递", "接", "站", "坐", "走", "跑", "焦点", "推近", "后拉",
    "hand", "finger", "brow", "eye", "mouth", "lip", "jaw", "shoulder", "swallow", "blink",
    "look", "gaze", "stare", "turn", "step", "lean", "sit", "stand", "walk", "hold", "drop",
    "second", "breath", "tear", "fist", "focus",
]
CAMERA_MOVES = [
    "推", "拉", "摇", "横移", "跟拍", "跟随", "环绕", "升", "降", "俯冲", "后拉", "手持",
    "push", "pull", "pan", "tilt", "truck", "track", "orbit", "crane", "dolly", "handheld", "zoom",
]
SHOT_SIZE_WORDS = ["远景", "全景", "中景", "近景", "特写", "wide", "medium", "close-up", "close up", "extreme"]
NEG_ALLOWED = ["字幕", "bgm", "背景音乐", "对白", "人声", "音效", "声音", "音乐", "旁白", "配乐",
               "subtitle", "caption", "music", "dialogue", "narration", "voice", "sound", "score", "bgm"]
NEG_PATTERNS = [r"不要[^，。；\n]{0,12}", r"不(?:能|准|得)?出现[^，。；\n]{0,12}", r"没有出现[^，。；\n]{0,12}",
                r"画面[里中内]没有[^，。；\n]{0,12}", r"不(?:能|准|得)有[^，。；\n]{0,12}", r"(?:^|[，。；\s])无(?!缝|论|法|参考)[^，。；\n|]{1,6}",
                r"\bno\s+[a-z\- ]{1,20}", r"\bwithout\s+[a-z\- ]{1,20}"]
DIRECTOR_NAMES = [
    "希区柯克", "斯皮尔伯格", "芬奇", "哈内克", "卡隆", "维伦纽瓦", "兰斯莫斯", "科恩", "埃德加", "吕美特",
    "马梅", "库布里克", "诺兰", "斯科塞斯", "伯格曼", "韦斯·安德森", "塔可夫斯基", "王家卫", "是枝裕和",
    "hitchcock", "spielberg", "fincher", "haneke", "cuar", "villeneuve", "lanthimos", "coen", "edgar wright",
    "lumet", "mamet", "kubrick", "nolan", "scorsese", "bergman", "wes anderson", "tarkovsky", "deakins",
    "wong kar", "malick", "tarantino", "anderson", "lynch", "ozu", "bresson",
]
CLICHE_PATTERNS = [
    (r"(缓慢?推近|缓推|push in|dolly in)[^。\n]{0,60}(泪|哭|悲伤|难过|tear|cry)", "悲伤脸缓推"),
    (r"(黄金时刻|golden hour|逆光[^。\n]{0,10}暖金|镜头光晕|lens flare)", "黄金时刻"),
    (r"(雨夜|rain)[^。\n]{0,30}(霓虹|neon)", "雨夜霓虹"),
    (r"(背影|背对镜头|from behind)[^。\n]{0,20}(望向远方|看向远处|远方|地平线|horizon|distance)", "背影望远"),
    (r"(慢动作|slow motion|slow-mo)[^。\n]{0,30}(泪|哭|拥抱|回头|tear|hug)", "慢动作情绪"),
]
EXTERNALIZATION_PHRASES = [
    "抿嘴", "抿着嘴", "吞咽", "手指停住", "手停住", "停住", "眼眶泛红", "泪滑落", "深吸一口气", "长出一口气",
    "低头", "抬头", "眨眼", "握拳", "摩挲", "肩膀下沉", "肩膀往下沉", "嘴角", "眉头",
    "swallow", "blink", "fist", "shoulders drop", "jaw", "lips pressed",
]
EDIT_TRIGGERS = ["编辑视频", "增加", "加上", "删除", "去掉", "修改", "替换", "改成"]
EXTEND_TRIGGERS = ["向前延长", "向后延长", "延续", "续写", "延长"]
SPEECH_LEAK = [r"说了一句", r"说着[^“\"]*的话", r"低声说.{0,6}[^“\"]", r"says something", r"tells (him|her) that"]

SECTION_ALIASES = {
    "refs": ["【素材绑定】", "REFERENCES"],
    "overview": ["【总述】", "OVERVIEW"],
    "opening": ["【起始状态】", "OPENING STATE"],
    "timeline": ["【分镜时间线】", "TIMELINE"],
    "global": ["【贯穿要求】", "GLOBAL RULES"],
}

SHOT_RE = re.compile(
    r"^(?:镜头|Shot)\s*(\d+)\s*[（(]\s*(\d+(?:\.\d+)?)\s*(?:s|秒)?\s*[-–~]\s*(\d+(?:\.\d+)?)\s*(?:s|秒)?[^)）]*[)）]",
    re.M,
)
ASSET_REF_RE = re.compile(r"(?:@?图片?|@?视频|@?音频|image|img|video|vid|audio|aud)\s*(\d+)", re.I)
ASSET_DECL_RE = re.compile(r"(?:@?图片?|@?视频|@?音频|image|img|video|vid|audio|aud)\s*(\d+)(?:\s*[-–至到]\s*(?:图片?|image|img)?\s*(\d+))?", re.I)
QUOTE_RE = re.compile(r"[“\"]([^”\"]{1,400})[”\"]")
SPEAKER_RE = re.compile(r"(?:台词\s*[（(]([^)）]{1,20})[)）]|([^\s，。；:：]{1,12})\s*(?:说|says|说道)\s*[（(]?[^:：“\"]{0,40}[:：]?\s*[“\"])")


def find_section(text, key):
    for alias in SECTION_ALIASES[key]:
        if alias in text:
            return True
    return False


def split_shots(text):
    """返回 [(no, start, end, body)]"""
    matches = list(SHOT_RE.finditer(text))
    shots = []
    for i, m in enumerate(matches):
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():body_end]
        # 截断到贯穿要求前
        for alias in SECTION_ALIASES["global"]:
            idx = body.find(alias)
            if idx >= 0:
                body = body[:idx]
        shots.append((int(m.group(1)), float(m.group(2)), float(m.group(3)), body))
    return shots


def declared_duration(text, override):
    if override is not None:
        return float(override)
    m = re.search(r"(\d+)\s*(?:秒|s\b|-second|second)", text)
    return float(m.group(1)) if m else None


def cjk_len(s):
    return sum(1 for ch in s if "一" <= ch <= "鿿")


def validate(path, duration_override=None):
    text = Path(path).read_text(encoding="utf-8")
    errors, warns, infos = [], [], []

    def err(code, msg): errors.append(f"{code} {msg}")
    def warn(code, msg): warns.append(f"{code} {msg}")
    def info(msg): infos.append(msg)

    is_edit = bool(re.search(r"编辑视频|edit", text[:300], re.I)) or "duration=-1" in text or "duration: -1" in text
    is_extend = bool(re.search(r"延长|extend", text[:200], re.I))
    is_keyframe = bool(re.search(r"关键帧|keyframe", text, re.I))

    # E01 / E12 / W07 structure
    if not find_section(text, "refs"):
        err("E01", "缺少【素材绑定】/REFERENCES 段（无素材也要写「无参考素材」）")
    if not is_edit and not find_section(text, "opening") and not is_extend:
        err("E12", "缺少【起始状态】/OPENING STATE 段")
    if not is_edit and not find_section(text, "global"):
        warn("W07", "缺少【贯穿要求】/GLOBAL RULES 段")
    if not re.search(r"不要字幕|无字幕|不额外加入.{0,4}字幕|no subtitles|no captions", text, re.I):
        warn("W07", "未声明字幕负向（建议加「不要字幕」）")
    if not re.search(r"bgm|背景音乐|环境音|music|room tone|ambien", text, re.I):
        warn("W07", "未声明声音策略（无 bgm / 只生成环境音 / bgm 描述）")

    # E07 triggers
    if is_edit and not any(t in text for t in EDIT_TRIGGERS):
        err("E07", "编辑任务缺少触发关键词（编辑视频/增加/加上/删除/去掉/修改/替换/改成）")
    if is_extend and not any(t in text for t in EXTEND_TRIGGERS):
        err("E07", "延长任务缺少触发关键词（向前/向后延长、延续、续写）")

    # E08 keyframe first sentence
    if is_keyframe and "关键帧分镜" not in text[:200]:
        first = text.strip().splitlines()[0] if text.strip() else ""
        if not re.search(r"以图片?\s*\d+\s*[至到\-–]\s*图片?\s*\d+\s*的顺序作为关键帧", first):
            err("E08", "关键帧任务首句必须是「以图片x至图片y的顺序作为关键帧」")

    # E05 asset refs
    refs_block = ""
    for alias in SECTION_ALIASES["refs"]:
        if alias in text:
            start = text.index(alias)
            nxt = len(text)
            for k in ("overview", "opening", "timeline"):
                for a2 in SECTION_ALIASES[k]:
                    i2 = text.find(a2, start + 1)
                    if i2 > 0:
                        nxt = min(nxt, i2)
            refs_block = text[start:nxt]
            break
    declared = set()
    for m in ASSET_DECL_RE.finditer(refs_block):
        a, b = int(m.group(1)), m.group(2)
        kind = re.sub(r"\d+|@|\s", "", m.group(0)).lower()
        kind = {"图片": "img", "图": "img", "image": "img", "img": "img", "视频": "vid", "video": "vid",
                "vid": "vid", "音频": "aud", "audio": "aud", "aud": "aud"}.get(kind, kind)
        if b:
            for n in range(a, int(b) + 1):
                declared.add((kind, n))
        else:
            declared.add((kind, a))
    # also keyframe first sentence range
    m = re.search(r"以图片?\s*(\d+)\s*[至到\-–]\s*图片?\s*(\d+)\s*的顺序作为关键帧", text)
    if m:
        for n in range(int(m.group(1)), int(m.group(2)) + 1):
            declared.add(("img", n))
    body_after_refs = text.replace(refs_block, "")
    used = set()
    for m in ASSET_REF_RE.finditer(body_after_refs):
        kind = re.sub(r"\d+|@|\s", "", m.group(0)).lower()
        kind = {"图片": "img", "图": "img", "image": "img", "img": "img", "视频": "vid", "video": "vid",
                "vid": "vid", "音频": "aud", "audio": "aud", "aud": "aud"}.get(kind, kind)
        used.add((kind, int(m.group(1))))
    missing = sorted(used - declared)
    if missing and (declared or "无参考素材" not in refs_block):
        err("E05", f"引用了未声明的素材：{', '.join(f'{k}{n}' for k, n in missing)}")
    info(f"素材声明 {len(declared)} 个，引用 {len(used)} 个")

    # timestamps
    shots = split_shots(text)
    dur = declared_duration(text, duration_override)
    if shots:
        for no, s, e, _ in shots:
            if s != int(s) or e != int(e):
                err("E02", f"镜头{no} 时间戳非整数秒：{s}-{e}")
            if e <= s:
                err("E03", f"镜头{no} 结束 ≤ 开始：{s}-{e}")
        if shots[0][1] != 0:
            err("E03", f"首镜不从 0 开始（{shots[0][1]}）")
        for (n1, s1, e1, _), (n2, s2, e2, _) in zip(shots, shots[1:]):
            if s2 != e1:
                err("E03", f"镜头{n1}→镜头{n2} 时间不连续：{e1} → {s2}")
        end = shots[-1][2]
        if end > 30:
            err("E06", f"clip 总时长 {end}s > 30s")
        if dur is not None and not is_edit and end != dur:
            err("E04", f"末镜结束 {end}s != 声明时长 {dur}s")
        info(f"镜头数 {len(shots)}，总时长 {end}s")
        # W04 pacing
        short = [no for no, s, e, _ in shots if e - s < 1.5]
        if short:
            warn("W04", f"单镜 < 1.5s：镜头 {short}（2.5 抗拒快切 [第三方]）")
        if len(shots) > 8 and end <= 30:
            warn("W04", f"30s 内 {len(shots)} 镜 > 8（剧情类建议 ≤ 8 [推论]）")
    elif not is_edit:
        warn("W08", "未识别到「镜头N（a-bs）」格式的分镜段落")

    # per-shot checks
    total_speech_chars = 0
    total_speech_words = 0
    for no, s, e, body in shots:
        length = e - s
        head = body[:80]
        if not re.search(r"【[^】]{2,40}】|\[[^\]]{2,60}\]", head):
            warn("W08", f"镜头{no} 段首缺少【景别，角度，运镜】标注")
        elif not any(w in head for w in SHOT_SIZE_WORDS):
            warn("W08", f"镜头{no} 标注里没有景别词")
        moves = [w for w in CAMERA_MOVES if w in body]
        # 去掉与"推门""拉开"等动作误报：只在标注括号内统计
        tag = re.search(r"【([^】]{2,60})】|\[([^\]]{2,80})\]", head)
        tag_txt = (tag.group(1) or tag.group(2)) if tag else ""
        tag_moves = [w for w in CAMERA_MOVES if w in tag_txt]
        if len(tag_moves) > 2:
            warn("W10", f"镜头{no} 标注含多个运镜词 {tag_moves}（每镜一个主要运镜）")
        if re.search(r"\d+\s*秒?内.{0,10}\d+\s*次|\d+\s*times? (?:per|in) \d+", body):
            warn("W09", f"镜头{no} 用时间戳控制频次（官方不建议）")
        # emotions
        for w in EMOTION_WORDS:
            if w in body and not any(h in body for h in OBSERVABLE_HINTS):
                warn("W03", f"镜头{no} 出现情绪词「{w}」且段内无可观察量（动作/部位/视线/秒数）")
                break
        # dialogue
        quotes = QUOTE_RE.findall(body)
        speakers = set(m.group(1) or m.group(2) for m in SPEAKER_RE.finditer(body))
        if quotes:
            zh = sum(cjk_len(q) for q in quotes)
            en_words = sum(len(q.split()) for q in quotes if cjk_len(q) == 0)
            total_speech_chars += zh
            total_speech_words += en_words
            est = zh / 4.0 + en_words / 2.5  # 估算秒数：中文 ~4 字/s，英文 ~2.5 词/s [推论]
            if est > length * 0.9:
                warn("W05", f"镜头{no} 台词约 {est:.1f}s 接近或超过镜长 {length}s")
            if len(speakers) >= 2:
                warn("W11", f"镜头{no} 有 {len(speakers)} 个说话人（{', '.join(speakers)}），确认不是同框同时说话")
            if not re.search(r"闭着嘴|抿嘴|不出声|嘴[^，。]{0,4}闭|mouth (?:stays )?closed|lips (?:pressed|closed)", body) and len(speakers) >= 1 and re.search(r"[两二]人|B|另一|对方|listener|the other", body):
                warn("W05", f"镜头{no} 有台词但未写非说话者嘴部状态")
        for pat in SPEECH_LEAK:
            if re.search(pat, body):
                warn("W06", f"镜头{no} 疑似引号外的台词描述（模型只念引号内文字）")
                break

    # W14 外化短语重复（整 clip 正文）
    prose_body = text
    for alias in SECTION_ALIASES["global"]:
        i = prose_body.find(alias)
        if i > 0:
            prose_body = prose_body[:i]
    ext_counts = {}
    for ph in EXTERNALIZATION_PHRASES:
        c = len(re.findall(re.escape(ph), prose_body, re.I))
        if c >= 3:
            ext_counts[ph] = c
    # 合并子串（"抿嘴" 与 "抿着嘴"）
    for ph, c in sorted(ext_counts.items(), key=lambda kv: -len(kv[0])):
        if any(ph != o and ph in o for o in ext_counts):
            continue
        warn("W14", f"外化短语「{ph}」出现 {c} 次（同一 clip ≤ 2；换通道或换成角色专属动作）")

    # W17 同一运镜连续 ≥ 3 镜（只看段首标注）
    tag_moves_seq = []
    for no, s_, e_, body in shots:
        tag = re.search(r"【([^】]{2,60})】|\[([^\]]{2,80})\]", body[:80])
        tag_txt = (tag.group(1) or tag.group(2)) if tag else ""
        mv = next((w for w in ["固定", "locked", "static"] if w in tag_txt), None) or \
             next((w for w in CAMERA_MOVES if w in tag_txt), None)
        tag_moves_seq.append(mv)
    run = 1
    for i in range(1, len(tag_moves_seq)):
        if tag_moves_seq[i] and tag_moves_seq[i] == tag_moves_seq[i - 1]:
            run += 1
            if run == 3 and tag_moves_seq[i] not in ("固定", "locked", "static"):
                warn("W17", f"运镜「{tag_moves_seq[i]}」连续 {run} 镜（连续 ≤ 2；固定机位不计）")
        else:
            run = 1

    # W13 导演名
    hits = [n for n in DIRECTOR_NAMES if re.search(re.escape(n), prose_body, re.I)]
    if hits:
        warn("W13", f"Prompt 正文出现导演/影片人名 {hits}（名字不是可观察量，改写为机位/光/运镜/部位）")

    # W15 反套路
    for pat, label in CLICHE_PATTERNS:
        if re.search(pat, prose_body, re.I):
            warn("W15", f"反套路组合「{label}」（允许，但 QA 里要写一行指回主控句的理由）")

    if shots:
        end = shots[-1][2]
        est_total = total_speech_chars / 4.0 + total_speech_words / 2.5
        if est_total > end * 2 / 3:
            warn("W05", f"总台词估时 {est_total:.1f}s > clip 的 2/3（{end * 2 / 3:.1f}s）")
        info(f"台词估时 {est_total:.1f}s")

    # W01 negatives（跳过参数表行，只扫 Prompt 正文）
    prose = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("|"))
    seen = set()
    for pat in NEG_PATTERNS:
        for m in re.finditer(pat, prose, re.I):
            frag = m.group(0).strip("，。； \n")
            if not frag or frag in seen:
                continue
            if any(a in frag.lower() for a in NEG_ALLOWED):
                continue
            seen.add(frag)
            warn("W01", f"画面级负向描述「{frag}」（官方只支持字幕/音频负向，改为正向）")

    # W02 vague
    found = [w for w in VAGUE_WORDS if re.search(re.escape(w), text, re.I)]
    if found:
        warn("W02", f"空泛风格词：{found}（改为可见量：媒介/光/色调/质地）")

    lens = None
    m = re.search(r"\|\s*透镜\s*\|\s*([^|\n]+)\|", text)
    if m:
        lm = re.search(r"L\d+", m.group(1))
        lens = lm.group(0) if lm else m.group(1).strip()
    return {"file": str(path), "errors": errors, "warnings": warns, "info": infos, "lens": lens,
            "ext_phrases": {ph: len(re.findall(re.escape(ph), prose_body, re.I)) for ph in EXTERNALIZATION_PHRASES}}


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__)
        return 2
    dur = None
    as_json = "--json" in argv
    if "--duration" in argv:
        dur = argv[argv.index("--duration") + 1]
        argv = [a for a in argv if a not in ("--duration", dur)]
    paths = [a for a in argv[1:] if not a.startswith("--")]
    results = [validate(p, dur) for p in paths]

    cross = []
    if len(results) > 1:
        lenses = [r["lens"] for r in results]
        for a, b in zip(results, results[1:]):
            if a["lens"] and a["lens"] == b["lens"]:
                cross.append(f"W16 相邻 clip 同一主透镜 {a['lens']}：{Path(a['file']).name} → {Path(b['file']).name}")
        known = [l for l in lenses if l]
        for l in set(known):
            if known.count(l) > max(1, len(results) / 3):
                cross.append(f"W16 透镜 {l} 出现 {known.count(l)}/{len(results)}，超过 1/3")
        agg = {}
        for r in results:
            for ph, c in r["ext_phrases"].items():
                if c:
                    agg[ph] = agg.get(ph, 0) + 1
        for ph, n in agg.items():
            if n >= 3 and n > len(results) * 0.6:
                cross.append(f"W14 外化短语「{ph}」在 {n}/{len(results)} 个 clip 中出现（跨 clip 重复）")

    if as_json:
        print(json.dumps({"results": results, "cross": cross}, ensure_ascii=False, indent=2))
    else:
        for result in results:
            print(f"== validate_prompt: {result['file']}")
            for e in result["errors"]:
                print(f"ERROR {e}")
            for w in result["warnings"]:
                print(f"WARN  {w}")
            for i in result["info"]:
                print(f"INFO  {i}")
            if result["lens"]:
                print(f"INFO  透镜 {result['lens']}")
            print(f"== {len(result['errors'])} error(s), {len(result['warnings'])} warning(s)")
        if cross:
            print("== cross-clip")
            for c in cross:
                print(f"WARN  {c}")
    return 1 if any(r["errors"] for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

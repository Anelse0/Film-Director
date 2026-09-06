#!/usr/bin/env python3
"""Prompt format/fidelity checks for film-seedance-director.
Usage: validate_prompt.py FILE... [--duration N] [--json]
       [--artifact production|performance|raw] [--record RECORD.json]
       [--entry-id N] [--batch sequence|independent]
Default production CLI remains compatible. ERROR is a format/contract issue,
not necessarily an official model limitation. WARN requires review.
F01-F06 concern record/schema/text fidelity; E20 concerns performance timing.
W14 reviews identical adjacent complete blocks; W18 and W19 are retired.
Semantic acting quality is always needs_review; render is always not_tested.
Exit 0 means no deterministic errors, 1 check failure, 2 invalid invocation/input.
"""
import argparse
import json
import math
import re
import sys
from pathlib import Path

from performance_checks import split_beats, timing_errors, check_record, check_raw, repeated_blocks
from prompt_structure import Document, dialogue_checks
from prose_hints import has_mouth_direction, has_subtitle_policy, has_sound_policy
from production_contract import metadata, task_type, parameters, roles_from_fields, check_parameters, TASKS

# ---------- 词表 ----------
VAGUE_WORDS = [
    "电影感", "唯美", "震撼", "史诗感", "高级感", "氛围感", "大片感", "大片",
    "cinematic", "stunning", "epic", "beautiful", "premium", "breathtaking",
]
CAMERA_MOVES = [
    "推", "拉", "摇", "横移", "跟拍", "跟随", "环绕", "升", "降", "俯冲", "后拉", "手持",
    "push", "pull", "pan", "tilt", "truck", "track", "orbit", "crane", "dolly", "handheld", "zoom",
]
SHOT_SIZE_WORDS = ["远景", "全景", "中景", "近景", "特写", "wide", "medium", "close-up", "close up", "extreme"]
NEG_ALLOWED = ["字幕", "bgm", "背景音乐", "对白", "人声", "音效", "声音", "音乐", "旁白", "配乐",
               "subtitle", "caption", "music", "dialogue", "narration", "voice", "sound", "score", "bgm"]
# Only explicit object-exclusion syntax; no blanket "no/without/无" scanning.
# Behavioral negation and ambiguous English phrases require semantic review.
NEG_PATTERNS = [r"不要出现[^，。；\n]{1,20}", r"不(?:能|准|得)?出现[^，。；\n]{1,20}",
                r"画面[里中内]没有[^，。；\n]{1,20}",
                r"\b(?:do not include|must not show|exclude)\s+[^.\n]{1,30}"]
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

ASSET_REF_RE = re.compile(r"(?:@?图片?|@?视频|@?音频|image|img|video|vid|audio|aud)\s*(\d+)", re.I)
ASSET_DECL_RE = re.compile(r"(?:@?图片?|@?视频|@?音频|image|img|video|vid|audio|aud)\s*(\d+)(?:\s*[-–至到]\s*(?:图片?|image|img)?\s*(\d+))?(?=\s*(?:=|＝|:|：|为))", re.I)
QUOTE_RE = re.compile(r"[“\"]([^”\"]{1,400})[”\"]")


def find_section(text, key):
    for alias in SECTION_ALIASES[key]:
        if alias in text:
            return True
    return False


def split_shots(text):
    return [(int(u.ident), u.start, u.end, u.body) for u in Document(text).shots]


def declared_duration(text, override):
    if override is not None:
        value = float(override)
        if not math.isfinite(value):
            raise ValueError("duration must be finite")
        return value
    m = re.search(r"\|\s*duration\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|", text, re.I)
    if m:
        return float(m.group(1))
    # Never take the first incidental reference-video/beat duration.
    m = re.search(r"(?:【总述】|【表演条件】|OVERVIEW[:：]?)\s*([^\n]+)", text, re.I)
    if m:
        number = re.search(r"(\d+(?:\.\d+)?)\s*(?:秒|s\b|-second|second)", m.group(1), re.I)
        if number:
            return float(number.group(1))
    return None


def speech_parameters(text):
    def field(key):
        match = re.search(r"\|\s*" + key + r"\s*\|\s*([^|\n]+)\|", text)
        return match.group(1).strip() if match else None
    density = field("台词密度")
    legacy = field("参数") or ""
    dense = density == "密" if density is not None else bool(
        re.search(r"(?:^|[·/；;、\s])(?:密度\s*)?密(?:$|[·/；;、\s])", legacy))
    # Density changes occupancy, not delivery speed. A dense scene can contain
    # slow lines. Faster rates require an explicit production estimate.
    defaults = (4.0, 2.5, 0.75 if dense else 2 / 3)
    values = []
    for key, default in zip(("语速字每秒", "语速词每秒", "台词占比上限"), defaults):
        raw = field(key)
        value = float(raw) if raw is not None else default
        if not math.isfinite(value) or value <= 0 or (key == "台词占比上限" and value > 1):
            raise ValueError(f"{key} invalid")
        values.append(value)
    return tuple(values)


def validate(path, duration_override=None, artifact="production", record=None, entry_id=None):
    text = Path(path).read_text(encoding="utf-8")
    metadata_text = text
    if artifact not in {"production", "performance", "raw"}:
        raise ValueError("invalid artifact")
    errors, warns, infos = [], [], []

    def err(code, msg): errors.append(f"{code} {msg}")
    def warn(code, msg): warns.append(f"{code} {msg}")
    def info(msg): infos.append(msg)

    if artifact == "raw":
        raw_errors, fidelity = check_raw(text, entry_id)
        return {"file": str(path), "errors": raw_errors, "warnings": [], "info": [],
                "lens": None, "ext_phrases": {},
                "checks": {"format": "not_applicable", "fidelity": fidelity,
                           "performance": "needs_review", "render": "not_tested"}}
    # Keep E-layer metadata out of observable prose and last shot/beat.
    text = re.split(r"^\|\s*(?:项|参数项)\s*\|", text, maxsplit=1, flags=re.M)[0]
    fields = metadata(metadata_text)
    task = task_type(fields, text) if artifact == "production" else None
    is_edit = task == "edit"
    is_extend = task == "extend"
    is_keyframe = task == "keyframe" or (task is None and bool(re.search(r"关键帧|keyframe", text, re.I)))
    parameter_state = "not_applicable"
    if artifact == "production":
        pe, pw, parameter_state = check_parameters(task, parameters(fields), roles_from_fields(fields))
        errors.extend(pe)
        warns.extend(pw)

    # E01 / E12 / W07 structure
    if artifact == "production" and not find_section(text, "refs"):
        err("E01", "缺少【素材绑定】/REFERENCES 段（无素材也要写「无参考素材」）")
    if artifact == "production" and task not in {"edit", "extend", "transition", "keyframe", "first_last", "motion"} and not is_keyframe and not find_section(text, "opening"):
        err("E12", "缺少【起始状态】/OPENING STATE 段")
    if artifact == "production" and not is_edit and not find_section(text, "global"):
        warn("W07", "缺少【贯穿要求】/GLOBAL RULES 段")
    if artifact == "production" and not has_subtitle_policy(text):
        warn("W07", "未声明字幕负向（建议加「不要字幕」）")
    if artifact == "production" and not has_sound_policy(text):
        warn("W07", "未声明声音策略（无 bgm / 只生成环境音 / bgm 描述）")

    # E07 triggers
    if is_edit and not any(t in text for t in EDIT_TRIGGERS):
        err("E07", "编辑任务缺少触发关键词（编辑视频/增加/加上/删除/去掉/修改/替换/改成）")
    if is_extend and not any(t in text for t in EXTEND_TRIGGERS):
        err("E07", "延长任务缺少触发关键词（向前/向后延长、延续、续写）")

    # E08 keyframe first sentence
    if is_keyframe:
        first = text.strip().splitlines()[0] if text.strip() else ""
        if not re.search(r"以图片?\s*\d+(?:(?:\s*[至到\-–、,，]\s*图片?\s*\d+)+)?\s*的顺序作为关键帧", first):
            err("E08", "关键帧任务首句须明确图片编号与顺序（单图或有序多图）")

    # E05 asset refs
    refs_block = ""
    for alias in SECTION_ALIASES["refs"]:
        if alias in text:
            start = text.index(alias)
            lines = text[start:].splitlines(keepends=True)
            kept = [lines[0]]
            for line in lines[1:]:
                if not line.strip() or ASSET_DECL_RE.match(line.lstrip()):
                    kept.append(line)
                else:
                    break
            refs_block = ''.join(kept)
            break
    declared = set()
    for m in ASSET_DECL_RE.finditer(refs_block):
        a, b = int(m.group(1)), m.group(2)
        first_ref = ASSET_REF_RE.match(m.group(0))
        kind = re.sub(r"\d+|@|\s", "", first_ref.group(0)).lower()
        kind = {"图片": "img", "图": "img", "image": "img", "img": "img", "视频": "vid", "video": "vid",
                "vid": "vid", "音频": "aud", "audio": "aud", "aud": "aud"}.get(kind, kind)
        if b:
            for n in range(a, int(b) + 1):
                declared.add((kind, n))
        else:
            declared.add((kind, a))
    # The keyframe sentence expresses order, not an upload declaration.
    # Its references must still appear in REFERENCES like all other assets.
    # Cross-references inside the binding section also need declarations.
    body_after_refs = text
    used = set()
    for m in ASSET_REF_RE.finditer(body_after_refs):
        kind = re.sub(r"\d+|@|\s", "", m.group(0)).lower()
        kind = {"图片": "img", "图": "img", "image": "img", "img": "img", "视频": "vid", "video": "vid",
                "vid": "vid", "音频": "aud", "audio": "aud", "aud": "aud"}.get(kind, kind)
        used.add((kind, int(m.group(1))))
    missing = sorted(used - declared)
    if missing:
        err("E05", f"引用了未声明的素材：{', '.join(f'{k}{n}' for k, n in missing)}")
    info(f"素材声明 {len(declared)} 个，引用 {len(used)} 个")

    # timestamps
    shots = split_shots(text)
    dur = declared_duration(metadata_text, duration_override)
    if dur is None and isinstance(record, dict) and type(record.get("duration")) in (int, float):
        dur = float(record["duration"])
    if dur is not None and (not math.isfinite(dur) or (not is_edit and (dur <= 0 or dur != int(dur)))):
        err("E04", "总时长必须为正整数秒")
    beats = split_beats(text)
    document = Document(text)
    errors.extend(document.ownership_errors())
    # All declarations refer to the same generated timeline (editing is locked
    # to the input instead). No precedence rule may silently hide a conflict.
    if not is_edit:
        overview_duration = declared_duration(text, None)
        if overview_duration is not None and dur is not None and overview_duration != dur:
            err("E04", "总述与参数/命令行声明的时长不一致")
        if duration_override is not None and fields.get("duration") is not None and float(fields["duration"]) != dur:
            err("E04", "参数表与命令行声明的时长不一致")
    if artifact == "performance" or beats or record is not None:
        errors.extend(timing_errors(beats, dur, shots, complete=artifact == "performance" or not shots))
    if artifact == "performance" and dur is not None and dur > 30:
        err("E06", "clip 总时长 > 30s")
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
    elif task not in {"edit", "motion", "transition"} and artifact == "production":
        warn("W08", "未识别到「镜头N（a-bs）」格式的分镜段落")

    # Explicit dialogue settings only; emotional intensity is independent.
    ZH_RATE, EN_RATE, SPEECH_CAP = speech_parameters(metadata_text)
    info(f"台词估算 {ZH_RATE:g} 字/s，{EN_RATE:g} 词/s，占比 {SPEECH_CAP:g}（可覆盖的估时假设）")

    # Camera checks remain shot-level; dialogue below uses the smallest timed unit.
    for no, s, e, body in shots:
        head = body[:80]
        if not re.search(r"【[^】]{2,40}】|\[[^\]]{2,60}\]", head):
            warn("W08", f"镜头{no} 段首缺少【景别，角度，运镜】标注")
        elif not any(w in head for w in SHOT_SIZE_WORDS):
            warn("W08", f"镜头{no} 标注里没有景别词")
        # 去掉与"推门""拉开"等动作误报：只在标注括号内统计
        tag = re.search(r"【([^】]{2,60})】|\[([^\]]{2,80})\]", head)
        tag_txt = (tag.group(1) or tag.group(2)) if tag else ""
        tag_moves = [w for w in CAMERA_MOVES if w in tag_txt]
        if len(tag_moves) > 2:
            warn("W10", f"镜头{no} 标注含多个运镜词 {tag_moves}（核对同步/先后关系与表演可见性，不自动删复合运镜）")
    de, dw, dialogue, total_speech = dialogue_checks(document, dur, (ZH_RATE, EN_RATE, SPEECH_CAP))
    errors.extend(de)
    warns.extend(dw)
    info(f"台词估时 {total_speech:.1f}s")
    # Ancillary prose hints inspect complete shots, including beat-external text.
    for no, s, e, body in shots or beats:
        if re.search(r"\d+\s*秒?内.{0,10}\d+\s*次|\d+\s*times? (?:per|in) \d+", body):
            warn("W09", f"镜头{no} 用时间戳控制频次（官方不建议）")
        # Acting quality is a semantic review, never a body-part keyword pass.
        # dialogue
        quotes = QUOTE_RE.findall(body)
        speakers = {row['speaker'] for row in dialogue if row['shot'] == str(no)}
        if quotes:
            if len(speakers) >= 2 and any(not row['explicit'] for row in dialogue if row['shot'] == str(no)):
                warn("W11", f"镜头{no} 有 {len(speakers)} 个说话人（{', '.join(speakers)}），确认不是同框同时说话")
            if not has_mouth_direction(body) and len(speakers) >= 1 and re.search(r"[两二]人|B|另一|对方|listener|the other", body):
                warn("W05", f"镜头{no} 有台词但未写非说话者嘴部状态")
        # W19 retired: punctuation cannot infer unrelated dramatic intentions.
        # Actual speech-window/occupancy checks above remain active.
        for pat in SPEECH_LEAK:
            if re.search(pat, body):
                warn("W06", f"镜头{no} 疑似引号外的台词描述（明确逐字台词，避免仅给概述）")
                break

    prose_body = text
    warns.extend(repeated_blocks(beats or shots))

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
                warn("W17", f"运镜「{tag_moves_seq[i]}」连续 {run} 镜（审阅是否有意持续；固定机位不计）")
        else:
            run = 1

    # W18 retired: reusable body actions are not prohibited quotations.

    # W13 导演名
    name_prose = re.sub(r'希区柯克变焦|Hitchcock\s+zoom', '', prose_body, flags=re.I)
    hits = [n for n in DIRECTOR_NAMES if re.search(re.escape(n), name_prose, re.I)]
    if hits:
        warn("W13", f"Prompt 正文出现导演/影片人名 {hits}（名字不是可观察量，改写为机位/光/运镜/部位）")

    # W15 反套路
    for pat, label in CLICHE_PATTERNS:
        if re.search(pat, prose_body, re.I):
            warn("W15", f"反套路组合「{label}」（允许，但 QA 里要写一行指回主控句的理由）")

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
            warn("W01", f"画面级负向描述「{frag}」（对象排除建议改为正向；行为保持不在此类）")

    # W02 vague
    found = [w for w in VAGUE_WORDS if re.search(re.escape(w), text, re.I)]
    if found:
        warn("W02", f"空泛风格词：{found}（改为可见量：媒介/光/色调/质地）")

    lens = None
    m = re.search(r"\|\s*透镜\s*\|\s*([^|\n]+)\|", metadata_text)
    if m:
        lm = re.search(r"L\d+", m.group(1))
        lens = lm.group(0) if lm else m.group(1).strip()
    fidelity = "not_checked"
    if record is not None:
        fidelity_errors, fidelity = check_record(record, beats, dur)
        errors.extend(fidelity_errors)
    return {"file": str(path), "errors": errors, "warnings": warns, "info": infos, "lens": lens,
            "task": task, "parameters": parameter_state, "dialogue": dialogue,
            "assets": {"declared": sorted(f"{kind}{n}" for kind, n in declared), "used": sorted(f"{kind}{n}" for kind, n in used)},
            "fidelity_scope": "original_exact" if record and record.get("mode") == "raw" else "beat_text_only; other prose and source semantics require review" if record else "not_checked",
            "ext_phrases": {},  # retained return key for 2.2 callers; no word-frequency judging
            "checks": {"format": "failed" if any(e.startswith("E") for e in errors) else "passed",
                       "fidelity": fidelity, "performance": "needs_review", "render": "not_tested"}}


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--duration", type=float)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--artifact", choices=("production", "performance", "raw"), default="production")
    parser.add_argument("--record", type=Path)
    parser.add_argument("--entry-id", type=int)
    parser.add_argument("--batch", choices=("sequence", "independent"), default="sequence")
    parser.add_argument("--production-record", type=Path, help="actual per-clip assets, parameters and review evidence")
    parser.add_argument("--require-ready", action="store_true", help="require production preflight, not a render-quality claim")
    args = parser.parse_args(argv[1:])
    if args.record and len(args.paths) != 1:
        parser.error("--record applies to exactly one prompt")
    if args.artifact == "raw" and (args.entry_id is None or args.record):
        parser.error("raw requires --entry-id and does not take --record")
    if args.entry_id is not None and args.artifact != "raw":
        parser.error("--entry-id requires --artifact raw")
    if (args.production_record or args.require_ready) and (args.artifact != "production" or len(args.paths) != 1):
        parser.error("production preflight applies to one production prompt")
    if args.require_ready and not args.production_record:
        parser.error("--require-ready requires --production-record")
    try:
        record = json.loads(args.record.read_text(encoding="utf-8")) if args.record else None
        if args.record and not isinstance(record, dict):
            raise ValueError("record must be an object")
        results = [validate(p, args.duration, args.artifact, record, args.entry_id) for p in args.paths]
        if args.production_record:
            from production_preflight import preflight
            results[0]["preflight"] = preflight(args.production_record, Path(args.paths[0]), results[0])
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.error(str(exc))
    as_json = args.json

    cross = []
    if len(results) > 1 and args.batch == "sequence":
        for a, b in zip(results, results[1:]):
            if a["lens"] and a["lens"] == b["lens"]:
                cross.append(f"W16 相邻 clip 同一主透镜 {a['lens']}：{Path(a['file']).name} → {Path(b['file']).name}")

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
            print("CHECK " + json.dumps(result["checks"], ensure_ascii=False))
            if "preflight" in result:
                print("PREFLIGHT " + json.dumps(result["preflight"], ensure_ascii=False))
            print(f"== {len(result['errors'])} error(s), {len(result['warnings'])} warning(s)")
        if cross:
            print("== cross-clip")
            for c in cross:
                print(f"WARN  {c}")
    return 1 if any(r["errors"] or (args.require_ready and r.get("preflight", {}).get("status") != "passed") for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

"""Deterministic timing and text-fidelity checks, not an acting quality scorer."""
import math
import re

from emotion_library import load_library
from prompt_structure import Document

def split_beats(text):
    return [unit.tuple() for unit in Document(text).beats]


def timing_errors(units, duration, shots=None, complete=True):
    errors = []
    if not units:
        return ["E20 未识别到表演节拍；使用「节拍 id（a-bs）：正文」或「a–b秒：正文」"]
    ids = [b[0] for b in units]
    if len(set(ids)) != len(ids):
        errors.append("E20 表演节拍标识重复")
    for ident, start, end, body in units:
        if not start.is_integer() or not end.is_integer():
            errors.append(f"E02 节拍 {ident} 时间戳非整数秒")
        if end <= start or start < 0:
            errors.append(f"E03 节拍 {ident} 时间范围无效")
        if not body:
            errors.append(f"E20 节拍 {ident} 正文为空")
        if shots and not any(s <= start < end <= e for _, s, e, _ in shots):
            errors.append(f"E20 节拍 {ident} 未完整包含于一个镜头")
    if complete and units[0][1] != 0:
        errors.append("E03 表演首节拍不从 0 开始")
    for a, b in zip(units, units[1:]):
        if (complete and a[2] != b[1]) or a[2] > b[1]:
            errors.append(f"E03 节拍 {a[0]} → {b[0]} 有缺口或重叠")
    if duration is None:
        errors.append("E04 缺少明确总时长；使用 --duration、记录或总述/表演条件")
    elif units[-1][2] > duration or (complete and units[-1][2] != duration):
        errors.append("E04 表演结束时间与总时长不一致")
    return errors


def is_number(value):
    return type(value) in (int, float) and math.isfinite(value)


def check_record(record, units, duration, library=None):
    """Compare an upstream C-layer record to independently parsed D-layer beats.

    No self-reported review score is accepted. Matching only proves text identity.
    """
    entries = load_library() if library is None else library
    errors = []
    if not isinstance(record, dict) or type(record.get("version")) is not int or record["version"] != 1:
        return ["F01 无效记录版本"], "failed"
    mode = record.get("mode")
    if mode not in {"raw", "adapt", "blend", "free"}:
        errors.append("F01 未识别的表演模式")
    rd = record.get("duration")
    if not is_number(rd) or rd <= 0 or rd != int(rd):
        errors.append("F01 记录 duration 必须为正整数秒")
    elif duration is not None and rd != duration:
        errors.append("F02 记录与 Prompt 总时长不一致")
    beats = record.get("beats")
    if not isinstance(beats, list) or not beats:
        return errors + ["F01 记录需要非空 beats"], "failed"
    if len(beats) != len(units):
        errors.append("F02 C/D 表演节拍数量不一致")
    all_ids, beat_ids = set(), set()
    for index, beat in enumerate(beats):
        if not isinstance(beat, dict):
            errors.append(f"F01 第 {index + 1} 个记录节拍不是对象")
            continue
        ident = beat.get("id")
        if not isinstance(ident, str) or not ident.strip() or ident in beat_ids:
            errors.append("F01 记录节拍 id 为空或重复")
        else:
            beat_ids.add(ident)
        if not isinstance(beat.get("actor"), str) or not beat["actor"].strip():
            errors.append(f"F01 节拍 {ident} 缺少角色")
        start, end, body = beat.get("start"), beat.get("end"), beat.get("text")
        if not (is_number(start) and is_number(end) and 0 <= start < end
                and start == int(start) and end == int(end)):
            errors.append(f"F01 节拍 {ident} 记录时间无效")
        if not isinstance(body, str) or not body.strip():
            errors.append(f"F01 节拍 {ident} 缺完整正文")
            body = ""
        if index < len(units):
            did, ds, de, dbody = units[index]
            if ident != did:
                errors.append(f"F02 节拍 {ident} C/D 标识不一致（输出 {did}）")
            if (start, end) != (ds, de):
                errors.append(f"F02 节拍 {ident} C/D 时间不一致")
            if body != dbody:
                errors.append(f"F03 节拍 {ident} C/D 正文不同（遗漏、增加、重排或改字）")
        entry_ids = beat.get("entry_ids")
        if not isinstance(entry_ids, list) or any(type(n) is not int for n in entry_ids):
            errors.append(f"F01 节拍 {ident} entry_ids 格式错误")
            entry_ids = []
        for eid in entry_ids:
            if eid not in entries:
                errors.append(f"F04 未知条目 {eid}")
            all_ids.add(eid)
        if mode != "free" and not entry_ids:
            errors.append(f"F04 节拍 {ident} 未关联条目；库外创作用 free")
        keep = beat.get("keep")
        if not isinstance(keep, list) or (mode != "free" and not keep):
            errors.append(f"F01 节拍 {ident} 缺少本次保留细节")
            keep = []
        for cue in keep:
            if (not isinstance(cue, dict) or not isinstance(cue.get("text"), str)
                    or not cue["text"].strip() or not isinstance(cue.get("reason"), str)
                    or not cue["reason"].strip()):
                errors.append(f"F01 节拍 {ident} 保留细节缺正文或理由")
            elif cue["text"] not in body:
                errors.append(f"F05 节拍 {ident} 已确认正文缺少保留细节：{cue['text']}")
        changes = beat.get("changes")
        if not isinstance(changes, list) or any(not isinstance(c, str) or not c.strip() for c in changes):
            errors.append(f"F01 节拍 {ident} changes 应为文本列表")
            changes = []
        if mode == "raw":
            if changes or len(entry_ids) != 1 or entry_ids[0] not in entries or body != entries[entry_ids[0]]["prompt"]:
                errors.append(f"F06 节拍 {ident} 不符合原文直用；调整内容应标 adapt/blend")
        elif mode in {"adapt", "blend"} and not changes:
            if not any(body == entries[n]["prompt"] for n in entry_ids if n in entries):
                errors.append(f"F06 节拍 {ident} 改编但未记录实质调整")
    if mode in {"raw", "adapt"} and len(all_ids) != 1:
        errors.append("F06 raw/adapt 整个记录只能关联一个条目；多条用 blend")
    if mode == "blend" and len(all_ids) < 2:
        errors.append("F06 blend 需要至少两个不同条目")
    if mode == "free" and all_ids:
        errors.append("F06 free 不能同时声称库条目保真")
    return errors, ("failed" if errors else "matched" if mode != "free" else "upstream_matched")


def check_raw(text, entry_id, library=None):
    entries = load_library() if library is None else library
    if entry_id not in entries:
        return ["F04 raw 需要有效 --entry-id"], "failed"
    # Permit one file-terminating newline, not whitespace or paraphrase changes.
    if text.removesuffix("\n") != entries[entry_id]["prompt"]:
        return ["F06 原文正文不一致；说明放正文之外，翻译/调整应标改编"], "failed"
    return [], "matched"


def repeated_blocks(units):
    """Flag identical adjacent complete units; do not count words/body parts."""
    warnings = []
    for first, second in zip(units, units[1:]):
        a = re.sub(r"^\s*(?:【[^】]*】|\[[^\]]*\])", "", first[3]).strip()
        b = re.sub(r"^\s*(?:【[^】]*】|\[[^\]]*\])", "", second[3]).strip()
        if a and a == b:
            warnings.append(f"W14 相邻完整表演块 {first[0]}/{second[0]} 相同；审阅是否有意持续，不要求换通道或换词")
    return warnings

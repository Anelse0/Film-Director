#!/usr/bin/env python3
"""概念卡校验（film-seedance-director S3a，2.5.5）。

用法: python3 validate_concept.py <01_concept.md> [--json]

只查格式与交付完整性，不判断创意质量。候选数量不固定；集中研究一个题材不是错误。

ERROR（退出码 1）:
  C01 没有候选，或候选只有标题 / 全部字段为空（空候选不能通过）
  C03 研究记录的查询与示例查询几乎相同（示例不是模板）
  C05 候选标题与工作示例相同且一句话 / 主控画面也与示例重合（常见标题本身不是抄袭证据）

WARN:
  C02 缺创作判断（最初理解 / 最后理解 / 独特之处 / 锁定与探索 少于 3 项）
  C04 ≥ 2 候选时缺"与其他候选的差异"行，或差异只提地点
  C06 候选主控画面共用物件词（可能只换了地点）
  C07 研究记录缺失、缺列、来源为占位符，或发现 / 可信范围 / 影响决定为空
  C08 候选声明依赖外部事实，但研究记录里没有对应行
  C09 候选缺必填行（一句话 / 主控画面 / 独特之处 / 人物 / 观众）
  C10 "这 N 秒拍什么"含镜头词（概念阶段偷做分镜）
  C11 候选一句话只是主题词（"关于……"且没有人物动作）
"""
import json
import re
import sys
from pathlib import Path

EXAMPLE_QUERIES = [
    "失智 配偶 照护 手续 实务", "探视 规定 家属 范围 实务", "分手后 还要 一起 处理 的 事 实务",
    "分手后 还要 一起 处理 的 事 手续 合租 宠物 账号 定金 清单",
    "情侣 分手 后 最 麻烦 的 共同 财产 共同 账户 会员 卡 怎么 处理 知乎",
    "分手 后 还要 一起 处理 的 手续 清单 实务", "情侣 分手 最麻烦 的 手续 共同 账户 合同 变更 纠纷",
]
# 工作示例（examples/concept-worked-examples.md）的候选：标题 + 内容一起比对。
# 常见词标题（钥匙、结婚证、健身卡…）不再单独构成错误：它们不是任何人的专属。
EXAMPLE_CANDIDATES = {
    "两次取平均": "女儿夜班后回家，父亲已经睡了；桌上血压计的记录本里，每天都是两行数字。 厨房顶灯下，记录本翻开，两行数字，旁边是她的护士鞋。",
    "袖带": "父亲来医院复查，排到女儿的诊室；她给他绑袖带时发现袖带位置他自己已经量对了。 诊室里，她的手停在他手臂的袖带上，两人都看着血压计。",
}
PLACEHOLDER = {"", "…", "...", "无", "-", "—", "略", "待补"}
SHOT_WORDS = ["近景", "特写", "全景", "中景", "远景", "缓推", "推近", "拉远", "摇镜", "跟拍", "切到", "手持", "越肩", "俯拍", "仰拍", "镜头"]
LOCATION_ONLY = ["发生在", "地点", "场所", "换到", "换成", "换个地方", "改在"]
DIFF_WORDS = ["人物", "选择", "事件", "理解", "观众", "回应", "放弃", "争取", "翻转", "判断", "关系", "结局", "动机", "决定"]
STUB_FIELDS = {"一句话", "人物", "观众", "主控画面", "独特之处", "依赖的事实与可信范围", "依赖的事实", "风险", "与其他候选的差异", "这"}


def toks(q):
    return set(t for t in re.split(r"[\s,，、/|]+", q.strip().lower()) if t)


def split_candidates(text):
    """返回 [(title, block_text)]；块从 '候选 〈…〉' 行到下一个候选或下一个二级标题。"""
    heads = [m for m in re.finditer(r"^\s*候选\s*\d*\s*[〈《]([^〉》]+)[〉》][^\n]*$", text, re.M)]
    out = []
    for i, m in enumerate(heads):
        start = m.end()
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        sect = re.search(r"^## ", text[start:end], re.M)
        if sect:
            end = start + sect.start()
        out.append((m.group(1).strip(), text[m.start():end]))
    return out


def field(block, name):
    m = re.search(rf"^\s*{re.escape(name)}[^:：\n]*[:：][ \t]*(.*)$", block, re.M)  # 不让 \s 吞掉换行
    return m.group(1).strip() if m else None


FIELD_LINE = r"^\s*(一句话|前提|反讽|基调|人物|观众|主控画面|这 ?.*拍什么|独特之处|依赖|风险|与其他候选)"


def field_lines(block):
    return [l for l in block.splitlines() if re.match(FIELD_LINE, l)]


def is_full(title, block):
    """被否候选只有一行（标题 + 一句话 + 不选理由）；有 ≥ 2 个字段行的才算完整候选。"""
    return len(field_lines(block)) >= 2


def is_empty(title, block):
    """只有标题，或所有字段行的值都是占位符：空候选。"""
    lines = block.splitlines()
    values = [re.sub(r"^[^:：]*[:：]\s*", "", l).strip() for l in field_lines(block)]
    head = lines[0] if lines else ""
    after_title = re.sub(r"^\s*候选\s*\d*\s*[〈《][^〉》]+[〉》]", "", head).strip(" \t—-–:：")
    rest = [l.strip() for l in lines[1:] if l.strip()]
    if not rest:
        return len(after_title) < 6  # 被否候选把一句话与理由写在标题行上，不算空
    return bool(values) and all(v in PLACEHOLDER for v in values) and len(rest) == len(values)


def grams(text, n=3):
    text = re.sub(r"\s+", "", text)
    return {text[i:i + n] for i in range(max(0, len(text) - n + 1))}


def main(path, as_json=False):
    text = Path(path).read_text(encoding="utf-8")
    errors, warns = [], []

    cands = split_candidates(text)
    if not cands:
        errors.append("C01 没有候选（需要至少 1 个「候选 〈标题〉」块）")
    for t, b in cands:
        if is_empty(t, b):
            errors.append(f"C01 候选〈{t}〉为空：只有标题或所有字段为占位符，空候选不能通过")
    full = [(t, b) for t, b in cands if is_full(t, b) and not is_empty(t, b)]
    if cands and not full and not any(is_empty(t, b) for t, b in cands):
        errors.append("C01 没有完整候选：每个候选块都只有一行（被否候选格式），没有任何一个可以选定的候选")

    # C02 创作判断
    judg = sum(1 for k in ("最初", "最后", "独特", "锁定") if re.search(k, text))
    if judg < 3:
        warns.append(f"C02 创作判断只找到 {judg}/4 项（最初理解 / 最后理解 / 独特之处 / 锁定与探索）")

    # C05 示例照搬：标题相同且内容重合才算；标题相同但内容自写只提示
    for t, b in cands:
        if t in EXAMPLE_CANDIDATES and "夹具" not in text[:400]:
            own = " ".join(x for x in ((field(b, "一句话") or ""), (field(b, "主控画面") or "")) if x)
            g_own, g_ex = grams(own), grams(EXAMPLE_CANDIDATES[t])
            overlap = len(g_own & g_ex) / len(g_ex) if g_ex else 0
            if own and overlap >= 0.5:
                errors.append(f"C05 候选〈{t}〉的标题与一句话 / 主控画面都与工作示例重合（示例不是模板）")
            else:
                warns.append(f"C05 候选〈{t}〉与工作示例同名；内容不同不算照搬，如无意请换标题避免混淆")

    # per-candidate checks
    m_res = re.search(r"^#+\s*(研究记录|检索记录)|^(研究记录|检索记录)\s*$", text, re.M)
    research_text = text[m_res.start():] if m_res else ""
    imgs = []
    for t, b in full:
        missing = [n for n in ("一句话", "人物", "观众", "主控画面", "独特之处") if (field(b, n) is None or field(b, n) in PLACEHOLDER)]
        if missing:
            warns.append(f"C09 候选〈{t}〉缺 {'/'.join(missing)}")
        one = field(b, "一句话") or ""
        if re.match(r"^(关于|一个关于|讲述)", one) and not re.search(r"[他她它们]\S*(要|想|做|说|拒|替|等|藏|去|回)", one):
            warns.append(f"C11 候选〈{t}〉一句话是主题词：「{one}」")
        shot = None
        for l in b.splitlines():
            if re.match(r"^\s*这\s*\S*\s*(秒|格式|分钟|s)?\S*拍什么", l):
                shot = l
        if shot and any(w in shot for w in SHOT_WORDS):
            warns.append(f"C10 候选〈{t}〉「拍什么」行含镜头词，概念阶段不分镜")
        if len(full) >= 2:
            diff = field(b, "与其他候选的差异")
            if diff is None:
                warns.append(f"C04 候选〈{t}〉缺「与其他候选的差异」行")
            elif not any(w in diff for w in DIFF_WORDS) or (any(w in diff for w in LOCATION_ONLY) and not any(w in diff for w in DIFF_WORDS)):
                warns.append(f"C04 候选〈{t}〉的差异只提地点或未指向人物 / 事件 / 观众理解：「{diff}」")
        dep = field(b, "依赖的事实与可信范围") or field(b, "依赖的事实")
        if dep and not re.search(r"无外部事实|无依赖|不依赖", dep):
            if not research_text.strip() or not re.search(r"^\s*\|", research_text, re.M):
                warns.append(f"C08 候选〈{t}〉声明依赖外部事实，但没有研究记录表")
        img = field(b, "主控画面")
        if img:
            imgs.append((t, set(re.findall(r"[一-鿿]{2,3}", img)) - {"一个", "一把", "一张", "画面", "两人", "他的", "她的", "始终", "下面"}))
    for i in range(len(imgs)):
        for j in range(i + 1, len(imgs)):
            common = imgs[i][1] & imgs[j][1]
            if len(common) >= 2:
                warns.append(f"C06 候选〈{imgs[i][0]}〉与〈{imgs[j][0]}〉主控画面共用物件词 {sorted(common)}")

    # research table
    rows = []
    for line in research_text.splitlines():
        s = line.strip()
        if s.startswith("|") and not re.match(r"^\|\s*-", s):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells and cells[0] in ("缺口", "粒度", "候选", "材料 / 来源"):
                continue  # 表头
            rows.append(cells)
    if not rows:
        if full and any((field(b, "依赖的事实与可信范围") or field(b, "依赖的事实") or "") and not re.search(r"无外部事实|无依赖", field(b, "依赖的事实与可信范围") or field(b, "依赖的事实") or "") for _, b in full):
            warns.append("C07 研究记录为空，但有候选依赖外部事实")
    for r in rows:
        if len(r) < 5:
            warns.append(f"C07 研究记录行缺列（需 缺口 / 材料与来源 / 具体发现 / 可信范围 / 影响哪项决定）：{r}")
            q = r[1] if len(r) > 1 else ""
        else:
            q = r[1]
            src_ok = re.search(r"https?://|未核实|访谈|手册|条例|规定|判例|问答|页|文件|书|报告", r[1])
            if r[1] in PLACEHOLDER or not src_ok:
                warns.append(f"C07 研究记录来源不可回访也未标「未核实」：「{r[1]}」")
            for idx, name in ((2, "具体发现"), (3, "可信范围"), (4, "影响哪项决定")):
                if r[idx] in PLACEHOLDER:
                    warns.append(f"C07 研究记录「{name}」为空：{r[:2]}")
        for ex in EXAMPLE_QUERIES:
            shared = len(toks(q) & toks(ex))
            if toks(q) and (toks(q) == toks(ex) or (shared >= 4 and shared >= 0.75 * len(toks(ex)))):
                errors.append(f"C03 研究查询「{q}」与示例查询几乎相同（示例不是模板）")
                break

    result = {"path": str(path), "errors": errors, "warnings": warns, "candidates": len(full), "rejected": len(cands) - len(full), "research_rows": len(rows)}
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"== validate_concept: {path}")
        for e in errors:
            print(f"ERROR {e}")
        for w in warns:
            print(f"WARN  {w}")
        print(f"INFO  完整候选 {len(full)}，被否候选 {len(cands) - len(full)}，研究记录 {len(rows)} 行")
        print(f"== {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__); sys.exit(2)
    sys.exit(main(args[0], as_json="--json" in sys.argv))

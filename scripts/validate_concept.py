#!/usr/bin/env python3
"""概念卡校验（film-seedance-director S3a）。

用法: python3 validate_concept.py <02_script/concept.md>

检查:
  C01 候选 < 3
  C02 检索记录缺失（有 WebSearch 环境时应有 ≥ 2 条 D1）
  C03 D1 查询与 concept-generation.md 的示例查询逐字相同（示例不是模板）
  C04 D1 查询之间相似度过高（共用词 ≥ 50%）或全部落在同一处境（如都含"分手"）
  C05 候选标题与工作示例候选相同（家庭共享 / 结婚证 / 疫苗本 / 五二零 / 第一次约会 / 浇水 / 备注名 / 健身卡）
  C06 三个候选的主控画面重复（同一物件词出现在 ≥ 2 个候选的主控画面里）
  C07 缺少 D0 内核展开（处境清单 < 6 条）
"""
import re
import sys
from pathlib import Path

EXAMPLE_QUERIES = [
    "失智 配偶 照护 手续 实务", "探视 规定 家属 范围 实务", "分手后 还要 一起 处理 的 事 实务",
    "分手后 还要 一起 处理 的 事 手续 合租 宠物 账号 定金 清单",
    "情侣 分手 后 最 麻烦 的 共同 财产 共同 账户 会员 卡 怎么 处理 知乎",
    "分手 后 还要 一起 处理 的 手续 清单 实务", "情侣 分手 最麻烦 的 手续 共同 账户 合同 变更 纠纷",
]
EXAMPLE_TITLES = ["家庭共享", "结婚证", "疫苗本", "五二零", "第一次约会", "浇水", "备注名", "健身卡", "钥匙", "酸奶"]
DEFAULT_SITUATION = ["分手", "前任", "breakup", "ex "]


def toks(q):
    return set(t for t in re.split(r"[\s,，、/|]+", q.strip().lower()) if t)


def main(path):
    text = Path(path).read_text(encoding="utf-8")
    errors, warns = [], []

    cands = re.findall(r"^\s*候选\s*\d+", text, re.M)
    if len(cands) < 3:
        errors.append(f"C01 候选只有 {len(cands)} 个（需要 3）")

    # D0
    d0 = re.search(r"(内核展开|处境清单)[\s\S]{0,1500}", text)
    if d0:
        lines = [l for l in d0.group(0).splitlines()[1:] if re.match(r"\s*[-•\d]", l)]
        if len(lines) < 6:
            warns.append(f"C07 内核展开处境 {len(lines)} 条 < 6")
    else:
        warns.append("C07 缺少 D0 内核展开段")

    # queries from 检索记录 table rows containing D1
    queries = []
    for line in text.splitlines():
        if line.strip().startswith("|") and re.search(r"D1", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                queries.append(cells[1])
    if not queries:
        warns.append("C02 检索记录里没有 D1 查询（无 WebSearch 环境可忽略，但需标「未核实」）")
    for q in queries:
        for ex in EXAMPLE_QUERIES:
            shared = len(toks(q) & toks(ex))
            if toks(q) == toks(ex) or (shared >= 4 and shared >= 0.75 * len(toks(ex))):
                errors.append(f"C03 D1 查询「{q}」与示例查询几乎相同（示例不是模板）")
                break
    for i in range(len(queries)):
        for j in range(i + 1, len(queries)):
            a, b = toks(queries[i]), toks(queries[j])
            if a and b and len(a & b) / min(len(a), len(b)) >= 0.5:
                warns.append(f"C04 D1 查询 {i+1} 与 {j+1} 共用词 ≥ 50%（应跨处境、跨形式）")
    if queries and all(any(d in q for d in DEFAULT_SITUATION) for q in queries):
        errors.append("C04 所有 D1 查询都落在默认处境「分手」（默认处境最多占一条）")

    # titles
    titles = re.findall(r"候选\s*\d+\s*[〈《]([^〉》]+)[〉》]", text)
    for t in titles:
        if t in EXAMPLE_TITLES:
            errors.append(f"C05 候选标题〈{t}〉与工作示例相同")
    # 主控画面 objects
    imgs = re.findall(r"主控画面[:：]\s*([^\n]+)", text)
    nouns = []
    for im in imgs:
        nouns.append(set(re.findall(r"[一-鿿]{2,3}", im)))
    for i in range(len(nouns)):
        for j in range(i + 1, len(nouns)):
            common = nouns[i] & nouns[j] - {"一个", "一把", "一张", "画面", "两人", "他的", "她的"}
            if len(common) >= 2:
                warns.append(f"C06 候选 {i+1} 与 {j+1} 的主控画面共用物件词 {sorted(common)}")

    print(f"== validate_concept: {path}")
    for e in errors:
        print(f"ERROR {e}")
    for w in warns:
        print(f"WARN  {w}")
    print(f"INFO  候选 {len(cands)}，D1 查询 {len(queries)}")
    print(f"== {len(errors)} error(s), {len(warns)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    sys.exit(main(sys.argv[1]))

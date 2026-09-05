"""2.4.0 concept validator contracts: no fixed candidate count, no topic ban, research rows carry 可信范围."""
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import validate_concept  # noqa: E402

JUDGEMENT = """## 创作判断
- 观众最初会怎样理解这件事：X
- 我们希望他们最后怎样理解人物：Y
- 本作最值得保留的独特之处：Z
- 锁定：A ／ 探索：B
"""

def cand(title, diff=None, dep="无外部事实依赖", shot="她把杯子推过去，他没接。"):
    lines = [f"候选 〈{title}〉", "一句话：她想把钥匙还回去，他不肯接。", "人物：她认为这是最后一次；她选择不说话。",
             "观众：最初以为她在告别 → 看见钥匙串上还有他家的门卡后改变判断。", f"主控画面：{title}和一把钥匙放在桌上。",
             f"这 30 秒拍什么：{shot}", "独特之处：她还的不是钥匙，是门卡。", f"依赖的事实与可信范围：{dep}", "风险：手部小动作。"]
    if diff is not None:
        lines.append(f"与其他候选的差异：{diff}")
    return "\n".join(lines) + "\n"

RESEARCH = """## 研究记录
| 缺口 | 材料 / 来源 | 具体发现 | 可信范围 | 影响哪项决定 |
|---|---|---|---|---|
| 依赖制度 | 分手后合租退租实务问答 https://example.org/a | 押金只退给签约人 | 真实材料；地区差异 | 候选〈杯子〉的阻力 |
| 依赖制度 | 分手后共同宠物归属判例摘要 https://example.org/b | 登记人优先 | 真实材料；判例摘要 | 候选〈杯子〉的结尾 |
"""

def run(text):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / '01_concept.md'
        path.write_text(text, encoding='utf-8')
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = validate_concept.main(str(path))
        return rc, buf.getvalue()

class ConceptValidatorTests(unittest.TestCase):
    def test_single_candidate_is_valid(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子"))
        self.assertEqual(rc, 0, out)
        self.assertIn("0 error(s), 0 warning(s)", out)

    def test_concentrated_topic_research_is_not_an_error(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", dep="押金只退签约人（真实材料）") + RESEARCH)
        self.assertEqual(rc, 0, out)
        self.assertNotIn("默认处境", out)

    def test_location_only_difference_warns(self):
        text = "# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", diff="发生在机场。") + cand("门卡", diff="人物选择不同：她主动留下门卡。")
        rc, out = run(text)
        self.assertEqual(rc, 0)
        self.assertIn("C04 候选〈杯子〉", out)
        self.assertNotIn("C04 候选〈门卡〉", out)

    def test_placeholder_source_warns(self):
        bad = RESEARCH.replace("https://example.org/a", "…").replace("分手后合租退租实务问答 ", "")
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", dep="押金只退签约人") + bad)
        self.assertEqual(rc, 0)
        self.assertIn("C07", out)

    def test_dependency_without_research_warns(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", dep="押金只退签约人"))
        self.assertIn("C08", out)

    def test_shot_words_in_concept_warn(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", shot="近景缓推到钥匙。"))
        self.assertIn("C10", out)

    def test_example_query_is_error(self):
        research = RESEARCH.replace("分手后合租退租实务问答 https://example.org/a", "探视 规定 家属 范围 实务")
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子", dep="x") + research)
        self.assertEqual(rc, 1)
        self.assertIn("C03", out)

    def test_no_candidate_is_error(self):
        rc, out = run("# Concept\n" + JUDGEMENT)
        self.assertEqual(rc, 1)
        self.assertIn("C01", out)

if __name__ == '__main__':
    unittest.main()

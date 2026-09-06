"""Concept validator contracts (2.4.0 + 2.5.5): no fixed candidate count, no topic ban, research rows carry 可信范围;
empty candidates fail, common titles are not plagiarism evidence."""
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

    # 2.5.5 P0 fixes
    def test_title_only_candidate_is_error(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n候选 〈空壳〉\n")
        self.assertEqual(rc, 1)
        self.assertIn("C01 候选〈空壳〉为空", out)

    def test_placeholder_only_candidate_is_error(self):
        text = "# Concept\n" + JUDGEMENT + "## 候选\n候选 〈占位〉\n一句话：\n人物：…\n观众：待补\n主控画面：-\n独特之处：无\n"
        rc, out = run(text)
        self.assertEqual(rc, 1)
        self.assertIn("C01 候选〈占位〉为空", out)

    def test_rejected_one_line_candidate_is_not_empty(self):
        text = "# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子") + "候选 〈门卡〉—— 她想进楼却没有门卡；不选因为：观众理解没有变化。\n"
        rc, out = run(text)
        self.assertEqual(rc, 0, out)
        self.assertIn("被否候选 1", out)

    def test_common_title_alone_is_not_plagiarism(self):
        for title in ("钥匙", "结婚证", "健身卡", "第一次约会"):
            with self.subTest(title=title):
                rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand(title))
                self.assertEqual(rc, 0, out)
                self.assertNotIn("C05", out)

    def test_example_title_with_own_content_only_warns(self):
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + cand("袖带"))
        self.assertEqual(rc, 0, out)
        self.assertIn("C05", out)
        self.assertNotIn("ERROR C05", out)

    def test_example_title_and_content_copied_is_error(self):
        block = ("候选 〈袖带〉\n一句话：父亲来医院复查，排到女儿的诊室；她给他绑袖带时发现袖带位置他自己已经量对了。\n"
                 "人物：父亲选择像陌生病人一样配合。\n观众：最初尴尬 → 看见她手停后改变判断。\n"
                 "主控画面：诊室里，她的手停在他手臂的袖带上，两人都看着血压计。\n独特之处：温度藏在流程里。\n")
        rc, out = run("# Concept\n" + JUDGEMENT + "## 候选\n" + block)
        self.assertEqual(rc, 1)
        self.assertIn("ERROR C05", out)

    def test_empty_required_value_warns_c09(self):
        text = "# Concept\n" + JUDGEMENT + "## 候选\n" + cand("杯子").replace("独特之处：她还的不是钥匙，是门卡。", "独特之处：")
        rc, out = run(text)
        self.assertEqual(rc, 0)
        self.assertIn("C09 候选〈杯子〉缺 独特之处", out)

if __name__ == '__main__':
    unittest.main()

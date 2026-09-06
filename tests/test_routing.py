"""2.5.5 P0: routing invariance under paraphrase, and no leftover creative gates in the creative-layer docs."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import route_check  # noqa: E402

CREATIVE_DOCS = [
    'SKILL.md', 'references/stage-1-intake.md', 'references/stage-3a-concept.md', 'references/stage-3b-story.md',
    'references/stage-3c-script.md', 'references/concept-generation.md', 'references/character-scene-development.md',
    'references/creative-loop.md', 'references/causal-chain.md', 'references/anti-mechanical.md',
    'references/research-to-craft.md', 'references/screenwriting-traditions.md', 'references/scene-parameters.md',
    'templates/concept.md', 'templates/story.md', 'templates/script-scene.md',
]
# Phrases that turned methods into gates in ≤ 2.5.0. Any reappearance is a regression.
RETIRED_GATES = [
    '没有概念卡，不进 S3b', '必停', '写不出就换', '写不出差异的候选换掉', '字段固定', '出现即需要一行理由',
    '没有物件、没有走位', '阻力必须让人物付出', '答不出的回到候选', '5–10 个答案', '通常 2–4 个',
    '可拍——物件 + 动作 + 光', '差异必须在', '方案必须能指回项目主控句', '固定三个',
]


def route(text, material=None):
    r = route_check.classify(text, material)
    return (r['intent'], r['entry'], r['autonomy'], r['save'])


class RoutingInvarianceTests(unittest.TestCase):
    def assert_same(self, a, b, material=None):
        self.assertEqual(route(a, material), route(b, material), (a, b))

    def test_paraphrases_do_not_change_scope_or_saving(self):
        self.assert_same('帮我想几个关于搬家的方向', '搬家这个题，构思几个版本')
        self.assert_same('这段台词太假', '这句对白太直白了，改改')
        self.assert_same('写一个关于搬家的短片', '给我写一部讲搬家的短片')
        self.assert_same('这是剧本，帮我拆分镜', '剧本在这，分镜拆一下', material='script')
        self.assert_same('先出一个 prompt 看看台词', '直接出 prompt 看看效果')
        self.assert_same('原文直出 Crying', '把憋哭的原文给我')

    def test_dialogue_in_text_does_not_mean_script_is_done(self):
        r = route_check.classify('我写了两句对白，帮我发展成故事', 'fragment')
        self.assertEqual(r['intent'], '发展已有想法')
        self.assertIn('S3b', r['entry'])
        r2 = route_check.classify('这是剧本，帮我拆分镜', 'fragment')
        self.assertNotIn('S4', r2['entry'])

    def test_mature_story_enters_script_without_restopping_story(self):
        r = route_check.classify('故事定了，写成剧本', 'story')
        self.assertEqual(r['intent'], '写完整剧本')
        self.assertIn('S3c', r['entry'])
        self.assertNotIn('S3a', r['entry'])

    def test_peek_changes_autonomy_and_saving_but_never_aesthetic(self):
        base = route_check.classify('写一个关于搬家的短片')
        peek = route_check.classify('写一个关于搬家的短片，看看效果')
        self.assertEqual(base['intent'], peek['intent'])
        self.assertEqual(base['autonomy'], '停靠式')
        self.assertEqual(peek['autonomy'], '自主到指定阶段')
        self.assertEqual(peek['save'], '不落盘（对话内交付）')
        self.assertEqual(base['aesthetic'], peek['aesthetic'])

    def test_save_word_only_changes_saving(self):
        a = route_check.classify('帮我想几个关于搬家的方向')
        b = route_check.classify('帮我想几个关于搬家的方向，存一下候选')
        self.assertEqual((a['intent'], a['entry'], a['autonomy']), (b['intent'], b['entry'], b['autonomy']))
        self.assertTrue(b['save'].startswith('显式保存'))

    def test_unknown_request_asks_instead_of_guessing(self):
        self.assertEqual(route_check.classify('嗯')['intent'], '需确认')


class CreativeGateRegressionTests(unittest.TestCase):
    def test_no_retired_gate_phrases_in_creative_docs(self):
        for name in CREATIVE_DOCS:
            text = (ROOT / name).read_text(encoding='utf-8')
            for phrase in RETIRED_GATES:
                with self.subTest(doc=name, phrase=phrase):
                    self.assertNotIn(phrase, text)

    def test_skill_routing_names_the_five_intents_and_three_axes(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        for word in ('想故事', '发展已有想法', '写完整剧本', '局部改写', '进入生产', '材料成熟度', '自主执行', '用户确认', '文件保存'):
            self.assertIn(word, text)
        self.assertIn('有台词不等于剧本已完成', text.replace('文本里有台词不等于剧本已完成', '有台词不等于剧本已完成'))

    def test_intake_entry_is_by_maturity(self):
        text = (ROOT / 'references/stage-1-intake.md').read_text(encoding='utf-8')
        self.assertIn('按材料成熟度，不按表面形式', text)
        self.assertIn('台词不等于剧本已完成', text)

    def test_skill_links_resolve(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        for ref in set(re.findall(r'`((?:references|templates|scripts|examples)/[^`]+)`', text)):
            self.assertTrue((ROOT / ref).exists(), ref)


if __name__ == '__main__':
    unittest.main()

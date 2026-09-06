"""2.5.5 engineering acceptance: protected production/performance core unchanged since v2.5.0;
creative-layer files carry the new methods; routing self-check exists. No creative quality is graded here."""
import hashlib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Files that 2.5.5 promised not to touch (emotion library, intensity/restraint, performance fidelity,
# prompt compiler, production constraints, storyboard tooling). Hashes taken at v2.5.0 / 47067bd.
PROTECTED = {
    'assets/emotion-library.json': 'ef22ac8bfec33567344e13a927d47f7b577c3c6f07b110cc5a2e316523599977',
    'references/emotion-performance.md': 'a150f6047b6a484a6ab858a93773d9c28fab022ac274bcc358dd20684468d8d0',
    'references/emotion-index.json': '3fe3f2946669c2e649f79bdc82917dfa8bc528220d992f7166350623ee03e3d5',
    'references/stage-4-performance.md': '22d8c416766030bf6433ac3e08e757cdcedab7e0ed4ce4d818e3794973eea2a9',
    'references/stage-5b-reference-assets.md': '167fee36b688f32f5a8796be58098e043eb3ae0d27af3624ce7ed75ff7adc2d0',
    'references/stage-6-prompt-compiler.md': '18f28369d44ef06adbc756d64000b4eebe051386925cb14894ff786b2afda424',
    'references/stage-7-qa-continuity.md': 'c5f9a95a9af2b9a21bdf33635be9a273f34e5c23eeaed60d55abea28656a470c',
    'references/production-workflow.md': '68d30274c6a375371cd9dfb6837958fea3f409da45d431df0debe99fd69f5961',
    'references/performance-record.md': '1c970fd3dc7db2d45706361e8f283ae2f2d6d70c00e55f3f369e0f1bb8bcd4eb',
    'references/seedance-2.5-capabilities.md': 'cee3b580a447f686b4fc62723438c39dbd8f8233f01c8550e3b1086878bf7a7b',
    'references/camera-vocabulary.md': 'de1cd86da8fbf17c778038a565d57a425218636c8a148abfec476aead1007bd8',
    'references/externalization-lexicon.md': '7a79bf1bf42805f185441a7767c95dd900dc390503674b286807df68eb709ce6',
    'references/genre-packs.md': '59e0d3858456582ec779a438ad96380afe3158e46c1fdff37f085cbdd7a9d742',
    'references/director-lenses.md': '1ed769d7a721c27b8af7371f759d69a5a2d27a4e965823ea5935987687bcd6bf',
    'templates/prompt-templates.md': '4f37de4d413ca36d042473b855b8ad4396802a1ea951787f9ddd5f680defa512',
    'templates/performance-record.json': 'aced33a04bd1e72fe33e6e78ca64e4a938402654cdb3028ee4139d75ae64d159',
    'templates/production-record.json': '7adc7226bf0b7648ecc2f2320db3edefe317297bf7486645271d9f87d8bb56fd',
    'templates/shot-card.md': '6b8b783d20af949afa15c3543192c0458a4a32811b0ca8031066cc86941671b0',
    'templates/reference-asset-brief.md': 'adc6b7c7c52c169d31ee7ba83111293496e7133572a7bedc08bf4a08d251df0b',
    'templates/asset-registry.md': '996818cda8aa55796820ae96c808c56459198f8f465b4e4924196d7ed8cc2943',
    'scripts/validate_prompt.py': '8f33f8373ebc092445540814cb669b6c3716f41c4a10b5002eba94a0f8244bd6',
    'scripts/prompt_structure.py': 'd9f73020e41eec19edee56b7ad8a45f9b973c28db9c93e451274ab6d1a0b60bf',
    'scripts/production_contract.py': '963653540c39519d99a731749736e96b39bed17005305af1082c857af5426bfa',
    'scripts/production_preflight.py': '80379ec01b3f952ee82cc1611e38b555ad41838bd0bb6f0ac52ddb5453605702',
    'scripts/emotion_library.py': '11b1257528d00edbf66a9637a9508966f26d23d1db97917b609127858ac0cc6d',
    'scripts/performance_checks.py': '5a54ee7c0cb77b67466ee6f7102ded648220cf8b922fea7da186f68ccd869ae0',
    'scripts/prose_hints.py': '22a5425c7cba5e01a9ea1608045192eb0c63cd5a9d48894ea43c9f8c9b035f5f',
}


def sha(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


class ProtectedZoneTests(unittest.TestCase):
    def test_production_and_performance_core_unchanged_since_2_5_0(self):
        # A deliberate change to any of these belongs to a production/performance release, with its own review;
        # it must not ride along with a story-development release.
        for name, expected in PROTECTED.items():
            with self.subTest(file=name):
                self.assertEqual(sha(name), expected)


class StoryWorkflowPresenceTests(unittest.TestCase):
    def read(self, name):
        return (ROOT / name).read_text(encoding='utf-8')

    def test_concept_protocol_has_comparison_dimensions_and_key_scene_first(self):
        text = self.read('references/concept-generation.md')
        for phrase in ('人物怎样理解处境', '人物之间有什么具体关系', '什么事发生，带来什么后果', '观众为什么愿意继续看', '关键场景先行', '熟悉题材可以写出好故事'):
            self.assertIn(phrase, text)

    def test_story_stage_is_prose_first_with_four_judgments(self):
        text = self.read('references/stage-3b-story.md')
        for phrase in ('故事正文优先', '短片可以围绕一个完整时刻成立', '不能冒充完整', '事情为什么发生', '前面的事怎样影响后面的可能性', '观众何时知道什么', '结尾为何在这个故事中成立', '不强制倒叙、三幕或最后反转'):
            self.assertIn(phrase, text)
        self.assertIn('## 故事正文', self.read('templates/story.md'))

    def test_dialogue_revision_targets_actual_cause(self):
        text = self.read('references/character-scene-development.md')
        for phrase in ('场景只为宣布主题而存在', '人物知道不该知道的信息', '每句话都精准接住上一句', '两人声音可以互换', '结尾总用金句总结', '用户锁定内容不能擅改', '现实事实需要可靠依据', '未锁定的虚构可以创造'):
            self.assertIn(phrase, text)

    def test_revision_ledger_and_stop_condition(self):
        text = self.read('references/creative-loop.md')
        for phrase in ('修订账本', '已确认内容', '暂定假设', '本轮问题', '需要保留的优点', '受影响部分', '达到目标就停'):
            self.assertIn(phrase, text)
        self.assertIn('修订账本', self.read('templates/script-scene.md'))

    def test_route_check_is_wired_into_skill(self):
        self.assertTrue((ROOT / 'scripts/route_check.py').exists())
        self.assertIn('scripts/route_check.py', self.read('SKILL.md'))


if __name__ == '__main__':
    unittest.main()

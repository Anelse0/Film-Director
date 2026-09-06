"""2.5.0 surface-cue regressions. No automatic naturalness score."""
import unittest
from test_production import prompt, run
from prose_hints import has_mouth_direction, has_subtitle_policy, has_sound_policy


class DirectionHintTests(unittest.TestCase):
    def test_affirmed_mouth_variants(self):
        for text in ('B闭口。', '听者闭嘴看着A。', 'B抿嘴。', 'B嘴唇紧闭。',
                     'B嘴微张但不出声。', 'B的嘴保持闭合。',
                     'The listener mouth remains closed.', 'B lips are pressed.'):
            with self.subTest(text=text):
                self.assertTrue(has_mouth_direction(text))

    def test_negation_is_not_an_affirmed_state(self):
        for text in ('B没有闭嘴。', 'B不再抿嘴。', 'B并未闭口。', '不要让B闭嘴。',
                     'B不是不出声。', 'B无需闭口。',
                     'B does not keep lips closed.', 'B never keeps mouth closed.'):
            with self.subTest(text=text):
                self.assertFalse(has_mouth_direction(text))

    def test_spoken_cue_is_not_direction(self):
        for text in ('台词（A）：“闭嘴！”', 'A says: "mouth stays closed"'):
            self.assertFalse(has_mouth_direction(text))

    def test_clause_boundary_allows_real_state_after_negation(self):
        self.assertTrue(has_mouth_direction('B没有笑，嘴保持闭合。'))
        self.assertFalse(has_mouth_direction('B没有笑，也没有闭嘴。'))

    def test_sound_and_subtitle_variants(self):
        for text in ('无音乐，不添加字幕。', '无配乐；不生成字幕。',
                     '只有环境音，不额外加入任何字幕。', 'No music; no captions.'):
            with self.subTest(text=text):
                self.assertTrue(has_sound_policy(text))
                self.assertTrue(has_subtitle_policy(text))

    def test_quoted_policies_do_not_count(self):
        self.assertFalse(has_subtitle_policy('A：“不要字幕。”'))
        self.assertFalse(has_sound_policy('A: "no music"'))
        self.assertFalse(has_subtitle_policy('并非无字幕。'))


class DialogueRegressionTests(unittest.TestCase):
    def test_mouth_hint_is_integrated_and_timing_still_warns(self):
        line = '这件事情我们今天必须说清楚到底要怎么办。'
        result = run(prompt(f'两人同框。B闭口。台词（A，0-1s，中文）："{line}"'))
        self.assertFalse(any('未写非说话者' in w for w in result['warnings']))
        self.assertTrue(any(w.startswith('W05') for w in result['warnings']))

    def test_negated_or_spoken_mouth_cue_still_warns(self):
        for state, line in [('B没有闭口。', '等等。'), ('', '闭嘴！')]:
            result = run(prompt(f'两人同框。{state}台词（A，0-3s，中文）："{line}"'))
            self.assertTrue(any('未写非说话者' in w for w in result['warnings']))

    def test_punctuation_does_not_change_estimate_or_infer_intentions(self):
        a = run(prompt('台词（A，0-10s，中文）："今天我来。明天你去。以后再说。"'))
        b = run(prompt('台词（A，0-10s，中文）："今天我来，明天你去，以后再说。"'))
        self.assertEqual(a['dialogue'][0]['estimate'], b['dialogue'][0]['estimate'])
        self.assertFalse(any(w.startswith('W19') for w in a['warnings']+b['warnings']))
        self.assertEqual(a['checks']['performance'], 'needs_review')

    def test_vague_prose_does_not_get_quality_pass(self):
        result = run(prompt('人物很悲伤，手动了。'))
        self.assertEqual(result['checks']['format'], 'passed')
        self.assertEqual(result['checks']['performance'], 'needs_review')
        self.assertEqual(result['checks']['render'], 'not_tested')

    def test_sound_subtitle_hints_integrate_without_global_marker_warning(self):
        text = prompt('A抬眼。').replace('无bgm，只有环境音；不要字幕。', '无音乐，不添加字幕。')
        self.assertFalse(any(w.startswith('W07') for w in run(text)['warnings']))

    def test_overlap_not_deleted_and_not_counted_as_extra_timeline(self):
        result = run(prompt('两人同框。台词（A，0-4s，中文）："还没说完呢。"\n'
                            '台词（B，3-6s，中文）："那你接着说。"'))
        self.assertEqual(result['errors'], [])
        self.assertEqual([(r['start'], r['end']) for r in result['dialogue']], [(0,4),(3,6)])
        self.assertTrue(any(w.startswith('W11') for w in result['warnings']))


if __name__ == '__main__':
    unittest.main()

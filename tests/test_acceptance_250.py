"""Frozen content/fidelity guards, not semantic grading of the authored cases."""
import hashlib
import re
import unittest
from test_production import ROOT
from validate_prompt import validate
from production_preflight import preflight


class Acceptance250Tests(unittest.TestCase):
    def test_frozen_30s_assets_unchanged(self):
        expected = {
            'examples/example-04-parameters-fight.prompt.md': 'eda19b683cdbb8617a007a4d60cf381f217b6eceef895b7716e45098eb360fdf',
            'examples/example-04-parameters-fight.md': '556ceddb0f5c5d8eaadf548bcd902099f8a6c0df72d57944e511d30af7dcd0db',
            'examples/production/30s-fight-t2v.prompt.md': 'b328e46b8422e98b921ce2b3a4fe4dbae90c58682cf596f0d107d27d04d314ed',
        }
        # Intentionally exact fixtures, not a prohibition on changing future
        # creative outputs. Deliberate fixture revisions require reviewed evidence.
        for name, sha in expected.items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(), sha)

    def test_demo_matches_precompilation_c_not_just_keywords(self):
        folder = ROOT/'tests/acceptance-2.5.0'
        upstream = (folder/'demo.upstream.md').read_text()
        c = re.search(r'```text\n(.*?)\n```', upstream, re.S).group(1)
        d = (folder/'demo.prompt.md').read_text().split('\n| 项 | 值 |')[0].strip()
        self.assertEqual(c, d)

    def test_demo_strict_preflight_and_pending_artistic_evidence(self):
        folder = ROOT/'tests/acceptance-2.5.0'
        result = validate(folder/'demo.prompt.md')
        self.assertEqual(result['errors'], [])
        self.assertEqual([r['text'] for r in result['dialogue']], [
            '你把我的名字划了？','主持人问谁上，我说我上。',
            '我们排的那一段呢？','我怕你到时候说不去。','我说的是周五。今天我来了。'])
        self.assertEqual([(r['start'],r['end']) for r in result['dialogue']],
                         [(1,4),(4,9),(10,14),(15,20),(23,28)])
        check = preflight(folder/'demo.production.json', folder/'demo.prompt.md', result)
        self.assertEqual(check['status'], 'passed', check)
        self.assertEqual(check['human_reviews'], 'recorded_not_machine_verified')
        self.assertEqual(check['render'], 'not_tested')
        self.assertEqual(result['checks']['performance'], 'needs_review')


if __name__ == '__main__':
    unittest.main()

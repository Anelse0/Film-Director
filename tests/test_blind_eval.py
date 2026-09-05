"""blind_eval.py contracts: versions hidden until every pair is judged; evidence required; tally maps back to labels."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import blind_eval  # noqa: E402


def run(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        blind_eval.main(argv)
    return buf.getvalue()


class BlindEvalTests(unittest.TestCase):
    def test_pack_hides_version_and_reveal_waits_for_all_verdicts(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp); ev = t / 'eval'
            (t / 'old.md').write_text('候选 〈甲〉\n一句话：旧版。', encoding='utf-8')
            (t / 'new.md').write_text('候选 〈乙〉\n一句话：新版。', encoding='utf-8')
            run(['pack', str(ev), '--pair', '01', '--topic', '爱情/悲/30s', '--a', str(t / 'old.md'), '--b', str(t / 'new.md'), '--a-label', '2.3.1', '--b-label', '2.4.0'])
            names = sorted(p.name for p in ev.glob('pair-01-*.md'))
            self.assertEqual(names, ['pair-01-X.md', 'pair-01-Y.md'])
            for n in names:
                self.assertNotIn('2.3.1', (ev / n).read_text(encoding='utf-8'))
            key = json.loads((ev / 'key.json').read_text(encoding='utf-8'))['01']
            self.assertEqual({key['X'], key['Y']}, {'2.3.1', '2.4.0'})
            with self.assertRaises(SystemExit):
                run(['reveal', str(ev)])
            with self.assertRaises(SystemExit):
                run(['record', str(ev), '--pair', '01', '--verdict', 'X', '--evidence', '好'])
            run(['record', str(ev), '--pair', '01', '--verdict', 'X', '--evidence', '候选〈乙〉的人物选择有依据，〈甲〉只有地点'])
            out = run(['reveal', str(ev)])
            self.assertIn(f"| 01 | 爱情/悲/30s | {key['X']} | {key['Y']} | X | {key['X']} |", out)
            self.assertIn(f"总计：{key['X']} 1", out)

    def test_tie_and_both_bad_are_counted_as_such(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp); ev = t / 'eval'
            (t / 'a.md').write_text('A', encoding='utf-8'); (t / 'b.md').write_text('B', encoding='utf-8')
            run(['pack', str(ev), '--pair', '01', '--topic', 't', '--a', str(t / 'a.md'), '--b', str(t / 'b.md')])
            run(['pack', str(ev), '--pair', '02', '--topic', 't', '--a', str(t / 'a.md'), '--b', str(t / 'b.md')])
            run(['record', str(ev), '--pair', '01', '--verdict', 'tie', '--evidence', '两版候选差异都只在地点'])
            run(['record', str(ev), '--pair', '02', '--verdict', 'both_bad', '--evidence', '两版人物都只有身份标签'])
            out = run(['reveal', str(ev)])
            self.assertIn('both_bad 1', out); self.assertIn('tie 1', out)

    def test_identical_outputs_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            t = Path(temp)
            (t / 'a.md').write_text('same', encoding='utf-8'); (t / 'b.md').write_text('same', encoding='utf-8')
            with self.assertRaises(SystemExit):
                run(['pack', str(t / 'eval'), '--pair', '01', '--topic', 't', '--a', str(t / 'a.md'), '--b', str(t / 'b.md')])


if __name__ == '__main__':
    unittest.main()

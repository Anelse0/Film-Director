"""Behavioral contract regressions; not a fixed emotion writing recipe."""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from emotion_library import load_library, select
from performance_checks import check_raw, check_record, split_beats, timing_errors, repeated_blocks
from validate_prompt import validate, declared_duration, speech_parameters


def sample_record():
    return {"version": 1, "mode": "adapt", "duration": 10, "beats": [
        {"id": "onset", "actor": "A", "start": 0, "end": 4,
         "text": "A 内眉角抬起并向中间聚拢，嘴角下拉。", "entry_ids": [19],
         "keep": [{"text": "内眉角抬起并向中间聚拢", "reason": "悲伤的部位变化"}],
         "changes": ["译写并选择起始部位表现"]},
        {"id": "hold", "actor": "A", "start": 4, "end": 10,
         "text": "A 下巴颤了一次，低头时视线跟着落下；用力吞咽，嘴角仍向下拉着。", "entry_ids": [19],
         "keep": [{"text": "用力吞咽，嘴角仍向下拉着", "reason": "吞咽未解除表情"}],
         "changes": ["译写；省去慢眨眼，为持续末态留时"]}
    ]}


def fragment(record):
    return f"【表演条件】{record['duration']}秒，固定近景，无对白。\n【表演时间线】\n" + "\n".join(
        f"节拍 {b['id']}（{b['start']}-{b['end']}s）：{b['text']}" for b in record["beats"])


def production(body, duration=10):
    return (f"【素材绑定】无参考素材。\n【总述】{duration}秒16:9。\n"
            "【起始状态】A 在画面中央，面朝前方。\n【分镜时间线】\n"
            f"镜头1（0-{duration}s）：【近景，平视，固定】\n{body}\n"
            "【贯穿要求】无bgm，只有环境音；不要字幕。\n")


class LibraryTests(unittest.TestCase):
    def test_archive_integrity(self):
        data = (ROOT / "assets/emotion-library.json").read_bytes()
        expected = (ROOT / "tests/emotion-library.sha256").read_text().strip()
        self.assertEqual(hashlib.sha256(data).hexdigest(), expected)
        self.assertEqual(len(load_library()), 25)  # archival fixture, not runtime limit

    def test_every_original_roundtrips_and_rejects_changes(self):
        for eid, entry in load_library().items():
            with self.subTest(entry=eid):
                self.assertEqual(check_raw(entry["prompt"], eid), ([], "matched"))
                self.assertEqual(check_raw(entry["prompt"] + "\n", eid), ([], "matched"))
                self.assertTrue(check_raw(entry["prompt"] + " She relaxes.", eid)[0])
                self.assertTrue(check_raw(" " + entry["prompt"], eid)[0])

    def test_internal_data_has_no_origin_metadata(self):
        for path in (ROOT / "assets/emotion-library.json", ROOT / "references/emotion-index.json"):
            raw = path.read_text()
            self.assertNotIn("https://", raw)
            for entry in json.loads(raw):
                self.assertFalse(set(entry) & {"source", "url", "source_url", "provenance", "retrieved_at"})

    def test_index_covers_library_without_becoming_a_limit(self):
        entries = load_library()
        index = json.loads((ROOT / "references/emotion-index.json").read_text())
        self.assertEqual(len(index), len(entries))
        self.assertEqual({r["id"] for r in index}, set(entries))
        extended = entries | {900: entries[1] | {"id": 900, "name": "Custom"}}
        self.assertEqual(select(extended, {}, ids=[900])[0]["name"], "Custom")

    def test_lookup_chinese_and_unknown(self):
        entries = load_library()
        index = {r["id"]: r for r in json.loads((ROOT / "references/emotion-index.json").read_text())}
        self.assertIn(21, [e["id"] for e in select(entries, index, query="害羞")])
        self.assertEqual(select(entries, index, query="nonexistent-emotion"), [])
        with self.assertRaises(ValueError):
            select(entries, index, ids=[999])


class PerformanceTests(unittest.TestCase):
    def run_validation(self, text, **kwargs):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "test.prompt.md"
            path.write_text(text, encoding="utf-8")
            return validate(path, **kwargs)

    def test_acceptance_demos_and_production_share_upstream(self):
        folder = ROOT / "examples/performance"
        records = sorted(folder.glob("*.performance.json"))
        self.assertTrue(records)
        for path in records:
            with self.subTest(demo=path.name):
                record = json.loads(path.read_text())
                prompt = path.with_name(path.name.replace(".performance.json", ".prompt.md"))
                result = validate(prompt, artifact="performance", record=record)
                self.assertEqual(result["errors"], [])
                self.assertEqual(result["warnings"], [])
                self.assertEqual(result["checks"]["fidelity"], "matched")
        result = validate(folder / "06-production-rage-hurt.prompt.md",
                          record=json.loads((folder / "05-rage-to-hurt.performance.json").read_text()))
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["checks"]["fidelity"], "matched")

    def test_fragment_needs_no_assets_or_story(self):
        r = sample_record()
        result = self.run_validation(fragment(r), artifact="performance", record=r)
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["checks"], {"format": "passed", "fidelity": "matched",
                                           "performance": "needs_review", "render": "not_tested"})

    def test_unrecorded_is_not_fidelity_pass(self):
        result = self.run_validation(fragment(sample_record()), artifact="performance")
        self.assertEqual(result["checks"]["fidelity"], "not_checked")

    def test_vague_body_never_gets_quality_pass(self):
        result = self.run_validation(production("人物很悲伤，手动了。"))
        self.assertEqual(result["checks"]["format"], "passed")
        self.assertEqual(result["checks"]["performance"], "needs_review")

    def test_same_body_part_can_progress(self):
        text = "0–3秒：A 嘴角上扬。\n3–7秒：A 嘴角被抿紧的双唇压住。\n7–10秒：A 嘴角展开，肩膀下沉。"
        result = self.run_validation(text, artifact="performance", duration_override=10)
        self.assertFalse(any(w.startswith(("W14", "W18")) for w in result["warnings"]))
        self.assertEqual(result["errors"], [])

    def test_identical_whole_blocks_get_review_not_rewrite(self):
        units = split_beats("0–4秒：A 目光留在地面。\n4–10秒：A 目光留在地面。")
        self.assertTrue(repeated_blocks(units)[0].startswith("W14"))

    def test_nested_beats_are_one_shot(self):
        r = sample_record()
        result = self.run_validation(production(fragment(r).split("【表演时间线】\n")[1]), record=r)
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("镜头数 1" in i for i in result["info"]))

    def test_beat_cannot_cross_cut(self):
        units = split_beats("0–7秒：A 抬眼。\n7–10秒：A 目光定住。")
        self.assertTrue(any(e.startswith("E20") for e in timing_errors(units, 10, [(1, 0, 5, ""), (2, 5, 10, "")])))

    def test_production_can_have_nonacting_intervals(self):
        r = sample_record()
        r["beats"] = [r["beats"][1]]
        text = ("【素材绑定】无参考素材。\n【总述】10秒。\n【起始状态】桌面与人物。\n"
                "【分镜时间线】\n镜头1（0-4s）：【特写，固定】桌面一封合上的信。\n"
                "镜头2（4-10s）：【近景，固定】\n"
                f"节拍 hold（4-10s）：{r['beats'][0]['text']}\n"
                "【贯穿要求】无bgm，只有环境音；不要字幕。")
        self.assertEqual(self.run_validation(text, record=r)["errors"], [])

    def test_asset_range_normalizes_kind(self):
        text = production("图2的人物抬眼。").replace("无参考素材。", "图1–图3 = 同一角色多视图。")
        self.assertFalse(any(e.startswith("E05") for e in self.run_validation(text)["errors"]))

    def test_raw_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "original.txt"
            path.write_text(load_library()[6]["prompt"], encoding="utf-8")
            p = subprocess.run([sys.executable, str(ROOT / "scripts/validate_prompt.py"), str(path),
                                "--artifact", "raw", "--entry-id", "6", "--json"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(json.loads(p.stdout)["results"][0]["checks"]["fidelity"], "matched")

    def test_valid_raw_and_blend_records(self):
        original = load_library()[6]["prompt"]
        r = sample_record()
        r["mode"] = "raw"
        r["beats"] = [r["beats"][0] | {"end": 10, "text": original, "entry_ids": [6],
                      "keep": [{"text": original, "reason": "完整原文"}], "changes": []}]
        self.assertEqual(check_record(r, split_beats(fragment(r)), 10), ([], "matched"))
        r = sample_record()
        r["mode"] = "blend"
        r["beats"][1]["entry_ids"] = [6, 19]
        self.assertEqual(check_record(r, split_beats(fragment(r)), 10), ([], "matched"))

    def test_metadata_cannot_supply_missing_beat_text(self):
        r = sample_record()
        text = fragment(r).replace(r["beats"][1]["text"], "A 看着前方。")
        text += f"\n| 项 | 值 |\n| 备注 | {r['beats'][1]['text']} |"
        self.assertEqual(self.run_validation(text, artifact="performance", record=r)["checks"]["fidelity"], "failed")

    def test_time_gaps_overlaps_and_shortfalls(self):
        cases = ["0–3秒：A 抬眼。\n4–10秒：A 低头。", "0–6秒：A 抬眼。\n5–10秒：A 低头。",
                 "1–10秒：A 抬眼。", "0–9秒：A 抬眼。", "0–0秒：A 抬眼。", "0–2.5秒：A 抬眼。\n2.5–10秒：A 低头。"]
        for text in cases:
            with self.subTest(text=text):
                self.assertTrue(self.run_validation(text, artifact="performance", duration_override=10)["errors"])

    def test_duration_is_explicit_not_first_incidental_seconds(self):
        self.assertEqual(declared_duration("视频1 = 5秒参考。\n【总述】10秒。", None), 10)
        self.assertIsNone(declared_duration("0–4秒：A 抬眼。", None))
        self.assertEqual(declared_duration("【总述】10秒。\n| duration | 12 |", None), 12)

    def test_missing_duration_and_empty_body_fail(self):
        self.assertTrue(self.run_validation("0–10秒：A 抬眼。", artifact="performance")["errors"])
        self.assertTrue(timing_errors(split_beats("0–10秒："), 10))

    def test_high_suppressed_does_not_change_speech_estimate(self):
        self.assertEqual(speech_parameters("| 参数 | 强度高 · 内收 · 已知 · 对等 · 温 · 稀 |"), (4.0, 2.5, 2/3))
        self.assertEqual(speech_parameters("| 参数 | 强度高 · 外放 · 已知 · 对等 · 灼 · 密 |"), (4.0, 2.5, .75))
        self.assertEqual(speech_parameters("| 参数 | 高 · 密 |\n| 台词密度 | 无 |"), (4.0, 2.5, 2/3))
        self.assertEqual(speech_parameters("| 语速字每秒 | 3 |\n| 台词占比上限 | 0.5 |"), (3, 2.5, .5))

    def test_bad_speech_settings_rejected(self):
        for text in ("| 语速字每秒 | 0 |", "| 语速词每秒 | nan |", "| 台词占比上限 | 2 |"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                speech_parameters(text)

    def test_undeclared_asset_even_with_no_reference_declaration(self):
        result = self.run_validation(production("图1的人物抬眼。"))
        self.assertTrue(any(e.startswith("E05") for e in result["errors"]))

    def test_behavioral_negation_not_object_exclusion(self):
        result = self.run_validation("0–10秒：The stare holds without blinking.", artifact="performance", duration_override=10)
        self.assertFalse(any(w.startswith("W01") for w in result["warnings"]))

    def test_dialogue_checked_in_fragment_and_smallest_window(self):
        text = '0–1秒：台词 (A): "这是一段显然不可能在一秒钟内完整说完的台词。"\n1–10秒：A 看着前方。'
        for prompt, artifact in ((text, "performance"), (production(text), "production")):
            with self.subTest(artifact=artifact):
                result = self.run_validation(prompt, artifact=artifact, duration_override=10)
                self.assertTrue(any(w.startswith("W05") for w in result["warnings"]))

    def test_lost_added_reordered_text_fails(self):
        r = sample_record()
        for changed in (fragment(r).replace("内眉角抬起并向中间聚拢，", ""),
                        fragment(r).replace("嘴角下拉。", "嘴角下拉。她恢复平静。"),
                        fragment(r).replace("低头时视线跟着落下；用力吞咽", "用力吞咽；低头时视线跟着落下")):
            with self.subTest(changed=changed):
                result = self.run_validation(changed, artifact="performance", record=r)
                self.assertEqual(result["checks"]["fidelity"], "failed")
                self.assertTrue(any(e.startswith("F03") for e in result["errors"]))

    def test_missing_keep_in_upstream_fails(self):
        r = sample_record()
        r["beats"][0]["keep"][0]["text"] = "不在正文的关键细节"
        self.assertTrue(any(e.startswith("F05") for e in check_record(r, split_beats(fragment(r)), 10)[0]))

    def test_unknown_id_wrong_mode_and_unrecorded_changes_fail(self):
        for transform in (lambda r: r["beats"][0].update(entry_ids=[999]),
                          lambda r: r.update(mode="raw"), lambda r: r.update(mode="blend"),
                          lambda r: r["beats"][0].update(changes=[])):
            r = sample_record()
            transform(r)
            self.assertTrue(check_record(r, split_beats(fragment(r)), 10)[0])

    def test_free_does_not_claim_library_fidelity(self):
        r = sample_record()
        r["mode"] = "free"
        for b in r["beats"]:
            b["entry_ids"] = []
        self.assertEqual(check_record(r, split_beats(fragment(r)), 10), ([], "upstream_matched"))

    def test_relation_reversal_cannot_be_certified_by_keywords(self):
        # Even a self-consistent but wrong translation cannot acquire semantic PASS.
        r = sample_record()
        r["beats"] = [r["beats"][0] | {"end": 10, "entry_ids": [23],
                          "text": "A 一边呼气一边露出笑容。",
                          "keep": [{"text": "呼气", "reason": "保留呼气"}],
                          "changes": ["中文译写"]}]
        result = self.run_validation(fragment(r), artifact="performance", record=r)
        self.assertEqual(result["checks"]["fidelity"], "matched")
        self.assertEqual(result["checks"]["performance"], "needs_review")

    def test_record_bad_shapes(self):
        for record in ({}, [], {"version": 1, "mode": "adapt", "beats": "bad"},
                       sample_record() | {"beats": [None]}, sample_record() | {"duration": float("nan")}):
            with self.subTest(record=record):
                self.assertTrue(check_record(record, [], 10)[0])

    def test_render_status_cannot_be_self_reported(self):
        r = sample_record() | {"render": "passed", "performance": "passed"}
        result = self.run_validation(fragment(r), artifact="performance", record=r)
        self.assertEqual(result["checks"]["render"], "not_tested")
        self.assertEqual(result["checks"]["performance"], "needs_review")

    def test_cli_bad_flags_do_not_traceback(self):
        for args in (["--duration"], ["missing.md"], ["x", "--artifact", "raw"], ["x", "--duration", "nan"]):
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/validate_prompt.py"), *args], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn("Traceback", proc.stderr)

    def test_independent_batch_skips_sequence_style_warning(self):
        path = ROOT / "examples/example-02-lens-B-haneke.prompt.md"
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/validate_prompt.py"), str(path), str(path),
                               "--batch", "independent", "--json"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["cross"], [])


if __name__ == "__main__":
    unittest.main()

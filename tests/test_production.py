"""2.3.1 regressions: meaningful contracts, not filenames or warning counts."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from prompt_structure import Document, dialogue_checks
from production_contract import check_parameters
from production_preflight import preflight, digest
from validate_prompt import validate


def prompt(body, duration=10):
    return (f'【素材绑定】无参考素材。\n【总述】{duration}秒16:9，室内对话。\n'
            '【起始状态】A 居中。\n【分镜时间线】\n'
            f'镜头1（0-{duration}s）：【近景，固定】\n{body}\n'
            '【贯穿要求】无bgm，只有环境音；不要字幕。')


def run(text, **kwargs):
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp)/'input.md'; path.write_text(text)
        return validate(path, **kwargs)


class TimelineTests(unittest.TestCase):
    def test_beat_external_dialogue_counted_once(self):
        line = '今天这个事情我一定要和你说清楚'*10
        speech = f'台词（A）："{line}"'
        body = speech+'\n节拍 a（0-10s）：A 嘴唇压紧。'
        result = run(prompt(body))
        self.assertEqual(sum(r['estimate'] for r in result['dialogue']), 37.5)
        self.assertTrue(any(w.startswith('W05') for w in result['warnings']))
        self.assertEqual(len(result['dialogue']), 1)

    def test_inside_outside_and_voiceover(self):
        body = '台词（A，0-2s，中文）："等等。"\n节拍 a（2-5s）：A 抬眼。台词（B，画外，2-4s，中文）："别走。"\n节拍 b（5-10s）：A 看着门。'
        result = run(prompt(body))
        self.assertEqual([r['text'] for r in result['dialogue']], ['等等。','别走。'])
        self.assertEqual([r['estimate'] for r in result['dialogue']], [.5,.5])
        self.assertEqual(result['errors'], [])

    def test_wrong_parent_not_any_matching_shot(self):
        text = prompt('节拍 a（5-10s）：A 抬眼。\n镜头2（5-10s）：【近景，固定】A 站着。').replace('镜头1（0-10s）','镜头1（0-5s）')
        self.assertTrue(any(e.startswith('E20') for e in run(text)['errors']))

    def test_speech_window_cannot_leave_beat_or_shot(self):
        text = prompt('节拍 a（0-4s）：台词（A，3-8s，中文）："等等。"\n节拍 b（4-10s）：A 站着。')
        self.assertTrue(any(e.startswith('E21') for e in run(text)['errors']))

    def test_many_lines_overload_parent(self):
        body = '\n'.join('台词（A）："我还有一点事情要跟你说。"' for _ in range(5))
        self.assertTrue(any('累计' in w for w in run(prompt(body))['warnings']))

    def test_mixed_language_and_nested_direction_quotes(self):
        result = run(prompt('台词（A，0-10s，中英混合）："等等 please wait."（"等等"重读）。'))
        self.assertEqual(len(result['dialogue']), 1)
        self.assertAlmostEqual(result['dialogue'][0]['estimate'], 2/4+2/2.5)

    def test_english_speech(self):
        result = run(prompt('Mara says (English, 0-4s): "Please stay."'))
        self.assertEqual(result['dialogue'][0]['speaker'], 'Mara')
        self.assertEqual(result['dialogue'][0]['estimate'], .8)

    def test_overlap_is_review_not_silently_deleted(self):
        result = run(prompt('台词（A，0-4s）："别走。" 台词（B，3-5s）："我没走。"'))
        self.assertEqual(len(result['dialogue']), 2)
        self.assertTrue(any(w.startswith('W11') for w in result['warnings']))

    def test_unknown_quote_is_not_zero_warning(self):
        self.assertTrue(any(w.startswith('W21') for w in run(prompt('"我们明天再说。"'))['warnings']))

    def test_conflicting_duration_declarations(self):
        self.assertTrue(any(e.startswith('E04') for e in run(prompt('A 抬眼。')+'\n| 项 | 值 |\n| duration | 12 |')['errors']))

    def test_negative_speech_window_is_not_parsed_as_positive(self):
        result = run(prompt('台词（A，-1-4s，中文）："等等。"'))
        self.assertEqual(result['dialogue'][0]['start'], -1)
        self.assertTrue(any(e.startswith('E21') for e in result['errors']))

    def test_unrecognized_speech_beside_valid_line_requires_review(self):
        result = run(prompt('台词（A，0-2s）："等等。" B（3-8s，中文）："这段也需要算时间。"'))
        self.assertTrue(any(w.startswith('W21') for w in result['warnings']))

    def test_duplicate_shot_ids_rejected(self):
        result = run(prompt('A 抬眼。\n镜头1（5-10s）：【近景，固定】A 低头。').replace('镜头1（0-10s）','镜头1（0-5s）'))
        self.assertTrue(any('编号重复' in e for e in result['errors']))

    def test_technical_camera_name_does_not_trigger_person_warning(self):
        result = run(prompt('希区柯克变焦，摄影机后退同时变焦，人物画面大小保持。'))
        self.assertFalse(any(w.startswith('W13') for w in result['warnings']))

    def test_dialogue_density_does_not_accelerate_slow_lines(self):
        text = prompt('台词（A，0-4s）："今天这个事情我一定要和你说清楚。"')+'\n| 项 | 值 |\n| 台词密度 | 密 |'
        self.assertEqual(run(text)['dialogue'][0]['estimate'], 15/4)


class ParameterTests(unittest.TestCase):
    def test_locked_tasks(self):
        for task, duration, roles in [('edit',-1,{'vid1':'reference_video'}),('extend',10,{'vid1':'reference_video'}),('first_last',10,{'img1':'first_frame'})]:
            with self.subTest(task=task):
                good = {'ratio':'adaptive','duration':duration,'output_format':'mov'}
                self.assertEqual(check_parameters(task,good,roles,True)[0], [])
                self.assertTrue(check_parameters(task,good|{'ratio':'16:9'},roles,True)[0])
        self.assertTrue(check_parameters('edit',{'ratio':'adaptive','duration':10},{'vid1':'reference_video'})[0])

    def test_role_types_and_unknown_tasks(self):
        self.assertTrue(check_parameters('r2v',{}, {'img1':'reference_video'})[0])
        self.assertTrue(check_parameters('r2v',{}, {'img1':'first_frame'})[0])
        self.assertTrue(check_parameters('new_task',{}, {},True)[0])
        self.assertTrue(check_parameters('keyframe',{}, {'aud1':'reference_audio'})[0])

    def test_mp4_is_recommendation_not_ban(self):
        errors,warnings,_ = check_parameters('edit',{'ratio':'adaptive','duration':-1,'output_format':'mp4'},{'vid1':'reference_video'},True)
        self.assertEqual(errors,[]); self.assertTrue(warnings)

    def test_invalid_locked_parameters_detected_in_old_cli(self):
        text = '编辑视频。\n【素材绑定】视频1 = 待编辑视频。\n修改视频1上衣为蓝色，其余不变。不要字幕，无bgm。\n| 项 | 值 |\n| 任务类型 | 编辑 |\n| ratio | 16:9 |\n| duration | 10 |'
        self.assertGreaterEqual(len([e for e in run(text)['errors'] if e.startswith('E22')]),2)

    def test_edit_body_cannot_declare_its_own_missing_reference(self):
        text='【素材绑定】视频1 = 原视频。\n编辑视频1，使用图2的外观，其余不变。\n| 项 | 值 |\n| 任务类型 | edit |'
        self.assertTrue(any(e.startswith('E05') for e in run(text)['errors']))

    def test_role_map_trailing_garbage_rejected(self):
        from production_contract import roles_from_fields
        with self.assertRaises(ValueError):
            roles_from_fields({'content.role':'img1→reference_image, broken'})

    def test_first_last_and_keyframe_do_not_require_redundant_opening(self):
        for task, prefix, roles in [('首尾帧','', 'img1→first_frame, img2→last_frame'),('关键帧','以图片1至图片2的顺序作为关键帧。\n','img1→reference_image, img2→reference_image')]:
            text = prefix+'【素材绑定】图1 = 首图，图2 = 尾图。\n【总述】10秒。\n【分镜时间线】\n镜头1（0-10s）：【近景，固定】由图1开始，人物抬头，结束于图2。\n【贯穿要求】不要字幕，无bgm，只有环境音。\n| 项 | 值 |\n| 任务类型 | '+task+' |\n| ratio | adaptive |\n| duration | 10 |\n| content.role | '+roles+' |'
            self.assertEqual(run(text)['errors'],[])


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.file = self.folder/'prompt.md'; self.file.write_text(prompt('A 抬眼。'))
        self.upstream = self.folder/'shots.md'; self.upstream.write_text('已确认：A 抬眼，固定近景，10秒。')
        self.record = {'version':1,'adapter':'ark-seedance-2.5-guide','task':'t2v',
            'parameters':{'duration':10,'ratio':'16:9','output_format':'mp4'},'assets':[],
            'prompt_sha256':digest(self.file),'upstream':[{'path':'shots.md','sha256':digest(self.upstream)}],
            'reviews':[{'category':c,'status':'reviewed','reviewer':'test-fixture','evidence':'测试夹具：检查此处起始状态、抬眼和可见范围；不声称视频已生成。'} for c in ('creative','performance','continuity')],
            'warning_decisions':[]}

    def check(self):
        path = self.folder/'production.json'; path.write_text(json.dumps(self.record))
        return preflight(path,self.file,validate(self.file))

    def test_valid_t2v_and_pending_render(self):
        result = self.check()
        self.assertEqual(result['status'],'passed',result)
        self.assertEqual(result['render'],'not_tested')
        self.assertEqual(result['human_reviews'],'recorded_not_machine_verified')

    def test_changed_prompt_and_upstream_rejected(self):
        self.file.write_text(self.file.read_text()+'\n新动作。')
        self.upstream.write_text('不同的动作。')
        result = self.check()
        self.assertTrue(any(e.startswith('P01') for e in result['errors']))
        self.assertTrue(any(e.startswith('P05') for e in result['errors']))

    def test_missing_reviews_block_handoff(self):
        self.record['reviews']=[]
        self.assertEqual(self.check()['status'],'failed')

    def test_missing_media_not_fabricated_as_uploaded(self):
        self.record['task']='r2v'
        self.record['assets']=[{'id':'img1','path':'missing.png','role':'reference_image','purpose':'A 外观'}]
        self.assertTrue(any('文件不存在' in e for e in self.check()['errors']))

    def test_unverified_adapter_not_silently_assumed(self):
        self.record['adapter']='unknown-provider'
        self.assertEqual(self.check()['status'],'failed')

    def test_asset_count_and_upload_order(self):
        image = self.folder/'fixture.png'; image.write_bytes(b'unit-test media placeholder')
        self.record['task']='r2v'
        self.record['assets']=[{'id':'img2','path':image.name,'sha256':digest(image),'role':'reference_image','purpose':'测试夹具'}]
        with patch('production_preflight.probe',return_value={'streams':[{'codec_type':'video','width':32,'height':32}],'format':{'format_name':'png_pipe'}}):
            result = self.check()
        self.assertTrue(any('上传顺序' in e for e in result['errors']))
        self.assertTrue(any('素材绑定' in e for e in result['errors']))

    def test_wrong_json_shapes_fail_cleanly(self):
        for field, value in [('assets',[None]),('reviews',True),('upstream',[5]),('parameters',[]),('version',True)]:
            with self.subTest(field=field):
                old=copy.deepcopy(self.record);self.record[field]=value
                self.assertEqual(self.check()['status'],'failed');self.record=old


if __name__ == '__main__': unittest.main()

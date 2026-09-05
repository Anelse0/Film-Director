"""Production task coverage and real-media handoff checks."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_production import run, ROOT
from production_preflight import preflight, digest
from validate_prompt import validate
from prompt_structure import Document

class TaskMatrixTests(unittest.TestCase):
    def test_all_documented_tasks(self):
        cases = {
            't2v': ('无参考素材。', '', '16:9',10,''),
            'r2v': ('图1 = 人物外观。','img1→reference_image','16:9',10,''),
            'motion': ('视频1 = 运镜参考。','vid1→reference_video','16:9',10,''),
            'keyframe': ('图1 = 第一关键帧。','img1→reference_image','16:9',10,'以图片1的顺序作为关键帧。\n'),
            'storyboard': ('图1 = 故事板。','img1→reference_image','16:9',10,''),
            'first_last': ('图1 = 严格首帧。','img1→first_frame','adaptive',10,''),
            'edit': ('视频1 = 原视频。','vid1→reference_video','adaptive',-1,''),
            'extend': ('视频1 = 原视频。','vid1→reference_video','adaptive',10,''),
            'transition': ('视频1 = 前段；视频2 = 后段。','vid1→reference_video, vid2→reference_video','16:9',10,''),
        }
        for task,(refs,roles,ratio,duration,prefix) in cases.items():
            with self.subTest(task=task):
                body = '镜头1（0-10s）：【近景，固定】人物抬眼。'
                if task == 'edit': body='编辑视频1，将上衣改为蓝色，其余保持。'
                if task == 'extend': body='向后延长视频1十秒。\n'+body
                if task == 'motion': body='参考视频1的运镜，保持顺序。'
                if task == 'transition': body='将视频1和视频2无缝衔接，保留原视频内容。'
                text = prefix+'【素材绑定】'+refs+'\n【总述】10秒，室内。\n【起始状态】人物居中。\n【分镜时间线】\n'+body+'\n【贯穿要求】无bgm，只有环境音；不要字幕。\n| 项 | 值 |\n| 任务类型 | '+task+' |\n| ratio | '+ratio+' |\n| duration | '+str(duration)+' |\n| 输出格式 | mov |\n| content.role | '+roles+' |'
                self.assertEqual(run(text)['errors'],[])

    def test_30s_design_locks(self):
        text = (ROOT/'examples/example-04-parameters-fight.prompt.md').read_text()
        result = run(text)
        self.assertEqual(result['errors'],[])
        # Original seven utterances are a content regression fixture, not rules.
        self.assertEqual([r['text'] for r in result['dialogue']],[
            '你连袜子都不会放了？','我明天六点的飞机。',
            '你上个月也是六点的飞机。你每次都是六点的飞机。',
            '我下周就——','你上周也这么说。',
            '你嫌我不回家？你自己哪天九点前进过这个门？','我今天回来了。'])
        shots=Document(text).shots
        self.assertEqual(len(shots),7)
        self.assertEqual((shots[0].start,shots[-1].end),(0,30))
        self.assertGreaterEqual(result['dialogue'][-1]['start']-shots[-2].start,3)
        self.assertEqual(result['checks']['render'],'not_tested')
        self.assertTrue(any(w.startswith('W05') for w in result['warnings']))

@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'real-media integration requires ffmpeg/ffprobe')
class RealMediaTests(unittest.TestCase):
    def test_r2v_manifest_probes_media_and_rejects_stale_content(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            image=folder/'reference.png'
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=gray:s=32x32','-frames:v','1',str(image)],check=True,capture_output=True)
            source=folder/'upstream.md'
            source.write_text('技术夹具：参考灰色图的颜色，10秒固定空画面；不是角色身份或艺术效果验收。')
            prompt=folder/'clip.md'
            prompt.write_text('【素材绑定】图1 = 灰色调参考。\n【总述】10秒16:9，灰色空画面。\n【起始状态】均匀灰色画面。\n【分镜时间线】\n镜头1（0-10s）：【全景，固定】保持图1的灰色调。\n【贯穿要求】只有均匀灰色画面，无bgm，无对白；不要字幕。\n| 项 | 值 |\n| 任务类型 | r2v |\n| ratio | 16:9 |\n| duration | 10 |\n| 输出格式 | mp4 |\n| content.role | img1→reference_image |')
            record={'version':1,'adapter':'ark-seedance-2.5-guide','task':'r2v','prompt_sha256':digest(prompt),'parameters':{'ratio':'16:9','duration':10,'output_format':'mp4'},'assets':[{'id':'img1','path':image.name,'sha256':digest(image),'role':'reference_image','purpose':'真实PNG技术夹具，仅用于颜色绑定'}],'upstream':[{'path':source.name,'sha256':digest(source)}],'reviews':[{'category':c,'status':'not_applicable','reviewer':'integration-fixture','evidence':'技术颜色输入测试，无人物表演或戏剧质量结论。'} for c in ('creative','performance','continuity')],'warning_decisions':[]}
            path=folder/'record.json';path.write_text(json.dumps(record))
            result=preflight(path,prompt,validate(prompt))
            self.assertEqual(result['status'],'passed',result)
            image.write_bytes(b'corrupt')
            self.assertTrue(any('SHA-256' in e for e in preflight(path,prompt,validate(prompt))['errors']))

if __name__ == '__main__': unittest.main()

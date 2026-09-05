"""Local production handoff checks. Does not call a generation API or score art.

Evidence is bound to exact files. A recorded human review is not automated
semantic verification; successful preflight never implies a rendered result.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from production_contract import asset_id, metadata, parameters, roles_from_fields, task_type, check_parameters
from performance_checks import check_record
from prompt_structure import Document


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError(f'无法读取媒体：{path.name}')
    return json.loads(result.stdout)


def preflight(record_path, prompt_path, validation):
    errors, warnings = [], []
    checked_assets = []
    human_reviews = 'not_recorded'
    try:
        record_path, prompt_path = Path(record_path), Path(prompt_path)
        record = json.loads(record_path.read_text(encoding='utf-8'))
        if not isinstance(record, dict) or type(record.get('version')) is not int or record['version'] != 1:
            raise ValueError('生产记录 version 必须为 1')
        if record.get('adapter') != 'ark-seedance-2.5-guide':
            raise ValueError('未核实的适配器；其他平台必须先核实参数契约')
        task, params, assets = record.get('task'), record.get('parameters'), record.get('assets')
        if not isinstance(params, dict) or not isinstance(assets, list):
            raise ValueError('缺少 parameters 对象或 assets 列表')
        if record.get('prompt_sha256') != digest(prompt_path):
            errors.append('P01 Prompt 已改变或缺少匹配的 SHA-256；重新审阅后更新记录')
        text = prompt_path.read_text(encoding='utf-8')
        fields = metadata(text)
        declared_task = task_type(fields, text)
        if declared_task is not None and declared_task != task:
            errors.append('P02 Prompt 与生产记录任务类型不一致')
        for key, value in parameters(fields).items():
            if value is not None and value != params.get(key):
                errors.append(f'P02 Prompt 与生产记录参数 {key} 不一致')
        roles, ids = {}, []
        counts = {'img':0, 'vid':0, 'aud':0}
        lengths = {'vid':0., 'aud':0.}
        frame_sizes = {}
        for asset in assets:
            if not isinstance(asset, dict): raise ValueError('素材条目必须为对象')
            ident = asset_id(asset.get('id', ''))
            if ident in ids: raise ValueError(f'素材编号重复：{ident}')
            ids.append(ident)
            kind = re.sub(r'\d+', '', ident)
            counts[kind] += 1
            if ident != f'{kind}{counts[kind]}':
                errors.append(f'P03 {ident} 不符合列表中的同类上传顺序')
            role = asset.get('role')
            roles[ident] = role
            if not isinstance(asset.get('purpose'), str) or not asset['purpose'].strip():
                errors.append(f'P03 {ident} 缺少参考职责')
            raw_path = asset.get('path')
            if not isinstance(raw_path, str) or not raw_path:
                raise ValueError(f'{ident} 缺少实际文件路径')
            path = (record_path.parent / raw_path).resolve()
            if not path.is_file():
                errors.append(f'P03 {ident} 文件不存在：{path}')
                continue
            if asset.get('sha256') != digest(path):
                errors.append(f'P03 {ident} 文件改变或缺少媒体 SHA-256')
                continue
            media = probe(path)
            streams = media.get('streams', [])
            visual = next((s for s in streams if s.get('codec_type') == 'video'), None)
            auditory = next((s for s in streams if s.get('codec_type') == 'audio'), None)
            if kind in {'img','vid'} and not visual or kind == 'aud' and not auditory:
                errors.append(f'P03 {ident} 实际媒体类型不匹配')
                continue
            duration = media.get('format', {}).get('duration')
            # Still-image demuxers include image2, png_pipe, jpeg_pipe etc.
            fmt = media.get('format', {}).get('format_name', '')
            is_image = 'image2' in fmt or '_pipe' in fmt
            if (kind == 'img') != is_image:
                errors.append(f'P03 {ident} 静态图像/连续媒体类型不匹配')
            if kind == 'img':
                width, height = visual.get('width', 0), visual.get('height', 0)
                if width <= 0 or height <= 0: errors.append(f'P03 {ident} 无有效图像尺寸')
                # The guide says "within 4K" without an exact pixel rectangle.
                # Do not invent 3840 vs 4096 as a model hard limit.
                if max(width,height) > 4096: warnings.append(f'P04 {ident} 超出常见 4K 长边，请按平台核实')
                if role in {'first_frame','last_frame'}: frame_sizes[role] = (width,height)
            else:
                try:
                    seconds = float(duration)
                    if not 0 < seconds < float('inf'): raise ValueError()
                    lengths[kind] += seconds
                except (TypeError, ValueError): errors.append(f'P03 {ident} 缺少可靠媒体时长')
                if task in {'edit','extend'} and kind == 'vid' and path.suffix.lower() != '.mov':
                    warnings.append(f'P04 {ident} 编辑/延长建议使用 MOV 输入')
            checked_assets.append({'id':ident, 'path':str(path), 'role':role})
        if set(ids) != set(validation.get('assets', {}).get('declared', [])):
            errors.append('P03 上传清单与 Prompt 素材绑定不一致')
        prompt_roles = roles_from_fields(fields)
        if prompt_roles and prompt_roles != roles:
            errors.append('P02 Prompt 与实际上传 role 映射不一致')
        for kind, maximum in [('img',30),('vid',10),('aud',10)]:
            if counts[kind] > maximum: errors.append(f'P04 {kind} 数量超过指南上限 {maximum}')
        if len(ids) > 50: errors.append('P04 参考素材合计超过 50')
        for kind, seconds in lengths.items():
            if seconds > 30: errors.append(f'P04 {kind} 总时长超过 30 秒')
        if len(frame_sizes) == 2:
            a, b = frame_sizes['first_frame'], frame_sizes['last_frame']
            if a[0]*b[1] != a[1]*b[0]: warnings.append('P04 首尾帧画幅不同，尾帧会被拉伸')
        pe, pw, _ = check_parameters(task, params, roles, strict=True)
        errors.extend(pe); warnings.extend(pw)
        # A real handoff supplies its approved upstream artefacts; a self-made
        # hash is version binding, not proof that approval happened.
        upstream = record.get('upstream')
        if not isinstance(upstream, list) or not upstream:
            errors.append('P05 缺少编译前创作/分镜依据')
        else:
            for item in upstream:
                if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                    raise ValueError('upstream 条目缺少路径')
                path = (record_path.parent / item['path']).resolve()
                if not path.is_file() or item.get('sha256') != digest(path): errors.append('P05 上游文件缺失或版本已改变')
        doc = Document(re.split(r'^\|\s*(?:项|参数项)\s*\|', text, maxsplit=1, flags=re.M)[0])
        if doc.beats:
            perf = record.get('performance_record')
            if not isinstance(perf, str): errors.append('P05 有表演节拍但缺少编译前表演记录')
            else:
                path = (record_path.parent / perf).resolve()
                upstream_paths = {(record_path.parent/i['path']).resolve() for i in (upstream or []) if isinstance(i,dict) and isinstance(i.get('path'),str)}
                if path not in upstream_paths: errors.append('P05 表演记录没有绑定上游版本')
                acting = json.loads(path.read_text(encoding='utf-8'))
                fe, _ = check_record(acting, [b.tuple() for b in doc.beats], params.get('duration'))
                errors.extend(fe)
        reviews = record.get('reviews', [])
        if not isinstance(reviews, list): raise ValueError('reviews 必须为列表')
        for category in ('creative','performance','continuity'):
            rows = [r for r in reviews if isinstance(r,dict) and r.get('category') == category]
            if len(rows) != 1 or rows[0].get('status') not in {'reviewed','not_applicable'} or not all(
                    isinstance(rows[0].get(key), str) and rows[0][key].strip() for key in ('reviewer','evidence')):
                errors.append(f'P06 缺少 {category} 审阅者与具体证据/不适用理由')
        if not any(e.startswith('P06') for e in errors): human_reviews = 'recorded_not_machine_verified'
        all_warnings = list(dict.fromkeys(validation.get('warnings', []) + warnings))
        decisions = record.get('warning_decisions', [])
        if not isinstance(decisions, list): raise ValueError('warning_decisions 必须为列表')
        handled = {d.get('warning') for d in decisions if isinstance(d,dict) and isinstance(d.get('reason'),str) and d['reason'].strip()}
        if any(w not in handled for w in all_warnings): errors.append('P06 存在未逐条处理的风险提示')
        if validation['errors']: errors.append('P07 Prompt 确定性检查仍有错误')
    except (OSError, ValueError, TypeError, KeyError, subprocess.TimeoutExpired) as exc:
        errors.append(f'P00 生产记录/媒体检查失败：{exc}')
    return {'status':'failed' if errors else 'passed', 'errors':errors, 'warnings':warnings,
            'assets':checked_assets, 'human_reviews':human_reviews, 'render':'not_tested'}

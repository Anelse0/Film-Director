"""Task-aware parameter contract for the user-supplied Ark Seedance 2.5 guide.

Model requirements live here, not in artistic heuristics. Other platforms need
their own verified adapter; this module never silently treats them as Ark.
"""
import math
import re

TASKS = {
    't2v': {'timed': True, 'locked': False},
    'r2v': {'timed': True, 'locked': False},
    'motion': {'timed': False, 'locked': False},
    'keyframe': {'timed': True, 'locked': False},
    'storyboard': {'timed': True, 'locked': False},
    'first_last': {'timed': True, 'locked': True},
    'edit': {'timed': False, 'locked': True},
    'extend': {'timed': True, 'locked': True},
    'transition': {'timed': False, 'locked': False},
}
TASK_PREFIXES = {
    't2v': ('t2v', '文生'), 'r2v': ('r2v', '参考生'),
    'motion': ('motion', '动作参考', '运镜参考'),
    'keyframe': ('keyframe', '关键帧'), 'storyboard': ('storyboard', '宫格'),
    'first_last': ('first_last', '首尾帧', '首帧'), 'edit': ('edit', '编辑', '视频编辑'),
    'extend': ('extend', '延长', '视频延长'), 'transition': ('transition', '无缝转场'),
}
REF_ROLES = {'img': 'reference_image', 'vid': 'reference_video', 'aud': 'reference_audio'}
ASSET_PATTERN = r'(?:@?(?:图片?|视频|音频)|image|img|video|vid|audio|aud)\s*\d+'


def asset_id(raw):
    m = re.fullmatch(r'@?(图片?|视频|音频|image|img|video|vid|audio|aud)\s*(\d+)', raw, re.I)
    if not m:
        raise ValueError(f'invalid asset id: {raw}')
    kind = {'图片':'img','图':'img','视频':'vid','音频':'aud','image':'img','video':'vid','audio':'aud'}.get(m[1].lower(),m[1].lower())
    if int(m[2]) < 1:
        raise ValueError('asset number must be positive')
    return f'{kind}{int(m[2])}'


def metadata(text):
    fields = {}
    for key, value in re.findall(r'^\|\s*([^|\n]+?)\s*\|\s*([^|\n]*?)\s*\|\s*$', text, re.M):
        if key not in {'项', '值', '---'}:
            if key in fields:
                raise ValueError(f'duplicate metadata field: {key}')
            fields[key] = value
    return fields


def task_type(fields, text):
    raw = fields.get('任务类型', fields.get('task', '')).lower()
    if raw:
        return next((key for key, prefixes in TASK_PREFIXES.items() if raw.startswith(prefixes)), 'unknown')
    # Compatibility hints are not a complete production declaration.
    if re.match(r'\s*(编辑视频|edit\b)', text, re.I): return 'edit'
    if re.match(r'\s*(向前延长|向后延长|延续|续写|extend\b)', text, re.I): return 'extend'
    return None


def roles_from_fields(fields):
    raw = fields.get('content.role 映射', fields.get('content.role', ''))
    roles = {}
    consumed = []
    for match in re.finditer(rf'({ASSET_PATTERN})\s*(?:→|=|:)\s*([a-z_]+)', raw, re.I):
        ident = asset_id(match[1])
        if ident in roles: raise ValueError(f'duplicate role: {ident}')
        roles[ident] = match[2]
        consumed.append((match.start(), match.end()))
    rest = raw
    for start, end in reversed(consumed):
        rest = rest[:start] + rest[end:]
    if rest.strip(' ,，;；') not in {'', '无', 'none', 'None'}:
        raise ValueError('无法完整解析 content.role 映射')
    return roles


def parameters(fields):
    duration = fields.get('duration')
    return {'ratio': fields.get('ratio'), 'duration': float(duration) if duration is not None else None,
            'output_format': fields.get('output_format', fields.get('输出格式'))}


def check_parameters(task, params, roles, strict=False):
    errors, warnings = [], []
    if task not in TASKS:
        return (['E22 未声明有效任务类型'] if strict or task == 'unknown' else []), [], 'not_checked'
    spec = TASKS[task]
    if strict:
        for field in ('ratio', 'duration', 'output_format'):
            if params.get(field) is None: errors.append(f'E22 缺少生成参数 {field}')
    ratio, duration, fmt = (params.get(k) for k in ('ratio','duration','output_format'))
    if spec['locked'] and ratio is not None and ratio != 'adaptive':
        errors.append('E22 有锁定任务 ratio 必须为 adaptive')
    if ratio is not None and ratio != 'adaptive':
        try:
            parts = str(ratio).split(':')
            value = float(parts[0]) / float(parts[1]) if len(parts) == 2 else float(ratio)
            if not math.isfinite(value) or not .4 <= value <= 2.5: raise ValueError()
        except (ValueError, ZeroDivisionError): errors.append('E22 ratio 不在指南画幅范围内')
    if duration is not None:
        if type(duration) not in (int, float) or not math.isfinite(duration):
            errors.append('E22 duration 必须为有限数值')
        elif task == 'edit' and duration != -1:
            errors.append('E22 编辑任务 duration 必须为 -1')
        elif task != 'edit' and (duration <= 0 or duration > 30 or duration != int(duration)):
            errors.append('E22 本地生成契约 duration 为 1–30 整数秒')
    if fmt is not None and fmt not in {'mp4','mov'}:
        errors.append('E22 当前适配器未核实该输出格式')
    if task in {'edit','extend'} and fmt == 'mp4':
        warnings.append('W22 编辑/延长建议输入输出 MOV；MP4 不是硬错误')
    for ident, role in roles.items():
        kind = re.sub(r'\d+', '', ident)
        allowed = {REF_ROLES.get(kind)}
        if task == 'first_last' and kind == 'img': allowed |= {'first_frame','last_frame'}
        if role not in allowed: errors.append(f'E22 {ident} 的 role 与素材类型/任务不符')
    if roles or strict:
        if task == 't2v' and roles: errors.append('E22 t2v 不应带参考素材；请按实际任务声明')
        if task != 't2v' and not roles: errors.append('E22 该任务缺少素材 role 映射')
        if task in {'keyframe','storyboard'} and not any(r == 'reference_image' for r in roles.values()):
            errors.append('E22 关键帧/故事板任务缺少参考图像')
        if task in {'edit','extend','transition'}:
            count = sum(r == 'reference_video' for r in roles.values())
            if count < (2 if task == 'transition' else 1): errors.append('E22 缺少任务所需参考视频')
        if task == 'first_last':
            if list(roles.values()).count('first_frame') != 1 or list(roles.values()).count('last_frame') > 1:
                errors.append('E22 严格首帧任务需要一个 first_frame，至多一个 last_frame')
    complete = all(params.get(k) is not None for k in ('ratio','duration','output_format')) and (roles or task == 't2v')
    return errors, warnings, 'failed' if errors else 'passed' if complete else 'incomplete'

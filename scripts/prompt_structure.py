"""Source spans keep shot, acting and dialogue tracks separate (stdlib only).

This parses the documented local format; it is not a natural-language judge.
Unknown prose is retained, never discarded because a nested beat exists.
"""
from dataclasses import dataclass
import re

NUMBER = r"\d+(?:\.\d+)?"
INTERVAL = rf"(-?{NUMBER})\s*(?:s|秒)?\s*[-–—~]\s*(-?{NUMBER})\s*(?:s|秒)"
SHOT_RE = re.compile(rf"^(?:镜头|Shot)\s*(\d+)\s*[（(]\s*{INTERVAL}[^)）]*[)）]", re.M | re.I)
BEAT_RE = re.compile(rf"^\s*(?:(?:节拍|Beat)\s+([^\s（(]+)\s*[（(])?{INTERVAL}\s*[)）]?\s*[:：]\s*", re.M | re.I)
BOUNDARY_RE = re.compile(r"^\s*(?:【|(?:镜头|Shot)\s*\d+\s*[（(]|\|\s*(?:项|参数项)\s*\||#{1,6}\s|```)", re.M | re.I)
SECTION_RE = re.compile(r"^\s*(?:【[^】]+】|(?:REFERENCES|OVERVIEW|LOOK|OPENING STATE|TIMELINE|GLOBAL RULES|AUDIO)\s*:)", re.M | re.I)


@dataclass(frozen=True)
class Unit:
    ident: str
    start: float
    end: float
    offset: int
    body_start: int
    stop: int
    body: str

    def tuple(self):
        return self.ident, self.start, self.end, self.body.strip()


def units(text, pattern, beat=False):
    matches = list(pattern.finditer(text))
    result = []
    for i, match in enumerate(matches):
        stop = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        boundary = (BOUNDARY_RE if beat else SECTION_RE).search(text, match.end(), stop)
        if boundary:
            stop = boundary.start()
        result.append(Unit(match.group(1) or str(i + 1), float(match.group(2)),
                           float(match.group(3)), match.start(), match.end(), stop,
                           text[match.end():stop]))
    return result


def owner(position, candidates):
    return next((u for u in candidates if u.body_start <= position < u.stop), None)


class Document:
    def __init__(self, text):
        self.text = text
        self.shots = units(text, SHOT_RE)
        self.beats = units(text, BEAT_RE, beat=True)

    def ownership_errors(self):
        errors = []
        for name, track in [('镜头', self.shots), ('节拍', self.beats)]:
            ids = [u.ident for u in track]
            if len(ids) != len(set(ids)):
                errors.append(f"E20 {name}编号重复，无法唯一绑定上游")
        for beat in self.beats:
            shot = owner(beat.offset, self.shots)
            if self.shots and (shot is None or not shot.start <= beat.start < beat.end <= shot.end):
                errors.append(f"E20 节拍 {beat.ident} 的时间不在其所属镜头内")
        return errors


# Canonical: 台词（角色，0-3s，中文普通话）："逐字台词".
# Existing 台词(角色): and A says (...) : forms remain readable.
SPEECH_RE = re.compile(
    r'(?:台词\s*[（(](?P<cn>[^)）\n]+)[)）]\s*[:：]\s*|'
    r'(?P<speaker>[^\s，。；:：“"()（）]+)\s+(?:says|speaks)\s*(?:\((?P<en>[^)\n]*)\))?\s*[:：]\s*|'
    r'(?P<zh>[^\s，。；:：“"()（）]+)(?:说|说道)\s*[:：]\s*)'
    r'[“"](?P<line>[^”"\n]*)[”"]', re.I)


def dialogue_checks(doc, duration, rates):
    """Count each declared utterance once, with its own or enclosing time window."""
    errors, warnings, rows = [], [], []
    zh_rate, en_rate, cap = rates
    matches = list(SPEECH_RE.finditer(doc.text))
    for match in matches:
        details = match.group('cn') or match.group('en') or ''
        speaker = (match.group('cn') or match.group('speaker') or match.group('zh')).split('，')[0].split(',')[0].strip()
        shot = owner(match.start(), doc.shots)
        beat = owner(match.start(), doc.beats)
        container = beat or shot
        explicit = re.search(INTERVAL, details, re.I)
        start, end = ((float(explicit.group(1)), float(explicit.group(2))) if explicit
                      else (container.start, container.end) if container else (0, duration))
        if explicit and (start < 0 or end <= start or (duration is not None and duration > 0 and end > duration)
                         or (container and not container.start <= start < end <= container.end)):
            errors.append(f'E21 {speaker} 台词窗口越界或无效：{start:g}-{end:g}s')
        if not explicit:
            warnings.append(f'W21 {speaker} 台词未给独立时间窗；当前按所属节拍/镜头估时：{match.group("line")[:24]}')
        line = match.group('line')
        zh = len(re.findall(r'[\u4e00-\u9fff]', line))
        en = len(re.findall(r"[A-Za-z]+(?:['’][A-Za-z]+)*", line))
        estimate = zh / zh_rate + en / en_rate
        rows.append({'speaker': speaker, 'text': line, 'start': start, 'end': end,
                     'estimate': estimate, 'explicit': bool(explicit), 'shot': shot.ident if shot else None})
        if end is not None and end > start and estimate > (end - start) * .9:
            warnings.append(f'W05 {speaker} 台词约 {estimate:.1f}s 接近或超过窗口 {end-start:g}s')
    # Do not silently certify unknown dialogue syntax. Quoted parenthetical acting
    # directions are not additional speech. Legacy unlabelled quotations get review.
    for quoted in re.finditer(r'[“"][^”"\n]+[”"]', doc.text):
        if any(m.start() <= quoted.start() < m.end() for m in matches):
            continue
        # A quoted word followed by an acting annotation is not a second line.
        # Other unmatched quotations remain visible even beside parsed speech.
        tail = doc.text[quoted.end():quoted.end()+12]
        if re.match(r'\s*(?:重读|轻读|之后|停住|一词|word)', tail, re.I):
            continue
        warnings.append('W21 未计入台词估时的引号内容：' + quoted.group()[:32] + '；须标为台词或非台词并核对')
    for i, first in enumerate(rows):
        for second in rows[i + 1:]:
            if first['explicit'] and second['explicit'] and max(first['start'], second['start']) < min(first['end'], second['end']):
                warnings.append(f'W11 台词时间窗重叠：{first["speaker"]}/{second["speaker"]}；确认有意重叠及口型/画外安排')
    # Aggregate each parent window as well as the whole clip. Many individually
    # short lines can still overload one shot; nested beats must not double-count.
    for unit in doc.shots or doc.beats:
        subtotal = sum(r['estimate'] for r in rows if r['start'] is not None and r['end'] is not None
                       and unit.start <= r['start'] < r['end'] <= unit.end)
        if subtotal > (unit.end - unit.start) * .9:
            warnings.append(f'W05 单元 {unit.ident} 台词累计 {subtotal:.1f}s 超过可用窗口')
    total = sum(r['estimate'] for r in rows)
    if duration is not None and duration > 0 and total > duration * cap:
        warnings.append(f'W05 总台词估时 {total:.1f}s > clip 的 {cap:.2f}（{duration*cap:.1f}s）')
    return errors, list(dict.fromkeys(warnings)), rows, total

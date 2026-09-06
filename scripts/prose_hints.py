"""Conservative surface hints, not a dialogue/acting quality classifier.

Quoted speech cannot satisfy stage-direction requirements. Affirmed mouth
cues are recognized in local clauses; ambiguous or negated cues stay pending.
This does not establish which listener or time interval the cue belongs to.
"""
import re


def direction_text(text):
    return re.sub(r'“[^”]*”|"[^"\n]*"', '', text)


MOUTH_CUE = re.compile(
    r'闭着嘴|闭口|闭嘴|抿嘴|不出声|嘴(?:唇|巴)?(?:保持|始终|仍然|仍|一直|紧紧|紧)?(?:闭合|紧闭|闭着)'
    r'|\bmouth\s+(?:(?:stays|remains|is)\s+)?closed\b'
    r'|\blips\s+(?:(?:stay|remain|are)\s+)?(?:pressed|closed)\b', re.I)
NEGATED_CONTEXT = re.compile(
    r'不(?:要|能|会|肯|再|必|曾)?|没(?:有)?|未|并非|无需|拒绝'
    r'|\b(?:not|never|without|no|cannot|can\x27t|doesn\x27t|isn\x27t)\b', re.I)


def has_mouth_direction(text):
    for clause in re.split(r'[，。；！？,;!?\n]', direction_text(text)):
        for match in MOUTH_CUE.finditer(clause):
            # Negation within "不出声" belongs to the affirmative behavior;
            # negation before it ("没有不出声") does not prove that behavior.
            if not NEGATED_CONTEXT.search(clause[:match.start()]):
                return True
    return False


def has_subtitle_policy(text):
    prose = direction_text(text)
    return bool(re.search(
        r'(?:^|[\s，。；：:、])(?:不要(?:出现|添加)?|无|不加|不添加|不生成|不额外加入.{0,4})字幕'
        r'|\bno\s+(?:subtitles|captions)\b', prose, re.I))


def has_sound_policy(text):
    # Positive and negative sound choices are both legitimate declarations.
    # This is intentionally only a presence hint, not a semantic consistency pass.
    return bool(re.search(r'bgm|背景音乐|环境音|音乐|配乐|music|room tone|ambien', direction_text(text), re.I))

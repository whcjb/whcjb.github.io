"""莱尔马太共用常量。"""
import re

# e-Sword 模块把 1857 原书的英式拼写成批改成了美式。下列各族在 1857 全书 OCR 里美式写法 0 次、
# 英式写法 ≥1 次（统计见 PROVENANCE.md），整族回改，不必逐处看图。
# 注意 1857 是纽约 Carter 版，honor/labor/neighbor/favor/judgment 原书本来就是美式——不在此列。
GLOBAL_SPELLING = {
    'savior': 'saviour', 'saviors': 'saviours', "savior's": "saviour's",
    'fulfill': 'fulfil', 'fulfills': 'fulfils', 'fulfillment': 'fulfilment', 'fulfillments': 'fulfilments',
    'fullness': 'fulness',
    'marvelous': 'marvellous', 'marvelously': 'marvellously',
    'offense': 'offence', 'offenses': 'offences',
    'defense': 'defence', 'pretense': 'pretence', 'pretenses': 'pretences',
    'traveler': 'traveller', 'travelers': 'travellers', 'traveling': 'travelling',
    'worshiped': 'worshipped', 'worshiping': 'worshipping', 'worshiper': 'worshipper', 'worshipers': 'worshippers',
    'unmistakable': 'unmistakeable',
    'skeptical': 'sceptical', 'skepticism': 'scepticism', 'skeptic': 'sceptic', 'skeptics': 'sceptics',
    'willful': 'wilful', 'willfully': 'wilfully',
}


def keep_case(src, rep):
    if src.isupper():
        return rep.upper()
    if src[:1].isupper():
        return rep[:1].upper() + rep[1:]
    return rep


GLOBAL_RE = re.compile(r"\b(" + '|'.join(sorted(map(re.escape, GLOBAL_SPELLING), key=len, reverse=True)) + r")\b",
                       re.I)


def respell(text):
    return GLOBAL_RE.sub(lambda m: keep_case(m.group(0), GLOBAL_SPELLING[m.group(0).lower()]), text)

"""教派 / 主义名每篇首次出现补英文原名（各书中文发布脚本共用）。

2026-11-03 用户问「阿明尼乌主义为什么不加英文注释」：模型对人名括注得好，教派名常漏。
按本篇英文原文里**实际用的写法**补，原文里没有对应词就不补、不编；已括注的跳过（幂等）。
"""
import re

SECT_TERMS = [
    ('阿明尼乌主义', r'Arminianism'), ('阿明尼乌派', r'Arminians?'),
    ('半柏拉糾主义', r'Semi-?[Pp]elagianism'), ('半柏拉糾派', r'Semi-?[Pp]elagians?'),
    ('柏拉糾主义', r'Pelagianism'), ('柏拉糾派', r'Pelagians'),
    ('抗辩派', r'Remonstrants?'), ('苏西尼派', r'Socinians?'), ('苏西尼主义', r'Socinianism'),
    ('加尔文派', r'Calvinists?'), ('路德派', r'Lutherans?'), ('耶稣会士', r'Iesuites?|Jesuites?|Jesuits?|Iesuits?'),
    ('多明我会', r'Dominicans?'), ('方济各会', r'Franciscans?'), ('多纳徒派', r'Donatists?'),
    ('诺斯底派', r'Gnostick?s?'), ('摩尼教', r'Manich\w+'), ('阿里乌派', r'Arrians?|Arians'),
    ('再洗礼派', r'Anabaptists?'), ('托马斯派', r'Thomists?'),
]


def annotate(zh: str, en: str, cls: str) -> str:
    """zh 里每个教派词第一次出现处补 <span class="{cls}">[原名]</span>。"""
    en_plain = re.sub(r'<[^>]+>|\*', ' ', en)
    for term, pat in SECT_TERMS:
        m_en = re.search(r'\b(?:' + pat + r')\b', en_plain)
        if not m_en:
            continue
        for m in re.finditer(re.escape(term), zh):
            i, j = m.start(), m.end()
            if term.startswith('柏拉糾') and zh[i - 1:i] == '半':
                continue
            if zh[j:j + 1] in '（(' or zh[j:].startswith('<span class="' + cls):
                break
            zh = zh[:j] + f'<span class="{cls}">[{m_en.group(0)}]</span>' + zh[j:]
            break
    return zh

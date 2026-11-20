"""正文照原书版式（扉页、献辞之外的经节页）。

文字一字不动，只给页面包一层 `.pd`（_includes/period-body.html 定样式：段首缩进、段间不空行、旁注小号正体、
经文无框悬挂、首字两行下沉）。卷首开篇页（原书有花饰条、篇题、木刻首字）另由
`<书>_raw/<卷>/manual_pages/opening.json` 指定：

    slug       哪一页（如 v1）
    headpiece  花饰条图（站内路径）
    head       篇题逐行 HTML（pd-head 的 a/b/c/d 字号类）
    initial    木刻首字图；替代该页第一个 dropcap
"""
import json
import re
from pathlib import Path


def apply(md, raw_dir, P, slug):
    raw_dir = Path(raw_dir)
    op_f = raw_dir / 'manual_pages' / 'opening.json'
    if op_f.exists():
        op = json.loads(op_f.read_text(encoding='utf-8'))
        if op.get('slug') == slug:
            head = (f'<img class="pd-hp" src="{{{{ site.baseurl }}}}{op["headpiece"]}" alt="">\n' if op.get('headpiece') else '') + \
                f'<div class="pd-head">\n{op["head"]}\n</div>\n\n'
            md = head + md
            if op.get('initial'):
                md = re.sub(r'<span class="' + P + r'-dropcap">(\w)</span>',
                            lambda x: f'<img class="pd-init" src="{{{{ site.baseurl }}}}{op["initial"]}" alt="{x.group(1)}">',
                            md, count=1)
    # 原书每节讲解首段第一个字母两行下沉；录入本只在全书开头标了 dropcap，其余节首是「HEre」这种首两字母大写的写法
    if f'{P}-dropcap' not in md and '<img class="pd-init"' not in md:
        md = re.sub(r'(</div>\n\n(?:<span class="' + P + r'-margin"[^>]*>.*?</span> )?)([A-Z])(?=[A-Z ])',
                    lambda x: x.group(1) + f'<span class="{P}-dropcap">{x.group(2)}</span>', md, count=1)
    return '{% include period-body.html %}\n\n<div class="pd" markdown="1">\n\n' + md.strip() + '\n\n</div>'

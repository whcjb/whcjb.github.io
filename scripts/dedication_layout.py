"""献辞照原书影像排版（old-book-ocr §5.6 的延伸：扉页之外，献辞页的题头、花饰、首字、正文字体、落款也照原图）。

正文文字仍取录入本／OCR，不动；只换版式。每本书一份 `<书>_raw/<卷>/manual_pages/dedication.json`：

    head       题头（致谁）逐行 HTML，照原图分行、字号（tpg 同一套 z0–z6 / sc / it 类）
    headpiece  页顶花饰条图（站内路径，裁自原图），可省
    initial    木刻首字图（站内路径），可省；有则替代正文第一个 dropcap
    salute     称呼行（SIR, / HONORABLE, / Right Honourable 等）的排法：left / center，可省
    italic     原书正文是否以斜体排（true 时正文斜体、录入本里标的斜体反作正体——原书斜体正文里的正体字）
    tail_from  落款从正文哪一句起切出（落款原混在末段时用），可省；默认取末尾的 closer 段
    tail       落款逐行 HTML（右对齐、缩进、小型大写照原图）
    note       页尾说明（如无同版影像），可省

apply(md, raw_dir, P) 返回改排后的 markdown；没有 json 时原样返回。
"""
import json
import re
from pathlib import Path


def apply(md, raw_dir, P):
    spec_f = Path(raw_dir) / 'manual_pages' / 'dedication.json'
    if not spec_f.exists():
        return md
    s = json.loads(spec_f.read_text(encoding='utf-8'))
    # 1. 题头：第一个 ### 行（保留行首页锚）；没有 ### 的底本（AGES 等）用 head_paras 指定开头几段
    if s.get('head_paras'):
        fm_end = md.find('\n---\n', 4) + 5 if md.startswith('---') else 0
        rest = md[fm_end:].lstrip('\n')
        paras = rest.split('\n\n')
        k = fm_end + (len(md[fm_end:]) - len(rest)) + len('\n\n'.join(paras[:s['head_paras']]))
        m = re.match(r'(?s)(.*)', md[fm_end:k])
        md = md[:fm_end] + '\n#### ' + re.sub(r'\s+', ' ', md[fm_end:k]) + md[k:]
    if s.get('head_re'):                                        # 题头是普通段落（1868 年本的 -quote 段）
        h = re.search(s['head_re'], md, re.S)
        assert h, f'题头找不到：{s["head_re"]}'
        md = md[:h.start()] + '\n\n#### ' + re.sub(r'\s+', ' ', h.group()) + '\n\n' + md[h.end():]
    m = re.search(r'^#{2,4} (.*)$', md, re.M)
    assert m, '献辞没有题头行'
    anchors = ''.join(re.findall(r'<span class="[^"]*-pb"[^>]*></span>', m.group(1)))
    head = (f'<img class="ded-hp" src="{{{{ site.baseurl }}}}{s["headpiece"]}" alt="">\n' if s.get('headpiece') else '') + \
        f'<div class="ded-head">\n{s["head"]}\n</div><!--ded-head-end-->'
    md = md[:m.start()] + anchors + '\n\n' + head + md[m.end():]
    # 2. 称呼
    if s.get('salute'):
        md = re.sub(r'<p class="' + P + r'-salute"', f'<p class="{P}-salute ded-salute-{s["salute"]}"', md, count=1)
    # 3. 落款：切出并换成手排块
    tail = f'<div class="ded-tail">\n{s["tail"]}\n</div>' if s.get('tail') else ''
    notes_at = md.find(f'<div class="{P}-notes"')
    body_end = notes_at if notes_at >= 0 else len(md)
    if s.get('tail_from'):
        k = md.rfind(s['tail_from'], 0, body_end)
        assert k >= 0, f'落款起句找不到：{s["tail_from"]}'
        e = md.find('\n\n', k)
        e = body_end if e < 0 or e > body_end else e
        if s.get('tail_to'):                                    # 落款延伸到这句为止（含）
            z = md.find(s['tail_to'], k, body_end)
            assert z >= 0, f'落款止句找不到：{s["tail_to"]}'
            e = z + len(s['tail_to'])
        after = list(re.finditer(r'<p class="' + P + r'-closer"[^>]*>.*?</p>', md[e:body_end], re.S))
        if after:                                               # 起句之后还有落款段：一并收进手排块
            e += after[-1].end()
        cut = md[k:e]
        md = md[:k].rstrip() + '\n\n' + tail + md[e:]
    else:
        cl = list(re.finditer(r'<p class="' + P + r'-closer"[^>]*>.*?</p>\s*', md[:body_end], re.S))
        assert cl, '献辞没有落款段（closer），请给 tail_from'
        a, b = cl[0].start(), cl[-1].end()
        md = md[:a] + tail + '\n\n' + md[b:]
    # 4. 首字
    if s.get('cap_at'):                                         # 排印本的素体两行下沉首字（无木刻图）
        a = s['cap_at']
        assert a in md, f'首字位置找不到：{a}'
        md = md.replace(a, f'<span class="ded-cap">{a[0]}</span>{a[1:]}', 1)
    if s.get('initial') and s.get('initial_at'):                # 底本没标 dropcap：把首字所在串换成图 + 余下字母
        a = s['initial_at']
        assert a in md, f'首字位置找不到：{a}'
        lead = re.match(r'[*_]*', a).group()
        md = md.replace(a, f'<img class="ded-init" src="{{{{ site.baseurl }}}}{s["initial"]}" alt="{a[len(lead)]}">' + lead + a[len(lead) + 1:], 1)
    elif s.get('initial'):
        md = re.sub(r'<span class="' + P + r'-dropcap">(\w)</span>',
                    lambda x: f'<img class="ded-init" src="{{{{ site.baseurl }}}}{s["initial"]}" alt="{x.group(1)}">',
                    md, count=1)
    # 5. 正文字体：题头之后、落款之前包一层
    if s.get('italic'):
        a = md.find('<!--ded-head-end-->') + len('<!--ded-head-end-->')
        b = md.find('<div class="ded-tail">') if tail else body_end
        f = md.find(f'<div class="{P}-fill"', a)               # 补文块（后来版本、现代拼法）不随原书斜体，也不能被包层劈开
        b = f if 0 <= f < b else b
        md = md[:a] + '\n\n<div class="ded-it" markdown="1">\n\n' + md[a:b].strip() + '\n\n</div>\n\n' + md[b:]
    if s.get('note'):
        md = md.rstrip() + f'\n\n<p class="tpg-note">{s["note"]}</p>\n'
    return '{% include titlepage-css.html %}\n\n' + md

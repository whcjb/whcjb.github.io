"""校对用：把 PDF 里含某句话的那一行裁成图，交给眼睛判。

输入一个 json 文件，每条 `{"vol":"v1|v2","probe":"一句话","out":"/tmp/x.png","lines":1}`。
probe 去 PDF 文本层里搜，所以要用**与 en_chapters 同一份 ABBYY OCR 的原串**；
搜不到就把串截短些，或换个锚点。lines 是往下多裁几行。

    python3 scripts/proofread/crop_line.py specs.json

裁出来的图直接 Read 看。页面影像是最终依据——多证人一致也可能一起读错。
"""
import sys, io, re
from pathlib import Path
import fitz
from PIL import Image, ImageOps
V = {'v1': 'propheciesisaiah01alexuoft.pdf', 'v2': 'propheciesisaiah02alexuoft.pdf'}
doc = {k: fitz.open(Path.home()/'Documents/论文/alexander'/v) for k, v in V.items()}
def shot(vol, probe, out, lines=1, lo=0, hi=None):
    d = doc[vol]
    hi = hi or d.page_count
    for i in range(lo, hi):
        rs = d[i].search_for(probe)
        if rs:
            pg, q = d[i], rs[0]
            h = q.y1 - q.y0
            pm = pg.get_pixmap(dpi=500, clip=fitz.Rect(pg.rect.x0+15, q.y0-3, pg.rect.x1-10, q.y0+h*lines+2))
            im = Image.open(io.BytesIO(pm.tobytes('png'))).convert('L')
            im = ImageOps.autocontrast(im, cutoff=1)
            im = im.resize((im.width*5, im.height*5), Image.LANCZOS)
            im.save(out)
            return i+1
    return None
if __name__ == '__main__':
    import json
    for spec in json.load(open(sys.argv[1])):
        p = shot(spec.get('vol','v1'), spec['probe'], spec['out'], spec.get('lines',1))
        print(spec['out'], '->pdf', p)

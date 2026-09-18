cd "$(dirname "$0")/.."
echo "══════ ① 逐词回退闸（§3.1，基准 HEAD）══════"
python3 scripts/qa_davenant_regress.py
echo
echo "══════ ② 附卷 + 索引结构闸（Gate A–G）══════"
python3 scripts/qa_davenant_appx.py 2>&1 | tail -30
echo
echo "══════ ③ 正文结构闸 ══════"
python3 scripts/qa_davenant.py 2>&1 | tail -12
echo
echo "══════ ④ 渲染层自检 ══════"
python3 - <<'PY'
import re, pathlib
bad = 0
for f in sorted(pathlib.Path('davenant/colossians').rglob('*.md')):
    if '/zh/' in str(f): continue
    t = f.read_text(encoding='utf-8')
    refs = set(re.findall(r'\[\^(\w+)\](?!:)', t)); defs = set(re.findall(r'^\[\^(\w+)\]:', t, re.M))
    m = []
    if refs - defs: m.append(f'引用无定义 {len(refs-defs)}')
    if defs - refs: m.append(f'定义无引用 {len(defs-refs)}')
    for tag in ('div', 'span', 'em', 'p', 'ul', 'ol', 'li'):
        if t.count(f'<{tag}') != t.count(f'</{tag}>'): m.append(f'<{tag}> 不配对')
    if '' in t or '' in t: m.append('私用码残留')
    ids = re.findall(r'id="([^"]+)"', t)
    if len(ids) != len(set(ids)): m.append('重复锚点 id')
    if m: print(f'  {f}: {m}'); bad += 1
print(f'结构有问题的页面：{bad}')
PY
echo
echo "══════ (4b) 花括号分析表 ══════"
python3 scripts/qa_davenant_brace.py
echo
echo "══════ (4c) 缩进块 ══════"
python3 scripts/qa_davenant_outline.py
echo
echo "══════ ⑤ 已识别错误类的残留普查 ══════"
python3 - <<'PY'
import re, pathlib
F = ([pathlib.Path(f'davenant/colossians/{n}.md') for n in (1,2,3,4)]
     + sorted(pathlib.Path('davenant/colossians/dissertation').glob('*.md'))
     + [pathlib.Path('davenant/colossians/gallican.md')]
     + sorted(pathlib.Path('davenant/colossians/indexes').glob('*.md')))
txt = '\n'.join(f.read_text(encoding='utf-8') for f in F)
CL = [('Jf/Jt/?f/[t', r'(?<![A-Za-z])(Jf|Jt|\?f|\[t|\[f|Js|\?s)[ .,]'),
      ('前导双引号',  r'[^=<]"[A-Z][a-z]{2,}'),
      ('功能词后多点', r'\b(of|that|may|in|to|the|is|was|it|he|since|which)\. [a-z]{2,}'),
      ('短功能词误读', r'[ >](ts|tt|tn|bv|aud|iu)[ ,.]'),
      ('] Cor 型',     r'[]|] (Cor|Epis|Thess|Tim|Pet|Kings)\.'),
      ('1/J 当 I',     r'(shall|will|should|would|may|if|that|when) [14JlY] [a-z]'),
      ('罗马数字误读', r'(Cor|Rev|Chap|Tim|lib|cap)\.? (in|ill|i1|iw|ti|vill)\. [0-9]'),
      ('rn→m',         r'(Horn|serin|Earn|eniinence|contempi)[ .,]'),
      ('// 当 ll',     r'[A-Za-z]//'),
      ('断词未合并',   r'[a-z]{3,}- [a-z]{2,}'),
      ('句点断词',     r'\b[a-z]{2,}\. [a-z]{2,}ing\b'),
      ('书眉泄漏',     r'(AN EXPOSITION [A-Z]{2}|EPISTLE TO T[HI][EI] COLOSS)'),
      ('卷号误读',     r'(?<![A-Za-z])(1I|Il|LI|IT|I1|Ll)\. *[0-9]'),
      ('人名粘连',     r'(?<![A-Za-z])(Heisan|Itisnot|Hehada|Forus|Paulacted|rendera)'),
      ('小型大写残',   r'(BurrrsoER|GnEVINCHOVIUS|AnETIUS|YrLopoamp|ExcrAwp|WirLraw|CaprTULA)')]
for name, rx in CL:
    n = len(re.findall(rx, txt))
    print(f'  {name:14} {n:5}' + ('' if n == 0 else '  ← 仍有残留'))
PY

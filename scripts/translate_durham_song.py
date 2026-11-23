#!/usr/bin/env python3
"""translate_durham_song.py —— 达拉谟《雅歌之钥》英文页 durham/songofsolomon/<页>.md → 中文 raw。

照 translate_owen_psalm130 的路子：质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用
translate_alexander_acts；短段附前后段英文；CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

英文页是 publish_durham_en.py 写出的 markdown，逐行处理：
  - 段落行（含 <p style…> 这类 HTML 行、书名页各行）→ 送模型，HTML 标签与 <!-- PAGE n --> 遮成占位符；
  - `# CHAP. N`、卷首各 H1、`## Verse(s) …`、`### BRIDE.` 这类结构行 → 程序按表译，不送模型；
  - `> **Vers. 5, 6.** …` 段首经文 → 程序按章节号填和合本，不送模型；
  - 锚点 div、页码注释、HTML 容器行 → 原样。
超长段按句切片（MAX_CHARS），译完在同一行里拼回。

缓存  durham_raw/song/zh_cache/<md5>.txt   ← 必须保留
输出  durham_raw/song/zh_chapters/<页>.md  ← 翻完 chmod 444
时刻  durham_raw/song/zh_meta.json         ← 每页译完的时刻（发布按页查表）

用法：python3 -u scripts/translate_durham_song.py --dry-run --all
      python3 -u scripts/translate_durham_song.py --section preface --resume      # 单路；自动发布
      python3 -u scripts/translate_durham_song.py --section 1 --limit 3           # 试译前 3 段，只打印不写出
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate_filibi as tf          # noqa: E402
import translate_alexander_acts as T   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'durham' / 'songofsolomon'
RAW = ROOT / 'durham_raw' / 'song'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'DURHAM_SONG::'
MAX_CHARS = 3200
SHORT_CTX = 300
MIN_FREE = 300 * 2**20
ORDER = ['preface', 'key', 'conclusions'] + [str(n) for n in range(1, 9)]

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'

SYSTEM = (
    "你是一位熟悉清教徒神学与改革宗教义的中文译者，正在翻译詹姆斯·达拉谟（James Durham, 1622–1658，"
    "苏格兰盟约派，格拉斯哥牧师）的《雅歌之钥》（Clavis Cantici, or An Exposition of the Song of Solomon，1668）。\n"
    "此书体例：先有总论（雅歌是圣经、不可按字面解、是寓意而非预表、主旨是基督与教会及信徒之间的相爱相交），"
    "再逐章逐节讲解。每节先「说明」经文（字义、比喻、说话的是谁），再列出由此学到的功课（Obs. 1. 2. 3.……）。"
    "雅歌里的说话人是新妇（教会与信徒）、新郎（基督）、耶路撒冷的众女子（外邦或软弱的认信者）。"
    "文风是十七世纪苏格兰讲章：拼写是当时的（spirituall / accesse / sheweth / doth / hath / ye / thir），"
    "长句套长句，多分号与括号插语。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系、分点层次不能丢，"
    "不得因为难读就删减从句或合并论点。不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表页码记号或排版标签，**必须原样逐个保留**，个数、先后都与原文一致\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。中文对应部分照样用 `*` 包，一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. 引用经文的原句一律照抄和合本措辞；达拉谟明说是原文字义或另一种译法时"
    "（in the Original / the word signifies / may be rendered 之类），按他的英文字面译，不换和合本。"
    "只给出处、没有引经文的，只译出处，不补经文。雅歌的称谓照和合本：my love → 我的佳偶；my beloved → 我的良人；"
    "my spouse → 我的新妇；my sister, my spouse → 我妹子，我新妇；my dove, my undefiled → 我的鸽子，我的完全人；"
    "daughters of Jerusalem → 耶路撒冷的众女子；the Song of Songs → 歌中的雅歌\n"
    "5. 经文出处：书卷名换和合本全称，章节写成阿拉伯数字加冒号（Psal. 45. 2. → 诗篇 45:2；Rev. 3. 20. → 启示录 3:20；"
    "1 Cor. 13. 13. → 哥林多前书 13:13；Chap. 5. 2. → 第 5 章 2 节；ver. 3. / vers. 3. → 第 3 节；ult. → 末节）\n"
    "6. 希腊文、拉丁文、希伯来文**逐字照抄，一个字母、一个重音符号都不许改**，**原文里没有的希腊文、希伯来文一个字母也不许添**；"
    "希腊词、希伯来词后用圆括号附中文译义；整句拉丁引文保留原文，后面括注中文大意\n"
    "7. `&c.` → ……（不作「等等」）；`i.e.` / `viz.` / `to wit` → 即；"
    "分点照原文层次：First / Secondly / Thirdly → 第一、第二、第三；1. 2. 照写；"
    "`Obs.` / `Observ.`（由经文得出的功课）→ 要点；`Ans.` → 答；`Quest.` / `Qu.` → 问；`Object.` / `Obj.` → 反驳；`Use` → 应用\n"
    "8. **凡音译出来的人名、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "俄利根（Origen）、伯尔纳（Bernard）、毕达哥拉斯（Pythagoras）。"
    "和合本里本来就有的圣经人名地名（所罗门、黎巴嫩、基达）不括注。英文原文没写的原名不要补，不要编\n"
    "9. 术语全书一律、互不撞词：Bride → 新妇；Bridegroom → 新郎；Spouse → 新妇；Christ → 基督；the Church → 教会；"
    "believer(s) → 信徒；professor(s) → 认信的人；hypocrite → 假冒为善的人；Ordinances → 典章；"
    "Minister(s) → 传道人；Watchmen → 守望的人；Allegory / allegorical → 寓意 / 寓意的；Type / typical → 预表 / 预表的；"
    "literal / properly → 字面的 / 按本义；Mystery → 奥秘；Scripture → 圣经；the Spirit / the Holy Ghost → 圣灵；"
    "Mediator → 中保；covenant → 约；grace → 恩典；faith → 信心；love → 爱；fellowship / communion → 相交；"
    "presence → 同在；sensible presence / sense → 可感受的同在 / 感受；desertion → 离弃；withdrawing → 隐退；"
    "frame → 心境；case → 光景；exercise → 操练；tentation / temptation → 试探；backsliding → 退后；"
    "security → 安逸（属灵的麻木）；corruption → 败坏；mortification → 治死；justification → 称义；"
    "sanctification → 成圣；assurance → 确据；from everlasting → 从亘古（「亘」不可写作「亡」）\n"
    "10. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "11. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的外文引文除外）\n"
    "12. 引号一律用弯引号“”（嵌套时内层用‘’），不要用直角引号「」\n"
    "13. 只有一个短语的标题、署名、书名页上的一行，译成简短的标题式短语，标点照原文"
)

# ── 程序译的结构行 ────────────────────────────────────────────────
H1 = {
    'TO THE CHRISTIAN READER · JOHN OWEN': '致基督徒读者（约翰·欧文）',
    'TO THE CHRISTIAN READER': '致基督徒读者',
    'CLAVIS CANTICI: A KEY OF THE SONG': '雅歌之钥：开启此歌的钥匙',
}
SPEAKER = {
    'BRIDE': '新妇', 'BRIDE.': '新妇', 'BRIDEGROOM.': '新郎', 'CHRIST.': '基督',
    'DAUGHTERS.': '众女子', 'Daughters of Ierusalem.': '耶路撒冷的众女子',
    '2 Part. CHRISTS Words.': '第二部分　基督的话',
    'Part 1. CHRISTS Words.': '第一部分　基督的话', 'Part 2. BRIDES Words.': '第二部分　新妇的话',
    'Part 3. BRIDES Words.': '第三部分　新妇的话', 'Part 4. CHRISTS Words.': '第四部分　基督的话',
    'Part 5. BRIDES Words.': '第五部分　新妇的话',
}
RE_VERSE_H = re.compile(r'^## Verses? ([\d–]+) \((\d+):([\d–]+)\)$')
RE_EPI = re.compile(r'^> \*\*Vers?\.\s*([^*]+?)\*\*\s*(.*)$')
# 书名页的书名两行手排（模型译成「又名，讲解，所罗门的雅歌。」，断行处理不好）
MANUAL = {
    '<p style="font-size:30px;letter-spacing:.06em;margin:0;">Clavis Cantici:</p>':
        '<p style="font-size:30px;letter-spacing:.06em;margin:0;">雅歌之钥</p>',
    '<p style="font-size:15px;letter-spacing:.12em;margin:6px 0 0;">OR, AN<br>EXPOSITION OF THE<br>SONG of SOLOMON.</p>':
        '<p style="font-size:15px;letter-spacing:.12em;margin:6px 0 0;">又名<br>所罗门之歌<br>讲解</p>',
}
RE_KEEP = re.compile(r'^(?:<div class="commentary-anchor"[^>]*></div>|<!-- PAGE \d+ -->|</?div[^>]*>|<hr[^>]*>|)$')


class DiskLow(RuntimeError):
    pass


def check_disk():
    free = shutil.disk_usage(RAW).free
    if free < MIN_FREE:
        raise DiskLow(f'磁盘剩余 {free / 2**20:.0f} MB < {MIN_FREE / 2**20:.0f} MB')


_CUV = None


def cuv(ch, vs):
    global _CUV
    if _CUV is None:
        _CUV = json.load(open(ROOT / 'assets' / 'cuv.json', encoding='utf-8'))['22']
    return ''.join(_CUV[str(ch)][str(v)].replace('　', '') for v in vs)


def epigraph_zh(label, ch, en=''):
    """`Vers. 5, 6.` → 第 5、6 节 + 和合本全文；认不出返回 None（交给模型）。

    两种特例：原书把一节拆成前后两半引（6:5，英文以 `—` 收尾／起头）→ 和合本按句号切开取对应半；
    只写说话人不引经文的（7:1–3 `BRIDEGROOM.`，后面再逐节分引）→ 只译说话人。"""
    nums = [int(x) for x in re.findall(r'\d+', label)]
    if not nums or ch is None or re.search(r'[A-Za-z]', re.sub(r'(?i)\b(?:and|to)\b', '', label)):
        return None
    if len(nums) == 2 and re.search(r'\d\s*[–-]\s*\d', label):
        nums = list(range(nums[0], nums[1] + 1))
    lab = f'> **第 {"、".join(map(str, nums))} 节**　'
    if en.strip() in SPEAKER:
        return lab + SPEAKER[en.strip()]
    try:
        text = cuv(ch, nums)
    except KeyError:
        return None
    e = re.sub(r'\*', '', en).strip()
    if len(nums) == 1 and (e.endswith(('—', ':—')) or e.startswith('—')):
        sents = [x + '。' for x in text.rstrip('。').split('。')]
        if len(sents) == 2:
            text = sents[1] if e.startswith('—') else sents[0]
    return lab + text


def split_long(b):
    if len(b) <= MAX_CHARS:
        return [b]
    pieces = re.split(r'([.?!;:][”"’)]?)\s+(?=[“"‘A-Z(*0-9⟦])', b)
    sents = [pieces[i] + (pieces[i + 1] if i + 1 < len(pieces) else '') for i in range(0, len(pieces), 2)]
    out, cur = [], ''
    for s in sents:
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            out.append(cur); cur = s
        else:
            cur = (cur + ' ' + s).strip()
    if cur:
        out.append(cur)
    return out


def blocks(slug):
    """→ [(kind, text)]：text 送模型（同一行切片后各占一项，以 join 标记拼回）/ keep 原样。"""
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].lstrip('\n')
    out, ch = [], None
    for k, line in enumerate(t.split('\n')):
        if k:
            out.append(('keep', '\n'))
        s = line.strip()
        m = re.match(r'^# CHAP\. (\d+)$', s)
        if m:
            ch = int(m.group(1)); out.append(('keep', f'# 雅歌第 {ch} 章')); continue
        if s.startswith('# ') and s[2:] in H1:
            out.append(('keep', '# ' + H1[s[2:]])); continue
        m = RE_VERSE_H.match(s)
        if m:
            out.append(('keep', f'## 第 {m.group(1)} 节（{m.group(2)}:{m.group(3)}）')); continue
        if s.startswith('### ') and s[4:] in SPEAKER:
            out.append(('keep', '### ' + SPEAKER[s[4:]])); continue
        m = RE_EPI.match(s)
        if m:
            zh = epigraph_zh(m.group(1), ch, m.group(2))
            if zh:
                out.append(('keep', zh)); continue
        if s in MANUAL:
            out.append(('keep', MANUAL[s])); continue
        txt = T.RE_ANY.sub('', s)
        # 已是中文的行（发布时写进去的编者说明，夹着 EEBO-TCP 这类缩写）原样保留
        if len(re.findall(r'[\u4e00-\u9fff]', txt)) > len(re.findall(r'[A-Za-z]', txt)):
            out.append(('keep', line)); continue
        if RE_KEEP.match(s) or not re.search(r'[A-Za-z]{2}', txt):
            out.append(('keep', line)); continue
        # 送模型：标题前缀（#…）、引用前缀（> ）留在外面
        pm = re.match(r'^(#{1,4} |> )', line)
        pre = pm.group(1) if pm else ''
        if pre:
            out.append(('keep', pre))
        for j, piece in enumerate(split_long(line[len(pre):])):
            if j:
                out.append(('keep', ' '))
            out.append(('text', piece))
    return out


def ctx_block(ctx):
    if not ctx:
        return ''
    return ("【上下文】下面是这段前后的原文，只帮助理解这段在说什么，**不要翻译、不要输出、不要评论**：\n"
            f"<上下文>\n{ctx}\n</上下文>\n\n【要翻译的这段】\n")


def translate_one(text, resume, label, ctx=''):
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not T.structural_diff(text, cached) or key in T.accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {T.structural_diff(text, cached)[:90]}', flush=True)
    base = ("把下面这段达拉谟《雅歌之钥》的十七世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
            "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    check_disk()
    raw = tf.call_claude(base + ctx_block(ctx) + text, timeout=900, label=label)
    out = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(raw)), text), text, label)
    diff = T.structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        with T.BAD_LOG.open('a', encoding='utf-8') as fh:
            fh.write(f'[{label}·first] {diff[:120]}\n  RAW: {raw[:400]!r}\n')
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** ⟦N⟧ 占位符（个数与先后都要对上）；"
               "希腊文逐字照抄、原文没有的不许添；**不得把任何英文词原样留在中文句子里**。"
               "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
        for k in (1, 2):
            out2 = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(
                tf.call_claude(fix + ctx_block(ctx) + text, timeout=900, label=f'{label}·retry{k}'))), text),
                text, f'{label}·retry{k}')
            if not T.structural_diff(text, out2):
                out = out2
                break
            if not T.is_severe(T.structural_diff(text, out2)) or T.is_severe(diff):
                out, diff = out2 or out, T.structural_diff(text, out2 or out)
        else:
            with T.BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {T.structural_diff(text, out)}\n  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')
            if T.is_severe(T.structural_diff(text, out)):
                raise T.SevereTranslation(f'{label}: {T.structural_diff(text, out)[:120]}')
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out


def plain(b):
    return re.sub(r'\s+', ' ', T.RE_ANY.sub(' ', b)).strip()


def run_section(slug, resume, dry, publish, limit=0):
    bl = blocks(slug)
    idx = [i for i, (k, _) in enumerate(bl) if k == 'text']
    todo = idx[:limit] if limit else idx
    keys = {tf.md5key(KEY_NS + T.mask(bl[i][1])[0]) for i in todo}
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    chars = sum(len(bl[i][1]) for i in todo)
    print(f'[{slug}] 需翻译 {len(todo)} 段，已缓存 {hit}，待调用 {len(keys) - hit}，约 {chars:,} 字符', flush=True)
    if dry:
        return len(keys) - hit, sum(len(bl[i][1]) for i in todo
                                    if not (CACHE / f'{tf.md5key(KEY_NS + T.mask(bl[i][1])[0])}.txt').exists())
    done = {}
    for c, i in enumerate(todo, 1):
        b = bl[i][1]
        ctx = ''
        if len(plain(b)) < SHORT_CTX:
            p = idx.index(i)
            prev = plain(bl[idx[p - 1]][1])[-600:] if p > 0 else ''
            nxt = plain(bl[idx[p + 1]][1])[:600] if p + 1 < len(idx) else ''
            ctx = (('【前】' + prev + '\n') if prev else '') + (('【后】' + nxt) if nxt else '')
        masked, tags = T.mask(b)
        done[i] = T.unmask(translate_one(masked, resume, f'{slug}#{c}', ctx), tags)
        if c % 10 == 0:
            print(f'  [{slug}] {c}/{len(todo)} 段', flush=True)
    if limit:
        for i in sorted(done):
            print('-----', bl[i][1][:300], '\n=====', done[i][:700])
        return
    body = ''.join(done.get(i, t) for i, (k, t) in enumerate(bl))
    body, missing = T.annotate_terms(body, (SRC / f'{slug}.md').read_text(encoding='utf-8'))
    if missing:
        print(f'    [names] {slug}: 英文源里有 {missing}，译文里没有原名、也找不到已知中文写法，未自动补', flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{slug}.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body.rstrip('\n') + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum((CACHE / f'{k}.txt').exists() for k in keys)
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    if slug not in meta or after > hit or not resume:
        meta[slug] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(slug)


def autopublish(slug):
    pub = ROOT / 'scripts' / 'publish_durham_song_zh.py'
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['durham/songofsolomon', 'durham_raw/song/zh_chapters', 'durham_raw/song/zh_cache',
                 'durham_raw/song/zh_meta.json', 'durham_raw/song/zh_translate_issues.log',
                 'durham_raw/song/zh_italic_notes.log', '_data/commentaries.yml', '_data/compare_sources.yml',
                 'commentaries/songofsolomon/index.html']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        name = {'preface': '书名页与序', 'key': '总论', 'conclusions': '结论'}.get(slug, f'第 {slug} 章')
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(durham): 雅歌之钥中译 · {name}（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', '--', *paths],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT, capture_output=True, text=True, timeout=300)
            if ps.returncode != 0:          # 别的会话刚推过：先 rebase 再推一次
                subprocess.run(['git', 'pull', '-q', '--rebase', '--autostash', 'origin', 'master'], cwd=ROOT,
                               capture_output=True, text=True, timeout=300)
                ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT, capture_output=True, text=True, timeout=300)
            print('    [autopublish] 已提交' + ('并推送' if ps.returncode == 0 else f'，推送失败 {ps.stderr[:160]}'), flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-publish', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='试译：只译前 N 段，只打印不写出')
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    secs = ORDER if a.all else a.section
    if not secs:
        ap.error('--section 或 --all')
    tot_calls = tot_chars = 0
    for s in secs:
        try:
            r = run_section(s, a.resume, a.dry_run, not a.no_publish, a.limit)
            if a.dry_run and r:
                tot_calls += r[0]; tot_chars += r[1]
        except DiskLow as e:
            print(f'⛔ 磁盘空间不足，中止：{e}', flush=True)
            sys.exit(43)
        except T.SevereTranslation as e:
            print(f'⛔ [{s}] 有段落重试后仍不合格，本篇不写出、不发布：{e}', flush=True)
            sys.exit(3)
        except RuntimeError as e:
            if 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)
            raise
    if a.dry_run:
        print(f'合计待调用 {tot_calls} 段，约 {tot_chars:,} 字符', flush=True)


if __name__ == '__main__':
    main()

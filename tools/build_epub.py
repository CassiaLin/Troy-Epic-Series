#!/usr/bin/env python3
# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""Build the Troy Epic Series EPUB 3 books from the repository files.
Volumes 01–05: <冊>/好讀版.md (part 1 + front matter + appendices) and <冊>/雙語校對版.md (part 2, line-by-line);
volume 90: 90_奧德賽的女作者/中文好讀版_附原文.md + images/. Covers: covers/NN_cover.png (converted to JPEG).
Output: build/TroyEpic_<NN>_<Name>_zh-TW_<tag>.epub (deterministic zip) + build/coverage.json
(text-coverage check: every character of the Markdown sources must appear in the XHTML).
usage (repository root): python tools/build_epub.py --repo [--tag v2.0.0] [01 02 ... 90]
(without --repo the script reads an editing-time working layout and is not meant for the repository.)
Only the Python standard library + Pillow (cover JPEG).
"""
import html, io, json, os, re, sys, uuid, zipfile

ROOT = 'work/v2'
SRC = f'{ROOT}/src'
OUT = f'{ROOT}/epub/out'
VER = 'v2.0.0'
TAG = 'v2.0.0'
MODIFIED = '2026-11-08T00:00:00Z'
CN = '一二三四五六七八九十'
GRK = r'Ͱ-Ͽἀ-῿'
GRUN = re.compile(rf'[{GRK}]+(?:[\s,.;:·᾽’ʼ\'\-—]*[{GRK}]+)*')

VOLS = {
    '01': dict(key='01_Iliad', name='Iliad', title='伊里亞德', orig='Ἰλιάς', author='荷馬', src_lang='grc', units=24, cover='01_cover.png'),
    '02': dict(key='02_Posthomerica', name='Posthomerica', title='荷馬續篇', orig='Τὰ μεθ᾽ Ὅμηρον', author='士麥那的昆圖斯', src_lang='grc', units=14, cover='02_cover.png'),
    '03': dict(key='03_Odyssey', name='Odyssey', title='奧德賽', orig='Ὀδύσσεια', author='荷馬', src_lang='grc', units=24, cover='03_cover.png'),
    '04': dict(key='04_Aeneid', name='Aeneid', title='埃涅阿斯紀', orig='Aeneis', author='維吉爾', src_lang='la', units=12, cover='04_cover.png'),
    '05': dict(key='05_Fragments', name='Epic_Cycle', title='史詩殘篇集', orig='Κυκλικὰ ἔπη', author='古代佚名作者群', src_lang='grc', units=6, cover='05_cover.png'),
    '90': dict(key='90_Authoress', name='Odyssey_Authoress', title='奧德賽的女作者', orig='The Authoress of the Odyssey', author='塞繆爾．巴特勒', src_lang='en', units=0, cover='90_cover.png'),
}


def cnum(n):
    if n < 10:
        return CN[n - 1]
    if n == 10:
        return '十'
    if n < 20:
        return '十' + CN[n - 11]
    return CN[n // 10 - 1] + '十' + (CN[n % 10 - 1] if n % 10 else '')


CNUM = {cnum(i): i for i in range(1, 40)}


# ---------------------------------------------------------------- inline / block markdown
def lang_wrap(h, default=None):
    """wrap Greek runs (outside tags) in <span lang="grc">."""
    if default == 'grc':
        return h
    parts = re.split(r'(<[^>]+>)', h)
    for i, p in enumerate(parts):
        if p and not p.startswith('<'):
            parts[i] = GRUN.sub(lambda m: f'<span lang="grc" xml:lang="grc">{m.group(0)}</span>', p)
    return ''.join(parts)


class Ctx:
    """per-xhtml-file context: footnotes, ids."""

    def __init__(self, fname, fn_file=None):
        self.fname = fname
        self.fn_file = fn_file or {}   # label -> file where its definition is rendered
        self.refcount = {}
        self.num = {}

    def ref(self, label):
        k = self.refcount.get(label, 0) + 1
        self.refcount[label] = k
        if label not in self.num:
            self.num[label] = len(self.num) + 1
        rid = f'r-{slug(label)}' + (f'-{k}' if k > 1 else '')
        tgt = self.fn_file.get(label, self.fname)
        href = (f'{tgt}' if tgt != self.fname else '') + f'#n-{slug(label)}'
        return f'<a class="nref" id="{rid}" href="{href}" epub:type="noteref">[{self.num[label]}]</a>'


def slug(s):
    return re.sub(r'[^0-9A-Za-z_-]', lambda m: f'_{ord(m.group(0)):x}', s)


def inline(s, ctx=None, default=None):
    s = html.escape(s, quote=False)
    s = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', lambda m: f'<img src="{m.group(2)}" alt="{m.group(1)}"/>', s)
    s = re.sub(r'(?<!!)\[([^\]^][^\]]*)\]\(([^)\s]+)\)', r'\1', s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)', r'<em>\1</em>', s)
    if ctx is not None:
        s = re.sub(r'\[\^([^\]\s]+)\]', lambda m: ctx.ref(m.group(1)), s)
    return lang_wrap(s, default)


def join_lines(lines):
    out = ''
    for i, l in enumerate(lines):
        t = l.rstrip()
        brk = l.endswith('  ')
        if i and out and not out.endswith('\n'):
            a, b = out[-1], t[:1]
            wide = lambda ch: ch and ('⺀' <= ch <= '鿿' or '＀' <= ch <= '￯' or '　' <= ch <= '〿')
            out += '' if (wide(a) or wide(b)) else ' '
        out += t
        if brk and i < len(lines) - 1:
            out += '\n'
    return out


def para(text, ctx, cls=None, default=None, pid=None):
    h = '<br/>'.join(inline(x, ctx, default) for x in text.split('\n'))
    a = (f' id="{pid}"' if pid else '') + (f' class="{cls}"' if cls else '')
    g = sum(1 for c in text if re.match(f'[{GRK}]', c))
    if default is None and g > 0.5 * max(1, len(re.sub(r'\W', '', text))):
        a += ' lang="grc" xml:lang="grc"'
        h = re.sub(r'<span lang="grc" xml:lang="grc">(.*?)</span>', r'\1', h)
    return f'<p{a}>{h}</p>'


def md_blocks(lines, ctx, hshift=0, default=None, anchors=True):
    """markdown lines -> list of xhtml blocks. footnote definitions are returned separately."""
    out, defs = [], []
    i, n = 0, len(lines)
    pending_id = None
    while i < n:
        l = lines[i]
        s = l.strip()
        m = re.match(r'^<!--\s*(U\d{4})\s*-->$', s)
        if m:
            pending_id = m.group(1)
            i += 1
            continue
        if not s or s in ('---', '\\newpage', '\\pagebreak') or s.startswith('<!--'):
            i += 1
            continue
        m = re.match(r'^\[\^([^\]\s]+)\]:\s*(.*)$', l)
        if m:
            body = [m.group(2)]
            i += 1
            while i < n and (lines[i].startswith('    ') or (not lines[i].strip() and i + 1 < n and lines[i + 1].startswith('    '))):
                body.append(lines[i][4:] if lines[i].strip() else '')
                i += 1
            ps = '\n'.join(body).split('\n\n')
            inner = ''.join(f'<p>{inline(join_lines(p.split(chr(10))), ctx, default)}</p>' for p in ps if p.strip())
            lab = m.group(1)
            aid = f' id="{pending_id}"' if pending_id else ''
            pending_id = None
            blk = f'<aside{aid} epub:type="footnote" class="fn" id="n-{slug(lab)}"><p class="fnlab"><a class="gen" href="#r-{slug(lab)}">註 {html.escape(lab)}</a></p>{inner}</aside>'
            blk = blk.replace(f'<aside id="{pending_id}" ', '<aside ') if False else blk
            if aid:
                blk = blk.replace(f'<aside{aid} ', '<aside ').replace('<p class="fnlab">', f'<p class="fnlab"{aid}>', 1)
            out.append(blk)
            defs.append(lab)
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', l)
        if m:
            lv = min(6, max(1, len(m.group(1)) - hshift))
            pid = f' id="{pending_id}"' if pending_id else ''
            pending_id = None
            out.append(f'<h{lv}{pid}>{inline(m.group(2).strip(), ctx, default)}</h{lv}>')
            i += 1
            continue
        if s.startswith('|'):
            rows = []
            while i < n and lines[i].strip().startswith('|'):
                rows.append(lines[i].strip())
                i += 1
            cells = [[c.strip() for c in r.strip('|').split('|')] for r in rows]
            body = [r for r in cells if not all(re.fullmatch(r':?-{2,}:?', c) for c in r if c)]
            hdr = len(cells) > 1 and all(re.fullmatch(r':?-{2,}:?', c) for c in cells[1] if c)
            t = '<table>'
            for k, r in enumerate(body):
                tag = 'th' if (hdr and k == 0) else 'td'
                t += '<tr>' + ''.join(f'<{tag}>{inline(c, ctx, default)}</{tag}>' for c in r) + '</tr>'
            out.append(t + '</table>')
            continue
        if re.match(r'^[-*] ', s) and not re.match(r'^\*[^ ]', s):
            items = []
            while i < n and re.match(r'^\s*[-*] ', lines[i]):
                items.append(re.sub(r'^\s*[-*] ', '', lines[i]))
                i += 1
                while i < n and lines[i].startswith('  ') and lines[i].strip() and not re.match(r'^\s*[-*] ', lines[i]):
                    items[-1] += lines[i].strip()
                    i += 1
            out.append('<ul>' + ''.join(f'<li>{inline(x, ctx, default)}</li>' for x in items) + '</ul>')
            continue
        if s.startswith('>'):
            q = []
            while i < n and lines[i].strip().startswith('>'):
                q.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            inner, d2 = md_blocks(q, ctx, hshift, default)
            defs += d2
            pid = f' id="{pending_id}"' if pending_id else ''
            pending_id = None
            out.append(f'<blockquote{pid}>' + ''.join(inner) + '</blockquote>')
            continue
        m = re.match(r'^!\[([^\]]*)\]\(([^)\s]+)\)\s*$', s)
        if m:
            pid = f' id="{pending_id}"' if pending_id else ''
            pending_id = None
            out.append(f'<figure{pid}><img src="{m.group(2)}" alt="{html.escape(m.group(1), quote=True)}"/><figcaption>{inline(m.group(1), ctx, default)}</figcaption></figure>')
            i += 1
            continue
        p = []
        while i < n and lines[i].strip() and not re.match(r'^(#{1,6}\s|\||>|!\[|<!--|\[\^[^\]\s]+\]:)', lines[i].strip()) and not re.match(r'^[-*] ', lines[i].strip()) and lines[i].strip() not in ('---', '\\newpage', '\\pagebreak'):
            p.append(lines[i])
            i += 1
        if not p:   # safety: unknown single line
            p = [lines[i]]
            i += 1
        out.append(para(join_lines(p), ctx, default=default, pid=pending_id))
        pending_id = None
    return out, defs


# ---------------------------------------------------------------- xhtml / packaging
CSS = '''@charset "utf-8";
body { font-family: "Noto Serif CJK TC", "Source Han Serif TC", "Noto Serif TC", serif; line-height: 1.8; margin: 0 4%; text-align: justify; }
h1 { font-size: 1.45em; line-height: 1.4; margin: 1.2em 0 0.9em; text-align: center; }
h2 { font-size: 1.2em; line-height: 1.45; margin: 1.3em 0 0.6em; }
h3 { font-size: 1.05em; margin: 1.1em 0 0.4em; }
h4, h5, h6 { font-size: 1em; margin: 1em 0 0.3em; }
p { margin: 0 0 0.75em; text-indent: 0; }
[lang="grc"] { font-family: "Noto Serif", "Gentium Plus", "New Athena Unicode", serif; }
[lang="la"], [lang="en"] { font-family: "Noto Serif", "Georgia", serif; }
.lp { margin: 0 0 0.55em; }
.lp p { margin: 0; }
.lp .o { font-size: 0.97em; line-height: 1.5; }
.lp .t { padding-left: 2.2em; line-height: 1.65; }
.ln { display: inline-block; min-width: 2.2em; font-size: 0.72em; opacity: 0.6; }
.meta { font-size: 0.9em; opacity: 0.85; border-left: 2px solid; padding-left: 0.8em; margin: 0.6em 0 1em; }
.xlink { text-align: center; font-size: 0.85em; margin: 0.4em 0 1.2em; }
.nref { font-size: 0.75em; vertical-align: super; line-height: 0; text-decoration: none; }
aside.fn { font-size: 0.88em; margin: 0.4em 0 0.8em; padding-top: 0.2em; }
aside.fn p { margin: 0 0 0.3em; }
.fnlab { font-weight: bold; }
.footnotes { border-top: 1px solid; margin-top: 2em; padding-top: 0.5em; }
table { border-collapse: collapse; width: 100%; margin: 0.6em 0 1em; font-size: 0.92em; }
td, th { border-bottom: 1px solid; padding: 0.3em 0.4em; vertical-align: top; text-align: left; }
ul { padding-left: 1.4em; margin: 0.4em 0 1em; }
li { margin: 0 0 0.35em; }
blockquote { margin: 0.6em 0 1em 1.5em; }
figure { margin: 1em 0; text-align: center; }
figure img { max-width: 100%; max-height: 90vh; }
figcaption { font-size: 0.88em; margin-top: 0.4em; }
.titlepage { text-align: center; margin-top: 18%; }
.titlepage .series { font-size: 0.95em; letter-spacing: 0.1em; }
.titlepage .main { font-size: 2em; margin: 0.8em 0 0.3em; }
.titlepage .orig { font-size: 1.2em; margin-bottom: 1.2em; }
.titlepage .sub, .titlepage .author, .titlepage .ver { margin: 0.4em 0; }
.part { text-align: center; margin-top: 30%; }
.part h1 { font-size: 1.7em; }
.part p { font-size: 0.9em; }
.cover { margin: 0; padding: 0; text-align: center; }
.cover img { max-width: 100%; max-height: 100vh; }
nav ol { list-style: none; padding-left: 1.2em; }
'''


def page(title, body, lang='zh-Hant-TW', cls=None, epub_type=None):
    b = f' class="{cls}"' if cls else ''
    sec = f'<section epub:type="{epub_type}">' if epub_type else '<section>'
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">\n'
            f'<head><meta charset="utf-8"/><title>{html.escape(title)}</title><link rel="stylesheet" type="text/css" href="css/book.css"/></head>\n'
            f'<body{b}>{sec}\n{body}\n</section></body></html>\n')


class Book:
    def __init__(self, vol):
        self.v = vol
        self.c = VOLS[vol]
        self.files = []        # (id, href, title, xhtml, toc_level or None, spine linear)
        self.images = []       # (href, bytes, media)
        self.cover_jpg = None
        self.coverage = []     # (file, md_sig_len, xhtml_sig_len, ok)

    def add(self, href, title, xhtml, toc=1, sig_src=None):
        fid = 'x' + re.sub(r'[^0-9A-Za-z]', '_', href[:-6])
        self.files.append((fid, href, title, xhtml, toc))
        if sig_src is not None:
            a, b = sig(sig_src), sig_xhtml(xhtml)
            self.coverage.append((href, len(a), len(b), a == b))

    def write(self, out):
        c = self.c
        uid = uuid.uuid5(uuid.NAMESPACE_URL, f'https://github.com/CassiaLin/Troy-Epic-Series/{VER}/{self.v}')
        man, spine = [], []
        man.append('<item id="css" href="css/book.css" media-type="text/css"/>')
        man.append('<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>')
        man.append('<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>')
        man.append('<item id="cover-image" href="images/cover-epub.jpg" media-type="image/jpeg" properties="cover-image"/>')
        for k, (href, data, mt) in enumerate(self.images):
            man.append(f'<item id="img{k}" href="{href}" media-type="{mt}"/>')
        for fid, href, title, x, toc in self.files:
            props = ' properties="svg"' if '<svg' in x else ''
            man.append(f'<item id="{fid}" href="{href}" media-type="application/xhtml+xml"{props}/>')
            spine.append(f'<itemref idref="{fid}"/>')
            if href == 'titlepage.xhtml':
                spine.append('<itemref idref="nav"/>')
        coll = '' if self.v == '90' else ''
        meta = f'''<dc:identifier id="pub-id">urn:uuid:{uid}</dc:identifier>
<dc:title id="t1">{html.escape(c['title'])}</dc:title>
<meta refines="#t1" property="title-type">main</meta>
<dc:creator id="cr">{html.escape(c['author'])}</dc:creator>
<meta refines="#cr" property="role" scheme="marc:relators">aut</meta>
<dc:contributor id="tr">特洛伊史詩叢書</dc:contributor>
<meta refines="#tr" property="role" scheme="marc:relators">trl</meta>
<dc:language>zh-Hant-TW</dc:language>
<dc:publisher>特洛伊史詩叢書</dc:publisher>
<dc:date>2026-11-08</dc:date>
<dc:rights>{html.escape(self.rights())}</dc:rights>
<meta property="dcterms:modified">{MODIFIED}</meta>
<meta id="series" property="belongs-to-collection">特洛伊史詩叢書</meta>
<meta refines="#series" property="collection-type">series</meta>
<meta refines="#series" property="group-position">{int(self.v)}</meta>
<meta name="cover" content="cover-image"/>'''
        opf = f'''<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="zh-Hant-TW">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
{meta}
</metadata>
<manifest>
{chr(10).join(man)}
</manifest>
<spine toc="ncx">
{chr(10).join(spine)}
</spine>
</package>
'''
        nav, ncx = self.navs(uid)
        z = zipfile.ZipFile(out, 'w')

        def w(name, data, comp=zipfile.ZIP_DEFLATED):
            zi = zipfile.ZipInfo(name, date_time=(2026, 11, 8, 0, 0, 0))
            zi.compress_type = comp
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
        w('mimetype', 'application/epub+zip', zipfile.ZIP_STORED)
        w('META-INF/container.xml', '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>\n')
        w('OEBPS/content.opf', opf)
        w('OEBPS/nav.xhtml', nav)
        w('OEBPS/toc.ncx', ncx)
        w('OEBPS/css/book.css', CSS)
        w('OEBPS/images/cover-epub.jpg', self.cover_jpg)
        for href, data, mt in self.images:
            w('OEBPS/' + href, data)
        for fid, href, title, x, toc in self.files:
            w('OEBPS/' + href, x)
        z.close()

    def rights(self):
        if self.v in ('01', '02', '03', '04'):
            return '第一部中文好讀版、書前、附錄與編輯文字：CC BY-NC-SA 4.0；第二部原文逐行對照：CC BY-SA 4.0（原文取自 Perseus Digital Library，CC BY-SA 4.0）；封面由 AI 生成，本叢書就封面所享有的權利（如有）依 CC BY-NC-SA 4.0 授權。'
        if self.v == '05':
            return '全書：CC BY-NC-SA 4.0；所收希臘文殘篇依據的校訂本屬公版；封面由 AI 生成，本叢書就封面所享有的權利（如有）依 CC BY-NC-SA 4.0 授權。'
        return '中文譯文與編輯文字：CC BY-NC-SA 4.0；英文原文與原書圖版屬公版；封面由 AI 生成，本叢書就封面所享有的權利（如有）依 CC BY-NC-SA 4.0 授權。'

    def navs(self, uid):
        items = [(t, h, lv) for _, h, t, _, lv in self.files if lv]
        # nested ol from levels 1/2
        nav = '<ol>'
        open2 = False
        for k, (t, h, lv) in enumerate(items):
            if lv == 1:
                if open2:
                    nav += '</ol></li>'
                    open2 = False
                nxt = items[k + 1][2] if k + 1 < len(items) else 1
                if nxt == 2:
                    nav += f'<li><a href="{h}">{html.escape(t)}</a><ol>'
                    open2 = True
                else:
                    nav += f'<li><a href="{h}">{html.escape(t)}</a></li>'
            else:
                nav += f'<li><a href="{h}">{html.escape(t)}</a></li>'
        if open2:
            nav += '</ol></li>'
        nav += '</ol>'
        first_body = next(h for _, h, t, _, lv in self.files if h.startswith(('r', 'c')) and h[1:3].isdigit()) if any(h.startswith(('r', 'c')) and h[1:3].isdigit() for _, h, *_ in self.files) else self.files[1][1]
        land = f'<nav epub:type="landmarks" hidden="hidden"><h2>導覽</h2><ol><li><a epub:type="cover" href="cover.xhtml">封面</a></li><li><a epub:type="titlepage" href="titlepage.xhtml">書名頁</a></li><li><a epub:type="toc" href="nav.xhtml">目錄</a></li><li><a epub:type="bodymatter" href="{first_body}">正文</a></li></ol></nav>'
        navx = ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-Hant-TW" xml:lang="zh-Hant-TW">'
                f'<head><meta charset="utf-8"/><title>目錄</title><link rel="stylesheet" type="text/css" href="css/book.css"/></head><body><nav epub:type="toc" id="toc"><h1>目錄</h1>{nav}</nav>{land}</body></html>\n')
        pts, k = [], 0
        stack = False
        for t, h, lv in items:
            k += 1
            pt = f'<navPoint id="np{k}" playOrder="{k}"><navLabel><text>{html.escape(t)}</text></navLabel><content src="{h}"/>'
            if lv == 1:
                if stack:
                    pts.append('</navPoint>')
                pts.append(pt)
                stack = True
            else:
                pts.append(pt + '</navPoint>')
        if stack:
            pts.append('</navPoint>')
        ncx = (f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1"><head><meta name="dtb:uid" content="urn:uuid:{uid}"/>'
               f'<meta name="dtb:depth" content="2"/><meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>'
               f'<docTitle><text>{html.escape(self.c["title"])}</text></docTitle><navMap>{"".join(pts)}</navMap></ncx>\n')
        return navx, ncx


# ---------------------------------------------------------------- coverage signatures
def sig(md_text):
    t = re.sub(r'<!--.*?-->', '', md_text)
    t = re.sub(r'\[\^[^\]\s]+\]:?', '', t)
    t = re.sub(r'!\[([^\]]*)\]\([^)]*\)', r'\1\1', t)   # alt + figcaption
    t = re.sub(r'\(([^)\s]*\.(?:jpg|png|xhtml)[^)\s]*)\)', '', t)
    return re.sub(rf'[^0-9A-Za-z一-鿿㐀-䶿{GRK}À-ɏ]', '', t)


def sig_xhtml(x):
    b = x.split('<body', 1)[1]
    b = re.sub(r'<(a|p|div|span)[^>]*class="(?:gen|xlink|nref|ln|fnlab)[^"]*"[^>]*>.*?</\1>', '', b, flags=re.S)
    b = re.sub(r'<img [^>]*alt="([^"]*)"[^>]*/>', lambda m: html.unescape(m.group(1)), b)
    b = re.sub(r'<[^>]+>', '', b)
    b = html.unescape(b)
    return re.sub(rf'[^0-9A-Za-z一-鿿㐀-䶿{GRK}À-ɏ]', '', b)


def read(p):
    return open(p, encoding='utf-8').read()


def strip_title_prefix(h, title):
    return re.sub(rf'^《{re.escape(title)}》\s*', '', h).strip()


# ---------------------------------------------------------------- bilingual parsing (01–05)
DROP_META = re.compile(r'^\s*>\s*(?:\*\*)?(?:SHA256|底本|參考譯本|叢書|行號依|雙語逐行對照版｜)')  # header lines only (prefix match)
DROP_LINE = [r'^（卷.*end.*全卷完）$', r'^【.*終】$', r'^\\(newpage|pagebreak)$', r'^---$']


def split_bilingual(vol, text):
    """return list of (unit_no, heading_text, lines) and list of dropped lines."""
    L = text.split('\n')
    pat = re.compile(r'^#{1,2}\s.*?(?:卷([一二三四五六七八九十]+)|第([一二三四五六]+)部)')
    units, cur, dropped = [], None, []
    for l in L:
        m = pat.match(l)
        if m and not ('全書' in l and ('完成' in l or '合集' in l)) and ('冊《' not in l or vol == '05'):
            k = CNUM.get(m.group(1) or m.group(2))
            if vol == '05' and '全譯文合集' in l:
                m = None
            if m:
                cur = [k, l, []]
                units.append(cur)
                continue
        if cur is None or re.match(r'^#\s.*全書.*(完成|終)', l):
            dropped.append(l)
            continue
        cur[2].append(l)
    return units, dropped


def numline(l):
    """a numbered source line: '12　…' / '12\t…' (may carry a CJK gap note) or '12 Latin…' (no CJK)."""
    m = re.match(r'^(\d+[a-z]?)(　|\t)(.*)$', l)
    if m:
        return m
    m = re.match(r'^(\d+[a-z]?)( )(.*)$', l)
    return m if m and not re.search(r'[一-鿿]', m.group(3)) else None


def bil_items(vol, lines):
    """lines of one unit -> items: ('pair', no, src, [zh]) / ('meta', [lines]) / ('md', [lines]); plus dropped."""
    items, dropped = [], []
    i, n = 0, len(lines)
    md = []

    def flush():
        if md:
            items.append(('md', md[:]))
            md.clear()
    while i < n:
        l = lines[i]
        s = l.strip()
        if any(re.match(p, s) for p in DROP_LINE):
            dropped.append(l)
            i += 1
            continue
        if s.startswith('>') and vol != '05':
            q = []
            while i < n and lines[i].strip().startswith('>'):
                q.append(lines[i])
                i += 1
            keep = [x for x in q if x.strip(' >') and not DROP_META.match(x)]
            dropped += [x for x in q if x not in keep]
            if keep:
                flush()
                items.append(('meta', keep))
            continue
        m = re.match(r'^\|\s*(\d+[a-z]?)([^|]*)\|(.*)\|(.*)\|\s*$', l)
        if m:
            flush()
            items.append(('pair', m.group(1) + m.group(2).strip(), m.group(3).strip(), [m.group(4).strip()]))
            i += 1
            continue
        if re.match(r'^\|\s*行\s*\|', l) or re.match(r'^\|[-\s|:]+\|\s*$', l):
            dropped.append(l)
            i += 1
            continue
        m = numline(l)
        if m and vol != '05':
            flush()
            zh = []
            i += 1
            while i < n and lines[i].strip() and not numline(lines[i]):
                zh.append(lines[i].strip().lstrip('　').strip())
                i += 1
            items.append(('pair', m.group(1), m.group(3).strip(), zh))
            continue
        md.append(l)
        i += 1
    flush()
    return items, dropped


def render_bilingual(book, vol, ctx_name, unit_no, heading, items):
    c = book.c
    lang = c['src_lang']
    ctx = Ctx(ctx_name)
    body, srcmd = [], []
    title = f'卷{cnum(unit_no)}' if vol != '05' else f'第{cnum(unit_no)}部'
    if vol == '05':
        h = re.sub(r'^#\s*05冊《史詩殘篇集》', '', heading).strip().lstrip('：:').strip()
        h = re.sub(r'^(第[一二三四五六]部)(?:（末部）)?[：:]', r'\1　', h)
        title = h
    body.append(f'<h1>{inline(title, ctx)}</h1>')
    srcmd.append(title)
    other = f'r{unit_no:02d}.xhtml'
    body.append(f'<p class="xlink"><a href="{other}">中文好讀版　{"卷" + cnum(unit_no) if vol != "05" else "第" + cnum(unit_no) + "部"}</a></p>')
    for it in items:
        if it[0] == 'pair':
            _, no, src, zh = it
            body.append(f'<div class="lp" id="L{slug(no)}"><p class="o" lang="{lang}" xml:lang="{lang}"><span class="ln">{no}</span>{inline(src, ctx, default=lang)}</p>'
                        + ''.join(f'<p class="t">{inline(z, ctx)}</p>' for z in zh) + '</div>')
            srcmd += [src] + zh
        elif it[0] == 'meta':
            ls = [re.sub(r'^\s*>\s?', '', x) for x in it[1]]
            sep = []
            for x in ls:   # each header line is its own paragraph
                sep += [x, '']
            blks, _ = md_blocks(sep, ctx)
            body.append('<div class="meta">' + ''.join(blks) + '</div>')
            srcmd += ls
        else:
            ls = it[1]
            if vol == '05':
                ls = [x for x in ls if not re.match(r'^#\s*05冊', x)]
            blks, _ = md_blocks(ls, ctx, hshift=0 if vol != '05' else 0)
            body.append('\n'.join(blks))
            srcmd += ls
    return title, page(title, '\n'.join(body)), '\n'.join(srcmd)


# ---------------------------------------------------------------- readable / front (01–05)
LAYOUT = {'mode': 'work'}   # 'work' = editing-time layout; 'repo' = repository layout (use --repo)
REPO_DIR = {'01': '01_伊里亞德', '02': '02_荷馬續篇', '03': '03_奧德賽', '04': '04_埃涅阿斯紀', '05': '05_史詩殘篇集', '90': '90_奧德賽的女作者'}


def split_combined(vol, text):
    """split a combined 好讀版 book (tools/build_book.py output) into front / chapters / appendices."""
    c = VOLS[vol]
    L = text.split('\n')
    chap = re.compile(rf'^# 《{re.escape(c["title"])}》(?:卷([一二三四五六七八九十]+)|第([一二三四五六])部)')
    appx = re.compile(r'^# 附錄([A-Z])')
    marks = []
    for i, l in enumerate(L):
        m = chap.match(l)
        if m:
            marks.append((i, 'c', CNUM[m.group(1) or m.group(2)]))
            continue
        m = appx.match(l)
        if m:
            marks.append((i, 'a', m.group(1)))

    def clean(ls):
        ls = list(ls)
        while ls and ls[-1].strip() in ('', '---'):
            ls.pop()
        return '\n'.join(ls) + '\n'
    front = clean(L[:marks[0][0]])
    chapters, apps = [], []
    for j, (i, kind, key) in enumerate(marks):
        end = marks[j + 1][0] if j + 1 < len(marks) else len(L)
        (chapters if kind == 'c' else apps).append((key, clean(L[i:end])))
    return front, chapters, apps


def load_series(vol):
    c = VOLS[vol]
    if LAYOUT['mode'] == 'repo':
        d = REPO_DIR[vol]
        f, ch, ap = split_combined(vol, read(f'{d}/好讀版.md'))
        return f, ch, ap, read(f'{d}/雙語校對版.md')
    R = f'{SRC}/readable/{c["key"]}'
    files = [(k, f'{R}/第{cnum(k)}部.md') for k in range(1, 7)] if vol == '05' else [(k, f'{R}/卷{k:02d}.md') for k in range(1, c['units'] + 1)]
    apps = [(p[10], read(f'{R}/{p}')) for p in sorted(os.listdir(R)) if re.fullmatch(r'_appendix_[A-Z]\.md', p)]
    bt = read(f'{SRC}/bilingual/TES_{vol}_{c["key"].split("_", 1)[1]}_雙語版_校對版_20261030.md')
    return read(f'{R}/_front.md'), [(k, read(f)) for k, f in files], apps, bt


def build_series(vol):
    c = VOLS[vol]
    b = Book(vol)
    front, chapters, apps, bt = load_series(vol)
    b.cover_jpg = cover_jpeg(c['cover'])
    b.add('cover.xhtml', '封面', page('封面', '<div class="cover"><img src="images/cover-epub.jpg" alt="封面"/></div>', cls='cover', epub_type='cover'), toc=None)
    head, rest = front.split('\n## ', 1)
    sub = '古希臘文—繁體中文逐行對照暨中文閱讀版' if vol in ('01', '02', '03') else ('拉丁文—繁體中文逐行對照暨中文閱讀版' if vol == '04' else '原文—繁體中文對照、見證翻譯暨中文閱讀版')
    tp = (f'<div class="titlepage"><p class="series">特洛伊史詩叢書 {vol}</p><h1 class="main">《{c["title"]}》</h1>'
          f'<p class="orig" lang="{"la" if vol == "04" else "grc"}" xml:lang="{"la" if vol == "04" else "grc"}">{c["orig"]}</p>'
          f'<p class="sub">{sub}</p><p class="author">{c["author"]}</p><p class="ver">{VER}</p></div>')
    b.add('titlepage.xhtml', '書名頁', page('書名頁', tp, epub_type='titlepage'), toc=1)
    secs = ('## ' + rest).split('\n## ')
    for k, s in enumerate(secs):
        s = s if s.startswith('## ') else '## ' + s
        t = s.split('\n', 1)[0][3:].strip()
        ctx = Ctx(f'f{k + 1:02d}.xhtml')
        blks, _ = md_blocks(s.split('\n'), ctx, hshift=1)
        b.add(f'f{k + 1:02d}.xhtml', t.split('：')[0], page(t, '\n'.join(blks), epub_type='frontmatter'), toc=1, sig_src=s)
    # part 1
    b.add('p1.xhtml', '第一部　中文好讀版', page('第一部　中文好讀版', '<div class="part"><h1>第一部　中文好讀版</h1></div>', epub_type='part'), toc=1)
    assert [k for k, _ in chapters] == list(range(1, c['units'] + 1)), (vol, [k for k, _ in chapters])
    for k, t in chapters:
        L = t.rstrip('\n').split('\n')
        h1 = strip_title_prefix(L[0][2:], c['title'])
        ctx = Ctx(f'r{k:02d}.xhtml')
        L2 = ['# ' + h1] + L[1:]
        blks, defs = md_blocks(L2, ctx)
        # footnote definitions -> move to end section
        body_b = [x for x in blks if not x.startswith('<aside')]
        fn_b = [x for x in blks if x.startswith('<aside')]
        xl = f'<p class="xlink"><a href="c{k:02d}.xhtml">原文逐行對照　{"卷" + cnum(k) if vol != "05" else "第" + cnum(k) + "部"}</a></p>'
        body = body_b[0] + xl + '\n'.join(body_b[1:]) + (('<section class="footnotes" epub:type="footnotes">' + ''.join(fn_b) + '</section>') if fn_b else '')
        b.add(f'r{k:02d}.xhtml', h1, page(h1, body, epub_type='chapter'), toc=2, sig_src='\n'.join(L2))
    # part 2
    p2note = ('<p>本部授權：CC BY-SA 4.0。所收' + ('拉丁文' if vol == '04' else '希臘文') + '取自 Perseus Digital Library（CC BY-SA 4.0）。</p>') if vol != '05' else '<p>希臘文殘篇依公版校訂本，中文逐條對照。</p>'
    b.add('p2.xhtml', '第二部　原文逐行對照', page('第二部　原文逐行對照', f'<div class="part"><h1>第二部　原文逐行對照</h1>{p2note}</div>', epub_type='part'), toc=1)
    units, dropped = split_bilingual(vol, bt)
    nums = [u[0] for u in units]
    assert nums == list(range(1, c['units'] + 1)), (vol, nums)
    stats = {'pairs': 0, 'dropped': len([d for d in dropped if d.strip()])}
    drop_log = [d for d in dropped if d.strip()]
    for k, h, ls in units:
        items, dr = bil_items(vol, ls)
        drop_log += [d for d in dr if d.strip()]
        stats['pairs'] += sum(1 for it in items if it[0] == 'pair')
        t, x, srcmd = render_bilingual(b, vol, f'c{k:02d}.xhtml', k, h, items)
        b.add(f'c{k:02d}.xhtml', t, x, toc=2, sig_src=srcmd)
    # appendices
    if apps:
        b.add('p3.xhtml', '附錄', page('附錄', '<div class="part"><h1>附錄</h1></div>', epub_type='part'), toc=1)
    for letter, atext in apps:
        L = atext.rstrip('\n').split('\n')
        h1 = L[0][2:].strip()
        href = f'a{letter.lower()}.xhtml'
        ctx = Ctx(href)
        blks, _ = md_blocks(L, ctx)
        x = '\n'.join(blks)
        if letter == 'F':
            x = re.sub(r'<h2>卷([一二三四五六七八九十]+)　', lambda m: f'<h2><a class="gen" href="r{CNUM[m.group(1)]:02d}.xhtml">卷{m.group(1)}</a>　', x)
            x = x.replace('<a class="gen" href', '<a href')   # keep heading text in coverage
        b.add(href, h1, page(h1, x, epub_type='appendix'), toc=2, sig_src='\n'.join(L))
    stats['drop_log'] = drop_log
    return b, stats


def cover_jpeg(name):
    from PIL import Image
    im = Image.open((f'covers/{name}' if LAYOUT['mode'] == 'repo' else f'{ROOT}/epub/covers/{name}')).convert('RGB')
    bio = io.BytesIO()
    im.save(bio, 'JPEG', quality=90, optimize=True, progressive=False)
    return bio.getvalue()


# ---------------------------------------------------------------- vol. 90
def build_90():
    c = VOLS['90']
    b = Book('90')
    b.cover_jpg = cover_jpeg(c['cover'])
    D90 = REPO_DIR['90'] if LAYOUT['mode'] == 'repo' else f'{SRC}/90'
    t = read(f'{D90}/中文好讀版_附原文.md' if LAYOUT['mode'] == 'repo' else f'{D90}/TES_90_Authoress_中文好讀版_附原文_20261108.md')
    pre, rest = t.split('\n# 中文好讀版\n', 1)
    zh, en = rest.split('\n# 附：英文原文\n', 1)
    for f in sorted(os.listdir(f'{D90}/images')):
        b.images.append((f'images/{f}', open(f'{D90}/images/{f}', 'rb').read(), 'image/jpeg'))
    b.add('cover.xhtml', '封面', page('封面', '<div class="cover"><img src="images/cover-epub.jpg" alt="封面"/></div>', cls='cover', epub_type='cover'), toc=None)
    tp = ('<div class="titlepage"><p class="series">特洛伊史詩叢書 90　附錄參考書</p><h1 class="main">奧德賽的女作者</h1>'
          '<p class="orig" lang="en" xml:lang="en"><i>The Authoress of the Odyssey</i></p><p class="author">塞繆爾．巴特勒</p>'
          f'<p class="ver">{VER}</p></div>')
    b.add('titlepage.xhtml', '書名頁', page('書名頁', tp, epub_type='titlepage'), toc=1)
    # preamble: lines up to first '## ' (title, subtitle, 編者說明) + ## sections except 目錄
    p_head, p_rest = pre.split('\n## ', 1)
    L = p_head.split('\n')
    L = [x for x in L if not x.startswith('# ') and not x.startswith('> 特洛伊史詩叢書 v')]   # repository license header line
    L = [('## 編者說明' if x.strip() == '〔編者說明〕' else x) for x in L]
    ctx = Ctx('f01.xhtml')
    blks, _ = md_blocks(L, ctx, hshift=1)
    b.add('f01.xhtml', '編者說明', page('編者說明', '\n'.join(blks), epub_type='frontmatter'), toc=1, sig_src='\n'.join(L))
    k = 1
    for s in ('## ' + p_rest).split('\n## '):
        s = s if s.startswith('## ') else '## ' + s
        title = s.split('\n', 1)[0][3:].strip()
        if title == '目錄':
            continue
        k += 1
        ctx = Ctx(f'f{k:02d}.xhtml')
        blks, _ = md_blocks(s.split('\n'), ctx, hshift=1)
        b.add(f'f{k:02d}.xhtml', title, page(title, '\n'.join(blks), epub_type='frontmatter'), toc=1, sig_src=s)

    def chunks(text):
        parts = re.split(r'\n(?=## )', '\n' + text)
        return [p.strip('\n') for p in parts if p.strip()]
    zc, ec = chunks(zh), chunks(en)
    first_u = lambda s: (re.findall(r'<!--\s*(U\d{4})\s*-->', s) or [None])[0]
    allu = lambda s: set(re.findall(r'<!--\s*(U\d{4})\s*-->', s))
    zfile = {i: f'z{i + 1:02d}.xhtml' for i in range(len(zc))}
    efile = {i: f'e{i + 1:02d}.xhtml' for i in range(len(ec))}
    u2e = {u: efile[i] for i, s in enumerate(ec) for u in allu(s)}
    u2z = {u: zfile[i] for i, s in enumerate(zc) for u in allu(s)}
    # footnote label -> file of its definition (Chinese half)
    fnf = {}
    for i, s in enumerate(zc):
        for lab in re.findall(r'^\[\^([^\]\s]+)\]:', s, re.M):
            fnf[lab] = zfile[i]
    b.add('p1.xhtml', '第一部　中文譯文', page('第一部　中文譯文', '<div class="part"><h1>第一部　中文譯文</h1></div>', epub_type='part'), toc=1)
    for i, s in enumerate(zc):
        L = s.split('\n')
        ctx = Ctx(zfile[i], fnf)
        blks, _ = md_blocks(L, ctx, hshift=1)
        title = L[0][3:].strip() if L[0].startswith('## ') else '書名頁與題詞'
        if not L[0].startswith('## '):
            blks = [f'<h1>{title}</h1>'] + blks
        u = first_u(s)
        xl = f'<p class="xlink"><a href="{u2e[u]}#E-{u}">英文原文</a></p>' if u in u2e else ''
        x = blks[0] + xl + '\n'.join(blks[1:])
        b.add(zfile[i], title, page(title, x, epub_type='chapter'), toc=2, sig_src=s if L[0].startswith('## ') else title + s)
    b.add('p2.xhtml', '第二部　英文原文', page('第二部　英文原文', '<div class="part"><h1>第二部　英文原文</h1><p>Samuel Butler, <i>The Authoress of the Odyssey</i>（1922 年紐約 E．P．達頓公司版，公版）</p></div>', epub_type='part'), toc=1)
    for i, s in enumerate(ec):
        L = s.split('\n')
        L = [re.sub(r'<!--\s*(U\d{4})\s*-->', r'<!-- E\1 -->', x) for x in L]
        ctx = Ctx(efile[i])
        blks, _ = md_blocks([re.sub(r'<!-- E(U\d{4}) -->', r'<!-- \1 -->', x) for x in L], ctx, hshift=1, default='en')
        blks = [re.sub(r' id="(U\d{4})"', r' id="E-\1"', x) for x in blks]
        title = L[0][3:].strip() if L[0].startswith('## ') else 'Title page'
        if not L[0].startswith('## '):
            blks = [f'<h1>{title}</h1>'] + blks
        u = first_u(s)
        xl = f'<p class="xlink"><a href="{u2z[u]}#{u}">中文譯文</a></p>' if u in u2z else ''
        x = blks[0] + xl + '\n'.join(blks[1:])
        b.add(efile[i], title, page(title, x, lang='en', epub_type='chapter'), toc=2, sig_src=s if L[0].startswith('## ') else title + s)
    return b, {'zh_chunks': len(zc), 'en_chunks': len(ec)}


def main():
    global OUT, TAG
    args = sys.argv[1:]
    if '--repo' in args:   # run from the repository root: reads <冊>/好讀版.md, 雙語校對版.md, covers/; writes build/
        args.remove('--repo')
        LAYOUT['mode'] = 'repo'
        OUT = 'build'
    if '--tag' in args:
        i = args.index('--tag')
        TAG = args[i + 1]
        del args[i:i + 2]
    vols = args or list(VOLS)
    os.makedirs(OUT, exist_ok=True)
    cov = {}
    for v in vols:
        b, st = build_90() if v == '90' else build_series(v)
        fn = f'{OUT}/TroyEpic_{v}_{VOLS[v]["name"]}_zh-TW_{TAG}.epub'
        b.write(fn)
        bad = [x for x in b.coverage if not x[3]]
        cov[v] = {'file': fn, 'size': os.path.getsize(fn), 'xhtml': len(b.files), 'coverage_checked': len(b.coverage),
                  'coverage_bad': bad, **{k: v2 for k, v2 in st.items() if k != 'drop_log'}, 'dropped_lines': st.get('drop_log', [])}
        print(v, os.path.basename(fn), f'{os.path.getsize(fn) / 1e6:.2f} MB', 'xhtml', len(b.files), 'coverage bad', len(bad), {k: v2 for k, v2 in st.items() if k != 'drop_log'})
        for x in bad[:5]:
            print('   ✗', x)
    json.dump(cov, open(f'{OUT}/coverage.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

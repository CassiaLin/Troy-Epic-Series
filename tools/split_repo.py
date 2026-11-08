# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""D4-9: GitHub cannot display the large combined files, so generate per-chapter files mechanically from the same sources.
Writes into the repository (run from the repository root):
  <冊>/分卷/README.md, <冊>/分卷/好讀版/NN_*.md, <冊>/分卷/雙語校對版/NN_*.md   (01–05)
  90_奧德賽的女作者/分章/README.md, 分章/中文/NN_*.md, 分章/英文/NN_*.md
Each split file = one license header line + one navigation line + the original text of that part (verbatim).
Check: concatenating the parts (without the two added lines) gives back the original file exactly (after its own header line).
usage (repository root): python tools/split_repo.py   (rerun after any change to 好讀版.md / 雙語校對版.md / 90 冊檔案)
"""
import os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_epub as B

R = '.'
import shutil
for _d in [f'{v}/分卷' for v in ('01_伊里亞德', '02_荷馬續篇', '03_奧德賽', '04_埃涅阿斯紀', '05_史詩殘篇集')] + ['90_奧德賽的女作者/分章']:
    shutil.rmtree(_d, ignore_errors=True)   # regenerate from scratch (stale chapter files must not remain)
VOL = {'01': '01_伊里亞德', '02': '02_荷馬續篇', '03': '03_奧德賽', '04': '04_埃涅阿斯紀', '05': '05_史詩殘篇集'}
MAXB = 0


def body_of(path):
    t = open(path, encoding='utf-8').read()
    head, rest = t.split('\n\n', 1)
    assert head.startswith('> 特洛伊史詩叢書 v'), path
    return head, rest


def cut(text, starts):
    """split text at the given line indices (sorted, first may be >0 -> leading chunk)."""
    L = text.split('\n')
    idx = sorted(set([0] + starts))
    return ['\n'.join(L[a:b]) + ('\n' if b < len(L) else '') for a, b in zip(idx, idx[1:] + [len(L)])]


def write(path, header, nav, chunk):
    global MAXB
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = header + '\n' + nav + '\n\n' + chunk
    open(path, 'w', encoding='utf-8', newline='\n').write(data)
    MAXB = max(MAXB, len(data.encode('utf-8')))


def safe(s):
    s = re.sub(r'^《[^》]+》', '', s).strip().rstrip('.')
    return re.sub(r'[\\/:*?"<>|\s]+', '_', s).strip('_')[:40]


total = 0
for vol, d in VOL.items():
    c = B.VOLS[vol]
    index = [f'# {d[3:]}：分卷檔', '', '合訂本檔案太大，GitHub 網頁無法直接顯示，這裡依卷拆開，內容與合訂本逐字相同。下載或全文搜尋請用上一層的合訂本。', '']
    for kind, fname in (('好讀版', '好讀版.md'), ('雙語校對版', '雙語校對版.md')):
        header, text = body_of(f'{R}/{d}/{fname}')
        L = text.split('\n')
        if kind == '好讀版':
            chap = re.compile(rf'^# 《{re.escape(c["title"])}》(?:卷[一二三四五六七八九十]+|第[一二三四五六]部)|^# 附錄[A-Z]')
        else:
            chap = re.compile(r'^#{1,2}\s.*?(?:卷[一二三四五六七八九十]+|第[一二三四五六]部)')
        starts = [i for i, l in enumerate(L) if chap.match(l) and not ('全書' in l and ('完成' in l or '合集' in l))]
        parts = cut(text, starts)
        assert ''.join(parts) == text
        index.append(f'## {kind}')
        index.append('')
        for k, p in enumerate(parts):
            first = next((l for l in p.split('\n') if l.startswith('#')), '')
            title = re.sub(r'^#+\s*', '', first).strip() or '書前'
            if k == 0 and not chap.match(p.split('\n')[0]):
                title = '書前與凡例' if kind == '好讀版' else '卷首說明'
            elif kind == '雙語校對版':
                m = re.search(r'(卷[一二三四五六七八九十]+|第[一二三四五六]部)', first)
                title = m.group(1)
            fn = f'{k:02d}_{safe(title)}.md'
            write(f'{R}/{d}/分卷/{kind}/{fn}', header, f'[← 分卷目錄](../README.md)　｜　[合訂本](../../{fname})', p)
            index.append(f'- [{title}]({kind}/{fn})')
            total += 1
        index.append('')
    open(f'{R}/{d}/分卷/README.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(index))
# vol. 90: split each half at '## ' headings; image paths adjusted (分章/中文/ -> ../../images/)
d = '90_奧德賽的女作者'
header, text = body_of(f'{R}/{d}/中文好讀版_附原文.md')
zh_at = text.index('\n# 中文好讀版\n') + 1
en_at = text.index('\n# 附：英文原文\n') + 1
halves = [('中文', text[:en_at]), ('英文', text[en_at:])]
assert halves[0][1] + halves[1][1] == text
index = ['# 奧德賽的女作者：分章檔', '', '全書檔案太大，GitHub 網頁無法直接顯示，這裡依章拆開，內容與全書檔逐字相同（圖片路徑改為相對於本資料夾）。下載或全文搜尋請用上一層的全書檔。', '']
for half, t in halves:
    L = t.split('\n')
    starts = [i for i, l in enumerate(L) if l.startswith('## ')]
    parts = cut(t, starts)
    assert ''.join(parts) == t
    index += [f'## {half}', '']
    for k, p in enumerate(parts):
        first = next((l for l in p.split('\n') if l.startswith('#')), '')
        title = re.sub(r'^#+\s*', '', first).strip() or '書名頁'
        fn = f'{k:02d}_{safe(title)}.md'
        p2 = p.replace('](images/', '](../../images/')
        write(f'{R}/{d}/分章/{half}/{fn}', header, '[← 分章目錄](../README.md)　｜　[全書](../../中文好讀版_附原文.md)', p2)
        index.append(f'- [{title}]({half}/{fn})')
        total += 1
    index.append('')
# 逐段對照工作檔: split before the heading units whose English line starts a chapter / preface / index
header, t = body_of(f'{R}/{d}/逐段對照工作檔.md')
L = t.split('\n')
starts = [i for i, l in enumerate(L) if re.match(r'^〔U\d{4} heading〕$', l) and i + 2 < len(L)
          and re.match(r'^> (CHAPTER|PREFACE|CONTENTS|LIST OF ILLUSTRATIONS|INDEX)', next((x for x in L[i + 1:i + 6] if x.startswith('> ')), ''))]
parts = cut(t, starts)
assert ''.join(parts) == t
index += ['## 逐段對照工作檔（中文＋英文原文並列）', '']
for k, p in enumerate(parts):
    en = next((x[2:] for x in p.split('\n') if x.startswith('> ')), '')
    title = '書名頁' if k == 0 else en.strip().rstrip('.')
    fn = f'{k:02d}_{safe(title)}.md'
    write(f'{R}/{d}/分章/逐段對照/{fn}', header, '[← 分章目錄](../README.md)　｜　[全檔](../../逐段對照工作檔.md)', p)
    index.append(f'- [{title}](逐段對照/{fn})')
    total += 1
index.append('')
open(f'{R}/{d}/分章/README.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(index))
print('split files', total, 'largest bytes', MAXB)

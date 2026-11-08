#!/usr/bin/env python3
# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
# -*- coding: utf-8 -*-
"""
合訂本建置：把一冊的逐卷檔案合併成「全書」檔。

用法：  python tools/build_book.py 04_Aeneid [--chapters 12]
        python tools/build_book.py 05_Fragments --parts 6        （《史詩集成殘篇》，檔名為「第一部.md」…）

讀取（都在 readable/<冊>/ 下）：
  _front.md                書名頁與書前凡例（可選）
  卷01.md … 卷NN.md         逐卷檔案（NN 由 --chapters 指定，預設依檔案自動偵測；檔名須為兩位數字）
  第一部.md … 第六部.md     逐部檔案（沒有 卷NN.md 時改找這種檔名；--parts 指定部數）
  _appendix_*.md           附錄（依檔名排序，可選）
輸出：
  readable/<冊>/<冊>_好讀版_全書.md

處理：
  1. 各章註腳標籤改寫成 [^卷號-原標籤]，避免跨章撞號（全書一個檔案，標籤必須唯一）
  2. 檢查註腳完整性：每個引用都有定義、每個定義都被引用
  3. 對合訂本跑 lint（半形標點、舊譯法、工作痕跡）
只使用 Python 標準函式庫。
"""
import sys, os, re, glob, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding='utf-8')
    except Exception:
        pass

REF = re.compile(r'\[\^([^\]\s]+)\](?!:)')
DEF = re.compile(r'^\[\^([^\]\s]+)\]:', re.M)


def relabel(text, k):
    def sub_def(m):
        return f'[^{k}-{m.group(1)}]:'
    def sub_ref(m):
        return f'[^{k}-{m.group(1)}]'
    text = DEF.sub(sub_def, text)
    text = REF.sub(sub_ref, text)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('volume')
    ap.add_argument('--chapters', type=int, default=0)
    ap.add_argument('--parts', type=int, default=0)
    a = ap.parse_args()
    d = a.volume if os.path.isdir(a.volume) else os.path.join(ROOT, 'readable', a.volume)
    CN = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
    files = sorted(glob.glob(os.path.join(d, '卷[0-9][0-9].md')))
    unit_no = lambda f: int(os.path.basename(f)[1:3])
    want = a.chapters
    if not files:
        files = sorted(glob.glob(os.path.join(d, '第?部.md')), key=lambda f: CN.get(os.path.basename(f)[1], 99))
        unit_no = lambda f: CN.get(os.path.basename(f)[1], 99)
        want = a.parts
    if want:
        files = [f for f in files if unit_no(f) <= want]
    if not files:
        sys.exit(f'找不到 {d} 下的 卷NN.md 或 第N部.md')
    nums = [unit_no(f) for f in files]
    if want and nums != list(range(1, want + 1)):
        miss = sorted(set(range(1, want + 1)) - set(nums))
        sys.exit(f'章節（部）不齊，缺：{miss}')
    parts = []
    front = os.path.join(d, '_front.md')
    if os.path.exists(front):
        parts.append(open(front, encoding='utf-8').read().rstrip() + '\n')
    refs_total = defs_total = 0
    problems = []
    for f in files:
        k = unit_no(f)
        t = open(f, encoding='utf-8').read()
        r = set(REF.findall(t)); df = set(DEF.findall(t))
        for x in sorted(r - df):
            problems.append(f'第{k}單位：引用 [^{x}] 沒有定義')
        for x in sorted(df - r):
            problems.append(f'第{k}單位：定義 [^{x}] 沒有被引用')
        refs_total += len(r); defs_total += len(df)
        parts.append(relabel(t, k).rstrip() + '\n')
    # 只讀 _appendix_A.md 這種「單一大寫字母」的檔名；備份檔（_appendix_A.舊版1.md）不可併入
    for f in sorted(glob.glob(os.path.join(d, '_appendix_[A-Z].md'))):
        parts.append(open(f, encoding='utf-8').read().rstrip() + '\n')
    out = os.path.join(d, f'{a.volume}_好讀版_全書.md')
    open(out, 'w', encoding='utf-8').write('\n\n---\n\n'.join(parts))
    print(f'✅ 已產生 {out}')
    print(f'   章數 {len(files)}；註腳引用 {refs_total}、定義 {defs_total}')
    if problems:
        print('⚠ 註腳問題：')
        for p in problems[:40]:
            print('   -', p)
    else:
        print('   註腳完整性：通過')
    # 合併後再檢查全書標籤是否唯一
    t = open(out, encoding='utf-8').read()
    defs = DEF.findall(t)
    dup = {x for x in defs if defs.count(x) > 1}
    print('   全書註腳標籤唯一性：' + ('通過' if not dup else f'有重複 {sorted(dup)[:10]}'))
    heads = [l.strip() for l in t.split('\n') if l.startswith('# ')]
    duph = sorted({h for h in heads if heads.count(h) > 1})
    print('   頂層標題重複檢查：' + ('通過' if not duph else f'⚠ 有重複 {duph[:6]}（可能把備份檔併進來了）'))
    if duph:
        sys.exit('合併失敗：頂層標題重複')
    from tes_metrics import lint_issues
    iss = lint_issues(out)
    print(f'   lint：{len(iss)} 項' + ('' if not iss else '（' + '；'.join(f'L{i} {x}' for i, x, _ in iss[:5]) + '）'))


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""驗證 90 冊雙語檔。用法: python tools/verify_90.py <units.json> <雙語檔.md> [--partial]
檢查: (1)每個單元恰出現一次、順序同底本 (2)英文欄與底本逐字相同 (3)中文欄非空(圖版無圖說者可用占位)
(4)[註n] 錨點英中一致 (5)希臘文片段在中文欄保留 (6)字數比 (7)禁用寫法 (8)半形標點
--partial: 只驗檔內已有的單元(章節進行中用)；沒有 --partial 則要求全數單元到齊。"""
import sys,re,json,collections
units=json.load(open(sys.argv[1],encoding='utf-8')); path=sys.argv[2]; partial='--partial' in sys.argv
txt=open(path,encoding='utf-8',newline='').read()
if '\r' in txt: print('✗ 檔案含 CR，必須是 LF')
blocks=re.split(r'\n(?=〔U\d{4} )',txt)
got={}; order=[]; errs=[]; warn=[]
for b in blocks:
    m=re.match(r'〔(U\d{4}) (\w+)〕\n',b)
    if not m: continue
    uid,typ=m.group(1),m.group(2); body=b[m.end():].rstrip('\n').split('\n')
    en=[l[2:] for l in body if l.startswith('> ')]
    zh=[l for l in body if not l.startswith('> ') and l.strip()]
    if uid in got: errs.append(f'{uid} 重複')
    got[uid]=(typ,' '.join(en).strip(),' '.join(zh).strip()); order.append(uid)
ids=[u['id'] for u in units]
src={u['id']:u for u in units}
if not partial:
    miss=[i for i in ids if i not in got]
    if miss: errs.append(f'缺少單元 {len(miss)} 個，例如 {miss[:5]}')
extra=[i for i in got if i not in src]
if extra: errs.append(f'多出單元 {extra[:5]}')
pos=[ids.index(i) for i in order if i in src]
if pos!=sorted(pos): errs.append('單元順序與底本不同')
GREEK=re.compile(r'[Ͱ-Ͽἀ-῿]+')
HALF=re.compile(r'[一-鿿][,.;:!?]|[,.;:!?][一-鿿]|[一-鿿]\(|\)[一-鿿]')
BAD=['——','・','伊利亞德','伊里亞特','荷馬史詩《奧德賽》女作者']
chap=collections.defaultdict(lambda:[0,0]); cur='前置'
for uid in order:
    if uid not in src: continue
    u=src[uid]; typ,en,zh=got[uid]
    if u['type']=='heading' and re.match(r'CHAPTER [IVXL]+',u['text']): cur=u['text']
    if en!=u['text']: errs.append(f'{uid} 英文欄與底本不同')
    if not zh:
        if not (typ=='figure' and not u['text']): errs.append(f'{uid} 中文欄空白')
        continue
    if typ=='figure' and '〔圖版' not in zh and u['text']: warn.append(f'{uid} 圖版占位格式')
    if sorted(re.findall(r'\[註\d+\]',en))!=sorted(re.findall(r'\[註\d+\]',zh)): errs.append(f'{uid} [註n] 錨點不一致')
    for g in GREEK.findall(en):
        if len(g)>=3 and g not in zh: errs.append(f'{uid} 希臘文片段未保留：{g[:12]}'); break
    for b in BAD:
        if b in zh: errs.append(f'{uid} 禁用寫法 {b}')
    if HALF.search(zh): errs.append(f'{uid} 疑似半形標點：{HALF.search(zh).group(0)}')
    w=len(en.split()); c=len(re.sub(r'[\sͰ-Ͽa-zA-Z0-9*\[\]]','',zh)); 
    if typ in('para','quote','footnote') and w>=25:
        r=c/w
        if not 1.35<=r<=2.6: warn.append(f'{uid} 字數比 {r:.2f}（英 {w} 字／中 {c} 字）')
        se=len(re.findall(r'[.?!]["”)]?\s|[.?!]$',en+' ')); sz=len(re.findall(r'[。？！]',zh))
        if se>=3 and sz<0.6*se: warn.append(f'{uid} 句數偏少（英 {se}／中 {sz}）')
    if typ in('para','quote','footnote'):
        chap[cur][0]+=w; chap[cur][1]+=c
print(f'單元 {len(got)}／{len(ids)}')
for k,(w,c) in chap.items():
    r=c/w if w else 0
    flag='' if r>=1.55 else '  ← 低於 1.55'
    if flag: errs.append(f'{k} 字數比 {r:.2f} 低於 1.55')
    print(f'  {k:14s} 英 {w:6d} 字  中 {c:6d} 字  比 {r:.2f}{flag}')
for w in warn[:60]: print('⚠',w)
if len(warn)>60: print(f'⚠ …另有 {len(warn)-60} 筆警告')
for e in errs[:80]: print('✗',e)
if len(errs)>80: print(f'✗ …另有 {len(errs)-80} 筆')
print(f'錯誤 {len(errs)}　警告 {len(warn)}')
sys.exit(1 if errs else 0)

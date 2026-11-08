#!/usr/bin/env python3
# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""把 Butler《The Authoress of the Odyssey》Gutenberg HTML 拆成「單元」(unit) 清單。
用法: python tools/extract_90.py <html路徑> <輸出json路徑>
單元類型: heading / para / quote / footnote / caption / figure / toc / index / rule
文字規則: <i>/<em> → *斜體*；頁碼 [Pg x] 與詩行編號 linenum 丟掉；腳註錨點 → [註n]；多重空白合成一格。
"""
import re,sys,json,html
from bs4 import BeautifulSoup, NavigableString
src,out=sys.argv[1],sys.argv[2]
soup=BeautifulSoup(open(src,encoding='utf-8').read(),'html.parser')
def inline(node):
    s=''
    for c in node.children:
        if isinstance(c,NavigableString): s+=str(c); continue
        cls=c.get('class') or []
        if c.name=='span' and ('pagenum' in cls or 'linenum' in cls): continue
        if c.name=='a':
            if 'fnanchor' in cls:
                m=re.search(r'\[(\d+)\]',c.get_text()); s+='[註%s]'%(m.group(1) if m else '?'); continue
            if not c.get('href') and not c.get_text(strip=True): continue
        if c.name in('i','em'): s+='*'+inline(c)+'*'; continue
        if c.name=='br': s+=' '; continue
        s+=inline(c)
    return s
def norm(s):
    s=html.unescape(s); s=re.sub(r'\s+',' ',s).strip()
    s=re.sub(r'\*\s*\*','',s); s=s.replace('* ,*',',')
    return s
units=[]; started=False; fignum=0
def fig(el):
    global fignum
    fignum+=1; im=el.find('img'); cap=el.find(class_='caption')
    add('figure',(cap.get_text(' ',strip=True) if cap else ''),image=(im.get('src') if im else ''),alt=(im.get('alt') if im else ''),fig=fignum)
def add(t,text,**kw):
    text=norm(text)
    if text or t=='figure': units.append(dict(id='U%04d'%(len(units)+1),type=t,text=text,**kw))
for el in soup.body.find_all(recursive=False):
    txt=el.get_text(' ',strip=True)
    if 'START OF THE PROJECT GUTENBERG' in txt: started=True; continue
    if 'END OF THE PROJECT GUTENBERG' in txt: break
    if not started or el.name=='hr': continue
    cls=el.get('class') or []
    if el.name in('h1','h2','h3','h4','h5'): add('heading',inline(el),level=el.name)
    elif el.name=='p': add('para',inline(el),css=' '.join(cls))
    elif el.name=='blockquote':
        for ch in el.children:
            if getattr(ch,'name',None)=='p': add('quote',inline(ch))
            elif getattr(ch,'name',None)=='div' and 'figcenter' in (ch.get('class') or []): fig(ch)
        if not el.find('p') and not el.find('img'): add('quote',inline(el))
    elif el.name=='div' and 'footnote' in cls:
        for p in el.find_all('p'):
            lab=p.find('span',class_='label'); n=re.sub(r'\D','',lab.get_text()) if lab else ''
            if lab: lab.extract()
            add('footnote',inline(p),note=n)
    elif el.name=='div' and 'figcenter' in cls: fig(el)
    elif el.name=='table': add('toc',el.get_text(' ',strip=True))
    elif el.name=='div': add('para',inline(el),css='div')
for k,u in enumerate(units):
    if u['type']=='para' and u['text']=='INDEX':
        for v in units[k+1:]:
            if v['type'] in('para',): v['type']='index'
        break
json.dump(units,open(out,'w',encoding='utf-8'),ensure_ascii=False,indent=1)
import collections
print(len(units),collections.Counter(u['type'] for u in units))
print('英文字數',sum(len(u['text'].split()) for u in units if u['type'] in('para','quote','footnote','heading')))

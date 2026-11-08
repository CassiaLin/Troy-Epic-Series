# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""Write VERSION_STATUS.md and SHA256SUMS.txt (after build/*.epub were built with tools/build_epub.py and checked with
EPUBCheck, whose console output is saved as build/check/<epub name without .epub>.txt).
usage (repository root): python tools/gen_status.py
"""
import hashlib, os, re

R = '.'
# 各冊目前版本：升版時改這裡（tag 為 <代號>-<版本>，EPUB 檔名為 TroyEpic_<NN>_<Name>_zh-TW_<版本>.epub）
VERSIONS = {'01': 'v2.0.0', '02': 'v2.0.0', '03': 'v2.0.0', '04': 'v2.0.0', '05': 'v2.0.0', '90': 'v2.0.0'}
SERIES = 'series-v2.0.0'
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
V = [('01', '伊里亞德', 'Iliad', '01-iliad'), ('02', '荷馬續篇', 'Posthomerica', '02-posthomerica'), ('03', '奧德賽', 'Odyssey', '03-odyssey'),
     ('04', '埃涅阿斯紀', 'Aeneid', '04-aeneid'), ('05', '史詩殘篇集', 'Epic_Cycle', '05-epic-cycle'), ('90', '奧德賽的女作者（附錄參考書）', 'Odyssey_Authoress', '90-odyssey-authoress')]
rows, sums = [], []
for n, t, e, tag in V:
    ver = VERSIONS[n]
    f = f'TroyEpic_{n}_{e}_zh-TW_{ver}.epub'
    h = sha(f'{R}/build/{f}')
    log = open(f'build/check/TroyEpic_{n}_{e}_zh-TW_{ver}.txt', encoding='utf-8', errors='replace').read()
    m = re.search(r'Messages: (\d+) fatals / (\d+) errors / (\d+) warnings / (\d+) infos / (\d+) usages', log)
    ck = '／'.join(m.groups()) if m else '?'
    rows.append(f'| {n} | {t} | {ver} | `{tag}-{ver}`；[下載 EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/{tag}-{ver}/{f}) | {ck} | 通過 | `{h}` |')
    sums.append(f'{h}  release-assets/{f}')
doc = ['# 版本狀態', '', '最後更新：2026-11-08（Asia/Taipei）', '',
       '| 冊次 | 作品 | 版本 | Release tag／下載 | EPUBCheck 5.3.0（fatal／error／warning／info／usage） | 實機檢查（Google Play 圖書，Android 電子紙閱讀器） | EPUB SHA-256 |',
       '|---|---|---:|---|---|---|---|'] + rows + ['', f'- 全套快照 tag：`{SERIES}`。', '- v1.x（2026-08）已封存，不再更新。', '- 版號規則見 [docs/06_版本與發布規則.md](docs/06_版本與發布規則.md)。', '']
open(f'{R}/VERSION_STATUS.md', 'w', encoding='utf-8', newline='\n').write('\n'.join(doc))
for root, ds, fs in os.walk(R):
    ds[:] = [d for d in ds if d != 'build']
    for f in fs:
        p = os.path.join(root, f)
        rel = os.path.relpath(p, R).replace('\\', '/')
        if rel != 'SHA256SUMS.txt':
            sums.append(f'{sha(p)}  {rel}')
sums = sorted(sums, key=lambda x: x.split('  ', 1)[1])
open(f'{R}/SHA256SUMS.txt', 'w', encoding='utf-8', newline='\n').write('# SHA-256：倉庫檔案與 Release assets（release-assets/ 前綴者為 GitHub Release 附件）\n' + '\n'.join(sums) + '\n')
print('status rows', len(rows), 'sums', len(sums))

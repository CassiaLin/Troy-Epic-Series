# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
"""D4-6 / NAMING 262: make the public copies of the rules documents (workflow wording neutralised; content and rulings unchanged).
Input : the rules package (rules_v2/), path given as argv[1]
Output: docs/  (00–06, 02, 92, 91, NAMING; 99 and 07 are not published)
        build/docs_report.md (replacement counts, residual hits, sample diffs) for spot checks
usage (repository root): python tools/make_public_docs.py <rules_v2 dir of the internal rules package>
"""
import difflib, os, re, sys

SRC = sys.argv[1]
OUT = 'docs'
FILES = ['00_總覽與索引.md', '01_翻譯規則.md', '02_全叢書統一譯名總表.csv', '03_底本與參考資料記錄規範.md', '04_成書結構與統一規範.md',
         '05_版權與授權規則.md', '06_版本與發布規則.md', '91_翻譯決策日誌.md', '92_固定修飾語對照表.csv', 'NAMING_DECISIONS.md']
VOLNO = {'01': '01冊', '02': '02冊', '03': '03冊', '04': '04冊', '05': '05冊'}

# (pattern, replacement, applies_to_csv) — applied in order
RULES = [
    (r'`?07_對話協作流程規範\.md`?(?:（B ?類[^）]*）)?', '工作流程文件（不公開）', True),
    (r'B ?類文件', '工作流程文件', True),
    (r'B ?類', '工作流程類', True),
    (r'Project Knowledge', '工作資料庫', True),
    (r'Claude 對話介面', '協作工具', True),
    (r'Claude Code|Claude|Codex', '編修工具', True),
    (r'TES-Q\s*複查', '品質複查', True),
    (r'TES-Q', '品質複查', True),
    (r'TES-C', '審核', True),
    (r'TES-V(0[1-5])', lambda m: f'{VOLNO[m.group(1)]}翻譯', True),
    (r'TES-R(0[1-5])', lambda m: f'{VOLNO[m.group(1)]}好讀版撰寫', True),
    (r'TES-[A-Z]+[0-9]*', '工作小組', True),
    (r'對話\s*1(?![0-9])', '編輯', True),
    (r'對話\s*一(?!度)', '編輯', True),
    (r'對話\s*([2-9])(?![0-9])', '分工', True),
    (r'分冊對話', '分冊翻譯', False),
    (r'本研究對話', '本研究', False),
    (r'子任務', '分工撰寫', True),
    (r'任務書|任務包', '工作清單', True),
    (r'第\s*([0-9]+)\s*輪', r'第 \1 次校訂', True),
    (r'輪次', '校訂次序', True),
    (r'(準備|收尾|最後一|本|下一|上一|前一|該|同一|這一)輪', r'\1次校訂', True),
    (r'`(?:work|reports|rounds|inputs|readable|bilingual_new|tools|release|outputs)/[^`]*`', '（工作紀錄檔）', True),
    (r'(?<![\w/])(?:work|reports|rounds|inputs|bilingual_new|outputs)/[\w\-./]+', '（工作紀錄檔）', True),
]
RULES += [
    (r'`工作流程_不上git/工作流程文件（不公開）', '`工作流程_不上git/`（工作流程文件，不公開）', False),
    (r'如何使用 協作工具協作生產', '如何使用協作工具進行生產', False),
    (r'（規則制定/協調對話）', '（負責規則制定與協調者）', False),
    (r'對話(記錄|紀錄|歷史)', r'工作', False),
    (r'(?<!《)對話機制', '協作機制', False),
    (r'(?<![《〈])對話(?![^《]*》)', '工作階段', False),
    (r'(?<=[^\s])\s(編修工具)\s(?=[^\s])', r'', False),
]
RULES += [(r'工作用 ?工作資料庫', '工作資料庫', False), (r'工作資料庫 同步', '工作資料庫同步', False), (r'若日後 工作流程類', '若日後工作流程類', False)]
RESIDUAL = r'TES|Claude|Codex|對話\s*[0-9一]|子任務|任務書|任務包|第\s*[0-9]+\s*輪|輪次|Project Knowledge|work/|reports/|rounds/'

os.makedirs(OUT, exist_ok=True)
rep = ['# docs 公開版產生報告（D4-6）', '', f'來源：規則包 rules_v2（2026-11-08 15:42 版）。99 與 07 不公開。', '',
       '## 一、替換次數', '', '| 檔案 | 規則 | 次數 |', '|---|---|---|']
residual, samples = [], []
for f in FILES:
    t = open(os.path.join(SRC, f), encoding='utf-8', newline='').read()
    orig = t
    is_csv = f.endswith('.csv')
    for pat, sub, csv_ok in RULES:
        if is_csv and not csv_ok:
            continue
        t, n = re.subn(pat, sub, t)
        if n:
            rep.append(f'| {f} | `{pat}` | {n} |')
    open(os.path.join(OUT, f), 'w', encoding='utf-8', newline='').write(t)
    for i, l in enumerate(t.split('\n'), 1):
        if re.search(RESIDUAL, l):
            residual.append(f'| {f} | {i} | {l.strip()[:120]} |')
    d = [x for x in difflib.unified_diff(orig.split('\n'), t.split('\n'), lineterm='', n=0) if x[:1] in '+-' and x[:3] not in ('+++', '---')]
    samples.append((f, len(d) // 2, d[:6]))
rep += ['', '## 二、殘留（需人工判斷）', '', '| 檔案 | 行 | 內容 |', '|---|---|---|'] + (residual or ['| — | — | 無 |'])
rep += ['', '## 三、改動行數與抽樣', '']
for f, n, d in samples:
    rep.append(f'- **{f}**：改動約 {n} 行')
    for x in d:
        rep.append(f'    - `{x[:150]}`')
os.makedirs('build', exist_ok=True)
open('build/docs_report.md', 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
print('residual', len(residual))
for f, n, _ in samples:
    print(f, n)

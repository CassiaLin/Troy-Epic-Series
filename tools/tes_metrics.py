#!/usr/bin/env python3
# SPDX-License-Identifier: MIT  (特洛伊史詩叢書工具；見 LICENSE-SOFTWARE-MIT)
# -*- coding: utf-8 -*-
"""
特洛伊史詩叢書 好讀版驗收工具（擷取規則寫在此檔）

子命令：
  metrics  逐卷指標：字數比、15字命中率、半形標點、旗標
  names    缺漏人名報告：總表人名在雙語版該卷出現、好讀版該卷未出現者（依出現次數排序）
  extract  印出某卷雙語版的「中文譯文」並附原文行號，供改寫時閱讀（比整份檔案省一半以上）
  facts    忠實度自檢：好讀版多出的總表人名、數量詞差異、雙語版明喻語境（寫完每章必跑，逐項人工處理）
  fragcheck 05冊專用：逐部核對殘篇編號是否齊全、EW 標示與版本說明數量
  lint     掃描好讀版：半形標點、已知錯誤用字（以總表為準）、工作痕跡字樣；任何一項非0都不得交付
  glossary 列出某卷出現的總表人名：譯名、穩定度、簡述、備註；同名多筆者標示（用於同名消歧義判斷）
  (向下相容) 不寫子命令時等同 metrics

範例：
  python3 tes_metrics.py metrics --bilingual B.md --readable R.md
  python3 tes_metrics.py metrics --bilingual B.md --readable R.md --chapters 卷三,卷四 --csv-out m.csv
  python3 tes_metrics.py names   --bilingual B.md --readable R.md --glossary 02_全叢書統一譯名總表.csv --chapters 卷三
  python3 tes_metrics.py extract --bilingual B.md --chapter 卷三
  python3 tes_metrics.py glossary --bilingual B.md --chapter 卷三 --glossary 02_全叢書統一譯名總表.csv

--format 預設 auto，依檔案內容辨識：
  odyssey   03冊：Tab 開頭的中文行
  indent    01/02冊：表格列「| 行 | 原文 | 中譯 |」第三欄，或兩個全形空白開頭的中文行
  aeneid    04冊：「數字＋空白＋拉丁文」行之後的中文行
  fragments 05冊：以「第X部」為單位，取中文為主的行

指標（逐卷；05冊以「部」為單位）：
  字數比   = 好讀版漢字數 ÷ 雙語版中文漢字數（雙語版先去除〔…〕行內註）
  命中率   = 好讀版（去標點）每個15字窗口，出現在同卷雙語版中文（去標點）中的比例
  半形標點 = 好讀版中半形 , : ; ! ? ( ) 的數量（中文行文應為0）
旗標：命中率>20%、字數比<0.40、半形標點>0

好讀版擷取：卷標題之後到下一卷標題之前；略過 # > 開頭行；遇「附註」「編輯註記」標題起至該卷結束不計。
"""
import re, sys, csv, argparse, json, signal
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except Exception:
    pass

GREEK = re.compile(r'[\u0370-\u03ff\u1f00-\u1fff]')
CJK = re.compile(r'[\u4e00-\u9fff]')
CH_STD = re.compile(r'^#{1,3}\s*(?:《[^》]+》|荷馬續篇|[^\s卷]*)?\s*(卷[一二三四五六七八九十]+)(?:[\s\u3000（(]|$)')
CH_FRAG = re.compile(r'^#\s*(?:05冊)?《史詩殘篇集》(第[一二三四五六七八九十]+部)')
NOTE_CUT = re.compile(r'^#{0,3}\s*(附註|編輯註記)')
NUM_LINE = re.compile(r'^(\d+[a-z]*)[\t\u3000 ]')
TABLE_ROW = re.compile(r'^\|\s*(\d+[a-z]*)\s*\|[^|]*\|(.*)\|\s*$')

# 已知錯誤用字 → 正確寫法（以總表與既往查核為準）
BAD = {
    '阿開亞人': '亞該亞人', '亞爾戈斯': '阿爾戈斯', '光耀的': '光輝的（φαίδιμος 禁用「光耀的」）',
    '頭盔閃亮的': '禁用舊譯', '板凳精良': 'γλαφυρός 誤譯，禁用', '得伊福波斯': '得伊福玻斯',
    '衣索比亞': '埃塞俄比亞', '伊利亞德': '伊里亞德（2026-11-08 決定 D1）', '史詩集成殘篇': '史詩殘篇集（D1）', '赫菲斯托斯': '赫淮斯托斯', '珀琉斯': '佩琉斯',
    '帕拉狄翁': '帕拉狄昂', '安特諾爾': '安忒諾爾', '阿斯提俄克': '阿斯堤俄克', '拉厄爾克斯': '拉厄爾刻斯',
    '雷俄克里托斯': '勒俄克里托斯', '厄佩俄斯': '埃佩伊俄斯', '杜馬斯': '狄馬斯', '波利忒斯': '波利特斯',
    '俄爾提羅科斯': '俄爾提洛科斯', '拉達曼提斯': '拉達曼堤斯', '菲羅墨勒伊得斯': '菲羅墨勒得斯',
    '阿尼俄斯': '阿尼烏斯', '波律': '波呂（波呂-系列統一用「呂」）',
    '佩涅洛佩': '潘妮洛碧', '波塞頓': '波賽頓', '埃吉斯托斯': '埃癸斯托斯', '西緒福斯': '西西弗斯', '奈琉斯': '涅琉斯',
    '忒爾摩東': '忒爾莫東', '克蕾娥帕特拉': '克蕾奧帕特拉', '塔西諾斯': '斯塔西諾斯',
    '該尼墨得斯': '伽倪墨得斯', '勒翁忒斯': '勒翁透斯', '彌刻涅': '密克涅', '珀利阿斯': '佩利阿斯', '阿法瑞俄斯': '阿法瑞斯',
    '繆斯': '繆思', '安喀塞斯': '安基塞斯',
    '艾同': '埃同', '特爾皮阿得斯': '特爾皮斯之子（Τερπιάδης 已是父稱）',
}
# 工作痕跡（讀者文件中不得出現）
TRACE = ['TES-', 'TES_', '決策日誌', '04文件', '對照版', '雙語', '底本', '批次', '待確認', '待TES', '草稿', '回報來源', '指令', 'Claude']

# 雙語版已知誤寫 → 總表寫法（僅用於人名比對前的雙語版文字，避免誤報與漏報）
NORMALIZE = {
    '俄爾提羅科斯': '俄爾提洛科斯', '波律波忒斯': '波呂波忒斯', '波魯克斯': '波呂丟刻斯', '費拉刻': '菲拉克',
    '佩利翁': '珀利翁', '波律多拉': '波呂多拉', '阿尼俄斯': '阿尼烏斯', '呂西亞': '呂基亞', '戈爾貢': '戈爾工',
    '阿開亞': '亞該亞',
    '艾同': '埃同',
    '珀利阿斯': '佩利阿斯', '忒爾摩東': '忒爾莫東', '克蕾娥帕特拉': '克蕾奧帕特拉',
    '塔西諾斯': '斯塔西諾斯', '安喀塞斯': '安基塞斯', '阿法瑞俄斯': '阿法瑞斯', '佩涅洛佩': '潘妮洛碧',
    '泰格托斯山': '塔宇革托斯山', '該尼墨得斯': '伽倪墨得斯', '安提克洛斯': '安提克羅斯', '波塞頓': '波賽頓',
    '勒翁忒斯': '勒翁透斯', '埃吉斯托斯': '埃癸斯托斯', '西緒福斯': '西西弗斯', '奈琉斯': '涅琉斯',
    '彌刻涅': '密克涅', '繆斯': '繆思', '許波普拉基亞的忒拜': '山麓忒拜',
    '卡菲里斯群礁': '凱菲柔斯礁岩',
    '波律': '波呂',
}
# 容易誤中短人名的固定片語（如「終於得以」誤中地名「於得」）
STOP = ['終於得以', '終於得到', '終於得知', '終於得見', '終於得', '黛安娜', '格拉古', '厄律曼托斯']


def mask_stop(text):
    for s in STOP:
        text = text.replace(s, '\u0000' * len(s))
    return text


def prep_names_text(text):
    for k, v in NORMALIZE.items():
        if k in v:  # 錯誤寫法是正確寫法的子字串：先遮掉正確寫法再替換
            text = text.replace(v, '\u0001').replace(k, v).replace('\u0001', v)
        else:
            text = text.replace(k, v)
    text = re.sub(r'門特(?!斯)', '門托爾', text)  # 譯名裁定：Μέντωρ 一律「門托爾」（雙語版卷二十二起寫「門特」）
    for s in STOP:
        text = text.replace(s, '\u0000' * len(s))
    return text


def cjk(s):
    return ''.join(CJK.findall(s))


def detect_format(lines):
    sample = lines[:6000]
    if any(l.startswith('\u3000\u3000') for l in sample) or any(TABLE_ROW.match(l) for l in sample):
        return 'indent'
    tab = sum(1 for l in sample if l.startswith('\t') and CJK.search(l))
    if tab > 50:
        return 'odyssey'
    lat = sum(1 for l in sample if re.match(r'^\d+[a-z]?\s[A-Za-z]', l))
    if lat > 50:
        return 'aeneid'
    return 'fragments'


def split_units(lines, fmt):
    rx = CH_FRAG if fmt == 'fragments' else CH_STD
    marks = []
    for i, l in enumerate(lines):
        m = rx.match(l.strip())
        if m:
            marks.append((i, m.group(1)))
    marks.append((len(lines), None))
    out = {}
    for k in range(len(marks) - 1):
        a, name = marks[k]
        if name not in out:
            out[name] = (a, lines[a + 1:marks[k + 1][0]])
    return out


def zh_lines(chunk, fmt, with_num=False):
    """回傳 [(原文行號或None, 中文行)]"""
    res = []
    cur = None
    for l in chunk:
        m = NUM_LINE.match(l)
        if m and (GREEK.search(l) or re.search(r'[A-Za-z]', l)):
            cur = m.group(1)
        if fmt == 'odyssey':
            if l.startswith('\t') and not GREEK.search(l):
                res.append((cur, l))
        elif fmt == 'indent':
            if l.startswith('|'):
                t = TABLE_ROW.match(l)
                if t and not GREEK.search(t.group(2)):
                    res.append((t.group(1), t.group(2)))
            elif l.startswith('\u3000\u3000') and not GREEK.search(l):
                res.append((cur, l))
        elif fmt == 'aeneid':
            s = l.strip()
            if not s or s[0] in '#>*-|' or re.match(r'^\d+[a-z]?\s', s):
                continue
            if CJK.search(s):
                res.append((cur, l))
        else:  # fragments
            s = l.strip()
            if not s or s[0] in '#>|' or re.match(r'^[-*]{3}', s):
                continue
            if len(CJK.findall(s)) >= 1 and len(CJK.findall(s)) >= len(GREEK.findall(s)):
                res.append((None, l))
    return res


def bilingual_zh(chunk, fmt, strip_notes=True):
    text = ''.join(t for _, t in zh_lines(chunk, fmt))
    if strip_notes:
        text = re.sub(r'〔[^〕]*〕', '', text)
    return text


def readable_text(chunk, quotes=True):
    """好讀版正文擷取。引文區塊（> 開頭）預設計入（去掉開頭的 >），--skip-quotes 可恢復舊行為。"""
    keep = []
    for l in chunk:
        s = l.strip()
        if NOTE_CUT.match(s):
            break
        if s.startswith('#'):
            continue
        if s.startswith('>'):
            if not quotes:
                continue
            l = s.lstrip('>').strip()
        keep.append(l)
    return '\n'.join(keep)


def masked_counts(text, names):
    """最長名稱優先計數並遮罩，避免短名（如「科斯」）誤中長名（如「俄爾提洛科斯」）之內。"""
    counts = {}
    for x in sorted(names, key=len, reverse=True):
        c = text.count(x)
        if c:
            counts[x] = c
            text = text.replace(x, '\u0000' * len(x))
    return counts


def load(path):
    return open(path, encoding='utf-8').read().split('\n')


def pick(units, chapters):
    if not chapters:
        return list(units)
    want = [c.strip() for c in chapters.split(',') if c.strip()]
    return [c for c in units if c in want]


def cmd_metrics(a):
    bl = load(a.bilingual)
    fmt = detect_format(bl) if a.format == 'auto' else a.format
    bu = split_units(bl, fmt)
    ru = split_units(load(a.readable), fmt)
    rows = []
    TB = TG = 0
    print(f"# 格式={fmt}  雙語版={a.bilingual}  好讀版={a.readable}")
    print(f"{'單位':<8}{'雙語漢字':>9}{'好讀漢字':>9}{'字數比':>8}{'命中率%':>9}{'半形標點':>9}  旗標")
    for name in pick(bu, a.chapters):
        if name not in ru:
            print(f"{name:<8} 好讀版缺此單位")
            continue
        B = cjk(bilingual_zh(bu[name][1], fmt))
        raw = readable_text(ru[name][1], not a.skip_quotes)
        G = cjk(raw)
        n = a.n
        grams = set(B[i:i + n] for i in range(len(B) - n + 1))
        tot = max(1, len(G) - n + 1)
        hit = sum(1 for i in range(len(G) - n + 1) if G[i:i + n] in grams) / tot * 100
        _core = re.sub(r'\[\^[^\]]*\]:?', '', raw)
        half = sum(_core.count(c) for c in ',:;!?()')
        ratio = len(G) / len(B) if B else 0
        flags = []
        if hit > 20: flags.append('命中率高')
        if ratio < 0.40: flags.append('字數比低')
        if half: flags.append('半形標點')
        TB += len(B); TG += len(G)
        rows.append([name, len(B), len(G), round(ratio, 3), round(hit, 1), half, '、'.join(flags)])
        print(f"{name:<8}{len(B):>9}{len(G):>9}{ratio:>8.2f}{hit:>9.1f}{half:>9}  {'、'.join(flags)}")
    print(f"{'合計':<8}{TB:>9}{TG:>9}{(TG / TB if TB else 0):>8.2f}")
    if a.csv_out:
        with open(a.csv_out, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(['單位', '雙語漢字', '好讀漢字', '字數比', '命中率%', '半形標點', '旗標'])
            w.writerows(rows)


def load_names(path):
    names = {}
    for r in csv.DictReader(open(path, encoding='utf-8')):
        x = re.sub(r'[（(].*?[）)]', '', r['現行繁中譯名']).strip()
        if 2 <= len(x) <= 8 and re.fullmatch(r'[\u4e00-\u9fff]+', x):
            names.setdefault(x, r.get('簡述背景', ''))
    return names


def cmd_names(a):
    bl = load(a.bilingual)
    fmt = detect_format(bl) if a.format == 'auto' else a.format
    bu = split_units(bl, fmt)
    ru = split_units(load(a.readable), fmt)
    names = load_names(a.glossary)
    out = []
    for name in pick(bu, a.chapters):
        if name not in ru:
            continue
        B = prep_names_text(bilingual_zh(bu[name][1], fmt))
        R = mask_stop(readable_text(ru[name][1], not a.skip_quotes))
        cb = masked_counts(B, names)
        cr = masked_counts(R, names)
        miss = sorted(((c, x) for x, c in cb.items() if x not in cr), reverse=True)
        out.append(f"## {name}　缺漏 {len(miss)} 個（總表人名在雙語版出現、好讀版未出現；族稱與一般稱謂可能為誤報，請逐一標明處置）")
        for c, x in miss:
            out.append(f"- {x}（雙語版 {c} 次）　{names[x][:40]}")
        out.append('')
    text = '\n'.join(out)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text)
        print(f"已寫入 {a.out}")
    else:
        print(text)


def cmd_extract(a):
    bl = load(a.bilingual)
    fmt = detect_format(bl) if a.format == 'auto' else a.format
    bu = split_units(bl, fmt)
    if a.chapter not in bu:
        sys.exit(f"找不到 {a.chapter}；可用單位：{list(bu)}")
    notes = [l.strip() for l in bu[a.chapter][1] if l.startswith('>')]
    if notes:
        print('【本卷註記】')
        for n in notes:
            print(n)
        print()
    for num, t in zh_lines(bu[a.chapter][1], fmt):
        t = t.strip()
        print(f"[{num}] {t}" if num else t)


def cmd_glossary(a):
    bl = load(a.bilingual)
    fmt = detect_format(bl) if a.format == 'auto' else a.format
    bu = split_units(bl, fmt)
    if a.chapter not in bu:
        sys.exit(f"找不到 {a.chapter}；可用單位：{list(bu)}")
    B = prep_names_text(bilingual_zh(bu[a.chapter][1], fmt))
    by = {}
    for r in csv.DictReader(open(a.glossary, encoding='utf-8')):
        x = re.sub(r'[（(].*?[）)]', '', r['現行繁中譯名']).strip()
        if 2 <= len(x) <= 8 and re.fullmatch(r'[\u4e00-\u9fff]+', x):
            by.setdefault(x, []).append(r)
    cb = masked_counts(B, list(by))
    items = sorted(((c, x, by[x]) for x, c in cb.items()), reverse=True)
    out = [f"# {a.chapter} 出現之總表人名 {len(items)} 個（依出現次數）；【同名多筆】者請依上下文判斷是哪一位，必要時依04文件加簡短區辨"]
    for c, x, rs in items:
        tag = f"【同名{len(rs)}筆】" if len(rs) > 1 else ''
        out.append(f"\n## {x}（{c}次）{tag}")
        for r in rs:
            out.append(f"- [{r.get('穩定度','')}|{r.get('出現冊次','')}] {r['現行繁中譯名']}：{r.get('簡述背景','')[:60]}　{r.get('備註','')[:120]}")
    text = '\n'.join(out)
    if a.out:
        open(a.out, 'w', encoding='utf-8').write(text)
        print(f"已寫入 {a.out}")
    else:
        print(text)


def lint_issues(path):
    """回傳 [(行號, 問題說明, 行首50字)]；空串列表示通過。"""
    out = []
    for i, l in enumerate(load(path), 1):
        if l.lstrip().startswith('<!--'):
            continue  # HTML 註解不計
        hits = []
        core = re.sub(r'\[\^[^\]]*\]:?', '', l)  # Markdown 註腳語法 [^1]: 不算半形標點
        h = [c for c in ',:;!?()' if c in core]
        if h:
            hits.append('半形標點 ' + ''.join(h))
        for k, v in BAD.items():
            canon = re.split(r'[（(]', v)[0].strip()
            lx = l.replace('帕爾繆斯', '\u0000' * 4)  # 帕爾繆斯（Πάλμυς，總表寫法）含「繆斯」，不算錯
            probe = lx.replace(canon, '\u0000' * len(canon)) if canon and k in canon else lx
            if k in probe:
                hits.append(f'錯誤用字「{k}」→{v}')
        if re.search(r'門特(?!斯)', l):
            hits.append('錯誤用字「門特」→門托爾（Μέντωρ；門特斯 Μέντης 不受影響）')
        for k in TRACE:
            if k in l:
                hits.append(f'工作痕跡「{k}」')
        for x in hits:
            out.append((i, x, l.strip()[:50]))
    return out


def cmd_lint(a):
    issues = lint_issues(a.readable)
    for i, x, s in issues:
        print(f"L{i}: {x}　｜{s}")
    print(f"lint 完成：{len(issues)} 項問題" + ('（可交付）' if not issues else '（修正後重跑，須為0）'))
    sys.exit(1 if issues else 0)


NUM_RX = re.compile(r'(?:[一二三四五六七八九十百千兩]{1,4}|\d+)(?:位|個|名|頭|艘|年|日|天|夜|次|匹|隻|條|座|行|塔蘭同|肘|人|件|副|張|把|支|枚|只|顆|套|層|回合|歲|城|族|輛|桶|杯|口|隊|組|枝|根|道|場|對|雙|倍|步|里)')
SIM_RX = re.compile(r'恰似|如同|宛如|彷彿|仿佛|好比|猶如|宛若|有如|就像|正如|恰如|好似|一如|猶似|像是|似的')


def _norm_num(tok):
    tok = tok.replace('兩', '二')
    tok = re.sub(r'(位|名|人|個)$', '個', tok)
    tok = tok.replace('日', '天')
    tok = re.sub(r'^一(?=[百千])', '', tok)
    return tok


def cmd_facts(a):
    bl = load(a.bilingual)
    fmt = detect_format(bl) if a.format == 'auto' else a.format
    bu = split_units(bl, fmt)
    ru = split_units(load(a.readable), fmt)
    if a.chapter not in bu or a.chapter not in ru:
        sys.exit(f"雙語版或好讀版找不到 {a.chapter}")
    B = bilingual_zh(bu[a.chapter][1], fmt)
    Bn = prep_names_text(B)
    R = readable_text(ru[a.chapter][1], True)
    Rn = mask_stop(R)
    names = load_names(a.glossary)
    cb, cr = masked_counts(Bn, names), masked_counts(Rn, names)
    print(f"# {a.chapter} 忠實度自檢（篩選用，逐項人工處理；不是結論）")
    extra = sorted(((c, x) for x, c in cr.items() if x not in cb), reverse=True)
    print(f"\n## 1. 好讀版出現、雙語版沒有的總表人名（{len(extra)}）：可能是新增、弄錯，或譯名正規化（雙語版用字與總表不同）")
    for c, x in extra:
        print(f"- {x}（好讀版 {c} 次）")
    nb = {_norm_num(x) for x in NUM_RX.findall(B)}
    nr = {_norm_num(x) for x in NUM_RX.findall(R)}
    small = re.compile(r'^[一二]個$')
    lost = sorted(x for x in nb - nr if not small.match(x))
    new = sorted(x for x in nr - nb if not small.match(x))
    print(f"\n## 2. 數量詞差異（已統一 日/天、位/名/人/個、兩/二；忽略「一個、二個」）")
    print(f"- 雙語版有、好讀版沒有：{lost}")
    print(f"- 好讀版有、雙語版沒有：{new}")
    print("\n## 3. 雙語版含明喻詞的語境（請逐一確認好讀版仍保有同一意象；「正如…所吩咐」這類比較句不是明喻，可略過）")
    for m in SIM_RX.finditer(B):
        print('- ' + re.sub(r'\s+', '', B[max(0, m.start() - 10):m.end() + 30]))


FRAG_ID = re.compile(r'^###\s*([IVXL]+(?:\s*[+＋]\s*[IVXL]+)?)(?=[\s.．（(〕]|$)')


def frag_ids(chunk):
    ids = []
    for l in chunk:
        s = l.strip()
        if not s.startswith('###'):
            continue
        if '卷首' in s[:16]:
            ids.append('卷首')
            continue
        m = FRAG_ID.match(s)
        if m:
            ids.append(re.sub(r'\s+', '', m.group(1)).replace('＋', '+'))
    return ids


def cmd_fragcheck(a):
    bu = split_units(load(a.bilingual), 'fragments')
    ru = split_units(load(a.readable), 'fragments')
    want = [x.strip() for x in a.parts.split(',') if x.strip()] if a.parts else list(bu)
    print(f"{'部':<6}{'雙語殘篇':>8}{'好讀殘篇':>8}  缺漏／多出　｜EW標示 雙語→好讀｜版本說明／提醒／說明 數")
    for name in want:
        if name not in bu:
            continue
        bi = frag_ids(bu[name][1])
        if name not in ru:
            print(f"{name:<6}{len(bi):>8}{'-':>8}  好讀版缺此部"); continue
        ri = frag_ids(ru[name][1])
        miss = [x for x in bi if x not in ri]
        extra = [x for x in ri if x not in bi]
        ewb = '\n'.join(bu[name][1]).count('EW')
        ewr = '\n'.join(ru[name][1]).count('EW')
        rt = '\n'.join(ru[name][1])
        notes = (rt.count('〔版本說明'), rt.count('〔提醒'), rt.count('〔說明'))
        print(f"{name:<6}{len(bi):>8}{len(ri):>8}  缺{miss}／多{extra}｜{ewb}→{ewr}｜{notes}")


def main():
    cmds = {'metrics', 'names', 'extract', 'glossary', 'lint', 'facts', 'fragcheck'}
    if len(sys.argv) > 1 and sys.argv[1] not in cmds and sys.argv[1].startswith('--'):
        sys.argv.insert(1, 'metrics')
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    for nm in cmds:
        p = sp.add_parser(nm)
        if nm != 'lint':
            p.add_argument('--bilingual', required=True)
        else:
            p.add_argument('--readable', required=True)
        p.add_argument('--format', default='auto', choices=['auto', 'odyssey', 'indent', 'aeneid', 'fragments'])
        if nm in ('metrics', 'names'):
            p.add_argument('--readable', required=True)
            p.add_argument('--chapters', default='')
            p.add_argument('--skip-quotes', action='store_true', help='不計入 > 引文區塊（舊行為）')
        if nm == 'metrics':
            p.add_argument('--n', type=int, default=15)
            p.add_argument('--csv-out', default='')
        if nm == 'names':
            p.add_argument('--glossary', required=True)
            p.add_argument('--out', default='')
        if nm in ('extract', 'glossary', 'facts'):
            p.add_argument('--chapter', required=True)
        if nm == 'glossary':
            p.add_argument('--glossary', required=True)
            p.add_argument('--out', default='')
        if nm == 'facts':
            p.add_argument('--readable', required=True)
            p.add_argument('--glossary', required=True)
        if nm == 'fragcheck':
            p.add_argument('--readable', required=True)
            p.add_argument('--parts', default='')
    a = ap.parse_args()
    {'metrics': cmd_metrics, 'names': cmd_names, 'extract': cmd_extract, 'glossary': cmd_glossary, 'lint': cmd_lint, 'facts': cmd_facts, 'fragcheck': cmd_fragcheck}[a.cmd](a)


if __name__ == '__main__':
    main()

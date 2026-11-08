# 特洛伊史詩叢書（繁體中文）｜Troy Epic Series

以公版原典為底本，從原文逐行翻譯的特洛伊戰爭史詩叢書。每冊收兩種譯文：

- **中文好讀版**：流暢的現代中文全文，附人物索引、同名人物對照、版本差異說明、地名表、各卷提要等附錄。
- **原文逐行對照**：希臘文或拉丁文與中文逐行對照，供讀者核對。

電子書（EPUB）把兩者合為一冊：第一部是中文好讀版，第二部是原文逐行對照。

合訂本檔案較大，GitHub 網頁無法直接顯示；要在網頁上閱讀，請用各冊的「分卷」，內容與合訂本逐字相同。

## 各冊（v2.0.0）

| 冊 | 作品 | 原文 | 中文好讀版 | 原文逐行對照 | 分卷閱讀 | 電子書 |
|---|---|---|---|---|---|---|
| 01 | 荷馬《伊里亞德》 | 希臘文 | [好讀版](01_伊里亞德/好讀版.md) | [雙語校對版](01_伊里亞德/雙語校對版.md) | [分卷](01_伊里亞德/分卷/README.md) | [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/01-iliad-v2.0.0/TroyEpic_01_Iliad_zh-TW_v2.0.0.epub) |
| 02 | 士麥那的昆圖斯《荷馬續篇》 | 希臘文 | [好讀版](02_荷馬續篇/好讀版.md) | [雙語校對版](02_荷馬續篇/雙語校對版.md) | [分卷](02_荷馬續篇/分卷/README.md) | [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/02-posthomerica-v2.0.0/TroyEpic_02_Posthomerica_zh-TW_v2.0.0.epub) |
| 03 | 荷馬《奧德賽》 | 希臘文 | [好讀版](03_奧德賽/好讀版.md) | [雙語校對版](03_奧德賽/雙語校對版.md) | [分卷](03_奧德賽/分卷/README.md) | [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/03-odyssey-v2.0.0/TroyEpic_03_Odyssey_zh-TW_v2.0.0.epub) |
| 04 | 維吉爾《埃涅阿斯紀》 | 拉丁文 | [好讀版](04_埃涅阿斯紀/好讀版.md) | [雙語校對版](04_埃涅阿斯紀/雙語校對版.md) | [分卷](04_埃涅阿斯紀/分卷/README.md) | [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/04-aeneid-v2.0.0/TroyEpic_04_Aeneid_zh-TW_v2.0.0.epub) |
| 05 | 《史詩殘篇集》（史詩集成六部殘篇） | 希臘文 | [好讀版](05_史詩殘篇集/好讀版.md) | [雙語校對版](05_史詩殘篇集/雙語校對版.md) | [分卷](05_史詩殘篇集/分卷/README.md) | [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/05-epic-cycle-v2.0.0/TroyEpic_05_Epic_Cycle_zh-TW_v2.0.0.epub) |

**附錄參考書（90 冊）：** 塞繆爾．巴特勒《奧德賽的女作者》（1897）全譯，主張《奧德賽》出自西西里一位年輕女性之手的假說性著作，作為《奧德賽》接受史的參考。
- [中文好讀版（附英文原文與 21 幅原書圖版）](90_奧德賽的女作者/中文好讀版_附原文.md)；[分章閱讀](90_奧德賽的女作者/分章/README.md)
- [EPUB](https://github.com/CassiaLin/Troy-Epic-Series/releases/download/90-odyssey-authoress-v2.0.0/TroyEpic_90_Odyssey_Authoress_zh-TW_v2.0.0.epub)

## 授權（分層）

| 內容 | 授權 |
|---|---|
| 中文好讀版、附錄、書前與編輯文字（各冊）；05 冊全書；90 冊中文譯文 | [CC BY-NC-SA 4.0](LICENSES/CC-BY-NC-SA-4.0.txt) |
| 01–04 冊原文逐行對照（雙語校對版） | [CC BY-SA 4.0](LICENSES/CC-BY-SA-4.0.txt)：所收原文取自 Perseus Digital Library，該資料以 CC BY-SA 4.0 授權 |
| 封面 | 由 AI 生成；本叢書就封面所享有的權利（如有），依 CC BY-NC-SA 4.0 授權 |
| `tools/` 程式 | [MIT](LICENSE-SOFTWARE-MIT) |
| 古典原文、公版校訂本、巴特勒原著與原書圖版 | 公版 |

詳見 [LICENSE-CONTENT.md](LICENSE-CONTENT.md)、[NOTICE.md](NOTICE.md)。以上授權說明不構成法律意見。

## 版本

- **v2.0.0（2026 年 11 月）是全新譯本**：全書依原文重新逐行翻譯，再改寫成好讀版，不是 2026 年 8 月 v1.x 版的修訂；v1.x 已封存。
- 版號規則：錯字與排版小修為修訂號，新增附錄或跨冊統一譯名為次版號，重譯或結構重大改變為主版號。每冊各自計算，Markdown 與 EPUB 共用同一個版號。見 [VERSION_STATUS.md](VERSION_STATUS.md)、[CHANGELOG.md](CHANGELOG.md)。
- 每本 EPUB 都通過 EPUBCheck 5.3.0（0 fatal／0 error／0 warning／0 info／0 usage）。雜湊見 [SHA256SUMS.txt](SHA256SUMS.txt)。

## 目錄結構

- `01_伊里亞德/` … `05_史詩殘篇集/`：各冊 `好讀版.md`、`雙語校對版.md`（合訂本），以及 `分卷/`（依卷拆開，供網頁閱讀）。
- `90_奧德賽的女作者/`：中文好讀版附英文原文、逐段對照工作檔、原書圖版，以及 `分章/`（依章拆開）。
- `covers/`：各冊封面原圖（PNG）。
- `docs/`：翻譯規則、統一譯名總表、固定修飾語對照表、成書規範、版本規則、譯名決策紀錄。
- `tools/`：EPUB 建置與檢查工具，說明見 [tools/README.md](tools/README.md)。

## 重建電子書

在倉庫根目錄執行（需要 Python 3 與 Pillow）：

```
python tools/build_epub.py --repo --tag v2.0.0
```

輸出在 `build/`。正式 EPUB 只放在 GitHub Release，不進 Git 歷史。

# tools｜建置與檢查工具（MIT）

全部用 Python 3 寫成。除特別註明外，只用標準函式庫。

| 程式 | 用途 | 用法（在倉庫根目錄執行） |
|---|---|---|
| `build_epub.py` | 從各冊 `好讀版.md`、`雙語校對版.md` 與 `covers/` 產生 EPUB 3（第一部中文好讀版、第二部原文逐行對照、書末附錄；90 冊為中文譯文加英文原文）。同一份輸入會產生位元完全相同的檔案。需要 Pillow（把封面轉成 JPEG）。 | `python tools/build_epub.py --repo --tag v2.0.0 [01 02 … 90]` → `build/` |
| `tes_metrics.py` | 好讀版的檢查工具：逐卷字數比、缺漏人名、忠實度自檢、lint（半形標點、已知錯誤用字、工作痕跡字樣）等。 | `python tools/tes_metrics.py lint --readable 01_伊里亞德/好讀版.md` |
| `build_book.py` | 把一冊的逐卷檔（`_front.md`、`卷NN.md` 或 `第N部.md`、`_appendix_X.md`）合併成合訂本，並檢查註腳完整性。本倉庫只收合訂本，逐卷檔不在倉庫裡，所以這支工具是給改作者自行分卷編修時用的。 | `python tools/build_book.py <逐卷檔資料夾> [--chapters N]` |
| `extract_90.py` | 把 Project Gutenberg 的 HTML 版《The Authoress of the Odyssey》拆成單元清單（JSON），作為 90 冊逐段對照的英文底稿。需要 BeautifulSoup（bs4）。 | `python tools/extract_90.py <html> <units.json>` |
| `verify_90.py` | 驗證 90 冊逐段對照工作檔：每個單元恰好一次、英文與底稿逐字相同、註腳錨點一致、禁用寫法與半形標點等。 | `python tools/verify_90.py <units.json> 90_奧德賽的女作者/逐段對照工作檔.md` |

說明：
- `build_epub.py` 沒有 `--repo` 時，會改讀編修期間的工作目錄結構；公開倉庫請一律加 `--repo`。
- EPUB 驗證使用 W3C 的 EPUBCheck 5.3.0（需 Java），不在本倉庫內：`java -jar epubcheck.jar <檔案.epub>`。

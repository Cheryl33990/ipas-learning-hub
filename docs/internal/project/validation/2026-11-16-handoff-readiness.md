<!--
title: 檢索原型交付整理與試用入口
status: in-review
updated: 2026-11-16
-->

# 檢索原型交付整理與試用入口

目前可交付雙科教材檢索原型及其評估證據。原完整查詢保留；同頁上限與題幹查詢實驗未採用，外部補證仍是獨立筆記。下一個必要的人工作業是試用結果判讀；提交前另需展示最終 diff 並取得授權。

## 提交範圍盤點

| 範圍 | 檔案 | 狀態 |
|---|---|---|
| 雙科檢索 | config/knowledge-base.json、src/ipas_hub/knowledge.py、cli.py、tests/test_knowledge.py | BM25／向量／混合、來源版本與合成測試 |
| 相依 | pyproject.toml、uv.lock | embedding 可選相依 |
| Docker／交付設定 | Dockerfile、compose.yaml、.dockerignore、.github/workflows/ci.yaml、delivery.yaml | 基本容器已驗證；hosted workflows 未實測 |
| 後續生成草案 | src/ipas_hub/rag.py、prompts/answer.txt | 既有連接草案；不列真實 LLM 已驗收 |
| 文件 | README.md、brief.md、progress.md、docs/internal/project/design/、本輪 validation 文件 | 評估與限制；外部證據尚未納入索引 |
| 本機資料 | data/ 全部 | 排除版控，含原文、索引、案例、診斷與試用結果 |

歷史筆記保留，當前結論以本入口及 progress 最新紀錄為準。核心來源：[缺口清單](2026-11-16-retrieval-gap-register.md)、[v2](2026-11-16-retrieval-support-v2.md)、[題幹實驗](2026-11-16-stem-query.md)、[MAE 補證](2026-11-16-mae-external-evidence.md)、[第4／40題補證](2026-11-16-fairness-mode-collapse-evidence.md)。第4題解析修訂建議待審，原解析未改。

## 本輪重新執行的驗證

版本 HEAD 5cf7d96 加目前未提交工作樹；程式與測試均保留既有版本，本輪只整理文件與 data/ 試用材料。

- Windows Python 3.14.7：`.venv/Scripts/python.exe -m pytest -p no:cacheprovider`，37 passed（0.19s）。
- Docker Desktop 引擎 29.6.2：test 目標建置成功；建置中的測試層使用快取，未將它當成本輪測試。另以 `docker run --rm --network none ipas-hub:handoff-test python -m pytest -p no:cacheprovider` 實際執行，Python 3.12.16，37 passed（0.18s）。
- `docker compose config --quiet` 成功；runtime 目標建置成功，`docker run --rm --network none ipas-hub:handoff-runtime --help` 成功。
- test 映像 config digest：4664b99bac51c568bbdda7d72373d959f2e3270d0de1e8b39c1db80dbe0f6de0；runtime：f2c13b091ea8708ed69b0d302a8f7ed29596cc1ddad09109b4a2a59df6b7d498。
- 三組 BM25 本機試用均取得五塊，保存來源與頁碼；不是人工通過。

Docker CLI 在沙箱不可見，經核准使用正常使用者環境的既有 CLI 後成功；不代表 Docker 未安裝。僅建立本專案 handoff 標籤，未啟動其他專案或 LLM 服務。本輪未重做容器真實教材建索引、embeddings 容器、hosted CI／delivery 或真實生成。

## 使用者試用

直接開啟本機 `data/review/handoff-trial/results.md`，三組原查詢及全部前五片段已備妥。方法固定 BM25、k=5、主機索引 19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108。此選擇為最容易啟動的試用路徑，不表示 BM25 品質最佳。

| 試用 | 查詢檔 | 需要你的判斷 |
|---|---|---|
| 完整題目，第10題 | 01-question.txt | 能否從前五取得有助選擇的依據？ |
| 自然語言概念查詢 | 02-concept.txt | 片段能否解答概念差異，而非只出現相近詞？ |
| 已知外部依據缺口 | 03-gap.txt | 能否辨認目前材料不足；哪些片段容易讓人誤以為已支持？ |

第10題不在八題基準，但既有50題解析已涵蓋，不能稱為從未接觸的獨立測試集。第2組為 AI 準備的使用者語氣查詢，第3組有已知缺口；此為可用性試用，不宣稱泛化成績。程式目前只回傳片段，沒有自動判定證據不足。

在 repo 根目錄的 PowerShell 可重跑任一組（只需更換檔名）：

```powershell
$env:PYTHONIOENCODING='utf-8'
.venv/Scripts/python.exe -m ipas_hub.cli search --index data/index/kb/19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108/index.json --method bm25 --k 5 --query-file data/review/handoff-trial/01-question.txt
```

每項回覆「有幫助／部分有幫助／無幫助＋一句理由」即可；AI 負責記錄及分析。使用者可以另問自己的問題，但不要直接改寫原八題基準。原文只放 data/。

2026-11-16 試用回覆補記：第1組已由使用者確認 OK（先前未注意到已取回內容，經釐清後接受）；第2／3組尚未明確回覆。公式分數結構扁平化仍為呈現改善項。原回饋及確認各自保存於 data/review/handoff-trial/，不覆寫。

## PR 準備與交接點

建議 Draft PR 標題：雙科教材檢索與 Docker 原型及支持範圍評估。內容應說明原型可查教材來源與片段、各輪負結果、外部補證未入庫及 LLM／hosted CI 限制。

本機完整工作樹差異保存在 data/review/handoff-trial/full-working-tree.patch，涵蓋 tracked diff 及未追蹤檔案；manifest-final.json 保存各變更檔 SHA-256。這是待審材料，並非已 staged 或正式獨立程式 review。後續若有修改，需重產差異及清單再請使用者批准。

目前交接給使用者的是三組試用判讀。收到回覆後，完成必要修正及最終 diff 審查，再依既有規則取得 commit／push／Draft PR 授權；本次「繼續直到需介入」不當作預先批准尚未展示的提交內容。


## 最終試用回覆與作者自查補記

第1組使用者確認 OK；第2組確認概念查詢有幫助；第3組確認教材依據仍不足，列出的 MSE 不足以回答 MAE。三組回覆均已收到，原話另存 data/review/handoff-trial/feedback-*.json。這確認試用價值與限制，不宣稱自動證據判別或完整解題已驗收。

本輪 AI 作者自查重讀檢索／CLI實作、生成草案與prompt、合成測試、Docker與兩份workflow、相依diff及交付文件。未發現阻止建立 Draft PR 的新增問題；這不是獨立真人程式審查或可直接合併結論。保留限制：公式排版可讀性、外部證據未入庫、LLM與hosted CI未實測；第4題措辭修訂仍待採用。

提交範圍為下列最終 manifest 中列出的29個檔案；未含data原文或任何本機評估輸出。PR草稿在 data/review/handoff-trial/pr-body.md，最終差異在 full-working-tree-final.patch，版本清單在 manifest-for-approval.json。舊 manifest-final.json／full-working-tree.patch 保留為先前快照，不作本次批准依據。

本輪尚未stage、commit、push或建立PR；現在可請使用者針對最終差異批准這三項操作。合併與公開不包含在該請求內。

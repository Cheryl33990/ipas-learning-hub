<!--
title: 勞動基準法獨立知識庫
status: in-review
updated: 2026-11-17
-->

# 勞動基準法獨立知識庫

> 內部紀錄：2026-11-18 起公開文件只保留 iPAS 範例，本頁移到 internal 保存；勞基法設定與路由仍可使用。路由未指定 profile 時使用通用設定，不再帶 iPAS 身份。

本案例驗證一般 PDF 匯入、不同知識庫的搜尋隔離與文件引用。僅涵蓋指定 PDF，不包含施行細則、函釋、判決或其他勞動法規；文件問答不等於完整法律判斷。第一輪關閉外部搜尋。

## 來源與版本

- [官方所有條文頁](https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=N0030001)，頁面與 PDF 標示民國 113 年 07 月 31 日修正。
- [官方 PDF 下載入口](https://law.moj.gov.tw/LawClass/FilesType.aspx?DataId=N0030001&md=m)，取得日期 2026-11-17。
- 本機 PDF：`data/raw/labor-law/labor-standards-act.pdf`；19 頁、302,061 bytes，SHA-256 記在 [設定檔](../../../../config/knowledge-base.labor-law.json)。原始檔與本機 manifest 不進版控。
- 官方下載入口可能隨修法更新。新版本應另核對、更新設定並建新索引，不自動略過 SHA-256 驗證；本案例沒有自動更新法規功能。

## 重現下載與建索引

先完成 [新手手冊](../../../setup.md) 的工具、套件、bge-m3 與資料庫準備，再於專案根目錄 PowerShell 執行：

```powershell
$cfg = Get-Content config/knowledge-base.labor-law.json -Raw -Encoding UTF8 | ConvertFrom-Json
$source = $cfg.sources[0]
New-Item -ItemType Directory -Force (Split-Path $source.pdf) | Out-Null
Invoke-WebRequest $source.download_url -OutFile $source.pdf
if ((Get-FileHash -LiteralPath $source.pdf -Algorithm SHA256).Hash.ToLower() -ne $source.sha256) {
  throw '官方 PDF 已變更，請先核對來源與版本，不要直接更改雜湊。'
}
$env:PG_DSN = 'host=127.0.0.1 port=5433 dbname=ipas user=ipas'
$env:PGPASSWORD = (Select-String '^PG_PASSWORD=(.*)' .env).Matches[0].Groups[1].Value
uv run python -m ipas_hub.cli index --config config/knowledge-base.labor-law.json --embedding-model BAAI/bge-m3 --to-pg
```

本機已建置的版本：`6f1226f8141db00bb31356bbb69991263284768b0be4ca0f2a1564f5d27abadb`，51 個片段、每個向量 1,024 維，已載入本機 pg。index_id 包含程式版本與檔案識別，別人的新建索引不必與此相同。

## 選擇知識庫與查詢

```powershell
uv run python -m ipas_hub.cli search --store pg --kb labor-law --method hybrid --query '雇主要保存出勤紀錄多久？'
uv run python -m ipas_hub.cli search --store pg --kb ipas --method hybrid --query '什麼是詞性標註？'
```

`--kb` 選文件群組；`--index` 可固定某次資料版本；兩個一起指定會核對是否同庫。歷史沒有 knowledge_base 欄位的 iPAS 索引視為 ipas，不需修改舊索引。

重要相容變更：資料庫有多個庫後，不能只靠全域「最新載入」決定查哪個庫。原本 `serve --store pg` 下次重啟請加 **`--kb ipas`**。已啟動的 8100 程序已固定舊索引，不會自動切換。多庫時省略 --kb／--index 會拒絕，不默默改搜勞基法。

## 聊天與 AnythingLLM 工作區

沿用既有 vLLM，不另啟動第二份生成模型。另開 PowerShell、重設上方 PG_DSN／PGPASSWORD，再執行：

```powershell
$env:LLM_MODEL = 'qwen3-vl-8b-fp8'
uv run python -m ipas_hub.cli serve --store pg --kb labor-law --web none --port 8101 --served-name labor-law
```

AnythingLLM 本版本的 Generic OpenAI Base URL 是全域共用，工作區只能獨立選模型，不能在各工作區填不同URL。要同時使用 iPAS 與勞基法，請改用共用入口（不要同時在8100啟動單庫服務）：

```powershell
uv run python -m ipas_hub.cli serve --store pg --routes config/rag-routes.json --port 8100 --model qwen3-vl-8b-fp8
```

路由設定 `rag` 對應 ipas（維基開啟）、`labor-law` 對應 labor-law（外搜關閉）。未知或未指定模型會拒絕，沒有預設跨庫退回。各模型啟動時固定索引，更新資料後仍須重啟。

在 AnythingLLM 使用「勞基法」工作區，模型供應者為 Generic OpenAI、工作區模型為 labor-law；共用 Base URL 沿用既有8100：

| 欄位 | 值 |
|---|---|
| Provider | OpenAI (Generic) |
| Base URL（全域、UI 容器使用） | `http://host.docker.internal:8100/v1` |
| Model | `labor-law` |
| API key | `local` |
| Context／token limit | `6144` |

工作區不需再上傳 PDF。已透過本機 AnythingLLM API 啟用既有勞基法工作區、設定 chatMode=chat 並實際提問；沒有修改原 rag 工作區或全域供應者設定。瀏覽器控制無法還原最小化視窗，未目視 UI；工作區頁面HTTP、工作區聊天API、對應data/runs與PDF連結均已驗證。

已啟用的[勞基法工作區](http://localhost:3001/workspace/d4b98ca9-b52c-45ef-8b48-fad9c0991f6a)（本機個別實例的slug，其他電腦會不同）。目前共用8100服務由本輪啟動，vLLM／ui／db沿用；重開機後仍需啟動服務。

可先問「勞工正常工作時間每日、每週的上限是多少？」確認回答顯示 `[文件n]`、文件修正版本及可點的 PDF 頁連結。回答中的 PDF 頁序不是法條條號。

## 本輪證據與限制

- 受測版本：main c4bd89d 加本輪未提交程式；索引 code_sha256 保存實際程式識別。
- 合成／資料庫測試：132 passed，含真實 pg 的獨立 schema 與 CLI 分庫測試。首次提權測試因 pytest 暫存權限失敗，改到專案 data/test-tmp 的新目錄後重跑；中途 2 個 FakeKB 缺新欄位的失敗修正後全通過。
- 真實混合搜尋管線題：工時、出勤紀錄、特休、服務證明書共 4 題，前五回傳均含預期頁（7／8／10／5），且回傳只屬 labor-law。這些是依文件建立的開發驗證題，非保留測試集或品質百分比宣稱。
- 既有五科 iPAS 索引 ce5090f4… 保留，資料庫／檔案的「詞性標註」BM25 結果一致；兩庫存在而未選範圍會拒絕。
- 沿用本機 vLLM、web none 實跑工時 1 題，回傳 supported，引用 PDF 第 7 頁，字詞警告 0。這是結構與管線檢查，法律正確性未經人工驗收。測試 HTTP 回答含文件標記與頁連結，PDF 回傳內容與來源檔完全相同；測試伺服器已停止，不影響 8100。
- 證據只在 `data/evaluation/labor-law/`：pipeline_cases.json、pipeline_report.json、answer.json、verify_pipeline.py；不與 iPAS 評估混合、不把問題或答案放入索引。
- 目前按頁內 400 字、步長 300 切塊；跨頁條文與標題可能斷開，尚未依條／項完整切分。無文字的 PDF 拒絕建立索引；掃描 PDF／OCR、複雜圖表不在本輪支援。

## 工作區啟用後補充驗證

- 新增共用模型路由後全套138 passed（含本機pg），涵蓋非串流／串流選庫、未知模型拒絕、同名來源的模型前綴檔案連結、每庫外搜政策及不合法設定。未跑本批hosted CI。
- 經AnythingLLM的2題：出勤紀錄題引用第8頁並回答五年；工時題引用第7頁，但對變形工時補充概括過度，字詞警告0仍未抓出此語意問題，明列為內容缺陷而非全部正確。未改prompt或刪除失敗對話來掩蓋結果。
- 實際data/runs確認labor-law、web none；工作區SSE、設定前備份及驗證在data/evaluation/labor-law/workspace_*。iPAS工作區chatProvider／chatModel／chatMode／prompt設定前後相同，兩種PDF連結均可讀。
- 此次路由更新沿用前輪索引6f1226f8…；索引code_sha256仍代表建索引當時版本，新router執行版本由本輪工作樹與執行紀錄補記，不改寫舊索引識別。

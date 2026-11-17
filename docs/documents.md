<!--
title: 一般 PDF 快速開始
status: in-review
updated: 2026-11-17
-->

# 一般 PDF 快速開始

先用自己的可擷取文字 PDF 跑通「匯入 → 檢索 → 頁碼」，不需要 GPU、資料庫或外部服務。以下在 repo 根目錄的 Windows PowerShell 執行；需已安裝 uv。請先把一份可使用的 PDF 放在 `data/raw/my-docs/manual.pdf`。這是使用者自備輸入，不附範例原文。

## 1. 安裝並建立來源設定

```powershell
uv sync --locked
if ($LASTEXITCODE -ne 0) { throw '安裝失敗' }
$documentPath = 'data/raw/my-docs/manual.pdf'
if (-not (Test-Path -LiteralPath $documentPath)) { throw '請先放入自己的文字型 PDF' }
$documentHash = (Get-FileHash -LiteralPath $documentPath -Algorithm SHA256).Hash.ToLower()
$documentConfig = @{
  schema_version = 1
  knowledge_base = 'my-docs'
  chunk_size = 400
  chunk_stride = 300
  sources = @(@{
    id = 'manual'
    name = '我的文件'
    version = 'local-v1'
    pdf = $documentPath
    sha256 = $documentHash
    parser = 'pdf'
  })
}
$configPath = Join-Path (Get-Location) 'data/my-docs.config.json'
if (Test-Path -LiteralPath $configPath) { throw '設定已存在，請先檢查既有版本，不覆寫' }
[System.IO.File]::WriteAllText($configPath, ($documentConfig | ConvertTo-Json -Depth 5), (New-Object System.Text.UTF8Encoding($false)))
```

設定留在不進版控的 data/，不暴露自有文件名稱。`knowledge_base` 使用 1–64 個小寫英數字、底線或連字號，第一字須為英數字；同庫內每個來源 id 必須唯一。`version` 應填實際文件版本；有來源網址／取得日期可加入 `url`／`retrieved_at`。新檔才計算新雜湊，不應用改雜湊掩蓋既有文件意外變動。

## 2. 建索引與檢索

```powershell
$indexOutput = uv run python -m ipas_hub.cli index --config data/my-docs.config.json
if ($LASTEXITCODE -ne 0) { throw '建索引失敗，請先檢查 PDF 與錯誤訊息' }
$documentIndex = ($indexOutput | ConvertFrom-Json).index
uv run python -m ipas_hub.cli search --index $documentIndex --kb my-docs --method bm25 --query '文件中想查的詞' --k 5
if ($LASTEXITCODE -ne 0) { throw '檢索失敗' }
```

將查詢改成文件中的實際內容。成功時 `knowledge_base` 為 my-docs，hits 的來源為 manual，`pdf_page` 對應 PDF 從 1 起算的頁序。人工開檔核對片段，找到頁碼不等於片段足以回答問題。無文字的 PDF 會建索引失敗；掃描檔應先另行 OCR，目前沒有內建流程。

## 3. 可選：向量、生成與介面

混合檢索先依 [新手手冊](setup.md) 安裝 embeddings 與下載模型，再重建索引：

```powershell
$indexOutput = uv run python -m ipas_hub.cli index --config data/my-docs.config.json --embedding-model BAAI/bge-m3
if ($LASTEXITCODE -ne 0) { throw '向量索引建立失敗' }
$documentIndex = ($indexOutput | ConvertFrom-Json).index
uv run python -m ipas_hub.cli search --index $documentIndex --kb my-docs --method hybrid --query '文件中想查的問題'
```

需先完成本機 LLM 設定並確認服務可用，才執行以下生成／介面命令。`LLM_MODEL` 必須與端點提供的模型名稱一致；既有 Compose 預設名稱是 qwen3-vl-8b-fp8。

```powershell
$env:LLM_MODEL = 'qwen3-vl-8b-fp8'
uv run python -m ipas_hub.cli ask --index $documentIndex --kb my-docs --web none --query '文件中想查的問題' --format text
# 另開終端機時需重新設定 documentIndex 為上述回傳的 index.json 路徑
uv run python -m ipas_hub.cli serve --index $documentIndex --kb my-docs --web none --served-name my-docs --port 8102
```

8102 是本例獨立端點，避免占用既有 8100；serve 會持續運作，Ctrl+C 停止。用 OpenAI 相容客戶端連 `http://127.0.0.1:8102/v1`、模型名稱 my-docs。既有 AnythingLLM 多工作區共用 Base URL 時，不應任意改它；沿用 [共用路由方式](examples/labor-law.md)，將索引載入 pg 並加入對應 model／knowledge_base／web 路由。

生成 prompt 尚有 iPAS 身份設定；本例證明可接文件管線，不宣稱新領域回答已驗收。外搜先關閉，模型仍只能依提供證據回答。PDF、索引和含片段的執行紀錄都保留在 data/，測試題及預期答案應另外存放，不能加入檢索文件。

## 4. 版本更新與驗證

更新文件時保留舊 PDF 與設定，使用新路徑、版本及雜湊建新索引；不要覆蓋舊檔後期待舊引用仍可用。file 模式明確指定 index.json；pg 模式可固定 index_id，`--kb` 只決定庫範圍。serve 在啟動時選定索引，載入新版本後要重啟才使用新版本。

本輪只核對命令與程式契約、執行現有合成測試；未替使用者放入真實新文件或重新下載模型。後續需對自己的文件實際檢查：文字是否完整、頁碼是否正確、有依據題是否回答、庫外題是否合理拒答。

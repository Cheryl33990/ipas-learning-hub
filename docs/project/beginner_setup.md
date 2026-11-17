---
title: Windows 新手操作手冊
status: in-review
updated: 2026-11-17
---

# Windows 新手操作手冊

目標是先找到教材片段，再啟用本機聊天。所有命令在專案根目錄的 PowerShell 執行；不要把 `PS>` 提示符也貼進去。這是依目前程式與設定整理的手冊，尚未由完全新手在乾淨電腦完整驗證。遇到錯誤先停在該步，不要把後面全部貼完。

## 1. 準備電腦與專案

- 安裝並啟動 [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/)，使用 Linux containers。
- 安裝 [Git for Windows](https://git-scm.com/downloads/win) 與 [uv](https://docs.astral.sh/uv/getting-started/installation/)。uv 管理 Python 與套件；安裝後重開 PowerShell。
- 搜尋教材只需 CPU；本機聊天另需相容 NVIDIA GPU。既有電腦使用 16 GB 顯存，模型服務設定約需 10 GB；其他硬體未驗證。模型、套件與 Docker 映像需要額外磁碟空間，不能把嵌入模型大小當全部安裝容量。

```powershell
git clone https://github.com/Cheryl33990/ipas-learning-hub.git
cd ipas-learning-hub
git rev-parse --short HEAD
docker version
uv --version
uv sync --locked --extra pg --extra embeddings
```

repo 目前為 private，clone 需要有存取權的 GitHub 帳號。已有專案時，進入既有資料夾即可。`docker version` 必須同時顯示 Client 與 Server。

## 2. 下載五科教材

以下從官方下載，設定檔決定檔名與儲存位置。教材不在 Git 裡。

```powershell
$base = 'https://www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/'
$cfg = Get-Content config/knowledge-base.no-errata.json -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($s in $cfg.sources) {
  New-Item -ItemType Directory -Force (Split-Path $s.pdf) | Out-Null
  Invoke-WebRequest ($base + (Split-Path $s.pdf -Leaf)) -OutFile $s.pdf
  if ((Get-FileHash -LiteralPath $s.pdf -Algorithm SHA256).Hash.ToLower() -ne $s.sha256) {
    throw "教材版本不符：$($s.id)"
  }
}
```

成功：五個檔案都下載完，沒有出現版本不符。官方若更換檔案，保留錯誤並回報，不要為了通過而改雜湊。

本手冊使用「無勘誤替換檔」設定：可獨立重現，但文字尚未套用官方勘誤，回答可能引用更正前內容。已有經核對的四份本機替換檔，才改用 `config/knowledge-base.json`；細節見 [README](../../README.md)。兩種索引的內容與識別不同。

## 3. 下載嵌入模型

嵌入模型把問題和教材轉成可比較的數字向量，不負責產生回答。

```powershell
uv run hf download BAAI/bge-m3 --exclude "onnx/*" --exclude "imgs/*" --exclude "*.jpg" --exclude "*.pt"
```

這一步需要網路，下載量與既有快取有關；請等命令結束。之後本專案只離線讀取快取。不要手動刪除快取內個別檔案。[Hugging Face CLI 說明](https://huggingface.co/docs/huggingface_hub/main/guides/cli)

## 4. 啟動資料庫並建立索引

用編輯器在專案根目錄建立 `.env`，先只需填入以下內容，把範例密碼換成自己的英數字密碼；檔名不是 `.env.txt`。已有 `.env` 時加入所缺欄位，不覆寫原內容。

```dotenv
PG_PASSWORD=ReplaceWithYourOwnPassword
```

```powershell
docker compose --profile db up -d db
docker compose ps db
$env:PG_DSN = 'host=127.0.0.1 port=5433 dbname=ipas user=ipas'
$env:PGPASSWORD = (Select-String '^PG_PASSWORD=(.*)' .env).Matches[0].Groups[1].Value
uv run python -m ipas_hub.cli index --config config/knowledge-base.no-errata.json --embedding-model BAAI/bge-m3 --to-pg
```

等資料庫顯示 healthy，再執行建索引；CPU 建向量可能需要數分鐘。成功輸出會包含 `index_id` 與資料庫載入結果，請保留。資料存於 Docker volume；檔案索引在 `data/index/kb/`。不要刪 volume 來解決連線問題。

## 5. 先確認混合搜尋可用

```powershell
uv run python -m ipas_hub.cli search --store pg --kb ipas --method hybrid --query "什麼是詞性標註？" --k 5
```

成功：回傳教材片段、教材名稱、頁碼與 `index_id`；這一步不用 GPU 或生成模型。確認來源有初級與中級五科；單次問題不一定會命中全部科目。

若要在 DBeaver 看資料，建立 PostgreSQL 連線：host `127.0.0.1`、port `5433`、database／user 都是 `ipas`，密碼為 `.env` 的 `PG_PASSWORD`。展開 `Schemas → public → Tables`：`kb_index` 是索引版本、`kb_source` 是教材、`kb_chunk.embedding` 是向量。純檢視不需要改資料。

## 6. 準備生成模型（首次安裝才做）

既有電腦已下載模型時，先確認既有 Docker volume 與 `.env` 的 `LLM_MODEL_VOLUME`，直接沿用，避免重複下載。完全新機可用以下候選路徑建立獨立快取；此下載路徑尚未在全新電腦實跑，不當作已通過的安裝步驟，詳見 [AI 架設指引](ai_setup.md)。

```powershell
docker volume create ipas-llm-models
docker run --rm -v ipas-llm-models:/hf python:3.12-slim sh -c 'pip install huggingface_hub && hf download Qwen/Qwen3-VL-8B-Instruct-FP8 --revision 9cdc6310a8cb770ce18efaf4e9935334512aee45 --cache-dir /hf/hub'
```

此步會下載額外映像、套件與大型生成模型；時間與容量尚未實測，請先檢查磁碟。下載失敗可先保留第 5 步的教材搜尋功能。新下載 volume 的路徑與檔案完整性須由實際啟動確認。

在 `.env` 加上（若沿用既有 volume，填其名稱）：

```dotenv
LLM_MODEL_VOLUME=ipas-llm-models
```

## 7. 啟動聊天

```powershell
docker compose --profile llm up -d vllm
docker compose logs --tail 40 vllm
```

等模型完成載入，再確認模型 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/models
$env:LLM_MODEL = 'qwen3-vl-8b-fp8'
uv run python -m ipas_hub.cli serve --store pg --kb ipas
```

最後一行會持續執行，請保持視窗開啟。另開一個 PowerShell 回到專案資料夾：

```powershell
docker compose --profile ui up -d ui
```

瀏覽器開 `http://localhost:3001`，依畫面完成首次設定並建立工作區。模型供應者應為 OpenAI (Generic)，值與 compose 相同：

| 欄位 | 值 |
|---|---|
| Base URL（UI 容器使用） | `http://host.docker.internal:8100/v1` |
| Model | `rag` |
| API key | `local` |
| Context／token limit | `6144` |

既有 UI 儲存設定可能蓋過環境變數，請在設定頁核對。這裡填的是本專案 RAG 端點；直接連 8000 會略過本專案教材檢索。詳見 [AnythingLLM Generic OpenAI 說明](https://docs.useanything.com/setup/llm-configuration/cloud/openai-generic)。

工作區不要上傳教材，直接提問。成功判準：回答有教材／外部依據，教材連結可開到對應 PDF 頁；證據不足時可能拒答。`http://127.0.0.1:8100` 是 API 說明頁，聊天介面在 3001。

## 8. 下次啟動、停止與排錯

下次不用重建索引：啟動 Docker Desktop，啟動 db、vllm、ui，於新的 PowerShell 重設第 4 步的 `PG_DSN`／`PGPASSWORD` 及第 7 步的 `LLM_MODEL`，再執行 `serve --store pg --kb ipas`。`.env` 不會自動變成主機 Python 的環境變數。加入第二個庫後，請明確指定 --kb 或 --index，不能再依全域最新索引猜測範圍。

停止：serve 視窗按 Ctrl+C，再執行：

```powershell
docker compose --profile llm --profile ui --profile db stop
```

| 情況 | 先檢查 |
|---|---|
| Docker 連不上 | Docker Desktop 是否已啟動、`docker version` 是否有 Server |
| 5433 被占用 | `.env` 增加 `PG_PORT=5434`，重建 db 容器，主機 PG_DSN／DBeaver 同改 5434 |
| 密碼錯誤 | 是否使用初始化資料庫時的密碼；改 `.env` 不會自動改既有資料庫帳號密碼 |
| 找不到嵌入模型 | 第 3 步是否下載到目前使用者的快取；不要靠重下載整個 repo 排錯 |
| vLLM 模型不在快取 | volume 名稱、固定 revision 與 `/hf/hub` 結構是否一致 |
| GPU 記憶體不足 | 先停止占用 GPU 的工作；保留錯誤訊息，不宣稱所有 GPU 均可用 |
| UI 回答無教材引用 | Base URL 是否指向 8100/v1、模型是否為 rag |
| 更新索引後仍用舊資料 | Ctrl+C 停止 serve 後重啟；執行中的程序不會自動換索引 |

完整新手驗證尚待實際找一位新使用者，依本手冊逐步操作，記錄卡點與最終版本。已存在快取的作者電腦通過，不代表新機安裝通過。

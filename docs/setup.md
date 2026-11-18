<!--
title: Windows 新手操作手冊
status: in-review
updated: 2026-11-18
-->

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

已有專案時，進入既有資料夾即可。`docker version` 必須同時顯示 Client 與 Server。

## 2. 下載五科教材

以下從官方下載，設定檔決定網址、檔名、儲存位置與預期的 SHA-256。教材不在 Git 裡；`fetch` 只用 https，已存在且雜湊相符的檔案會跳過，雜湊不符就不留下檔案。

```powershell
uv run python -m ipas_hub.cli fetch --config examples/ipas/knowledge-base.no-errata.json
```

成功：五個來源都顯示 `downloaded` 或 `present`。官方若更換檔案，保留錯誤並回報，不要為了通過而改雜湊。

本手冊使用「無勘誤替換檔」設定：可獨立重現，但文字尚未套用官方勘誤，回答可能引用更正前內容。已有經核對的四份本機替換檔，才改用 `examples/ipas/knowledge-base.json`；替換檔位置由該設定的 patches 欄位指定，每檔為含 id、old、new 的陣列，缺檔或替換字串未命中會停止建索引。替換檔含教材原文，不進版控；兩種索引的內容與識別不同。

## 3. 下載嵌入模型

嵌入模型把問題和教材轉成可比較的數字向量，不負責產生回答。

```powershell
uv run hf download BAAI/bge-m3 --exclude "onnx/*" --exclude "imgs/*" --exclude "*.jpg" --exclude "*.pt"
```

這一步需要網路，下載量與既有快取有關；請等命令結束。之後本專案只離線讀取快取。不要手動刪除快取內個別檔案。[Hugging Face CLI 說明](https://huggingface.co/docs/huggingface_hub/main/guides/cli)

## 4. 啟動資料庫並建立索引

在專案根目錄由範本建立 `.env`，再用編輯器把 `PG_PASSWORD=` 後面的 `<choose-a-strong-password>` 換成自己的英數字密碼；其他行先維持註解即可。已有 `.env` 時不要覆寫，只從 [.env.example](../.env.example) 補上所缺欄位。所有環境變數的用途、是否必填與預設值都列在 `.env.example`。

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
notepad .env
```

```powershell
docker compose --profile db up -d db
docker compose ps db
$env:PG_DSN = 'host=127.0.0.1 port=5433 dbname=ipas user=ipas'
$env:PGPASSWORD = (Select-String '^PG_PASSWORD=(.*)' .env).Matches[0].Groups[1].Value
uv run python -m ipas_hub.cli index --config examples/ipas/knowledge-base.no-errata.json --embedding-model BAAI/bge-m3 --to-pg
```

等資料庫顯示 healthy，再執行建索引；CPU 建向量需要數分鐘（作者電腦約 6 分鐘）。成功輸出會包含 `index_id` 與資料庫載入結果，請保留。資料存於 Docker volume；檔案索引在 `data/index/kb/`。不要刪 volume 來解決連線問題。

## 5. 先確認混合搜尋可用

```powershell
uv run python -m ipas_hub.cli search --store pg --kb ipas --method hybrid --query "什麼是詞性標註？" --k 5
```

成功：回傳教材片段、教材名稱、頁碼與 `index_id`；這一步不用 GPU 或生成模型。確認來源有初級與中級五科；單次問題不一定會命中全部科目。

若要在 DBeaver 看資料，建立 PostgreSQL 連線：host `127.0.0.1`、port `5433`、database／user 都是 `ipas`，密碼為 `.env` 的 `PG_PASSWORD`。展開 `Schemas → public → Tables`：`kb_index` 是索引版本、`kb_source` 是教材、`kb_chunk.embedding` 是向量。純檢視不需要改資料。

## 6. 準備生成模型（首次安裝才做）

既有電腦已下載模型時，先確認既有 Docker volume 與 `.env` 的 `LLM_MODEL_VOLUME`，直接沿用，避免重複下載。完全新機可用以下候選路徑建立獨立快取；此下載路徑尚未在全新電腦實跑，不當作已通過的安裝步驟，詳見 [AI 架設指引](internal/project/ai_setup.md)。

```powershell
docker volume create ipas-llm-models
docker run --rm -v ipas-llm-models:/hf python:3.12-slim sh -c 'pip install huggingface_hub && hf download Qwen/Qwen3-VL-8B-Instruct-FP8 --revision 9cdc6310a8cb770ce18efaf4e9935334512aee45 --cache-dir /hf/hub'
```

此步會下載額外映像、套件與大型生成模型；時間與容量尚未實測，請先檢查磁碟。下載失敗可先保留第 5 步的教材搜尋功能。新下載 volume 的路徑與檔案完整性須由實際啟動確認。

volume 名稱是預設的 `ipas-llm-models` 時不需改 `.env`；沿用其他名稱的既有 volume 時，取消 `.env` 中 `LLM_MODEL_VOLUME` 那行的註解並填入名稱：

```dotenv
LLM_MODEL_VOLUME=<docker-volume-name>
```

## 7. 啟動聊天

### 方法 A：全部用 Docker 啟動（建議）

RAG 端點也在容器內執行，不必另開視窗。容器要用第 3 步下載的嵌入模型，先在 `.env` 加一行，指向自己的 Hugging Face 快取資料夾（唯讀掛入，容器不會下載模型）：

```dotenv
HF_CACHE_DIR=C:/Users/<你的使用者名稱>/.cache/huggingface
```

```powershell
docker compose --profile serve --profile ui up -d
docker compose logs --tail 40 vllm serve
```

`serve` profile 會一併啟動 db、vllm 與 RAG 端點；第一次會建立含嵌入模型套件的映像（約 3 GB，作者電腦約 2 分鐘）。等 serve 的紀錄出現「多知識庫端點」，再確認：

```powershell
Invoke-RestMethod http://127.0.0.1:8100/v1/models
```

應列出 `rag`。端點預設使用 [examples/ipas/routes.json](../examples/ipas/routes.json)（只有 iPAS），只公開在本機 127.0.0.1；已另外建立其他知識庫（見[自訂資料](custom-data.md)）時，在 `.env` 設 `RAG_ROUTES`，例如 `config/rag-routes.json`。路由列出的知識庫都必須已建索引並載入，否則端點會在啟動時停止。

### 方法 B：在主機執行端點

適合修改程式時測試，程式改完不必重建映像。

```powershell
docker compose --profile llm up -d vllm
docker compose logs --tail 40 vllm
```

等模型完成載入，再確認模型 API：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/models
$env:LLM_MODEL = 'qwen3-vl-8b-fp8'
uv run python -m ipas_hub.cli serve --store pg --kb ipas --profile examples/ipas/profile.json
```

最後一行會持續執行，請保持視窗開啟。另開一個 PowerShell 回到專案資料夾：

```powershell
docker compose --profile ui up -d ui
```

兩種方法都使用 8100 埠，同時只能執行一種。

### 設定聊天介面

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

下次不用重建索引：啟動 Docker Desktop。方法 A 只要執行 `docker compose --profile serve --profile ui up -d`；程式更新後加上 `--build` 重建端點映像。方法 B 啟動 db、vllm、ui，於新的 PowerShell 重設第 4 步的 `PG_DSN`／`PGPASSWORD` 及第 7 步的 `LLM_MODEL`，再執行 `serve --store pg --kb ipas --profile examples/ipas/profile.json`。`.env` 只由 Docker Compose 讀取，不會自動變成主機 Python 的環境變數（見 `.env.example` 的 B 區）。加入第二個庫後，請明確指定 --kb 或 --index，不能再依全域最新索引猜測範圍。

停止：方法 B 先在 serve 視窗按 Ctrl+C，再執行：

```powershell
docker compose --profile llm --profile ui --profile db --profile serve stop
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
| 更新索引後仍用舊資料 | Ctrl+C 停止 serve 後重啟（方法 A：`docker compose restart serve`）；執行中的程序不會自動換索引 |
| serve 容器啟動失敗、找不到嵌入模型 | `.env` 的 `HF_CACHE_DIR` 是否指向含 `hub/models--BAAI--bge-m3` 的資料夾；`docker compose logs serve` 看錯誤 |
| 8100 被占用 | 方法 A 與 B 是否同時在跑；只保留一種 |

2026-11-18 作者電腦重新 clone 到新資料夾，依本手冊執行第 1–5 步與第 7 步方法 A（全新資料庫；套件、嵌入模型、生成模型與 Docker 映像沿用既有快取，第 6 步未執行），全部通過；過程中發現預設路由含未建立的知識庫，已修正。完整新手驗證仍待實際找一位新使用者在乾淨電腦依本手冊操作；作者電腦通過不代表新機安裝通過。

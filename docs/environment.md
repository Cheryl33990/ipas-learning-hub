<!--
title: 實際硬體與執行環境
status: in-review
updated: 2026-11-17
-->

# 實際硬體與執行環境

## 作者實際使用配置

以下為 **2026-11-17 本機唯讀查核**，是本專案的開發／自用環境，不是最低硬體需求，也不表示同一配置在其他資料量下有相同效能。

| 項目 | 實際配置 |
|---|---|
| CPU | AMD Ryzen 7 9800X3D，8 核心／16 執行緒 |
| RAM | 安裝 32 GiB；Windows 回報可用於系統的總實體記憶體約 31.1 GiB（不是當下剩餘量） |
| GPU | NVIDIA GeForce RTX 5070 Ti，標稱 16 GB；nvidia-smi 回報 16,303 MiB |
| NVIDIA 驅動 | 610.88 |
| OS | Windows 11 專業版，build 26200 |
| 本機 Python | 3.14.7（目前 .venv）；容器／CI 使用 3.12 |
| Docker Desktop | 4.83.0.234302，Linux containers |
| Docker Engine／CLI | 29.6.2／29.6.2 |
| Docker Compose | 5.3.1 |
| 本機 uv | 0.12.20；Docker／CI 固定 0.9.11 |

CPU／RAM／OS 以 Windows CIM 查核，GPU／驅動以 nvidia-smi 查核，工具版本以各 CLI／執行檔資訊查核。不收錄電腦名稱、序號、帳號、IP 或裝置 ID。硬碟容量／完整安裝占用未量測；不把模型檔案大小當作全部磁碟需求。

## 模型如何分配到硬體

| 工作 | 執行位置與配置 |
|---|---|
| PDF 解析、BM25、融合排序 | 主機 Python／CPU |
| Embedding | BAAI/bge-m3，現行 encoder 固定 CPU；向量為 1,024 維 |
| 向量距離查詢 | Docker 內 PostgreSQL＋pgvector；資料庫查詢不使用 GPU |
| 回答生成 | Docker 內 vLLM，使用 NVIDIA GPU；Qwen3-VL-8B-Instruct-FP8，只載入文字部分 |
| 聊天 UI | Docker 內 AnythingLLM，呼叫主機 RAG 端點 |

目前 Compose 的生成配置：上下文上限 6,144、KV cache FP8、GPU memory utilization 0.62、max-num-seqs 4、enforce-eager，並啟用 WSL2 pinned memory。這些是設定值，不是四人並行容量或實際使用量保證；來源為 [compose.yaml](../compose.yaml)。模型 revision 與映像 digest 也固定在該檔，授權見 [第三方清單](../THIRD_PARTY_NOTICES.md)。

過去本機載入觀察約 125–130 秒、模型權重占用約 9.12 GiB，為歷史單次環境記錄，並非本輪重測或效能 SLA。品質／延遲證據見 [評估](evaluation.md)，本輪只盤點配置，未重啟模型或做 benchmark。

目標與 AC 的主來源仍是 [brief](internal/project/brief.md)。本頁整理環境前提與需求追溯，不新增一套已接受的產品規格；未完成項是審查建議，不能因寫入文件就視為驗收通過。

## 執行環境

| 使用層級 | 必要條件 | 不需要的元件／限制 |
|---|---|---|
| PDF＋BM25 檢索 | Python ≥3.11、uv、可讀文字的 PDF；`uv sync --locked` | 不需要 GPU、Docker、資料庫或生成模型 |
| 向量／混合檢索 | 上列加 `uv sync --locked --extra embeddings`；本機 embedding snapshot | 現行 encoder 使用 CPU；模型必須先下載，建索引與查詢不自動下載 |
| PostgreSQL 儲存 | 加 `--extra pg`、PostgreSQL＋pgvector、PG_DSN／PGPASSWORD | 可用 Compose db；檔案模式不需要資料庫 |
| 本機生成 | 可用 OpenAI 相容 LLM 端點；現行 Compose 使用固定版本 vLLM／Qwen 模型快取 | 既有 16 GB NVIDIA 顯卡環境設定約用 10 GB 顯存，並非所有硬體的最低保證 |
| 聊天介面 | 上列生成流程、serve、AnythingLLM；Compose 路徑需 Docker Linux containers | 工作區不需上傳文件；不是完整 OpenAI API 實作 |

Python 3.12 是現行 CI 安裝版本；Windows 本機及 Linux CI 的驗證不能推定所有 OS／Python 組合都通過。模型、Docker 映像、Python 套件及資料容量分別計算，目前沒有完整磁碟／RAM 下限量測。完整新機設定見 [新手手冊](setup.md)，可選環境變數見 [compose.yaml](../compose.yaml) 與 [llm.py](../src/ipas_hub/llm.py)。

套件來源以 [pyproject.toml](../pyproject.toml) 與 [uv.lock](../uv.lock) 為準，不新增手寫 requirements.txt。如果日後部署工具只接受 requirements.txt，再由鎖檔產生衍生檔，不另維護版本。

<details>
<summary>產品需求與後續驗收規劃（維護參考）</summary>

## 產品需求與證據對照

以下是既有需求摘要，並非新的 AC 編號。

| 需求／來源 | 實作或證據 | 未達條件 |
|---|---|---|
| iPAS 問題可回查來源／brief 原始情境 | 頁碼引用、勘誤設定、靜態解析、rag.py | 理由與引用的完整人工品質判定 |
| 替換自有文件／brief 產品方向 | parser=pdf、來源 manifest；勞基法案例 | prompt 仍有 iPAS 假設；非任意格式、排版或領域保證 |
| 知識庫隔離／brief 文件範圍 | --kb、index_id、model 路由；test_documents／test_pgstore／test_routing | 只隔離檢索範圍，不包含身份與授權 |
| 外部知識補強／brief 產品方向 | 維基百科、web none、外部引用 | 通用外搜、模型記憶補充未交付；新領域外搜需驗證 |
| 可供他人參考／brief 完整參考專案 | README、環境說明、新手手冊、CI | 乾淨新機全流程、可分享展示素材、品質評估集與 LICENSE 決定 |
| 可追溯與回復／既有 RAG 設計 | 來源／模型／程式識別、index_id、data/runs | 備份還原演練、維運規格未完成 |

## 建議的下一批交付判準（暫定，待負責人採用）

1. **可展示**：用可分享的自寫文件示範一題有依據回答、一題合理拒答及 PDF 回查，保留版本與失敗說明。
2. **可重現**：另一個乾淨環境依文件從下載、建索引到聊天完成；記錄實際時間、容量、硬體與卡點，不預設尚未量測的門檻。
3. **可評估**：每個示範庫有分開的調整題與保留題；人工核對引用支持、答案及拒答，報分母與錯誤案例。測法沿用 [評估方案](evaluation.md)。
4. **可延伸**：非 iPAS 文件無需改程式便能匯入；生成／外搜領域設定可替換，非 iPAS 問題不被考試身份影響。需程式變更另定測法。

公開多人服務、OCR、Word 與多輪記憶不是完成本機 side project 的必要前提；若新增這些目標，再確認範圍與 AC。程式授權由作者選擇，本輪未代選。

</details>

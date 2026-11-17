<!--
title: Historical README (2026-11-17 snapshot)
status: archived
updated: 2026-11-17
-->

# Historical README

> Archived snapshot: contains historical stage descriptions. For current capabilities and setup, start at [README](../../../README.md) and [setup](../../setup.md).

iPAS AI 應用規劃師的備考輔助。目標是讓每一道題目都能找到教材出處，之後再提供選項解析。

目前是本機 RAG 原型：初級兩科＋中級三科教材、BM25／向量混合搜尋、PostgreSQL＋pgvector、本機 LLM 與 AnythingLLM 聊天介面，可回傳帶教材頁碼的解答。供作者自用，尚未驗收公開／多人服務及整體答題品質。範圍與成功條件見 [brief](brief.md)，進度見 [progress](progress.md)。

- 第一次操作：[Windows 新手手冊](../../setup.md)。
- 交給 AI 協助：[架設任務指引](ai_setup.md)。
- 評估與展示：[完整度與混合搜尋證據](../../evaluation.md)。
- 第二個文件情境：[勞動基準法獨立知識庫](../../examples/labor-law.md)（一般 PDF、明確選庫、關閉外搜的驗證）。多庫時請以 `--kb ipas` 或 `--kb labor-law` 指定範圍。

既有 50 題靜態逐選項解析與雙科索引保留；使用者接受目前內容，14 題有逐題判定，其餘 36 題不宣稱已逐題驗證。

解析入口：[逐選項解析與雙科索引](explanations/115-3-subject1.md)。引用區分教材依據與相關頁，供學習對照，不認定為實際命題出處；人工判定見[複核紀錄](validation/2026-11-16-explanation-review.md)。

## 第一輪做什麼

- 探索一：一份初級試題 50 題，分成「找不到／找到但要自己推理／教材沒有」三類，並記下依據頁碼。答案由作者填，依據頁碼與分類由 AI 代填。
- 探索二：同一批題目比較關鍵字檢索與向量檢索。

第二輪解析由 AI 在協作對話中撰寫，不呼叫付費 API。當時未納入 web search、中級教材、模擬考介面與公開上線；後續已加入維基外部搜尋、中級教材與聊天介面。模擬考介面及公開上線仍未交付。

## 專案配置

```text
.
├── README.md
├── AGENTS.md                   AI 協作規則入口
├── .github/                    PR 格式
├── pyproject.toml              Python 專案與相依套件
├── src/ipas_hub/               程式碼
├── tests/                      單元測試
├── data/                       不進版控，需自行下載
│   ├── raw/                    官方教材、勘誤表與試題 PDF：beginner／intermediate 下各分 guides、errata、exams
│   └── index/                  索引（kb/<index_id>/）與勘誤替換檔（errata/）
└── docs/
    ├── project/                本專案的紀錄：brief、progress 與按需建立的文件
    └── workflow/               工作指南、規則與空白範本
```

## 從零重現：教材 → PostgreSQL＋pgvector → 聊天介面（Windows PowerShell）

教材、試題、索引與模型都不在 repo 內，需自行下載。以下步驟只在本機執行，所有服務只綁 127.0.0.1。需要：Docker Desktop、[uv](https://docs.astral.sh/uv/)、約 10 GB 顯存的 NVIDIA 顯示卡（本機 LLM 用）、約 4 GB 磁碟（嵌入模型約 2.3 GB，加上資料庫映像與 Python 套件；本機 LLM 的模型另計）。

1. 下載設定檔列出的學習指引（初級 2 份、中級 3 份，約 26 MB；來源：[官方學習資源頁](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)）。檔名就是官方原名，放在 `data/raw/<級別>/guides/`。建索引時會比對 config/knowledge-base.json 的 SHA-256，檔案版本不同就會停止。

   ```powershell
   $base = 'https://www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/'
   $cfg = Get-Content config/knowledge-base.json -Raw -Encoding UTF8 | ConvertFrom-Json
   foreach ($s in $cfg.sources) {
     New-Item -ItemType Directory -Force (Split-Path $s.pdf) | Out-Null
     Invoke-WebRequest ($base + (Split-Path $s.pdf -Leaf)) -OutFile $s.pdf
   }
   ```

   試題與勘誤表不需要下載也能提問；要的話依同樣網址開頭，放在 `data/raw/<級別>/exams/`、`data/raw/<級別>/errata/`。

2. 勘誤：官方勘誤要先整理成替換字串檔（data/index/errata/beginner-subject1.json 等）才能套用。這些檔含教材原文，不在 repo 內。沒有的話，改用 `config/knowledge-base.no-errata.json` 建索引：索引會記錄 `errata: not_applied`，勘誤頁的回答會依更正前的文字。中級的替換檔是 data/index/errata/intermediate-subject1.json 與 intermediate-subject3.json；中級科目 2 的勘誤只在不進知識庫的職能基準頁，所以沒有替換檔。
3. 安裝相依並下載嵌入模型（BAAI/bge-m3，約 2.3 GB，只需一次；程式之後只讀本機快取、不自動下載）。排除用不到的 ONNX 版本、圖片與附加權重，否則會多下載約 2.3 GB（程式載入時也忽略同一組檔案）：

   ```powershell
   uv sync --extra pg --extra embeddings
   uv run hf download BAAI/bge-m3 --exclude "onnx/*" --exclude "imgs/*" --exclude "*.jpg" --exclude "*.pt"
   ```

4. 在 repo 根目錄的 `.env`（不進版控）設定資料庫密碼與 LLM 模型所在的 volume，例如：

   ```text
   PG_PASSWORD=自行設定的密碼（英數字）
   # 本機 5433 埠已被占用時才需要：PG_PORT=5434，並把下一步 PG_DSN 的 port 改成相同的值
   LLM_MODEL_VOLUME=存放 Hugging Face 快取的 Docker volume 名稱
   ```

5. 啟動資料庫，建索引並載入：

   ```powershell
   docker compose --profile db up -d db
   $env:PG_DSN = 'host=127.0.0.1 port=5433 dbname=ipas user=ipas'
   $env:PGPASSWORD = (Select-String '^PG_PASSWORD=(.*)' .env).Matches[0].Groups[1].Value
   uv run python -m ipas_hub.cli index --embedding-model BAAI/bge-m3 --to-pg            # 有勘誤替換檔
   # uv run python -m ipas_hub.cli index --config config/knowledge-base.no-errata.json --embedding-model BAAI/bge-m3 --to-pg   # 沒有時
   ```

   `index` 先在 data/index/kb/<index_id>/ 建檔案索引（版本來源，可保留舊版回復），`--to-pg` 再驗證後載入資料庫；也可分開執行 `pg-load --index <index.json>`。同一份索引重複載入會略過。

6. 啟動本機 LLM 與聊天介面，提問：

   ```powershell
   docker compose --profile llm up -d vllm      # 首次約 2 分鐘
   docker compose --profile ui up -d ui
   $env:LLM_MODEL = 'qwen3-vl-8b-fp8'
   uv run python -m ipas_hub.cli serve --store pg --kb ipas
   ```

   開 http://localhost:3001 建立工作區後提問（不要上傳文件）。預設混合檢索（關鍵字＋向量）；`--store pg --kb ipas` 未指定 `--index` 時用該庫最近載入且含向量的索引。也可以只在終端機問：`uv run python -m ipas_hub.cli ask --store pg --kb ipas --query "題目" --format text`。

用完：`docker compose --profile llm stop vllm` 釋放顯存；資料庫資料留在 volume `pg-data`。

不想裝資料庫或不想下載嵌入模型時：略過步驟 3 的 `hf download` 與步驟 5 的資料庫，`index` 不加 `--embedding-model`、`--to-pg`，提問時加 `--index <index.json>`（預設 `--store file`）。這樣建出的索引沒有向量，程式會自動改用 BM25 關鍵字檢索並在終端機提醒；明確指定 `--method hybrid` 或 `vector` 時則會報錯。

## 執行探索二

需要 [uv](https://docs.astral.sh/uv/)。探索二固定使用初級科目 1 教材與 115 年第三次第一科試題，檔案位置見 src/ipas_hub/explore2.py 的 GUIDE_PDF、EXAM_PDF（data/raw/beginner/ 下，官方原名），然後：

```text
uv sync
uv sync --extra embeddings
uv run pytest
uv run python -m ipas_hub.explore2
```

第一次執行會從 Hugging Face 下載 BAAI/bge-m3 模型（約 2 GB），之後在本機 CPU 上跑。結果寫到 data/index/explore2_results.json。勘誤的替換字串放在 data/index/errata/beginner-subject1.json，這個檔含教材原文所以沒有收錄，沒有它程式照樣能跑，只是不套用勘誤。

## 第三輪：Docker 雙科檢索原型

目前交付範圍、最新驗證與三組試用方式見[交付與試用入口](validation/2026-11-16-handoff-readiness.md)。

第三輪先完成檢索；生成見下方第四輪。尚無自動解題的品質驗收或網頁介面。[設計與限制](design/rag-prototype.md)記錄執行契約，[驗證紀錄](validation/2026-11-16-docker-retrieval.md)區分本機、容器與尚未執行的 CI／LLM 測試。

Docker Desktop 使用 Linux containers。來源清單是 config/knowledge-base.json，目前列出初級兩科與中級三科的 PDF、版本與 SHA-256；設定的勘誤必須套用成功才建立索引。另需設定檔 patches 欄位指定的四份本機替換檔（data/index/errata/ 下，初級科目 1、2 與中級科目 1、3）。這些檔含原文、不進版控；新環境應依官方勘誤表建立陣列，每筆欄位為 id、old、new。設定的檔案缺失或未命中更正字串會明確失敗，不略過；沒有替換檔請使用上方的無勘誤設定。

PowerShell 操作：

```powershell
docker compose build app
$built = docker compose run --rm app index | ConvertFrom-Json
$kbIndex = $built.index
docker compose run --rm app search --index $kbIndex --query "差分隱私" --k 5
```

要貼完整題目，先儲存為 data/review/question.txt，再執行：

```powershell
docker compose run --rm app search --index $kbIndex --query-file data/review/question.txt
docker compose run --rm app evaluate --index $kbIndex --cases data/evaluation/rag-retrieval-cases.json
```

評估案例需另建在 data/，格式是陣列，每筆有 id、query、expected；expected 是 source 與 page 的陣列。頁碼與科目一起比對，不能只比對相同頁碼。程式不自動把現有解析視為完整正確答案。

向量與混合檢索另需 embedding 相依與本機快取：

```text
uv sync --extra embeddings
uv run python -m ipas_hub.cli index --embedding-model BAAI/bge-m3
```

索引指令會回傳 index.json 路徑；後續 search／evaluate 使用該路徑，指定 --method vector 或 --method hybrid。原型只使用已快取模型，未快取時不自動下載。容器的可選 embedding 建置使用 `docker compose build --build-arg EMBEDDINGS=true app`；需另外將本機 HF 快取複製進 hf-cache volume，預設不傳送模型。此大型映像尚未實測，不把主機向量測試當作容器向量測試。

基本映像不含教材、題目、索引、模型或 Git，只在執行時掛載 data/；每次索引另存內容版本目錄，查詢及評估紀錄寫入 data/runs/。可指定舊 index.json 回復資料版本，模型 revision 與索引不符會拒絕向量查詢。

## 第四輪：端到端 RAG（教材＋維基百科＋本機 vLLM）

`ask` 指令把題目同時送去教材檢索與外部搜尋，再由本機 LLM 產生帶引用的解答。解答逐句標出依據：句末的 [教材n]／[外部n] 由程式依片段資料產生，對應下方依據清單（科目、頁碼，或維基百科條目與固定版本網址）。模型引用不存在的片段時給一次修正機會，仍錯就拒絕顯示。程式另以字詞比對檢查每句與所引片段：句中的英文詞或數字不在片段內、或中文字詞重疊過低時，在該句下方標 ⚠。這只是簡單比對，不是語意驗證，不保證解答正確。外部搜尋先查中文維基；縮寫或多義詞會加上領域詞以排除同名條目（如 LIME 不查到水果），中文沒有相關結果時改查英文維基，取頁面中含該詞的段落，引用標為「英文維基百科」。

1. 準備模型：vLLM 從一個 Docker volume 唯讀載入 Hugging Face 快取，離線執行、不自動下載。在 repo 根目錄建立 `.env`（不進版控）指定 volume 名稱，例如 `LLM_MODEL_VOLUME=dev_infra_qwen_trial_cache`。預設模型為 Qwen/Qwen3-VL-8B-Instruct-FP8（只載入文字部分）。
2. 啟動與提問（PowerShell）：

```powershell
docker compose --profile llm up -d vllm      # 首次載入約 2 分鐘，GPU 需約 10 GB
docker compose run --rm app ask --index $kbIndex --query-file data/review/question.txt --format text
docker compose --profile llm stop vllm       # 用完釋放顯存
```

不用 Docker 時，主機也可直接執行：`$env:LLM_MODEL='qwen3-vl-8b-fp8'; .venv/Scripts/python.exe -m ipas_hub.cli ask --index <index.json> --query-file <題目檔> --format text`。

### 聊天介面

`serve` 指令把同一套流程包成 OpenAI 相容端點（只綁 127.0.0.1），再用 AnythingLLM 當聊天介面：

```powershell
docker compose --profile llm up -d vllm
docker compose --profile ui up -d ui
$env:LLM_MODEL='qwen3-vl-8b-fp8'; .venv/Scripts/python.exe -m ipas_hub.cli serve --index <index.json>
```

開啟 http://localhost:3001 ，建立工作區後直接提問；不要在工作區上傳文件，檢索與外部搜尋由本專案負責。模型未啟動或回答不合格時，畫面會顯示「⚠ 無法產生有依據的解答」與原因。

教材引用同時列出章節頁碼與 PDF 頁，例如「3-36（PDF 第 42 頁）」。`serve` 執行期間，依據清單的教材項目是連結，點下去由瀏覽器開啟 `http://127.0.0.1:8100/files/<教材識別>.pdf#page=N`。教材檔只從本機 data/ 唯讀提供，且雜湊須與索引相同；埠或主機名稱不同時用 `--link-base` 指定連結開頭。PDF 頁碼需要用目前版本重建的索引（`index` 指令），舊索引仍可使用，但只顯示章節頁碼。

- 外部搜尋：`--web wikipedia`（預設）或 `--web none`。搜尋介面在 src/ipas_hub/websearch.py，新增提供者只要回傳相同欄位。
- 換成 OpenAI 等遠端 API：設定 `LLM_BASE_URL`、`LLM_MODEL`、`LLM_API_KEY`，並加 `--allow-remote`。預設拒絕本機以外的端點，避免誤用付費服務；金鑰不寫入執行紀錄。
- 執行紀錄（含題目、片段、搜尋詞、模型與耗時）寫入 data/runs/。

## CI/CD 與 MLOps 邊界

- CI：PR／main 推送時，用合成資料跑 Python 測試、Compose 設定驗證、容器測試及斷網啟動；官方原文與模型不送到 hosted runner。
- CD：手動 delivery workflow 重建測試與 commit 標籤映像、記錄 image ID；不推送 registry、不部署，屬交付檢查而非生產 CD。
- MLOps：索引保存來源／勘誤雜湊、切塊設定、程式及 lockfile 識別、embedding snapshot 與向量雜湊；執行紀錄保存方法、版本、結果與延遲。尚未引入模型註冊、漂移監控或自動重訓平台。
- llm Compose profile 為本機 vLLM，映像以 digest 固定、模型以 revision 固定；CI 只驗證 Compose 設定，不在 hosted runner 啟動模型。

## 檢查與產生解析

主來源是 docs/internal/project/explanations/115-3-subject1.json，閱讀用 Markdown 由程式產生，請勿直接修改。需要本機的科目 1 教材與 115 年第三次第一科試題（位置同探索二）；科目 2 教材的位置見 JSON 的 additional_guides。

```text
uv run python -m ipas_hub.explain
uv run pytest
```

程式檢查答案一致與引用的科目、頁碼及詞是否存在，不判斷所有解析理由是否正確。含題目原文的複核對照只寫入 data/review/；若重產內容與原檔不同，會另存 .generated.md，保留原檔筆記。uv 若無法執行，可使用既有虛擬環境的 `.venv/Scripts/python.exe -m ipas_hub.explain` 與 `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`。

## 資料來源與使用限制

教材、勘誤表與試題來自經濟部產業發展署的 [iPAS AI 應用規劃師學習資源頁](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)。這些檔案的著作權屬原權利人，本 repo 不收錄也不再散布原始檔與由其產生的索引；需要的人請自行到官方頁下載，放到 data/raw/。各檔案內的聲明原文與授權確認進度記在 progress。

## 工作方式

本專案沿用 problem-def-template 的流程：先讀 [使用指南](../workflow/guide.md)，AI 工具的共同規則在 [AGENTS.md](../../../AGENTS.md)。

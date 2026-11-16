---
title: ipas-learning-hub
status: draft
updated: 2026-11-16
---

# ipas-learning-hub

iPAS AI 應用規劃師的備考輔助。目標是讓每一道題目都能找到教材出處，之後再提供選項解析。

第一輪兩個探索已有結果；第二輪已完成 115 年第三次初級科目 1 的 50 題逐選項解析，並提供兩科教材對照索引。使用者已確認目前解析與人工審查紀錄通過；14 題有逐題判定，其餘 36 題不宣稱已逐題驗證。目前只供作者本人自用，尚無查題介面。範圍與成功條件見 [brief](docs/project/brief.md)，目前進度與下一步見 [progress](docs/project/progress.md)。

解析入口：[逐選項解析與雙科索引](docs/project/explanations/115-3-subject1.md)。引用區分教材依據與相關頁，供學習對照，不認定為實際命題出處；人工判定見[複核紀錄](docs/project/validation/2026-11-16-explanation-review.md)。

## 第一輪做什麼

- 探索一：一份初級試題 50 題，分成「找不到／找到但要自己推理／教材沒有」三類，並記下依據頁碼。答案由作者填，依據頁碼與分類由 AI 代填。
- 探索二：同一批題目比較關鍵字檢索與向量檢索。

第二輪解析由 AI 在協作對話中撰寫，不呼叫付費 API。web search、中級教材、模擬考介面與公開上線不在目前實作範圍；已另獲授權從官方頁下載科目 2 指引，補充現有 50 題的跨科依據。

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
│   ├── raw/                    官方教材、勘誤表與試題 PDF
│   └── index/                  切塊與檢索索引
└── docs/
    ├── project/                本專案的紀錄：brief、progress 與按需建立的文件
    └── workflow/               工作指南、規則與空白範本
```

## 執行探索二

需要 [uv](https://docs.astral.sh/uv/)。先把教材、試題各一個 PDF 放到 data/raw/guide/ 與 data/raw/exam/，然後：

```text
uv sync
uv sync --extra embeddings
uv run pytest
uv run python -m ipas_hub.explore2
```

第一次執行會從 Hugging Face 下載 BAAI/bge-m3 模型（約 2 GB），之後在本機 CPU 上跑。結果寫到 data/index/explore2_results.json。勘誤的替換字串放在 data/index/errata_patches.json，這個檔含教材原文所以沒有收錄，沒有它程式照樣能跑，只是不套用勘誤。

## 第三輪：Docker 雙科檢索原型

目前交付範圍、最新驗證與三組試用方式見[交付與試用入口](docs/project/validation/2026-11-16-handoff-readiness.md)。

目前先完成檢索，LLM 下一步再選型，尚無自動解題的品質驗收或網頁介面。[設計與限制](docs/project/design/rag-prototype.md)記錄執行契約，[驗證紀錄](docs/project/validation/2026-11-16-docker-retrieval.md)區分本機、容器與尚未執行的 CI／LLM 測試。

Docker Desktop 使用 Linux containers。來源清單是 config/knowledge-base.json：兩份 PDF、版本與 SHA-256 都明列；所有勘誤必須套用成功才建立索引。另需本機的 data/index/errata_patches.json（科目 1）與 data/index/subject2-errata-patches.json（科目 2）。這兩份含原文、不進版控；新環境應依官方勘誤表建立陣列，每筆欄位為 id、old、new。缺檔或未命中更正字串會明確失敗，不略過。

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

## CI/CD 與 MLOps 邊界

- CI：PR／main 推送時，用合成資料跑 Python 測試、Compose 設定驗證、容器測試及斷網啟動；官方原文與模型不送到 hosted runner。
- CD：手動 delivery workflow 重建測試與 commit 標籤映像、記錄 image ID；不推送 registry、不部署，屬交付檢查而非生產 CD。
- MLOps：索引保存來源／勘誤雜湊、切塊設定、程式及 lockfile 識別、embedding snapshot 與向量雜湊；執行紀錄保存方法、版本、結果與延遲。尚未引入模型註冊、漂移監控或自動重訓平台。
- 可選 llm Compose profile 與 Ollama adapter 僅為後續連接草案；本輪沒有選用或啟動 LLM，不動既有其他專案服務。

## 檢查與產生解析

主來源是 docs/project/explanations/115-3-subject1.json，閱讀用 Markdown 由程式產生，請勿直接修改。需要本機科目 1 教材位於 data/raw/guide/、試題位於 data/raw/exam/，各一份 PDF；科目 2 教材的檔名與位置見 JSON 的 additional_guides，存放在 data/raw/guide-subject2/，與探索一、二資料分開。

```text
uv run python -m ipas_hub.explain
uv run pytest
```

程式檢查答案一致與引用的科目、頁碼及詞是否存在，不判斷所有解析理由是否正確。含題目原文的複核對照只寫入 data/review/；若重產內容與原檔不同，會另存 .generated.md，保留原檔筆記。uv 若無法執行，可使用既有虛擬環境的 `.venv/Scripts/python.exe -m ipas_hub.explain` 與 `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`。

## 資料來源與使用限制

教材、勘誤表與試題來自經濟部產業發展署的 [iPAS AI 應用規劃師學習資源頁](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)。這些檔案的著作權屬原權利人，本 repo 不收錄也不再散布原始檔與由其產生的索引；需要的人請自行到官方頁下載，放到 data/raw/。各檔案內的聲明原文與授權確認進度記在 progress。

## 工作方式

本專案沿用 problem-def-template 的流程：先讀 [使用指南](docs/workflow/guide.md)，AI 工具的共同規則在 [AGENTS.md](AGENTS.md)。

---
title: 雙科 RAG 原型與 Docker 執行契約
status: draft
updated: 2026-11-17
---

# 雙科 RAG 原型與 Docker 執行契約

範圍與授權見 [brief](../brief.md) 的下一輪；實際驗證見 [progress](../progress.md)。本輪是自用技術原型，先提供 CLI，未交付網頁介面或部署服務。

## 執行與資料邊界

`index → search → ask → evaluate` 分開執行。來源只由 config/knowledge-base.json 明列的兩份教材建立，不讀試題與現有完整解析。原始教材、勘誤替換字串、索引、模型與查詢紀錄均不進映像／Git／CI。Docker Compose 把原始 PDF 掛唯讀，索引與執行紀錄存本機 data/；LLM 是可選 profile，模型需明確指定並另行下載，不自動選型。

使用者本輪進一步選擇「先完成檢索，下一步再選 LLM」。Ollama adapter 與 llm profile 僅為可替換的連接草案，本輪未選定 LLM、未啟動模型服務。小型雙科語料先沿用 BM25 與 NumPy 本機向量，不增加資料庫服務。向量檢索用本機已快取的 BAAI/bge-m3，固定 snapshot revision，未快取即失敗；不在查詢時下載新模型。混合檢索以兩路排名融合為原型候選，不宣稱優於單一路徑。向量方法無適用的品質閾值，仍可能回傳不相關片段，需用評估與人工內容審查判定。

## 可追溯性與回復

每個索引保存資料 schema、來源 PDF 與勘誤雜湊、實際套用頁、切塊設定、程式 commit／檔案雜湊、uv.lock 雜湊與 embedding revision／向量雜湊；整體內容雜湊是 index_id。新索引另建目錄，舊索引保留，查詢指定 index.json 即可回復版本。執行紀錄保存問題、片段、方法、索引識別、prompt 雜湊與延遲，只寫 data/runs/。這是 MLOps 的最小追蹤基礎，尚無模型註冊／漂移監控平台。

## 生成 prompt 契約（原型 v0.1）

- 實際 prompt：src/ipas_hub/prompts/answer.txt，程式以內容 SHA-256 追蹤。依據為已確認的下一輪方向及原先「程式檢查不等於理由正確」的限制，未虛構已採用的產品 AC。
- 輸入：JSON 的 question 字串與 evidence 陣列；每個片段含 id、source、name、version、page、text、rank、index_id。
- 輸出：JSON 的 status（supported／insufficient）、answer（繁體中文，包含選項時逐項解釋並區分推論）、citations（提供片段 ID 的陣列）。
- 正例：合成來源 s2:3-1:0 支持問題概念時，answer 引用該 ID，citations 亦列該 ID。
- 反例：無 evidence 時不呼叫模型；模型引用不存在的 ID，或聲稱 supported 卻沒有引用，程式拒絕該回答。
- 已知失敗：引用 ID 正確但文字仍可能不被片段支持；局部引用不能證明整段理由；模型可能遵從題目／教材中的惡意指令或把自身記憶冒充依據。prompt 只作約束，不把它當作已解決這些風險。需要人工或另外的語意驗證。
- 本機模型呼叫：Ollama /api/generate，JSON、非串流、temperature=0；僅允許 localhost、127.0.0.1 或 Compose ollama，不提供雲端 API 金鑰參數。模型連線、載入、逾時或輸出格式失敗明確回報，不退回編造答案。（v0.1 歷史描述；2026-11-17 起由下節 v0.2 取代）

## 生成契約 v0.2：教材＋外部搜尋（2026-11-17）

依 brief 第四輪的使用者決定實作；取代 v0.1 的 Ollama 介面。

- 流程：教材檢索前 k 塊 → 模型規劃最多 3 個搜尋詞（prompts/web_queries.txt）→ 每個詞輪流取外部結果，上限 --web-k → 模型依 prompts/answer.txt 回答。
- LLM 介面（src/ipas_hub/llm.py）：OpenAI 相容 /chat/completions，temperature=0、JSON 輸出。預設只允許 localhost、127.0.0.1 與 Compose 的 vllm；遠端端點須 --allow-remote 且為 https。金鑰只讀 LLM_API_KEY，執行紀錄只記端點與模型名。回覆被截斷、非 JSON、連線失敗都明確報錯。
- 外部搜尋（src/ipas_hub/websearch.py）：統一欄位 id、source_type、provider、title、url、revision、text、retrieved_at、query。維基百科以 zh-TW 取繁體，網址以 curid＋oldid 固定版本；429 依 Retry-After 等待後只重試一次（上限 5 秒）。搜尋失敗不中止，記在執行紀錄的 web.error，只用教材回答。
- 輸入：evidence 每筆含 id、source_type（textbook／external）、label、text，外部另含 url。
- 輸出：status、answer、citations。程式依片段資料加上 sources（逐筆標教材或外部）與 basis（textbook_only／external_only／mixed／none），不採信模型自稱的來源。
- 拒絕規則：引用不存在的 id、supported 卻無引用、格式不符時，把問題回饋模型修正一次；仍不合格即拒絕。教材與外部 id 重複時拒絕。無任何依據時不呼叫模型。
- 已知失敗（實測見 progress 第四十一筆）：引用 id 存在但內容不支持該句，例如第 28 題首次執行把 MAE 掛在沒有 MAE 的教材塊上；模型可能把引用集中放在答案末尾，讀者無法分辨哪句來自教材、哪句來自外部；外部搜尋可能回傳無關條目；模型可能用自身記憶作答或說得過度肯定。這些需要人工或另外的語意檢查。

## CI 與交付

CI 使用合成資料跑單元／流程測試、Compose config、Docker test stage 與 runtime --help，不把官方 PDF 或模型送到 hosted runner。手動 delivery workflow 只重建測試與 commit 標籤映像並記 image ID，不推送、不部署，尚不是生產 CD。Python 與 uv 基底映像已固定實際建置取得的 digest；vLLM 映像已以 digest 固定、模型以 revision 固定；hosted CI 不啟動模型。容器實測與真實 LLM 執行必須各有證據，不能從 YAML 存在推定通過。

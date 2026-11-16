---
title: 雙科 RAG 原型與 Docker 執行契約
status: draft
updated: 2026-11-16
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
- 本機模型呼叫：Ollama /api/generate，JSON、非串流、temperature=0；僅允許 localhost、127.0.0.1 或 Compose ollama，不提供雲端 API 金鑰參數。模型連線、載入、逾時或輸出格式失敗明確回報，不退回編造答案。

## CI 與交付

CI 使用合成資料跑單元／流程測試、Compose config、Docker test stage 與 runtime --help，不把官方 PDF 或模型送到 hosted runner。手動 delivery workflow 只重建測試與 commit 標籤映像並記 image ID，不推送、不部署，尚不是生產 CD。Python 與 uv 基底映像已固定實際建置取得的 digest；可選 Ollama 草案仍為版本 tag，待選型後再定正式交付模型 digest、評估與目標環境。容器實測與真實 LLM 執行必須各有證據，不能從 YAML 存在推定通過。

<!--
title: 目前狀態
status: in-review
updated: 2026-11-18
-->

# 目前狀態

- **階段**：可自用與展示的本機原型；管線不綁定領域，附 iPAS 範例（[examples/ipas](../examples/ipas/README.md)）。
- **repo 可見性**：Private（2026-11-18 查核）；公開前須先完成下方「公開前待辦」。
- **授權**：程式授權尚未選定；教材、模型、維基內容各有不同權利條件，見 [THIRD_PARTY_NOTICES](../THIRD_PARTY_NOTICES.md)。
- **已經能做的**：iPAS 五科教材與一般文字型 PDF 的官方下載核對（`fetch`）與版本化索引、領域 profile、BM25／向量／混合檢索、PostgreSQL＋pgvector、本機 vLLM 生成、逐句引用與核對、AnythingLLM 聊天介面、PDF 原頁連結、多知識庫路由。
- **驗證方式**：`uv run pytest` 與 `uv run python -m ipas_hub.demo`；GitHub Actions CI 另跑 pgvector 整合測試、容器測試與啟動檢查。主張與測試的對照見 [EVIDENCE](EVIDENCE.md)。
- **尚未證明的**：混合檢索在現行五科索引上穩定勝過 BM25；回答理由的語意正確性；乾淨新機從零完整安裝；多人服務。詳見 [評估](evaluation.md)。

## 已知限制

- 只支援可擷取文字的 PDF；沒有 OCR、表格或圖片理解。
- 非 iPAS 領域的回答品質未另外驗證；部分固定訊息（例如「教材與外部搜尋都沒有取得依據」）仍使用「教材」一詞。
- 外搜的搜尋詞規劃提示以機器學習術語為例，其他領域的外搜品質未驗證。
- 聊天是單輪：只取最後一則使用者訊息；SSE 在完整生成後才傳送。
- 字詞核對只是提示，不是事實查核。

## 公開前待辦（需作者決定）

1. 選定程式授權並加入 LICENSE。
2. 確認 repo 內沒有教材原文、試題或個人資料（`data/` 已不進版控，CI 會檢查）。
3. 複核 `docs/internal/project/explanations/` 的逐選項解析：不含題目原文，但逐題列出官方答案與各選項內容的改寫，公開前需確認權利，或改為不追蹤。
4. 決定是否公開 repo，並補上 GitHub 描述與 topics。

## 下一步

1. 建立保留題目集，產出一張 BM25／向量／混合的對照表（方案見 [評估](evaluation.md#下一輪評估方案暫定待採用未執行)）。
2. 錄製一段「提問 → 逐句引用 → 開啟 PDF 原頁」的操作畫面放進 README。

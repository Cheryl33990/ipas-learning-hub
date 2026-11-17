---
title: 一般 PDF 與勞基法知識庫
status: in-review
updated: 2026-11-17
---

# 一般 PDF 與勞基法知識庫

## 2026-11-17 AnythingLLM 實機接線修訂

使用者要求直接啟用工作區試用。核對目前 AnythingLLM 容器程式，workspace 只可獨立存 chatProvider／chatModel，Generic OpenAI Base URL 為共用環境設定，前輪「各工作區填不同URL」指引不適用本版本。為保留 iPAS 設定，增加 serve --routes 設定：共用8100以請求 model 選已列明的知識庫與 web 政策，rag→ipas／wikipedia、labor-law→labor-law／none。每個模型固定對應索引，未知或缺少模型拒絕，/v1/models只列已設定名稱；檔案連結加模型前綴避免同名來源衝突。這是檢索路由，不是權限隔離。

事前測法：HTTP非串流／串流分別核對選對callback、未知／缺模型400且未呼叫callback、兩模型同名PDF使用不同路徑；CLI設定重複或不合法模型名稱、kb與web欄位不合法需拒絕。再從AnythingLLM勞基法工作區送出真實題目，確認本機data/runs記錄labor-law／web none及文件引用；檢查原rag工作區設定未改。瀏覽器控制若不可用，以工作區API與同一聊天API結果驗證，明記未目視畫面。

本輪使用者授權加入官方勞動基準法作第二個隔離知識庫，沿用先通用文件、再補強回答的順序。來源為 https://law.moj.gov.tw/LawClass/LawAll.aspx?PCode=N0030001 。不改既有索引或搬移 iPAS PDF，不自動提交發布。

## 最小實作與相容

- 來源可指定 `parser: pdf`，依 PDF 頁序收錄非空文字，不要求 iPAS 頁尾。預設解析模式仍沿用 iPAS；新的來源可保存官方 URL、取得日期與 parser。空白頁略過、全檔無文字則拒絕。
- 設定可指定 `knowledge_base`（本輪為 labor-law）；保存於索引 manifest，無此欄位的歷史索引視為 ipas。此相容規則限定本 repo 的歷史資料，非任意舊索引自動分類。
- CLI 增加 `--kb`。pg 以知識庫範圍選最近適用索引；明確 index_id 與 --kb 不符時拒絕。多個庫存在而未指定 --kb／--index 時報錯，避免新庫變成原服務的全域預設。file 仍要求 --index，--kb 用於核對。
- 使用現有 JSON manifest，不新增資料表或改舊雜湊。serve 啟動時固定一個知識庫與版本；勞基法測試用獨立 8101、model labor-law、--web none，不動使用者原 8100。AnythingLLM 使用對應的工作區供應者設定，尚不做單端點多模型路由。
- 一般文件的來源標示為文件，保留既有教材相容標記。PDF 頁連結沿用允許清單及檔案雜湊檢查。

## 測法與判準（實作前）

1. 合成一般 PDF 不含章節頁碼仍擷取到各頁、空白頁不產生片段；無文字明確失敗；iPAS 既有測試與初級片段回歸保持。
2. 合成 A／B 相似文字索引，pg 分庫查詢、明確索引核對、向量查詢限同 index_id。未知庫拒絕、多庫省略選擇拒絕；每個 DB 測試用獨立 schema。
3. 官方 PDF 在 data/raw/labor-law，雜湊與來源取得紀錄保存在設定／本機 manifest；測試問題與預期頁在 data/evaluation/labor-law，答案不進語料。
4. 實際建立 bge-m3 索引並載入 pg，選 labor-law 查數個條文概念、核對回傳頁與來源、確認只有該庫來源；固定舊 iPAS index_id 回歸。這是管線試跑，不是檢索品質保留測試集。
5. 若本機 vLLM 已可用，勞基法 --web none 少量回答與 PDF 連結 smoke test；未跑、介面未點選或法律正確性未人工判定須明寫。

一般 PDF 固定頁內字元視窗只是第一版；條文跨頁、條款標題保留與條號 metadata 為已知改善點，不把 PDF 頁碼當條號。此次不承諾法律判斷、法規自動更新或跨使用者權限隔離。

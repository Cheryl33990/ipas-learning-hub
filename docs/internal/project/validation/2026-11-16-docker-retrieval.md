<!--
title: 雙科檢索與 Docker 原型驗證
status: draft
updated: 2026-11-16
-->

# 雙科檢索與 Docker 原型驗證

被測版本：main 5cf7d96 加上 docs/rag-next-iteration-plan 的未提交原型修改；沒有冒稱為已合併版本。範圍與測法見 [brief](../brief.md)，資料與介面見[設計](../design/rag-prototype.md)。使用者確認這輪先完成檢索，LLM 下一步再選。

使用者確認（2026-11-16）：回覆「當前的內容 OK」，記為接受目前原型內容；不將此確認解讀為 5／8 已符合正式品質門檻、未跑項已通過，或另行授權 commit／推送。

## 程式與容器

| 實際執行 | 結果 | 限制 |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -p no:cacheprovider` | Windows Python 3.14.7：37 passed | 合成資料；生成測試為注入的 fake，不是真實 LLM |
| `docker build --target test -t ipas-hub:test .` | Linux Python 3.12.16：37 passed，映像建置完成 | 最初 1 題失敗：runtime 無 git 指令；改以環境版本／檔案雜湊回報，重驗後通過 |
| `docker compose --profile llm config --quiet` | 通過 | 僅設定驗證，沒有啟動 llm profile |
| `docker compose build app` | 成功 | 基本映像含 BM25；大型 embeddings 映像未建置 |
| `docker run --rm --network none ipas-hub:local --help` | 成功 | 斷網 CLI 啟動，不是生成服務端到端 |
| `docker compose run --rm app index` | 兩科 123 個有頁碼頁面、266 塊；科目 1 六筆、科目 2 一筆勘誤皆套用成功 | 文字擷取的既有限制保留；不等於每個頁面目視檢查 |
| Compose search 查詢差分隱私，k=2 | 首筆為科目 2 的 3-47，次筆為 3-48，帶科目、版本、頁碼與片段 ID | 只是一筆人工可核對的搜尋案例 |
| runtime 檔案檢查 | 不含 PDF、.git 或 tests，prompt 檔存在 | 原文只由執行時 volume 掛載，沒有發送到 GitHub |

Docker Desktop 4.83.0、Engine 29.6.2、Compose 5.3.1。runtime image ID：`sha256:589d783c3ca32022aa3b948009525e6baeabb5669bf3bc2d8ec3fec186787dd5`，約 98.4 MB（Docker inspect 回報 98,394,094 bytes）。Python、uv 基底的實際 digest 已固定於 Dockerfile；commit 標籤／正式交付由後續 CI 設定處理，本次未發布 Registry。

## 新的雙科檢索基準

案例為 3、4、18、23、28、32、40、49，共 8 題；問題含題幹與選項，沒有答案欄。預期來源由現有解析的 basis 抽出，是有人工內容接受紀錄的參考，並未逐頁獨立複核所有依據。這是新原型基準，與探索二 26 題不是同一次比較，不覆寫原結果。語料只收兩份教材與適用勘誤，沒有索引試題或完整解析。

向量使用已存在的本機 BAAI/bge-m3 快取，snapshot `5617a9f61b028005a4858fdac845db406aefb181`，CPU。索引只建立一次，評估沿用同一 index_id，前 5 個片段中有任一來源＋頁碼符合即命中。

| 題號 | BM25 | 向量 | 混合排名融合 |
|---|---|---|---|
| 3 | 命中 | 命中 | 命中 |
| 4 | 未命中 | 未命中 | 未命中 |
| 18 | 未命中 | 命中 | 命中 |
| 23 | 命中 | 命中 | 命中 |
| 28 | 命中 | 命中 | 命中 |
| 32 | 命中 | 未命中 | 命中 |
| 40 | 未命中 | 未命中 | 未命中 |
| 49 | 命中 | 命中 | 未命中 |
| 合計 | 5／8 | 5／8 | 5／8 |

不能據此宣稱混合檢索更好。第 4 題 BM25 有找回科目 2 相關頁，但未落在原 basis 預期集合，故仍按預定規則記未命中；預期頁集合可能不完整，不事後補到通過。下一步應先判讀未命中原因與參考頁的支持範圍，再議檢索改善或品質門檻。

可重做命令（index 與案例均在本機 data/）：`python -m ipas_hub.cli evaluate --index data/index/kb/19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108/index.json --cases data/evaluation/rag-retrieval-cases.json --method bm25 --k 5`；向量與混合分別改 method 為 vector／hybrid，需要 embeddings 相依。Docker 另建的 BM25 索引為 `582ef86a39e915cec9f9ca32229484a49aee15a977a607c1c8a38817bb486de3`，容器 evaluate 結果同為 5／8。

原始案例、片段與完整執行紀錄在 data/evaluation/、data/index/kb/、data/runs/，不進版控。主機向量索引約 84 秒完成；CLI 量得的容器索引約 2.3 秒，容器 8 題 BM25 評估整體約 48 ms。兩個索引建置是否含模型、執行環境及計時範圍不同，不能直接作效能優劣比較。

## 尚未執行

- GitHub hosted CI、手動 delivery workflow：只有設定與本機對應步驟證據，未推送、未觸發，不宣稱 CI 綠燈或 CD 完成。
- Docker embeddings 映像與容器向量查詢未實測；主機向量實測不能替代此項。
- 沒有啟動或下載生成模型，沒有真實 LLM 回答、生成品質或拒答品質驗證。adapter 的引用 ID 檢查只能驗結構，不能證明回答受教材支持。
- 沒有選定生成模型、向量資料庫服務、模型註冊平台、對外部署、監控告警或訓練流程。本輪僅提供資料／索引版本與執行紀錄的最小 MLOps 基礎。

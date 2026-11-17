---
title: 交給 AI 的架設任務
status: in-review
updated: 2026-11-17
---

# 交給 AI 的架設任務

本檔是架設操作指引，協作規則仍以根目錄 [AGENTS.md](../../AGENTS.md) 為唯一入口。本檔不取代規則，也不代表已在所有電腦驗證。

把以下文字交給能操作終端機的 AI，並讓它讀取本 repo：

> 請依 AGENTS.md、使用指南、brief、progress 與 docs/project/beginner_setup.md，在目前電腦架設這個專案。先辨識作業系統、工具、GPU、可用磁碟、既有模型快取／Docker volume、占用埠及既有服務。沿用可用資源，先完成五科教材混合搜尋，再完成本機聊天。新增大型模型下載前回報模型、快取位置、既有重用情況及大小未知項，按本次授權執行；費用 API 與對外發布未在此任務範圍。一步一驗證，記錄實跑與未跑，失敗先排原因，不自動清除快取或資料卷。最後交付啟停命令、版本、健康檢查、題目與引用驗證、剩餘問題。不要把原始資料、密碼或模型提交到 Git，也不要自動 commit／push／開 PR。

## 操作順序與通過證據

| 步驟 | 實際操作 | 必須保存的結果 |
|---|---|---|
| 盤點 | git status／HEAD、Docker／Compose／uv、GPU、磁碟、volume、埠 | 版本、缺件、重用資源；只讀所需設定，不把密碼輸出到紀錄 |
| 教材 | 按設定下載並比對 SHA-256 | 五科來源、雜湊；版本不符則停止建索引 |
| 勘誤 | 檢查四份本機替換檔是否存在 | 缺少時選 no-errata 並明寫限制，不自行假造替換檔 |
| 嵌入 | 下載必要 bge-m3 檔案、離線載入 | 實際 snapshot；不能用乾跑當完整下載成功 |
| 資料庫 | 啟動 db、檢查 healthy、建索引並載入 | index_id、五科片段數、向量數與維度；重載同索引應略過 |
| 搜尋 | 明確指定 hybrid 並查詢 | 實際檢索方法、來源與頁碼，不接受意外退回 BM25 當混合通過 |
| 模型 | 沿用固定 revision 的生成模型快取 | vLLM 啟動成功及 `/v1/models`；不能只看容器 running |
| 端點 | 主機啟動 serve --store pg --kb ipas（或指定其他庫） | 8100 說明頁、`/v1/models`、完整回答來回；第二庫採獨立端點，見勞基法案例 |
| 介面 | UI 指向 host.docker.internal:8100/v1，model rag | 3001 實際提問、引用與 PDF 頁連結；未操作畫面就記未驗證 |
| 收尾 | 檢查 diff、更新 progress | 已啟動服務、停止方式、未完成項；不把搭建成功當品質驗收 |

主機 PostgreSQL 連 `127.0.0.1:5433`；app 容器連 `db:5432`。主機生成 API 為 `127.0.0.1:8000/v1`；UI 容器呼叫主機 RAG 為 `host.docker.internal:8100/v1`。若改埠，同步所有使用者設定。新開 PowerShell 必須重設 Python 所需環境變數。

## 已知的新機缺口

既有重現曾使用全新 clone、全新 Python 環境與獨立資料庫，但共用了已運作的 vLLM，不算從零下載生成模型的端到端證據。beginner_setup 的新 volume 模型下載指令是候選做法；helper 映像與下載套件尚未固定 digest／版本，尚未在乾淨主機實跑。執行者需記下當次版本、下載容量、revision、volume 結構、vLLM 啟動與回答結果，才可提升為已驗證路徑。

模型快取需有 `hub/models--Qwen--Qwen3-VL-8B-Instruct-FP8/snapshots/<revision>/` 及其引用的檔案；volume 掛在 vLLM 的 `/hf`，HF_HOME=/hf。不得直接改固定 revision 來掩蓋下載缺檔，或指向別的模型後仍宣稱重現同一配置。

回復以停止本次新增程序與容器、保留資料及 log 為原則；索引可指定舊 index_id，但教材路徑與雜湊也要相容。修改既有資料庫密碼或清除 volume 應另判斷影響。

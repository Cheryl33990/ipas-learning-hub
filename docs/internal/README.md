# 維護與歷史紀錄

本目錄供維護者追溯需求、決策、驗證及 AI 協作，不是產品操作手冊。讀者入口是 [公開文件](../README.md)。歷史內容保留當時版本與限制，不代表目前功能狀態；目前能力請看根 README。

本目錄納入 Git 版本控制，**internal 表示讀者分類，不是存取權限**；repo 公開時這些文件也會公開。不將整個目錄加入 .gitignore，避免遺失維護證據及解析工具依賴的資料。僅供本機的草稿、原文對照與輸出放已忽略的 data/review/；密鑰、個資、受限原文不得寫入追蹤文件。已追蹤內容不會因新增 ignore 規則而消失；若誤提交敏感資料，需另處理移除、歷史與憑證撤換，而非只靠忽略規則。

| 位置 | 用途 |
|---|---|
| [project/brief.md](project/brief.md) | 目標、範圍與確認紀錄的主來源 |
| [project/progress.md](project/progress.md) | 當前接手狀態與歷次工作紀錄 |
| [project/design](project/design) | 歷次技術設計與驗收方法 |
| [project/validation](project/validation) | 歷史實驗、審查與驗證報告 |
| [project/discovery](project/discovery) | 早期探索及標註資料 |
| [project/explanations](project/explanations) | 既有學習解析及其 JSON 主來源 |
| [project/ai_setup.md](project/ai_setup.md) | AI 協助架設指引 |
| [project/readme_history.md](project/readme_history.md) | 封存的輪次式 README |
| [workflow/guide.md](workflow/guide.md) | 協作方法與規則；templates 為參考材料，不是成果 |

2026-11-17 整理時，原 `docs/project/` 移至 `docs/internal/project/`，原 `docs/workflow/` 移至 `docs/internal/workflow/`；操作／環境／評估文件提取至 docs/。程式產生器與連結同步調整，無刪除歷史驗證或把草案改標成已接受。

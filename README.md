---
title: ipas-learning-hub
status: draft
updated: 2026-11-16
---

# ipas-learning-hub

iPAS AI 應用規劃師的備考輔助。目標是讓每一道題目都能找到教材出處，之後再提供選項解析。

目前在第一輪探索，只供作者本人自用。程式只有探索用的檢索比較，還沒有可以拿來查題目的介面。範圍與成功條件見 [brief](docs/project/brief.md)，目前進度與下一步見 [progress](docs/project/progress.md)。

## 第一輪做什麼

- 探索一：一份初級試題 50 題，分成「找不到／找到但要自己推理／教材沒有」三類，並記下依據頁碼。答案由作者填，依據頁碼與分類由 AI 代填。
- 探索二：同一批題目比較關鍵字檢索與向量檢索。

LLM 解析、web search、中級教材、模擬考介面與公開上線都不在本輪範圍，理由見 brief。

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
uv run pytest
uv run python -m ipas_hub.explore2
```

第一次執行會從 Hugging Face 下載 BAAI/bge-m3 模型（約 2 GB），之後在本機 CPU 上跑。結果寫到 data/index/explore2_results.json。勘誤的替換字串放在 data/index/errata_patches.json，這個檔含教材原文所以沒有收錄，沒有它程式照樣能跑，只是不套用勘誤。

## 資料來源與使用限制

教材、勘誤表與試題來自經濟部產業發展署的 [iPAS AI 應用規劃師學習資源頁](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)。這些檔案的著作權屬原權利人，本 repo 不收錄也不再散布原始檔與由其產生的索引；需要的人請自行到官方頁下載，放到 data/raw/。各檔案內的聲明原文與授權確認進度記在 progress。

## 工作方式

本專案沿用 problem-def-template 的流程：先讀 [使用指南](docs/workflow/guide.md)，AI 工具的共同規則在 [AGENTS.md](AGENTS.md)。

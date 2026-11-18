# iPAS AI 應用規劃師範例

這個資料夾是本專案唯一附帶的領域範例：用 iPAS AI 應用規劃師的官方學習指引建立知識庫，回答備考問題。管線本身不綁定這個領域；換成自己的資料時，照這個資料夾的結構寫一份自己的設定即可，見 [換成自己的資料](../../docs/custom-data.md)。

## 檔案

| 檔案 | 內容 | 進版控的是什麼 |
|---|---|---|
| [knowledge-base.no-errata.json](knowledge-base.no-errata.json) | 五科學習指引（初級 2、中級 3）的路徑、版本、SHA-256 與官方下載網址前綴；不套勘誤 | 只有設定與雜湊；PDF 不在 repo 內 |
| [knowledge-base.json](knowledge-base.json) | 同上，另指定本機勘誤替換檔 | 替換檔含教材原文，只在作者本機 `data/`，不進版控 |
| [profile.json](profile.json) | 助理角色「iPAS 備考輔助」、文件名稱「官方學習指引」、規則「不要聲稱找到實際命題出處」 | 全文 |
| [sample/notes.json](sample/notes.json) | 作者自寫的 iPAS 主題短筆記，供離線示範 | 全文；不是官方教材的內容或摘錄 |

## 兩種跑法

**一分鐘離線示範**（不需 GPU、網路或教材）：

```sh
uv run python -m ipas_hub.demo
```

使用 `sample/notes.json` 與 `profile.json`，模型以照腳本回覆的替身代替，重播六種情境：選擇題正確引用、修正一次後通過、捏造引用被拒、術語對不上被標 ⚠、找不到依據就不呼叫模型、索引被竄改就拒絕載入。

**完整五科知識庫**：先從官方下載教材並核對雜湊，再建索引：

```sh
uv run python -m ipas_hub.cli fetch --config examples/ipas/knowledge-base.no-errata.json
uv run python -m ipas_hub.cli index --config examples/ipas/knowledge-base.no-errata.json
uv run python -m ipas_hub.cli search --index <上一步輸出的 index> --kb ipas --method bm25 --query "什麼是詞性標註？"
```

接上向量檢索、本機 LLM 與聊天介面的完整步驟見 [Windows 完整安裝](../../docs/setup.md)；生成時加上 `--profile examples/ipas/profile.json`。

## 權利邊界

- **教材**：iPAS 學習指引可從[官方學習資源](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)取得，但 PDF 內有版權聲明。本 repo 不再散布 PDF、切塊原文或含原文的索引，只記錄官方網址與雜湊，由使用者自行下載。官方若更新檔案，`fetch` 會因雜湊不符而停止，請確認新版本後再更新設定。
- **自寫筆記**：`sample/notes.json` 是本專案作者自己寫的內容，與程式同採 [MIT](../../LICENSE)。
- **外部搜尋**：開啟維基百科補充時，引用會標示 CC BY-SA 4.0 與條目版本連結，並註明句子經模型改寫。
- 更完整的工具、模型與資料授權盤點見 [THIRD_PARTY_NOTICES](../../THIRD_PARTY_NOTICES.md)。

本範例是獨立學習專案，不代表 iPAS 主辦單位的立場。

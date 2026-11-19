<!--
title: 第三方工具、模型與資料授權盤點
status: in-review
updated: 2026-11-18
-->

# 第三方工具、模型與資料授權盤點

本專案使用下列第三方工具與模型，權利屬各原作者。本頁說明用途、查核來源與需遵守的條件；**不是授權條款全文，也不是「整個專案已完成法律合規驗證」的證明**。本專案的程式與作者自寫內容自 2026-11-18 起採 [MIT](LICENSE)；MIT 只涵蓋本專案自有的部分，不能因此把依賴套件、模型、教材或生成結果視為同一授權。

查核日期：2026-11-17。程式基底 `ceea64a2502b1f44d5d67842c61b0c4761aa5620`，含同日未提交文件。版本依據為 [pyproject.toml](pyproject.toml)、[uv.lock](uv.lock)、[Dockerfile](Dockerfile)、[compose.yaml](compose.yaml)。官方連結多為上游當前分支；除另註外，尚未逐一核對鎖定版本的發布包與完整映像授權，因此下表是主要元件盤點，不是完整 SBOM 或可直接用於二進位再散布的 notices bundle。

## 主要開源工具

| 工具／版本依據 | 本專案用途 | 上游授權及來源 |
|---|---|---|
| Python，要求 ≥3.11，容器 3.12-slim | CLI、檢索與 HTTP 服務 | [PSF 與 Python 所附歷史／第三方條款](https://docs.python.org/3/license.html) |
| NumPy，lock 有 2.4.6／2.5.5，依環境解析 | 向量運算與索引驗證 | 核心 [BSD-3-Clause](https://github.com/numpy/numpy/blob/main/LICENSE.txt)；wheel 另有內含元件條款 |
| pypdf 7.1.0 | PDF 文字擷取 | [BSD-3-Clause](https://github.com/py-pdf/pypdf/blob/main/LICENSE) |
| Sentence Transformers 6.3.0（可選） | 載入 embedding 模型 | [Apache-2.0](https://github.com/huggingface/sentence-transformers/blob/main/LICENSE) |
| Psycopg／psycopg-binary 3.3.9（可選） | PostgreSQL 連線 | [LGPL v3](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt)；本機套件 metadata 為 LGPL-3.0-only |
| PostgreSQL 17 系列 | 索引、來源及片段儲存 | [PostgreSQL License](https://www.postgresql.org/about/licence/) |
| pgvector，Compose tag 0.8.6-pg17＋digest | 資料庫向量距離查詢 | [PostgreSQL License](https://github.com/pgvector/pgvector/blob/master/LICENSE) |
| vLLM，Compose tag v0.26.0＋digest | 本機模型推論服務 | [Apache-2.0](https://github.com/vllm-project/vllm/blob/main/LICENSE)；不涵蓋整個映像所有元件 |
| AnythingLLM，Compose latest＋固定 digest | 現成聊天介面 | [MIT](https://github.com/Mintplex-Labs/anything-llm/blob/master/LICENSE)；不是本專案自行開發的 UI |
| uv，Docker／CI 0.9.11 | Python 套件與環境管理 | [MIT OR Apache-2.0，可擇一](https://github.com/astral-sh/uv#license) |
| Hatchling，build-system 未固定版本 | Python 套件建置 | [MIT](https://github.com/pypa/hatch/blob/master/LICENSE.txt)；實際建置版本待交付時記錄 |
| pytest 9.2.0 | 自動化測試 | [MIT](https://github.com/pytest-dev/pytest/blob/main/LICENSE) |
| Docker Compose，使用者安裝版本 | 啟動 db／LLM／UI | [Apache-2.0](https://github.com/docker/compose/blob/main/LICENSE) |

Python extras 還會帶入 PyTorch、Transformers、Hugging Face Hub、Tokenizers、Safetensors、SciPy、scikit-learn 等依賴。uv.lock 記錄解析版本與檔案雜湊，但不是完整授權清單。本輪讀取本機套件 metadata 已見 NumPy／PyTorch 含多種授權，不能把整個 wheel 簡化成上表核心授權。完整傳遞依賴、原生函式庫及每個映像內的 OS／CUDA 元件仍需在打包再散布前盤點。

Docker Desktop **不等於 Docker Compose 的開源授權**。它適用 Docker Subscription Service Agreement；官方列個人使用等免費條件，大型組織專業使用與政府單位等另有付費要求，應依實際使用情境核對。[官方說明](https://docs.docker.com/subscription-billing/desktop-license/)

## 模型權重另行看待

| 模型 | 用途／版本 | 查核結果 |
|---|---|---|
| BAAI/bge-m3 | 文字 embedding；實際 snapshot revision 記在索引 manifest | [官方模型卡標示 MIT](https://huggingface.co/BAAI/bge-m3)；未逐一核對使用者快取 snapshot 全部檔案 |
| intfloat/multilingual-e5-small | 僅供離線 embedding 選型實驗；revision `614241f622f53c4eeff9890bdc4f31cfecc418b3`，非正式服務模型 | 2026-11-18 查核[官方模型卡標示 MIT](https://huggingface.co/intfloat/multilingual-e5-small)；權重僅存本機 data/models，不進版控，未完成整個 snapshot 的再散布盤點 |
| Qwen/Qwen3-VL-8B-Instruct-FP8 | 本機生成；Compose 固定 revision `9cdc6310a8cb770ce18efaf4e9935334512aee45`，僅載入文字部分 | [官方模型卡標示 Apache-2.0](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct-FP8)；本輪工具未能讀取該 revision 的 LICENSE 全文，精確 snapshot 再散布查核仍未完成 |

模型由使用者自行取得，repo 不附權重。若未來打包模型，需保留該 snapshot 的條款、必要聲明與來源，另外核對 tokenizer、模型程式及其他附檔；不將推論框架授權套到權重上。模型授權也不會自動授予輸入教材或輸出中第三方表達的再利用權利。

## 遵守授權時要做什麼

以下是工作摘要，適用時仍以該發布包完整條款為準：

- **MIT／BSD／PostgreSQL**：再散布時保留要求的著作權、授權及免責聲明；BSD 的不背書條件也要遵守。不能只有本頁的超連結就當作已附上必要全文。
- **Apache-2.0**：附授權、保留適用聲明，修改檔案需註記；上游有應保留的 NOTICE 時一併處理。程式授權不代表取得商標背書權。
- **LGPL（Psycopg）**：依實際散布方式核對函式庫原始碼、修改、必要告知及讓使用者替換／重新連結函式庫等義務；不能直接推論整個 app 必須改為 LGPL，也不能推論裝進容器就免除條件。[授權全文](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt)
- `psycopg[binary]` 的 wheel 帶有所需原生函式庫，須另查內含元件；只記 Psycopg 本身不足以完成二進位分發盤點。[官方安裝說明](https://www.psycopg.org/psycopg3/docs/basic/install.html)

目前 repo 交付設定只在本機／CI 建映像，不推送 registry。若要發布容器、安裝包或模型包，應以實際 artifact 產生完整清單、保留 LICENSE／NOTICE、履行適用原始碼提供義務，再確認可發布；本頁不能取代這些工作。

## 文件、教材與搜尋內容

| 素材 | 現況與來源 | 本專案採取的邊界 |
|---|---|---|
| iPAS 學習指引、勘誤及試題 | [官方學習資源](https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources)可取得；既有 PDF 檢查記錄有版權聲明，見 [brief](docs/internal/project/brief.md) | 不推定可下載就是開放授權。PDF、原文切塊、勘誤替換檔、索引及含原文日誌不進版控；公開重製或服務前需確認適用權利依據 |
| 法律條文本身 | 臺灣著作權法第 9 條列法律等不作為著作權標的 | 不把此規則擴張成所有政府網站內容皆無權利；第三方註釋、圖像或教材另判斷。保留來源與版本，非官方背書。[法條來源](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0070017) |
| 維基百科文字 | 依頁面適用授權；通常可選 CC BY-SA 4.0，例外內容須另看 | 再利用時保留來源／作者歸屬方式、授權連結與修改標示；涉及改作分享時遵守相同方式分享。不能把 AI 改寫當作自動免除條件。[Wikimedia 條款](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use)、[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) |
| 範例筆記 `examples/ipas/sample/notes.json` | 作者自寫的 iPAS 主題短文，不是官方教材的內容或摘錄 | 與程式採相同授權；供離線示範，不代表教材原文 |
| 自有或公司 PDF | 匯入者須具備使用該內容的權限 | 公司文件還涉及保密／個資與外送政策；本機使用亦不自動解除義務，先用本機模型與 web none |
| 逐選項解析 `docs/internal/project/explanations/` | AI 撰寫（檔頭已標示）、作者複核；不含題目原文，列官方答案代碼、各選項正誤理由與教材頁碼 | 2026-11-18 作者判斷可保留公開：試題依下列第 9 條說明不受保護，答案代碼屬事實，理由為自行撰寫、未搬運第三方詳解。純 AI 生成部分不一定能主張著作權；不得加入他人網站或參考書的詳解 |
| 報告、展示截圖 | README 的 GIF 含一頁官方學習指引畫面，僅示範引用跳頁、停留約 3 秒 | 不擷取整份教材或可連續閱讀的頁面；示範文字優先用自寫內容 |

非商業、學習或註明出處都不單獨保證任何利用合法。引用／合理使用需依具體利用方式及適用法律判斷，不是「有引用就可任意公開」；臺灣著作權法第 52、64、65 條分別涉及引用、出處及合理使用判斷。[法規](https://law.moj.gov.tw/LawClass/LawAll.aspx?pcode=J0070017) iPAS 依《經濟部推動產業人才能力鑑定及管理辦法》辦理，該辦法法源為產業創新條例第 18 條第 2 項（[辦法條文，第三方法規網站](https://6laws.net/6law/law3/經濟部推動產業人才能力鑑定及管理辦法.htm)），作者據此認定公告試題屬第 9 條第 1 項第 5 款「依法令舉行之各類考試試題」，不得為著作權標的；此為作者判斷，非法律意見，現行條文宜再以全國法規資料庫核對。學習指引不是試題，不適用此款。

## 目前尚未完成的合規工作

1. ~~本專案程式授權~~：2026-11-18 採 MIT。協作範本來源 `problem-def-template` 為作者自己的 repo；本 repo 已移除範本副本，改為連結。
2. ~~公開展示內容審查~~：逐選項解析與 GIF 的判斷見上表（2026-11-18）。其他新增展示素材仍先採自寫文件。
3. **維基輸出告知**：2026-11-18 起，維基來源帶 `license: CC BY-SA 4.0`，輸出在引用後標示授權、附授權連結與條目 revision 連結，並註明句子由模型改寫、非原文（`rag.py`；`test_wikipedia_sources_carry_license_and_modification_notice`）。作者歸屬以條目版本連結（含編輯歷史）呈現；改作後再分享時的相同方式分享義務仍由分享者判斷，本程式不代為處理。
4. **二進位／映像再散布**：精確模型 snapshot、所有傳遞依賴、OS／CUDA、LICENSE／NOTICE 與適用原始碼提供方式尚未驗證，不能標成已可再散布。

本輪證據：`git ls-files data` 及追蹤 PDF／PNG／JPG／NPY／safetensors 查詢均無結果；`.dockerignore` 採 allowlist 排除資料及模型。這只代表當前追蹤／建置邊界，不是所有歷史提交、文字引用與授權均已清查。本輪沒有對外發布，也沒有修改既有服務。

若準備正式公開服務、散布含第三方素材的套件，或對教材利用依據仍有疑義，需向權利人或合格法律專業人士確認具體情境；本頁提供可追溯盤點與待辦，不能保證零侵權風險。

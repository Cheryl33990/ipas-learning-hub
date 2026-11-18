<!--
title: 進度與接手
status: draft
updated: 2026-11-18
-->

# 進度與接手

目前階段與前進判斷（2026-11-18，本機服務重啟，等待使用者在畫面確認排版）：PR #32 已由使用者合併（2fd31b8），CI run 44277252794 通過。使用者同意後重啟本機 serve：停止 2026-11-17 啟動的舊 process（--store pg --routes config/rag-routes.json --port 8100），以 main 2fd31b8 的程式重新啟動相同參數；PG_DSN 指向 Compose db（127.0.0.1:5433），PGPASSWORD 在單一指令內從 .env 讀入環境變數，未印出、未寫入檔案。服務掛在 Claude Code session 底下，session 結束可能隨之停止。驗證：/v1/models 回 rag 與 labor-law；以顯著性圖原題呼叫 /v1/chat/completions（model rag，開外搜），回覆 Markdown 中模型核對 ⚠ 各自成段，結尾有「模型核對 5 句：1 句未直接支持、1 句部分支持」。Chrome 擴充未連線，AnythingLLM 畫面排版未由 AI 檢視。使用者截圖（問 ADAM 與 SGD 差異）回報：⚠ 各自成段、依據連結正常，但結尾「核對：…」與「模型核對…」併成同一段。修正（分支 fix/markdown-verify-line，基於 2fd31b8）：render_text 的 Markdown 版在模型核對統計前空一行，終端機版不變；先寫失敗測試再修，全部 171 passed／7 skipped，ruff 通過。修正需再重啟 serve 才會生效，尚未重啟。使用者另回報「不是解題也會出現答案或選擇」：掃描 data/runs 中 30 筆無選項的提問，4 筆含「答案：B」（差分隱私與 K 匿名化，11-18 11:14 左右），都由 11-17 啟動的舊 serve 回答；移除多餘答案的 drop_unasked_choice 於 399f3d5（11-18 11:49）才加入，舊 process 沒有載入。重啟後 ADAM 那題模型仍寫了「答案：D」，已由程式移除（removed_choice=D），畫面上未出現。其餘紀錄沒有選項式用語，判定不需再改程式。這是本機服務重啟，不是部署或驗收。

目前階段與前進判斷（2026-11-18，修正切題後重新判讀三方法皆拒答題，草稿待使用者確認）：PR #31 已由使用者合併（5678a6c），CI run 44275856208 通過；AnythingLLM 畫面上 ⚠ 排版尚未看過。分支 docs/refusal-review-reparse（基於 5678a6c）。以 248 題補充結果（225 題正式＋23 題重跑）重算三方法皆拒答：13 題（原 15 題）。離開名單 3 題：i115-1-s2-47、s3-43（修正後三方法答對）、s3-47（圖題，修正後 BM25 與混合答錯）；新進 1 題：i115-1-s2-39（新切出）。13 題中 9 題題目文字未變，沿用 PR #27 已確認的判讀；需重判 4 題（s2-39 新切出；s2-45、s2-46、s3-41 加回題組情境或截掉混入文字）。做法同前：以修正後題目重跑混合（k=5、外搜關閉、qwen3-vl-8b-fp8、檔案索引 ce5090f4…，未使用 .env 密碼），4 題皆仍拒答；混合 top-5 與重跑評估相同；取三方法 top-20，並以關鍵詞搜尋 1,389 個片段。本機檔案 data/evaluation/refusal-review-reparse/（diagnose.py、raw.json，含原文不進版控）。AI 草稿：s2-45、s2-46 未涵蓋（教材無 groupby、nlargest、布林篩選等語法，Pandas 只出現名稱）；s3-41 未涵蓋（教材只把翻轉列為一般影像資料增強，未說明不適用於有方向的字母）；s2-39 程式碼在圖中，且教材無 Python 函式預設參數等內容（def、append、預設參數皆 0 筆），分類待使用者決定「未涵蓋」或「圖表」。檢索失敗 0。使用者 2026-11-18 確認 4 題草稿皆同意，s2-39 分為未涵蓋。結果：13 題中未涵蓋 12、圖表 1、題幹解析 0、檢索失敗 0。新判定檔 examples/ipas/eval/refusal-review-reparse-2026-11-18.json（13 題，標明沿用或重判；不含原文），舊判定檔不改寫；evaluation.md 新增小節並在舊小節的後續更正加連結；STATUS 已完成與下一步更新（下一步：在 AnythingLLM 畫面確認 ⚠ 排版）。本輪只改文件與判定檔，未改程式。下一步：開 PR、等 CI，等使用者合併。

目前階段與前進判斷（2026-11-18，引用主題相近但沒有直接支持，設計與測試規劃）：PR #30 已由使用者合併（9a22e8c）。分支 feat/citation-support（基於 9a22e8c）。先量現況（本機 data/evaluation/review-sample/raw.json，20 題抽樣的回答原文）：130 句中 94 句帶引用，字詞核對標記 34 句（15／20 題至少一句被標）；34 句中 32 句的原因是「找不到題目中的詞（可能只是重述題目）」，只有 2 句是低重疊。顯著性圖那題（b115-2-s1-30）的第一句其實有被標記（Saliency、Map 不在片段中），但理由和其他 31 句一樣是「可能只是重述題目」，所以沒有區分度；evaluation.md 寫「字詞核對沒有抓出」不精確，本輪一併更正。該詞也不在該題 top-5 任何片段中，代表這句來自模型本身的知識，重新選引用無法修正，應改標為推論或不引用；被標的題目詞中只有 4 句可在其他未引用的片段找到。已向使用者提出測法（逐句標註＋以同題未引用片段替換做合成負例、量召回率與誤標率、先量基準不設門檻）與兩種改法（本機 LLM 逐句核對、只改字詞規則），等使用者決定。

使用者 2026-11-18 決定：改法 A（本機 LLM 逐句核對）、測法只用合成負例（不做人工標註）、不支持的句子只在畫面標示（不改寫回答）。實作（審查與交付）：rag.verify_segments 與 prompts/verify_citations.txt；回答後再呼叫模型一次，送出帶引用的句子與被引用片段（每個片段只送一次，因 vLLM 上下文 6144），逐句判定 supported／partial／unsupported，寫入 check.support；呼叫失敗、格式不對或漏句標 unverified 並顯示原因，不當作通過；render_text 分開顯示模型核對與字詞核對，結尾加模型核對統計；字詞核對的 flagged_segments 意義不變。answer() 預設 verify=False；cli ask／serve 預設開啟（--no-verify 關閉），exam_eval 組的參數沒有 verify，評估流程不變。測法與結果：先寫 10 個失敗的合成測試（預設關閉、只送帶引用句、判定寫入與顯示、四種失敗皆標未核對、無引用句不呼叫、ask 依參數開關），實作後全部通過；全部 170 passed／7 skipped，ruff check 與 format --check 通過，demo 通過。合成負例（本機 data/evaluation/citation-verify/run.py、run1.json、run2.json，含原文不進版控；qwen3-vl-8b-fp8，兩次判定完全相同，40 次呼叫約 97 秒）：作者判完全支持的 18 題 86 句中模型標出 19 句（22%），字詞核對 30 句（35%）；合成負例 94 句模型標出 63 句（67%），字詞核對 51 句（54%）；顯著性圖題 5 句皆 unsupported；引用練習題那題 0 句（這類問題抓不到）。Claude 抽查（未經作者確認）：負例被判 supported 的 31 句抽 10 句，約 3 句片段確實支持、4 句部分、3 句明顯漏抓；完全支持題被標的 19 句抽 8 句都含片段沒寫的細節或推論。逐句判定（不含原文）存 examples/ipas/eval/citation-verify-2026-11-18.json。真實端到端（ask --store file，索引 ce5090f4…，--web none）：顯著性圖原題 5 句皆顯示「模型核對：引用片段沒有直接寫出此句」。文件：evaluation.md 新增小節並加「字詞核對沒有抓出」的後續更正；README 中英、EVIDENCE、STATUS（下一步改為重新判讀三方法皆拒答題）、architecture 同步。下一步：開 PR、等 CI，等使用者合併。

目前階段與前進判斷（2026-11-18，ruff format）：PR #29 已由使用者合併（38f083c），CI run 44272951815 通過，是 main ruleset 生效後第一個 PR。全域 git email 與 GitHub email 隱私設定由使用者自行處理，AI 未驗證。分支 style/ruff-format（基於 38f083c）。使用者選擇做 ruff format。範圍：版控內 Python 檔只有 src 與 tests 共 27 個（先前估計約 31 檔），其中 26 檔被重新格式化，沿用 line-length 120。測法：格式化前後對 27 檔各算 ast.dump 的 SHA-256，兩份完全相同（純格式、行為不變）；ruff format --check、ruff check 通過；pytest 160 passed／7 skipped。commit 拆兩筆：fcb4c1b（只有格式化）與後續一筆（CI 新增 ruff format --check 步驟、pyproject 註解、README 中英 CI 說明、.git-blame-ignore-revs 列入格式化 commit，讓 git blame 略過它）。.git-blame-ignore-revs 依賴保留原 commit hash，所以本 PR 要用 merge commit 合併，不要 squash。下一步：開 PR、等 CI，等使用者合併。

目前階段與前進判斷（2026-11-18，資安收尾，等待使用者決定）：PR #28 已由使用者合併（4c06689）。分支 chore/security-hardening（基於 4c06689）。唯讀檢查（gh api，未修改任何設定）：secret scanning、push protection、Dependabot alerts 與 security updates 皆未開啟；main 沒有分支保護，也沒有 ruleset；CI 的 check 名稱為 test-and-container；forks 0。commit email（只判斷是否為 noreply，未輸出地址）：68 個 commit 中有 25 個的作者與 committer 都是同一個非 noreply 地址，時間分布在 2026-11-16 到 2026-11-18，不是只有早期；最早一筆之後 main 上有 66 個 commit，改寫歷史會讓這些 hash 全部改變，已追蹤文件中引用的既有 commit hash 有 58 個。全域 git email 不是 noreply；本 repo 的本機設定已是 noreply。使用者 2026-11-18 決定：(a) 執行，不加 dependabot.yml；(b) 選 A（只防止以後再外洩，不改寫歷史）；(c) 照建議設定。已執行並以 gh api 讀回驗證：secret_scanning、secret_scanning_push_protection、dependabot_security_updates 皆為 enabled；vulnerability-alerts 回 204（已開啟）；automated-security-fixes enabled=true。新增 ruleset「main」（id 27535237，enforcement active，目標為預設分支）：禁止刪除、禁止 force push、必須經 PR（不要求審核人數）、必須通過 test-and-container；未設 bypass。rules/branches/main 讀回這四條規則。email 選 A 後，已公開的 25 個 commit 不改寫；全域 git email 改為 noreply，以及 GitHub 的 Keep my email addresses private 與 Block command line pushes that expose my email，由使用者自行設定，AI 未代為執行，也未驗證。本 PR 是 ruleset 生效後的第一個 PR，會實際測到必須通過 CI 才能合併的規則。下一步：使用者合併本 PR；之後從「引用主題相近但沒有直接支持」、ruff format、重新判讀三方法皆拒答的題目三項中選一項。

目前階段與前進判斷（2026-11-18，修正試題切題解析）：PR #27 已由使用者合併（b3bc6d3）。分支 fix/exam-question-groups（基於 b3bc6d3）。檢查真實試題 PDF 後發現的問題比 PR #27 記錄的更多：(1) 答案欄全形字母（Ａ–Ｄ）未被辨識，i115-1-s1-50、s2-39、s2-40、s3-44、s3-45 共 5 題從未切出，整題併入前一題，所以正式評估實際只涵蓋 248 題中的 243 題；(2)「題目 答案」順序相反的頁首未移除；(3)「二、程式題」大題標題接在前一題；(4) 題組情境與指示句（可能在情境前或後、可能跨行）接在前一題，題組內各題反而沒有情境。修正：exam.py 接受全形字母並轉回 A–D；頁首與大題標題列入雜訊；題組情境從最後一個 (D) 後第一個縮排行切出，移除指示句，加在題組範圍內每一題的前面。測法：先寫 4 個失敗的合成測試（全形與反序頁首、情境在指示句後、情境在指示句前、指示句跨行與大題標題），修正後全數通過；全部測試 160 passed／7 skipped，ruff 通過。真實 PDF 比對（本機）：五卷題號皆連續，共 248 題；與舊版相比 23 題不同（新切出 5、文字變更 18），沒有頁首或指示句殘留；3 題「(A) 出現兩次」是題幹原文引用。重跑：使用者選擇在指令內帶入 PGPASSWORD（從 .env 讀入單一 process 環境變數，未印出、未寫入檔案）；以本機子集設定 data/evaluation/reparse-2026-11-18/manifest.json 執行正式 exam_eval，23 題 × 3 方法共 69 筆完成，索引 ce5090f4…、prompt b9e2e2a7…、程式 54cb88d。combine.py 以 summarize() 合併 225 題正式結果＋23 題重跑：248 題 BM25 204（82.3%）、向量 207（83.5%）、混合 218（87.9%）；混合對 BM25 +5.6 個百分點（CI +2.4 ~ +9.7），向量 +1.2（−2.8 ~ +5.2）；以同一函式重算正式 243 題與已發布數字一致。i115-1-s2-47 加回題組情境後三方法皆答對，PR #27 判為「未涵蓋」是因題目缺情境；判定檔不改寫，於 evaluation.md 加後續更正。結果寫入 evaluation.md（補充小節、更正、證據表）、README 中英版、STATUS。正式 243 題數字不改寫。已開 PR #28，CI 通過（run 44271119216）；未合併。下一步：等使用者合併。

目前階段與前進判斷（2026-11-18，三方法皆拒答 15 題判讀，草稿待使用者確認）：PR #26 已由使用者合併（aaa7e87），repo 已 Public。分支 docs/refusal-review（基於 aaa7e87）。做法：以正式評估相同設定（混合、k=5、外搜關閉、qwen3-vl-8b-fp8；檔案索引 ce5090f4…，避免使用 .env 密碼）重跑 15 題，皆仍拒答，混合 top-5 與正式評估（pg）逐筆相同；另取三方法 top-20，並以關鍵詞搜尋全部 1,389 個片段，確認教材是否涵蓋。題幹混入下一題組的 3 題，手動截掉後重跑。本機檔案在 data/evaluation/refusal-review/（diagnose.py、clean_stem.py、raw.json、clean_stem.json、draft.json、review.md；含試題與教材原文，不進版控）。AI 草稿分類：未涵蓋 12（GRPO、AutoSkill、Dify 對話歷史、Agentic Coding、合約上下文設計、Agent 任務規劃器、Solution Graph、ReAct、Pandas 三題、翻轉破壞字母方向）、圖表 2（Apriori 交易表、描述 A–F）、題幹解析 1（i115-1-s3-43：截掉後答 D＝官方答案）、檢索失敗 0。另發現 243 題中有 7 題題幹混入下一題組文字（exam.py 解析問題），其中 3 題在本 15 題內。使用者 2026-11-18 確認 15 題分類全部同意，並決定本 PR 只放判讀結果、exam.py 修正另開 PR。判定（不含原文）存 examples/ipas/eval/refusal-review-2026-11-18.json，結果寫入 evaluation.md（新增小節、更新 24 題說明、證據表與不支持描述）與 STATUS（下一步改為修正切題解析）。已開 PR #27，CI 通過（run 44268840400）；未合併。下一步：等使用者合併；之後可另開 PR 修正 exam.py 切題（7 題題幹混入下一題組）並重跑受影響題目。

目前階段與前進判斷（2026-11-18，repo 公開）：PR #25 已由使用者合併（bd860a5）。使用者自行將 repo 改為 Public；已以 gh repo view 確認 visibility=PUBLIC，未登入的 HTTP 請求取得 200。本分支 docs/status-public 更新 STATUS 可見性與公開前準備區塊。公開前準備（檢核、PR #22–#25、About／topics）全部完成。可選後續（未授權、未開始）：ruff format（約 31 檔）；三方法皆拒答 15 題逐題判讀；引用主題相近但未直接支持的改善。

目前階段與前進判斷（2026-11-18，GitHub About 與 topics）：PR #24 已由使用者合併。使用者同意照提案修改 About 與 topics（對外動作），已以 gh repo edit 執行並讀回確認：description「Local RAG that cites every answer sentence back to the exact PDF page and version, with BM25/vector/RRF hybrid retrieval, pgvector and vLLM. Example: Taiwan iPAS AI Application Planner exam prep.」；topics bm25、citations、hybrid-search、llm-evaluation、local-llm、pgvector、postgresql、python、rag、retrieval-augmented-generation、traditional-chinese、vllm；homepage 留空。repo 仍為 PRIVATE：改為 Public 使用者尚未同意，未執行。下一步：等使用者決定是否公開（指令：gh repo edit Cheryl33990/ipas-learning-hub --visibility public --accept-visibility-change-consequences）；之後可做 ruff format 與拒答 15 題判讀。

目前階段與前進判斷（2026-11-18，PR C：雙語 README）：PR #23 已由使用者合併（fd0a4f1）。分支 docs/bilingual-readme（基於 fd0a4f1）。使用者確認語言分層：README 中英雙語（英文 README.md 為預設、README.zh-TW.md 為中文），About／topics／PR 與 commit 標題／pyproject description／.env.example／CI 用英文；docs/ 維持中文；docs/internal 不翻譯；程式註解維持中文；prompts、回答與錯誤訊息、profile 必須中文。本輪：git mv README.md → README.zh-TW.md 並加語言切換；新寫英文 README.md，結構與中文版一致，並註明 docs/、prompts 與回答為中文；docs/README.md 改連中文版並附英文連結；pyproject description 改英文。順帶修正：中文 README「為什麼做這個」表最後一列仍寫「樣本太小、尚不足以宣稱勝出」，已與 evaluation.md 不一致，兩版改為「243 題保留題：混合比 BM25 高 5.3 個百分點；向量相對 BM25 的區間含 0」。驗證：腳本比對兩版 README 二級標題數（11／11）與正文數字（排除程式碼區塊與連結後完全相同）、相對連結皆存在；數字對照 evaluation.md。已開 PR #24，CI 通過（run 44266232799）；GitHub API 渲染結果含切換連結、mermaid 與 GIF，尚未目視檢查；未合併。下一步：等使用者合併 PR #24，再提出 About／topics／公開指令，待使用者同意才執行。

目前階段與前進判斷（2026-11-18，PR B：.env.example）：PR #22 已由使用者合併（8d6741e）。分支 docs/env-example（基於 8d6741e）。從 compose.yaml、程式 getenv、CI 與文件整理全部環境變數，新增 .env.example（英文註解，依讀取者分 A Compose 自動讀取／B 主機 Python 須在 shell 設定／C 開發與建置三區；每項註明用途、必填與預設，值一律佔位符；未讀取 .env 實際值）。查核發現：RAG_PORT 只告訴 UI 連哪個埠，serve 本身用 --port（預設 8100）；IPAS_CODE_VERSION 只在 git 不可用時作為後備；compose 的 app 容器 LLM_MODEL 由 LLM_SERVED_NAME 帶入。.gitignore 的 `.env` 規則不排除 .env.example（git check-ignore 確認），未改 .gitignore。setup.md 改為由範本複製 .env、移除「repo 為 private」句；README、custom-data、SECURITY 加上引用。驗證：docker compose --env-file .env.example（三個 profile）config 通過；PowerShell 複製指令與 PGPASSWORD 擷取在暫存資料夾實跑可用；git diff --check 通過。只改文件與範本，未跑 pytest（CI 會跑）。已開 PR #23（6effd01），CI 通過（run 44264028240）；未合併。下一步：等使用者合併 PR #23，再做 PR C（英文 README）。

目前階段與前進判斷（2026-11-18，公開前成熟度檢核與架構清理）：main 5891f4c（PR #21 已合併）。檢核（以首次閱讀的資深工程師角度）：47 個 commit 歷史未曾追蹤 data/、PDF、.env，未發現密鑰或本機路徑，tracked 檔無教材／試題長段原文；25 個 commit 作者 email 為個人信箱，使用者決定接受（PR refs 會保留舊 commit，改寫歷史也無法完全移除），本 repo 本機 git 設定改用 noreply；範本 repo problem-def-template 已由使用者公開，連結回 200，選 (a) 保留連結。使用者確認並授權的範圍：PR A（本分支 chore/public-cleanup）刪除探索期模組 explore2／explain／record／scoring 與其測試、拆分 rag.answer、加入 ruff check；之後依序 PR B（.env.example）、PR C（英文 README）、最後提出 About／topics／公開指令待使用者同意。rag.answer 測法：既有 test_rag 約 40 個 answer 測試＋一次性等價腳本（11 種情境含修正、選擇題、同頁多段、外部、無證據、拒絕），重構前後完整輸出逐位元相同（腳本與輸出在 session 暫存，不進版控）；answer 由約 83 行降為 43 行。驗證：uv run pytest --basetemp 暫存 156 passed／7 skipped（移除 14＋2 個探索模組測試，原 172）；ruff check 通過；demo 六情境符合預期；git diff --check 通過。未做：ruff format（會改 31 檔，另開 PR）；乾淨新機安裝仍未驗證。已提交 742c56b 並開 PR #22，GitHub Actions CI 全部步驟通過（run 44263376325）；未合併。下一步：等使用者合併 PR #22，再做 PR B（.env.example）。

目前階段與前進判斷（2026-11-18，答對題理由與引用抽樣判讀）：PR #20 已由使用者合併（71ef78a）。分支 docs/reasoning-review（基於 71ef78a），未提交。從混合答對 212 題中每卷隨機抽 4 題（random.Random(0)），以正式評估相同設定重跑取得原文（20 題選項皆與正式評估相同），產出本機對照表 data/evaluation/review-sample/review.md（含試題與教材原文，不進版控；腳本 sample.py、原始輸出 raw.json 同處）。使用者（作者本人）判讀：理由對 20（i115-1-s3-48 原誤填「支」，使用者確認為「對」）；引用支 18、部 2（b115-2-s1-30 引用 NLP 概論而無顯著性圖說明；i115-1-s3-48 引用章末練習題題目）、不 0。判定（不含原文）存 examples/ipas/eval/reasoning-review-2026-11-18.json，結果寫入 evaluation.md、README、STATUS。另發現 i115-1-s3-48 題幹混入下一題組情境文字（試題解析問題）。非獨立第三方審查。使用者授權提交並開 PR。

目前階段與前進判斷（2026-11-18，保留題評估完成，審查與交付）：PR #19 已由使用者合併（132ea9a），本分支基底 c82fcb1 已在 main 內。正式評估 729 筆全部完成，無中斷：BM25 199／243（81.9%）、向量 204（84.0%）、混合 212（87.2%）；混合對 BM25 改善 17、退步 4，差 +5.3 個百分點（成對 bootstrap 95% CI +1.7 ~ +9.0），向量對 BM25 CI −2.1 ~ +6.2 含 0。檢索 p50 21／245／242 ms，生成 p50 約 7 秒。錯誤 5 筆皆為修正後仍引用不存在的 id；補全觸發 5 筆（4 題）；修正 46 筆；三方法皆錯 24 題（15 題皆拒答，原因未人工判讀）；字詞警告約六成回答出現，雜訊高。結果填入 docs/evaluation.md、README、STATUS；逐筆輸出留 data/evaluation/heldout-2026-11-18/（不進版控）。驗證：172 passed／7 skipped，diff check 通過。未做：理由／引用語意判讀、拒答題逐題判讀。下一步：提交並開 PR。

（以下為同日稍早紀錄）保留題評估實作：PR #19（MIT、移除範本）當時已開，未合併。使用者選定 240 題方案並授權執行。分支 feat/heldout-eval（基於 chore/public-prep c82fcb1），未提交。新增 exam_eval.py（官方答案自動比對、三方法輪換、可續跑、成對 bootstrap、報告不含題目原文、code_version 未提交時加 +dirty）與 examples/ipas/eval/heldout.json（5 卷 243 題）；試跑 3 題×3 方法發現模型少寫片段序號導致拒答，經使用者選 A，新增 rag.complete_chunk_ids（唯一對應才補全並記 completed_citations）。測試 172 passed／7 skipped。正式評估 2026-11-18 背景執行中：索引 ce5090f4…、qwen3-vl-8b-fp8、prompt b9e2e2a7…、web none、k=5，輸出 data/evaluation/heldout-2026-11-18/。下一步：完成後填入 docs/evaluation.md 與 README，提交並開 PR。

目前階段與前進判斷（2026-11-18，公開前準備，審查與交付）：PR #18 已由使用者合併（5f0f098，CI pass）。使用者決定：程式採 MIT、移除協作範本、評估試題先列清單。分支 chore/public-prep（基於 5f0f098），未提交。新增 LICENSE（MIT，Copyright 2026 Cheryl33990）與 pyproject license 欄位（wheel metadata 為 License-Expression: MIT，uv lock --check 通過）；查得 problem-def-template 為作者自有私人 repo（HEAD 仍為 4c73a73），本機 docs/internal/workflow 與其差異僅路徑改名與 metadata 格式，故移除 35 檔，AGENTS、PR 範本、internal README、brief、progress、readme_history、驗證紀錄的連結改指範本 repo 4c73a73；README／STATUS／THIRD_PARTY_NOTICES／examples 授權敘述改為 MIT；依使用者查證與法源（產業人才能力鑑定辦法，法源產業創新條例第 18 條第 2 項），逐選項解析判斷可保留並記理由與限制。驗證：162 passed／7 skipped；39 份 Markdown 失效連結 0；EVIDENCE 58 個測試名稱皆存在。評估試題盤點：本機 14 份公告試題皆可解析並附官方答案（每份 39–50 題）；開發期間 115 年第三次初級科目 1 大量使用，其他梯次僅零星 1–2 題；115 年第一次中級三科完全未用。下一步：使用者選定保留測試集後實作批次評估。

目前階段與前進判斷（2026-11-18，通用管線＋iPAS 單一範例，審查與交付）：分支 docs/public-presentation（基於 09947fb），未提交。第一段：參考 Hsiang-Tang/canopus 的公開呈現，新增離線示範、docs/EVIDENCE.md、docs/STATUS.md、SECURITY.md，重寫 README，CI 加示範步驟，pyproject 描述更新。第二段（使用者 2026-11-18 決定：勞基法只移出公開文件、示範改用自寫 iPAS 筆記、套件名維持 ipas_hub）：參考 Azure-Samples/azure-search-openai-demo、zylon-ai/private-gpt、Langchain-Chatchat 等做法，新增 profile.py（prompts/answer.txt 改為共用契約＋{{intro}} 等欄位；iPAS profile 組出的 prompt 雜湊等於抽出前 b9e2e2a7…，歷史 prompt_sha256 可比較；未指定時用通用設定），ask／serve 加 --profile，路由可選 profile（rag 指向 iPAS，labor-law 改用通用設定）；新增 fetch.py 與 cli fetch（https、SHA-256 不符不留檔、不覆寫不同內容；download_base 放設定頂層以免改變既有 index_id）；維基來源標示 CC BY-SA 4.0、授權連結與「經模型改寫」；iPAS 設定搬到 examples/ipas/（knowledge-base*.json、profile.json、sample/notes.json 自寫筆記、README），index 預設 --config 同步；demo 改用自寫筆記與 iPAS profile；docs/documents.md 改為 docs/custom-data.md（換資料三要素），docs/examples/labor-law.md 移到 docs/internal/project/examples/ 並修連結；setup、architecture、environment、THIRD_PARTY_NOTICES、EVIDENCE、STATUS 同步；Dockerfile／.dockerignore 加入 examples。驗證：Windows 159 passed／7 skipped（pg 未設 DSN 略過）；Docker test 目標 159 passed／7 skipped，runtime 映像 --network none 可跑 demo；cli fetch 對本機五份教材皆 present，另實際自官方下載初級科目 1 至暫存路徑、雜湊相符後刪除；EVIDENCE 55 個測試名稱皆存在；74 份 Markdown 只剩既有範本佔位連結 1 個；README 示範輸出與實際一致；uv lock --check、git diff --check 通過；hosted CI 未跑；真實 LLM 未重跑。未決（作者決定）：LICENSE、explanations 逐選項解析的權利、repo 公開與 GitHub 描述、操作畫面錄製。補充（同日）：使用者錄製 GIF（真實 vLLM、iPAS profile、rag 路由）時，非選擇題「請問差分隱私與K匿名化的差異」回答末尾出現「答案：B」；送出的 prompt 與改版前相同，屬既有行為。新增 rag.drop_unasked_choice：題目無選項時由程式移除「答案：X」並記錄 removed_choice，選擇題不變；3 項新測試，2 項既有選擇題測試補上選項；Windows 162 passed／7 skipped。使用者重啟 serve 後重錄（非選擇題「請問差分隱私跟同態加密的差異」，回答末尾已無「答案：X」，引用連到 PDF 第 172 頁），即為本版在真實 vLLM 上的人工確認。GIF 由原檔（桌面，2466×1365、37 秒，未修改）裁切聊天欄與 PDF 區、輸入 2 倍速、等待 4 倍速並加字幕、PDF 留 3 秒、縮至 960px，輸出 docs/assets/demo.gif（16.6 秒、4.6 MB），放入 README「實際畫面」。下一步：使用者看 diff，授權後提交與開 PR。

目前階段與前進判斷（2026-11-17，分支清理完成）：使用者明確要求檢查並刪除雲端舊分支。本機／遠端 main 為 09947fb，工作樹開始時乾淨；原遠端共 18 個分支、無開啟中的 PR。17 個非 main 分支逐一以 merge-base 與 rev-list 核對，皆為 main 祖先、未合併提交數 0，且對應 PR #1–#17 全部已合併、head SHA 相符；刪除前的名稱／SHA 存於 data/review/branch-cleanup-20261117.json。已以 atomic push 與各分支預期 SHA 的 force-with-lease 完成 17 個遠端分支刪除，fetch --prune 後 ls-remote --heads 確認只剩 main，SHA 未變。本機分支保留，程式與服務未改，不執行應用測試。本輪清理完成，無待刪遠端分支；本段為本機未提交紀錄，不另開補記 PR。

目前階段與前進判斷（2026-11-17，文件整理提交與合併）：使用者詢問 docs/internal 是否應忽略，並明確授權討論後提交、開 PR 與 merge。判斷為保留版控：此處含設計／驗證及解析工具所需紀錄，internal 並非私密；README／gitignore 註解已說明，本機草稿沿用 data/review。GitHub 查核目前 repo 為 private，本輪不改可見性。開始為審查與交付；沿用前輪程式 131 passed／7 skipped 與連結／產生器驗證，提交前再檢查實際 staged diff、機敏資料與搬移完整性；CI 須對應本批 head 通過才依授權合併。保留智慧財產與公開準備缺口，AI 自查不冒充真人批准。最終提交、PR、CI 與 merge 識別記在該 PR 和回覆，不另開補記 PR；此紀錄隨本批提交。

目前階段與前進判斷（2026-11-17，面試作品集文件整理完成）：可送使用者審查。README 聚焦用途、工程重點、架構、實測硬體與使用入口；公開文件為 docs/{README,architecture,environment,setup,documents,evaluation}.md 與 docs/examples/labor-law.md。64 個原有檔案搬移，歷史／協作集中 docs/internal/project、docs/internal/workflow；AGENTS、PR 範本、explore2／explain 讀寫路徑同步修正。Markdown 頁頂 metadata 全改 HTML 註解，產生器同步，歷史狀態與證據保留。硬體查核為 Ryzen 7 9800X3D／8C16T、32 GiB RAM、RTX 5070 Ti 16 GB、Windows 11 Pro build 26200，詳細軟體版本見 [環境](../../environment.md)。初次受限 CIM 拒絕及 Docker／uv 不可執行後，經工具核准在使用者環境完成唯讀查核；未讀序號或變更服務。

本輪驗證：基底 ceea64a＋累積工作樹；`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=data/test-tmp/docs-layout-20261117` 為 131 passed／7 skipped（PG_TEST_DSN 未設定），3.05 秒；50 筆探索標註可讀、render_public 與搬移後解析全文一致。70 份 Markdown 無頁頂 YAML 表格；本機連結無新增斷鏈（原範本 HTML 註解中的示意「路徑」保留），diff check 通過。原始資料／索引未改；未重跑真實模型、Docker build、hosted CI 或 GitHub 頁面目視。Git 尚未 stage，搬移會先顯示舊檔 D／新檔 ??，不是丟棄歷史。未提交／PR／合併／開源發布；下一步使用者審閱公開入口，另批處理既有授權與品質缺口。

目前階段與前進判斷（2026-11-17，面試作品集文件整理開始）：使用者要求實際硬體環境、精簡公開目錄與移除頁頂 metadata 表格。已授權文件結構調整；方案為公開文件集中 docs、協作與歷史集中 docs/internal，AGENTS／產生器引用同步更新；metadata 改 HTML 註解。事前測法：搬移前記錄本機相對連結基線，搬移後確認無新增斷鏈／舊路徑，檢查產生器輸出及既有測試；不變更 RAG 行為與運作服務。硬體唯讀核對，不收錄序號或機器名稱。下一步完成搬移、環境表與 README 精簡／AI。

目前階段與前進判斷（2026-11-17，開源與智慧財產盤點完成）：新增根目錄 [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md)，列主要工具／模型用途、lock／Compose 版本依據、官方授權來源、資料與再散布邊界，README／brief 已連入。查核官方 LICENSE／模型卡、Docker Desktop／Wikimedia 條款及臺灣著作權法；本機 metadata 發現 Psycopg LGPL-3.0-only、NumPy／PyTorch 多重條款。Qwen 固定 revision 的 LICENSE 未能讀取，僅確認官方模型卡 Apache-2.0；未冒充精確 artifact 查核。git ls-files data 與指定 PDF／圖片／向量／權重副檔名無追蹤結果；文件 51 個本機連結及 diff check 通過。本輪純文件未重跑應用測試，前輪 131 passed／7 skipped 只屬前輪。結論為可送文件審查，非法律合規保證；本專案／模板授權、教材與解析公開權利、維基輸出授權告知、完整映像及傳遞依賴盤點仍待處理。下一步由作者決定分享形式與程式授權，依實際交付 artifact 完成權利核對；本輪無公開、提交、部署或對外聯絡。

目前階段與前進判斷（2026-11-17，開源與智慧財產盤點開始）：使用者要求說明開源工具並符合智慧財產。沿用前輪未提交文件，核對 pyproject／uv.lock／Docker／模型設定、官方授權與資料來源政策；先建立清單與分享邊界，再檢查連結及差異。未完成條件為精確套件／映像所含全部授權、教材再利用權限與本專案授權決定；不將工具開源或非商業使用推定成所有素材均可再散布。未授權公開發布；下一步補授權說明／AI。

目前階段與前進判斷（2026-11-17，side project 盤點完成）：文件實作與 AI 自查完成，可送使用者審查。README 已重整為產品／架構入口；新增 requirements、一般 PDF 快速開始及[嚴格審查](validation/2026-11-17-side-project-review.md)，原 README 封存 readme_history.md，修正 AI 架設文件的過期分庫指引。基底 ceea64a 加本輪純文件差異；131 passed、7 skipped（未設定 PG_TEST_DSN），52 個本機連結與四段 PowerShell 語法檢查通過、CLI 選項核對與 diff check 通過。尚缺乾淨新機重現、可分享示範／人工品質評估、生成 prompt 通用化及授權選擇；建議下一輪先補自寫 PDF 示範與分庫案例，候選判準未視為使用者接受。未改程式、服務、資料庫或索引，未提交／PR／合併／發布；審查不是品質驗收或整體結案。

目前階段與前進判斷（2026-11-17，side project 嚴格盤點）：探索與文件修訂。使用者授權檢查完整度、重整 README、補充 requirements 與通用文件 RAG 定位。基底 ceea64a2502b1f44d5d67842c61b0c4761aa5620，開始時工作樹乾淨。最小證據為程式／設定／測試／既有驗證交叉核對；測法為現有離線測試、CLI 範例、相對連結及 diff 檢查。未達條件為陌生人重現、內容品質及分享門檻；本輪不改執行行為、不操作現有服務。下一步完成 README、通用匯入說明與具優先序的審查發現／AI。

目前階段與前進判斷（2026-11-17，本批交付）：使用者已確認本次進展並明確授權提交、開PR與合併。feat/document-knowledge-bases基底c4bd89d，受審範圍為一般PDF、勞基法獨立庫、模型分庫路由、測試及操作文件；提交前重跑138 passed（含本機pg），未改動運作中的服務。AI自查可送審，依本批hosted CI結果合併；最終CI／merge SHA以同一PR紀錄為準，不另開合併補記PR。本筆與末筆隨功能同批提交，品質缺陷及未驗證範圍仍保留。

目前階段與前進判斷（2026-11-17，使用者工作區試用與設定說明）：使用者已實際試用並確認勞基法回答到問題、詢問機器學習時不提供解答（OK）；這是該次操作確認，不推定全面品質驗收。截圖中AnythingLLM向量計數0屬其內建LanceDB空工作區；自建RAG另查pgvector，唯讀核對ipas為1,389／1,389個向量、labor-law為51／51個向量，皆1,024維。說明兩層設定與搜尋參數差異，不改目前運作設定。

目前階段與前進判斷（2026-11-17，勞基法工作區已啟用）：本機操作驗證完成、可供使用者試用。使用者要求直接執行並給連結；已啟動共用8100，rag→ipas／維基、labor-law→labor-law／web none，沿用現有勞基法工作區並實跑2題。138測試通過，UI頁HTTP與實際工作區SSE／PDF可用，原rag設定保持；工時題的變形工時補充概括過度已記內容缺陷。原8101臨時服務已由共用入口取代並停止，db／ui／vLLM保留。工作區連結與啟停見labor_law_setup.md；未提交合併或對外發布。

目前階段與前進判斷（2026-11-17，勞基法實作）：實作完成、審查與試用。feat/document-knowledge-bases 在 main c4bd89d 加未提交變更；一般 PDF／--kb／跨庫拒絕已實作，勞基法官方 PDF 建立 51 塊、1,024 維索引 6f1226f8… 並載入 pg。132 個測試通過（含資料庫），4 題真實檢索與 1 題 LLM／HTTP 引用管線通過；不宣稱法律或整體品質驗收。操作見 labor_law_setup.md，原 8100 未動，多庫重啟 iPAS 須加 --kb ipas。未提交、開 PR 或發布，詳見末筆。

目前階段與前進判斷（2026-11-17，通用 PDF 與知識庫隔離）：定義轉設計。使用者將範圍擴至內部文件／法條等文字型 PDF，要求文件與測試分割，並同意上一輪順序。已更新 brief，核對既有 SQL 依 index_id 隔離、預設卻選全域最近索引的限制；第一批候選為通用 PDF、明確知識庫選擇、跨庫不召回及測試資料隔離。尚未改程式／資料庫或確定重大架構，下一步定介面、相容策略與逐項測法。

目前階段與前進判斷（2026-11-17，可換教材的 RAG side project）：定義階段。使用者明確提出可擴充非 iPAS 教材、以模型知識或 web 補強，以及供他人參考的完整產品體驗；已寫入 brief 的「產品方向更新」。缺口為文件格式／匯入方式、無依據補充政策與驗收邊界。一般 PDF 與來源分層屬 AI 候選方案，未當作已確認 AC；本輪不直接改 parser／prompt。下一步將通用教材匯入、回答來源與示範交付拆成可驗證小批次。

目前階段與前進判斷（2026-11-17，新手交接與效能證據盤點）：本輪從探索／文件設計進到審查。使用者已親自看見資料庫向量，詢問完整度、新手／AI 架設文件與混合搜尋說服力。已建立新手手冊、AI 架設指引與證據盤點，README 更新現況；只新增文件，未修改檢索。新機從零生成模型路徑與新手實測未通過驗證，評估方案為暫定未採用；未執行新 benchmark、提交或發布。詳見末筆。

目前階段與前進判斷（2026-11-17，本輪交付完成）：使用者明確授權提交、開 PR、合併。已提交 e9bdd9e，建立 [PR #15](https://github.com/Cheryl33990/ipas-learning-hub/pull/15)，本批 CI 通過後轉 ready 並合併為 c4bd89d。本機 main 已快轉同步。交付證據見末筆；部署、介面試用與品質驗收尚未完成。本段及末筆為合併後本機補記，尚未提交。

目前階段與前進判斷（2026-11-17，本輪接手審查）：審查與交付。受審版本為 chore/data-layout-intermediate、基底 127f204 加未提交的 13 檔變更。README 的 UTF-8 讀檔及五科操作說明已修正，本輪單元測試與真實教材回歸通過，AI review 判斷可提交並開 PR；合併仍須本批 CI 通過及負責人最後決定。尚未提交、開 PR 或合併；答題品質及人工勘誤複核未驗收。詳細證據見末筆。

本檔是當前工作入口。第一輪結果保留；第二輪解析與補記分別由 PR #1、#2 合併，main 為 5cf7d96。第三輪先做雙科檢索、Docker、CI/CD 與 MLOps 基礎，LLM 下一步再選。使用者已回覆「當前的內容 OK」，接受目前原型；第廿一筆記錄主機及 Docker 37 個測試通過、新 8 題基準三種檢索各 5／8。檢索限制、hosted CI 及 LLM 未驗證項保留。docs/rag-next-iteration-plan 分支尚未 commit 或推送，本次內容接受不當作提交授權。

第二十四筆完成指定未命中診斷：24 組前五頁碼序列與歷史一致，原結果維持各 5／8；5 題、9 組未命中的排名與片段支持範圍見[診斷](validation/2026-11-16-retrieval-miss-analysis.md)。建議先做獨立的支持範圍標註版評估 v2，尚未採用；原排序、索引、案例與解析未變。AI 判讀待關鍵人工確認。

第二十五筆：使用者已同意 v2 方案；[v2 結果](validation/2026-11-16-retrieval-support-v2.md)完成全 8 題、90 筆片段標註與 24 組凍結結果重評，120 個前五位置均有分類。方法採用與內容判讀分開：標註仍為 AI 待審，原 v1 保留，未改排序或選 LLM。資料主來源為 data/evaluation/rag-retrieval-support-v2.json；原文對照與獨立驗證腳本在同目錄，不進版控。

目前進度（第三十八筆）：使用者已批准最終 29 檔 diff 的 commit／push／Draft PR；已提交並推送 b38e031，建立 [Draft PR #3](https://github.com/Cheryl33990/ipas-learning-hub/pull/3)。目前為程式審查與雲端 CI 待確認階段；三組試用已回覆，本輪先前 Windows／Docker 各37項測試通過。上方及歷史紀錄按當時狀態保留，最新動作以此與末筆為準。本筆交付紀錄為提交後補記，尚未提交。

目前進度（第六十四筆）：PR #14 已合併為 127f204。data/raw 已改為級別／類型兩層、官方檔名；中級三科教材與 AI 整理的中級勘誤已納入新索引 ce5090f4…（已載入資料庫），中級試題 6 題實跑 5 題引用中級教材。未提交，待使用者審查。見末筆。

目前進度（第六十三筆）：刪除多下載的模型檔並修正因此發現的載入問題；聊天回覆改為每句分段、瀏覽器開端點時顯示說明頁；與 README 修正一起提交、開 PR 並合併。接著調整資料夾並納入中級教材。見末筆。

目前進度（第六十二筆）：PR #13 已合併為 a8b085f、main CI success。依 README 在全新 clone 從頭重現成功；發現 README 的模型下載指令會多抓 2.3 GB，已在 docs/repro-verification 修正，未提交。AnythingLLM 畫面經 --store pg 的操作待使用者試用。見末筆。

目前進度（第六十一筆）：PR #12 已合併為 96d91cb；預設檢索方法改為混合（兩種儲存皆同，沒有向量時自動改用 BM25 並提醒）；feat/pgvector 提交並開 PR，待同意合併。見末筆。

目前進度（第六十筆）：PostgreSQL＋pgvector 已在 feat/pgvector 實作並實機驗證（資料庫與檔案索引檢索結果相同、serve --store pg 可用），未提交，待使用者審查；PR #12 待同意合併。見末筆。

目前進度（第五十七筆）：選擇題改為一定明寫「答案：X」、⚠ 註明是否為題目用詞、圓括號內的 id 會清除；同 8 題重跑 8 題都明寫並與官方一致。準備提交並開 PR，之後做 pgvector，見末筆。

目前進度（第五十六筆）：PR #10、#11 已合併，main 為 7371408、CI success。官方資源 17 份已下載到 data/raw/ 的新子目錄；新試題抽 8 題試跑皆選出官方答案，並記下四項觀察到的問題。pgvector 細部設計待提，見末筆。本筆與第五十五筆尚未提交。

目前進度（第五十五筆）：PDF 頁碼提交為 135e1a1、開 PR #11；PR #10、#11 皆待使用者同意合併。試題下載網址與大小已列出，等使用者確認範圍，尚未下載，見末筆。

目前進度（第五十四筆）：第二步已提交為 9814af5、開 PR #10（CI pass，待使用者同意合併）。PDF 頁碼與教材連結在分支 feat/pdf-page-links 實作完成並實機核對，未提交；AnythingLLM 畫面上點連結尚未驗證，見末筆。

目前進度（第五十三筆）：新對話接手並核對狀態；第二步變更（端點＋AnythingLLM）已備妥 diff，等使用者同意提交與開 PR。之後依序做 PDF 頁碼與教材連結、試題下載、pgvector，做法已提案待確認，見末筆。

目前進度（第五十二筆）：PR #9 已合併為 222013a；使用者試用後決定補 PDF 頁碼（可連到教材該頁）、下載其他試題、加入 pgvector。第二步變更仍未提交，見末筆。

目前進度（第五十一筆）：PR #9 已開、CI pass、待合併；第二步的 OpenAI 相容端點與 AnythingLLM 介面已實作並實機跑通 3 則，未提交，見末筆。

目前進度（第四十九筆）：LibreChat 與 AnythingLLM 內建 RAG 已用相同 6 題加勘誤探針實測並與本專案並排，見末筆；等使用者決定是否保留自建檢索、補 PDF 頁碼及第二步的平台。compose.yaml 與本筆未提交。

目前進度（第四十八筆）：第四十七筆補記經 PR #8 合併為 cac0f1c，main CI success；網頁介面平台的授權已查證並提出候選比較，等使用者選定實測平台與同意下載映像。本筆尚未提交，見末筆。

目前進度（第四十七筆）：PR #7 已合併為 7ecb211，main CI success；下一步在新對話做網頁介面選型（現成平台＋本專案 RAG 端點）。本筆補記與 brief 修訂尚未提交。

目前進度（第四十六筆）：PR #6 已合併為 877feb4；在 feat/web-search-context 實作外部搜尋前後文與英文維基備援，未提交，見末筆。

目前進度（第四十五筆）：第四十四筆補記經 PR #5 合併為 add04c5；在 feat/sentence-citations 實作逐句引用與字詞核對，未提交，見末筆。

目前進度（第四十四筆）：PR #4 端到端 RAG 已於 2026-11-17 合併為 7c74cbe，PR 與 main 的 CI 均通過；本筆合併補記尚未提交。以下第三十九筆段落為歷史狀態。

目前進度（第三十九筆，取代上段的「CI 待確認」狀態）：實際查證 PR #3 已於 2026-11-16T10:30:32Z 合併為 7376873，PR 與合併後 main 的 hosted CI 均為 success。本機 main 已快轉至 7376873；第三十八、三十九筆補記在新分支 docs/record-pr-3-merge 的工作樹，尚未提交。獨立真人程式審查仍無紀錄，合併不等於品質驗收、部署或結案。MAE 外部補證的可追溯化方案已獲使用者接受並實作（第四十筆），13 條主張待人工審查，全部變更尚未提交。

## 初始化與路徑對照
- 模板來源／採用 commit：problem-def-template `4c73a73`；本 repo 初始 commit `c6f651c`
- 專案目標與 AC 主來源：[brief.md](brief.md)
- 程式：src/ipas_hub/（Python，用 uv 管理，相依套件在 pyproject.toml）。探索二的進入點是 `uv run python -m ipas_hub.explore2`
- 第三輪程式：knowledge.py（雙科版本化索引）、cli.py（index／search／evaluate；ask 為未實測生成草案）、rag.py 與 prompts/answer.txt（後續生成契約）。Dockerfile、compose.yaml 與 .dockerignore 在 repo 根目錄；.github/workflows/ci.yaml、delivery.yaml 為尚未推送執行的 CI／手動交付設定。
- 第三輪設計與證據：[設計](design/rag-prototype.md)、[本輪驗證](validation/2026-11-16-docker-retrieval.md)。來源清單 config/knowledge-base.json；科目 2 勘誤替換在 data/index/subject2-errata-patches.json，不進版控。索引在 data/index/kb/，執行紀錄在 data/runs/，新基準在 data/evaluation/，都不進版控。
- 可執行測試：tests/test_core.py、tests/test_explain.py，用 `uv run pytest` 執行；目前 uv 存取遭拒，可用 `.venv/Scripts/python.exe -m pytest -p no:cacheprovider`
- 原始資料：data/raw/（guide、errata、exam 三個子目錄），已由 .gitignore 的 data/ 規則排除
- 科目 2 教材：data/raw/guide-subject2/（刻意與科目 1 的 guide/ 分開，避免既有探索程式選錯 PDF）；擷取文字與查證腳本只在 data/index/。解析 JSON 的 additional_guides 記檔名、來源識別與雜湊。
- 索引與切塊：data/index/（同樣被排除）。目前有 errata_patches.json（人工從勘誤表整理的替換字串，含教材原文所以不進版控）與 explore2_results.json（探索二的原始輸出）
- 逐選項解析：資料檔 explanations/115-3-subject1.json（主來源），閱讀用 [explanations/115-3-subject1.md](explanations/115-3-subject1.md) 由 `uv run python -m ipas_hub.explain` 產生；兩者都不含題目原文，進版控
- 雙科參照：閱讀用解析開頭提供 50 題索引，引用明列科目、頁碼與支持程度；目前 21 題列有科目 2 依據或相關頁，不能視為 21 題已確認實際命題出處。對照檔重產如與原檔不同會另存 data/review/115-3-subject1-review.generated.md，原筆記保留。
- 複核對照：data/review/115-3-subject1-review.md（含題目原文，不進版控）；判定記在 [validation/2026-11-16-explanation-review.md](validation/2026-11-16-explanation-review.md)
- 探索二結果：[discovery/exploration-2-results.md](discovery/exploration-2-results.md)，進版控，只記題號與頁碼
- 外部下載：PyPI 套件（pypdf、numpy、sentence-transformers 及其相依，含 torch）；Hugging Face 模型 BAAI/bge-m3，存在使用者的 Hugging Face 快取，不在 repo 內
- 探索一紀錄表：[discovery/exploration-1-record.md](discovery/exploration-1-record.md)，進版控，只記題號、答案、頁碼與分類，不含題目或教材原文
- 已建立的決策／設計／實驗／驗證結果：只有上列探索一紀錄表；其餘需要時新增
- 裁剪與 N/A 理由：docs/template-maintenance 已移除（只屬於模板本身）；教學 examples 保留
- 專案負責人與 review／合併方式：使用者本人；合併方式待確認

### 初始化待辦
- [x] 根 README 改寫為本專案介紹，移除模板維護入口（2026-11-16）
- [x] 移除 docs/template-maintenance（2026-11-16）
- [x] .gitignore 加入原始資料與索引的路徑：data/（2026-11-16；已用 git check-ignore 確認 data/raw 與 data/index 被排除）
- [ ] 確認 AI 工具是否自動讀取 AGENTS.md：Claude Code 在 2026-11-16 這次工作階段有自動載入；其他工具未測

## 目前階段與前進判斷

依 [方法論導航](https://github.com/Cheryl33990/problem-def-template/blob/4c73a73/docs/workflow/guide.md#method-map) 判定，按本輪任務更新，不代表整個專案的百分比。

| 任務／本輪範圍 | 目前階段 | 已有最小產出／證據連結與版本 | 未達條件／待確認或風險 | 前進判斷 | 下一個最小動作／負責人 |
|---|---|---|---|---|---|
| 第八輪：PDF 頁碼與教材連結（引用定位 v0.6） | 審查與交付（實作完成，待使用者看 diff 與畫面試用） | 分支 feat/pdf-page-links（基於 9814af5），未提交；[設計 v0.6](design/rag-prototype.md)；Windows 98 passed；新索引頁序核對與端點實跑見第五十四筆 | AnythingLLM 畫面上連結是否可點、是否跳到該頁未驗證（瀏覽器自動化工具連不上）；實機只跑 1 則；Docker test 目標未跑 | 可送審；畫面驗證需使用者重啟 serve 後點一次 | 使用者看 diff、重啟 serve 試點連結、同意提交／使用者 |
| 第七輪：網頁介面（現成平台＋本專案 RAG 端點） | 實作（第二步：端點＋AnythingLLM；第一步比較已完成） | brief 第四輪「網頁介面」列；授權查證見第四十八筆、並排實測見第四十九筆 | 實機只跑 3 則；畫面排版未經 AI 檢視（使用者已親自試用）；沒有多輪對話；引用只有章節頁碼；變更未提交、無獨立真人程式審查 | 可送審：使用者已選 AnythingLLM 並試用（第五十、五十二筆）；Windows 92 passed（第五十三筆實跑） | 使用者看 diff 後同意提交與開 PR／使用者；之後 PDF 頁碼與連結、試題下載、pgvector／AI 提案待確認 |
| 第六輪：外部搜尋前後文＋英文維基備援（v0.4） | 已合併（2026-11-17，PR #7 → 7ecb211） | 分支 feat/web-search-context（基於 877feb4）；[設計 v0.4](design/rag-prototype.md)；77 passed（Windows）；同 6 題實跑見第四十六筆 | 6 題結果不代表泛化，第 15 題前後結果不穩；維基 429 限流；中文相關性規則仍放過部分無關頁；Docker 未跑 | 同 6 題由 3 對／1 錯／2 不足變為 6 題皆選出官方答案 | 無（已合併；限制保留於第四十六筆） |
| 第五輪：逐句引用＋字詞核對（生成契約 v0.3） | 已合併（2026-11-17，PR #6 → 877feb4） | 分支 feat/sentence-citations（基於 637944a）；[設計 v0.3](design/rag-prototype.md)；67 passed（Windows）；vLLM 實跑 6 題（第 28 題＋8 題以外 5 題），見第四十五筆 | 字詞核對會漏標（第 15 題掛到 RANSAC 條目未被標出）；檢索／維基搜尋對 LIME 等詞找不到依據，2 題回依據不足；1 題證據在手仍推理錯（第 15 題）；Docker 未跑 | 逐句標示已可用；核對只是輔助提示 | 無（已合併；限制轉入第六輪） |
| 第四輪：端到端 RAG（教材＋維基百科＋vLLM） | 已合併（2026-11-17） | PR #4：ef67cea → 合併提交 7c74cbe；PR CI 與 main CI（run 44004961566）皆 success；57 passed；8 題實跑與使用者試用見第四十一、四十二筆 | 引用只檢查 id、不檢查內容是否支持該句；8 題不代表泛化；向量／混合檢索未做端到端；pgvector 未做；無獨立真人程式審查 | 合併完成，不等於品質驗收或結案 | 新對話接續：先提交本筆補記，再選下一項（建議引用逐句化與內容核對） |
| MAE 外部補證可追溯化 | 停止（2026-11-17 使用者決定刪除） | 登錄檔、evidence.py 與其測試已刪除且從未提交；過程見第三十九、四十筆 | 無 | 停止：外部依據改由 RAG 即時搜尋提供 | 無 |
| 第三輪 PR #3 交付 | 已合併（2026-11-16 實際查證） | b38e031 → 合併提交 7376873；[PR #3](https://github.com/Cheryl33990/ipas-learning-hub/pull/3)；CI run 43849133563（PR）與 43849483100（main）皆 success | 無獨立真人程式審查紀錄；hosted CI 只跑合成測試與容器檢查，未涵蓋真實教材、embeddings 容器、delivery workflow 或 LLM；未部署 | 合併完成，不等於品質驗收或結案 | 提交合併補記（需使用者看 diff 後授權）；原列內容見第三十八筆 |
| 第4／40題外部補證 | 筆記完成、待審 | [補證](validation/2026-11-16-fairness-mode-collapse-evidence.md)：六份第一手來源 | 第4題優先性仍為推論，B／D措辭待修；未整合索引 | 核心定義已有外部支持 | 審查來源範圍與最小修訂建議 |
| 第28題 MAE 外部補證 | 證據筆記完成、待審 | [補證](validation/2026-11-16-mae-external-evidence.md)：五份官方文件與自造算例 | 尚未納入教材索引；非官方考綱查證 | 定義與搭配已有外部支持 | 先審查獨立筆記，再議來源整合或第4／40題補證 |
| 檢索與內容缺口清單 | 整理完成 | [清單](validation/2026-11-16-retrieval-gap-register.md)：三組核心排名缺口、全八題內容限制及評估集合落差 | 不證明全教材不存在；僅28／32所審判讀獲人工確認 | 優先處理已確認的 MAE 補證需求 | 外部補證與排序實驗分別規劃，原結果保留 |
| 題幹單因素實驗 | 探索完成 | [比較](validation/2026-11-16-stem-query.md)：原前20重現、48組檢索及43筆補標 | 新標註為 AI 待審；八題有限 | 三方法皆退步，不採用一律移除選項 | 收斂預處理試驗，整理可用範圍與缺口 |
| 實際內容重疊分析 | 探索完成 | [分析](validation/2026-11-16-content-overlap.md)：2,727 對獨立檢核通過 | 無完全包含；字面重疊不能判定語意冗餘 | 整塊去重無本批改善證據 | 停止為命中調低去重門檻；下一輪選單一查詢因素 |
| 28／32 關鍵判讀對照 | 審查準備完成 | data/evaluation/review-28-32.md：兩題、六塊完整原文與三個確認項；雜湊核對一致 | 使用者已確認兩題所審判讀；MAE 需外部支持；第 28 題獨立資訊損失尚未證明 | 可直接審查，不將片段數減少當作實質退步 | 人工確認見第二十八筆；接續量測實際內容重疊 |
| 同頁去重單因素實驗 | 探索完成，待關鍵判讀審查 | [實驗](validation/2026-11-16-page-dedup.md)：24 組比較與獨立重播通過；只有第 32 題向量新增核心命中 | 第 28 題核心片段流失；AI 判讀未經人工確認，非端到端效能測試 | 不建議採用同頁一塊為預設，保留正式排序 | 確認得失判讀；下一候選只排除實際內容重複，尚未執行 |
| 支持範圍標註版評估 v2 | 審查與交付（AI 標註完成） | [v2 結果](validation/2026-11-16-retrieval-support-v2.md)：8 題、90 筆、24 組／120 個位置；獨立讀回及雜湊驗證通過 | 內容判讀待人工確認；有限候選池、非盲審；不宣稱品質驗收 | 可審查內容；原 v1 各 5／8 保留，未改排序 | 使用者確認關鍵判讀；AI 依意見另版修訂，不開始多因素改善 |
| 第三輪後續：未命中診斷 | 探索（已有結果，待關鍵判讀確認） | [診斷](validation/2026-11-16-retrieval-miss-analysis.md)：來源與切塊核對、24 組前五重現、9 組未命中逐片段判讀；HEAD 5cf7d96 加未提交原型 | AI 支持範圍判讀未經使用者確認；knowledge.py 與主機索引記錄雜湊不同；無逐頁影像目視 | 可進選擇：有證據提出獨立評估 v2；本輪不採用或改排序 | 使用者確認第 4、40、49 題的關鍵判讀與是否採用 v2 提案；AI 備妥原文對照 |
| 第三輪：雙科檢索與 Docker | 實作（可審查原型） | 主機及容器 37 passed；雙科共 266 塊；7 筆勘誤套用；Docker 內建索引／搜尋／評估已跑，見[驗證](validation/2026-11-16-docker-retrieval.md) | 8 題基準三方法各 5／8，未達成任何自定品質門檻；hosted CI 與大型 embeddings 映像未跑；未 commit | 可審查 diff 與證據，不宣稱檢索品質已驗收 | 判讀未命中與預期頁集合完整性，確認檢索下一步；LLM 依使用者選擇延後選型 |
| 探索一：50 題分類 | 探索（已有結果） | [紀錄表](discovery/exploration-1-record.md) 50 題皆有分類與依據或註明找不到：A 1、B 25、C 24 | 依據頁碼與類型是 AI 代填，使用者未複核；A／B 區分不反映使用者體驗 | 可返回定義：結果足以討論第二輪先做什麼，但只來自一份試題 | 抽查幾題邊界題（3、4、24、37、40、41）／使用者，非必要 |
| 探索二：關鍵字與向量檢索比較 | 探索（已有結果） | [結果](discovery/exploration-2-results.md)：26 題前 5 筆命中，BM25 21、向量 24；程式已納入 1fcff63 | 只跑一次、一種設定；標準答案未經人工複核；未獨立 review | 原結果保留，第二輪已開始 | 本輪不重跑，也不以新增科目 2 改寫舊數字 |
| 第二輪：逐選項解析 | 審查與交付（成果與補記皆已合併） | PR #1 af2a9ce、PR #2 5cf7d96；必看 9 題、抽查 5 題皆正確 | 其餘 36 題無逐題判定；候選 AC 未逐項確認採用；獨立程式 review 與來源查證限制保留 | 原成果保留，可作下一輪的參考資料，不當作已完成 RAG | 下一輪另定義流程與測法，不改寫原探索結果 |
| 第二輪補查：跨科教材依據 | 審查與交付（已隨 PR #1 合併） | 50 題雙科索引；21 題列科目 2 引用；使用者確認目前解析通過 | 不是兩科逐頁人工查證；相關頁不認定實際命題來源；科目 2 勘誤未完整套用，外部原文查證限制仍保留 | 整理結果已合併，第一輪結果保持原樣 | 保留來源限制，依後續實際疑問補查 |
| 授權確認 | 探索 | 官方頁尾僅有版權所有聲明；三份 PDF 內的聲明原文見下方 2026-11-16 第二筆紀錄 | 沒有任何授權或轉載條款可依據；著作權法第 9 條是否適用於這些試題未查證；未向主辦單位詢問 | 留在本步：不阻擋自用，仍阻擋公開 | 決定是否寫信詢問主辦單位／使用者 |

階段沿用指南：起始／定義／探索／選擇／設計與測試規劃／實作／審查與交付／收尾。
前進判斷寫「留在本步」「可進入某階段」「返回某階段」或「停止」，附原因；不能只寫已完成。

## 本輪任務
| 任務 | AC 或探索疑問 | 狀態 | 分支／Issue／PR／證據 | 阻礙與下一步 |
|---|---|---|---|---|
| 支持範圍評估 v2 | 原頁碼命中與實際支持範圍分開 | 待審（全批已建立） | [契約](design/retrieval-support-v2.md)、[結果](validation/2026-11-16-retrieval-support-v2.md)；本機 data/evaluation/ | 方法已獲同意；標註仍為 AI 待審；人工只需確認關鍵判讀 |
| 未命中診斷 | 區分排序、內容支持與預期集合限制 | 待審（診斷已產出） | [逐題診斷](validation/2026-11-16-retrieval-miss-analysis.md)；原文及腳本只在 data/diagnostics/2026-11-16-misses/ | 不改原 5／8；先確認關鍵判讀與單一 v2 提案，未選 LLM |
| 第三輪檢索與 Docker | 本輪已確認技術原型邊界，未設品質百分比 | 待審 | 本機分支未提交；設計與驗證文件見上列 | 先審查新 8 題未命中與資料支持範圍；CI 尚待推送後實跑，生成模型下一步才選 |
| 探索一 | 三類題目各幾題？依據在哪一頁？ | 探索已有結果，分類待人工複核 | [紀錄表](discovery/exploration-1-record.md)，已隨 PR #1 合併 | A 1、B 25、C 24；AI 代填，未複核，未改寫歷史結果 |
| 探索二 | 兩種檢索各找回多少依據段落？ | 已完成（探索有結果，非產品驗收） | [結果](discovery/exploration-2-results.md)；程式在 src/ipas_hub，已 commit | 程式未經獨立 review |
| 逐選項解析 | AC-03、AC-04、AC-05（定義採用仍暫定） | 人工審查通過，成果與補記已合併 | PR #1 af2a9ce、PR #2 5cf7d96 | 跨科原始資料只留 data/，其他限制保留 |
| 授權確認 | 能否公開再散布？ | 進行中 | 聲明原文見下方紀錄 | PDF 內沒有授權條款；下一步是否詢問主辦單位待使用者決定 |
| 初始化待辦 | N/A（專案設定） | 已完成三項 | 已隨 PR #1 合併至 main | 第四項只測了 Claude Code；本次 PR 已採 merge commit，未推定未來皆用同一方式 |

任務狀態：待開始／進行中／受阻／待審／已完成。完成需有結果，不因文件 approved 自動完成。

## 每次工作結束追加

### 2026-11-16（版本：c6f651c 加上未提交的 brief、progress 修改）
- 完成事項與證據：從使用者描述釐清問題，寫入 brief；讀取官方學習資源頁，確認考科、教材、勘誤與公告試題清單。
- 未完成、失敗與限制：未下載任何檔案；試題下載連結、是否附答案、教材正式版次均未確認；未查證著作權法適用性。本次修改尚未 commit。
- 已確認決策與待確認事項：已確認第一輪範圍與先做自用版本。待確認科目與試題份別、費用上限、合併方式。
- 階段變動與依據：起始 → 定義 → 探索（範圍經使用者確認，缺基準故轉探索，不先定產品 AC）。
- 下一步與需要的資料：使用者確認科目與試題；完成初始化待辦；開始探索一。

### 2026-11-16 第二筆（版本：分支 chore/init-and-exploration-1-setup，基於 c6f651c，全部未 commit）
- 完成事項與證據：
  - 初始化：改寫根 README；git rm docs/template-maintenance（6 個檔）；.gitignore 加入 data/。git check-ignore 確認 data/raw、data/index 被排除，下載後 git status 沒有出現 data/。
  - 下載（來源為官方學習資源頁上的連結，檔案實際位於 www.ipas.org.tw）：
    | 檔案（data/raw/ 下） | 大小 | SHA-256 |
    |---|---|---|
    | guide/初級-學習指引-科目1_人工智慧基礎概論1141203.pdf | 5,237,777 bytes | 11eec1f79617aee49989e9e2f1c54c7a33dcaedc5f21d375a9dba5a393ca216c |
    | errata/初級-學習指引勘誤表11404.pdf | 193,306 bytes | 6ed5fe70f12a16f97a99621bbaeeabe6a647a2e55b89fa7a7e64e1a30a3cde50 |
    | exam/115年第三次初級_第一科_人工智慧基礎概論_公告試題.pdf | 590,445 bytes | c6d11084c73e9f9b1edff5a802465135d66a6da14cc3d3ed6fe80525b8a0cc3d |
  - 教材版次：封面標「2025 年版」；官方檔名帶 1141203，上傳時間戳 20251222。PDF 內沒有版次頁，也沒有文件屬性可查。共 71 頁，頁尾頁碼 1-1、2-1、3-1 至 3-63、A-1。
  - 試題附官方答案：是。每題左側「答案」欄有一個字母，擷取文字後數到 50 題、題號 1–50 齊全。答案內容未逐題核對。
  - 勘誤：11404 版勘誤表（PDF 建立日期 2025-04-30）的更正沒有併入 1141203 版教材；抽查 3-25、3-27、3-31、3-32 的字串，教材仍是更正前的文字。
  - PDF 內的著作權或使用聲明原文：
    - 學習指引封面：「2025 年版　版權所有 © 經濟部產業發展署」。同頁列「主辦單位 經濟部產業發展署」「執行單位 工業技術研究院」。
    - 學習指引序言：「本手冊為學習指引，旨在提供學習方向與準備參考，並非正式教材或題庫，亦不保證考試通過之責，建議考生依循考試簡章所公告之評鑑主題內容，進行充分準備，以確保應試成效。」署名「經濟部產業人才能力鑑定推動小組」。
    - 試題：沒有著作權或使用聲明。每頁只有頁首「115 年第三次 AI 應用規劃師-初級能力鑑定【公告試題】」、科目、考試日期與頁碼。
    - 勘誤表：沒有著作權或使用聲明。
  - 建立探索一[紀錄表](discovery/exploration-1-record.md)：50 列，只填題號，其餘留白給使用者。
- 未完成、失敗與限制：
  - 探索一的分類一題都還沒做。沒有寫檢索程式，探索二的判準沒有寫（依指示等探索一完成後、執行前才寫）。
  - 聲明的查找方式是對 pdftotext 擷取的文字搜尋「版權、著作權、翻印、轉載、授權、重製、未經」等關鍵字，加上讀封面圖片。內頁若有以圖片呈現的聲明會漏掉；教材內頁沒有逐頁目視。
  - 本機沒有 PDF 轉圖工具（pdftoppm 未安裝），PDF 檢視外掛與瀏覽器外掛都連不上，所以封面是從 PDF 內嵌的 JPEG 直接取出來看的。教材 PDF 內還嵌有另一張圖，內容是科目 2「考前指引」的封面，標「114 年版」；它出現在哪一頁、是否就是封底，沒有確認。
  - 教材有部分文字擷取不出來：目錄的章標題，以及 PDF 第 46、47 頁（頁尾 3-40、3-41）共 240 個無法解碼的字元。對 Ctrl+F 與之後的切塊都有影響，範圍未細查。
  - 勘誤比對只抽查字串，沒有逐條核對六處更正。
  - 「確認 AI 工具是否自動讀取 AGENTS.md」只確認了 Claude Code。
  - 本次所有修改尚未 commit，等使用者看過 diff。
- 已確認決策與待確認事項：沿用第一輪範圍，沒有新增或變更。待確認：科目與試題是否改標已確認；紀錄表進版控是否可接受；是否向主辦單位詢問授權；費用上限；合併方式。
- 階段變動與依據：探索一仍在探索（資料與表格備妥，分類未開始）；探索二仍在定義；授權確認仍在探索（PDF 內聲明已查，沒有可依據的授權條款）。
- 下一步與需要的資料：使用者看 diff 並決定是否 commit；使用者填探索一紀錄表。探索一完成後再寫探索二判準。

### 2026-11-16 第三筆（版本：分支 chore/init-and-exploration-1-setup，本筆與前一筆的修改一起 commit）
- 完成事項與證據：使用者看過回報後回覆「全部接受」。brief 的科目與試題改標已確認；探索一紀錄表留在版控；在工作分支建立 commit。
- 未完成、失敗與限制：未 push、未合併到 main。探索一仍未開始。是否向主辦單位詢問授權，使用者的回覆沒有明說，未寄出任何信。
- 已確認決策與待確認事項：已確認科目與試題、紀錄表進版控、本次變更可 commit。使用者表示之後會將 repo 轉為 public；轉之前需再檢查版控內沒有原始教材、試題或其擷取內容，data/ 下的檔案能否再散布仍未確認。待確認：是否詢問主辦單位、費用上限、合併方式。
- 階段變動與依據：無變動。
- 下一步與需要的資料：使用者填探索一紀錄表；決定分支如何合併。

### 2026-11-16 第四筆（版本：7cc6f06 加上未提交的紀錄表、brief、progress 修改）
- 完成事項與證據：
  - 使用者自行填完 50 題正確答案；與試題 PDF 的官方答案欄逐題比對，50 題一致。
  - 使用者要求 AI 代填其餘欄位。AI 讀完試題與教材的擷取文字，填入依據頁碼、類型、Ctrl+F 與備註。Ctrl+F 欄是用題目上印的詞對教材擷取文字做字串比對算出來的，每個詞命中的頁碼寫在備註。
  - 結果：A 1 題（第 30 題）、B 25 題、C 24 題。
  - 在 brief 寫下探索二判準草案（暫定）。
- 未完成、失敗與限制：
  - 依據頁碼與類型沒有人工複核。B 與 C 的邊界有幾題可以兩判（3、4、24、37、40、41）。
  - A 與 B 的區分改由字串比對決定，不是使用者實際查找的體驗；「命中太多處」沒有客觀門檻。
  - 字串比對的對象是 pdftotext 擷取的文字，不是 PDF 閱讀器的 Ctrl+F。
  - C 類 24 題的依據是否在科目 2 學習指引內，沒有查（科目 2 教材不在本輪邊界內，也沒有下載）。
  - 沒有寫檢索程式；探索二未執行。本次修改尚未 commit。
- 已確認決策與待確認事項：已確認探索一改由 AI 代填（使用者 2026-11-16）。待確認：探索二判準、embedding 模型、費用上限、是否詢問主辦單位、合併方式。
- 階段變動與依據：探索一由「尚未開始」到「已有結果，可返回定義」；探索二由定義進到探索的執行前準備（判準已草擬、未確認）。
- 下一步與需要的資料：使用者確認探索二判準並決定 embedding 模型與費用上限，之後才寫檢索程式。

### 2026-11-16 第五筆（版本：7468599 加上未提交的程式、測試、結果文件與 brief、progress、README 修改）
- 完成事項與證據：
  - 使用者選擇本機開源 embedding 模型，並回覆「可以接續開發」。探索一結果與探索二判準已 commit（7468599）。
  - 建立 Python 專案（uv、pyproject.toml）。寫了文字正規化與斷詞、教材逐頁擷取與切塊、勘誤套用、試題切分、紀錄表讀取、BM25、命中判定，以及探索二的執行程式。
  - 測試：`uv run pytest`，9 個單元測試通過（合成資料，不含真實教材或試題）。另外對真實檔案做了檢查：試題切出 1–50 題、每題四個選項齊全、答案欄與紀錄表一致；教材 66 頁有頁碼、切成 143 塊；6 筆勘誤都套用成功。
  - 執行探索二一次。26 題計分，前 1／3／5 筆命中：BM25 10／20／21，向量（BAAI/bge-m3）13／22／24。逐題結果與未命中原因歸類在[探索二結果](discovery/exploration-2-results.md)。
- 未完成、失敗與限制：
  - 只跑一次、一種切塊設定、一個模型，沒有調參，也沒有重複執行確認結果穩定。
  - 標準答案未經人工複核。未命中的 6 題中有 3 題（34、40、41）與標準答案的頁碼判定有關；依判準沒有事後修改標準答案。
  - 勘誤表第 7 題解析的補充說明沒有套用。
  - 沒有量檢索分數能否分辨 C 類（教材沒有依據）的題目；兩種方法對 C 類一樣回傳 5 筆。
  - 沒有端對端的自動化測試；真實檔案的檢查是手動跑的，沒有寫成測試（原始檔不進版控）。
  - 程式沒有經過 review。本次修改尚未 commit。
- 已確認決策與待確認事項：已確認用本機開源模型。待確認：第二輪範圍、是否詢問主辦單位、合併方式。
- 階段變動與依據：探索二由執行前進到已有結果。第一輪兩個探索的完成條件都有產出，可返回定義討論第二輪；這不是產品驗收。
- 下一步與需要的資料：使用者看探索二結果與 diff，決定是否 commit，以及第二輪先做什麼。

### 2026-11-16 第六筆（版本：分支 chore/init-and-exploration-1-setup，本筆與第五筆的修改一起 commit）
- 完成事項與證據：使用者同意 commit 探索二的程式、測試與結果文件。使用者對第二輪提出看法：教材沒有的題目大多需要人做情境理解；已記為 brief 的 H-05，連同 AI 不完全相同的粗略分法。
- 未完成、失敗與限制：第二輪範圍尚未定義，沒有開始任何第二輪的工作。H-05 未驗證。未 push、未合併。
- 已確認決策與待確認事項：待確認第二輪要解的問題與做法、是否詢問主辦單位、合併方式。
- 階段變動與依據：第一輪兩個探索結束，回到定義，討論第二輪。
- 下一步與需要的資料：使用者回答第二輪的方向問題。

### 2026-11-16 第七筆（版本：1fcff63 加上未提交的解析、程式、測試與 brief、progress 修改）
- 完成事項與證據：
  - 使用者確認第二輪：每題逐選項解析；不用付費 API；對錯由人做最小但關鍵的介入判定。
  - AI 寫完 50 題的逐選項解析（每題一句重點、四個選項的對錯與理由、教材依據頁碼或教材外標示）。
  - 寫了檢查與產生文件的程式。`uv run python -m ipas_hub.explain` 對真實試題與教材檢查通過：題號齊全、答案與官方答案欄一致、每個選項的對錯與答案一致、引用的頁碼都存在且該頁確實有引用的詞。
  - `uv run pytest`：19 個單元測試通過（合成資料）。
  - 建立人工複核紀錄：必看 9 題（3、4、7、15、19、23、38、47、50），抽查 5 題（18、28、32、40、49）。
- 未完成、失敗與限制：
  - 解析內容的正確性沒有任何人看過。程式檢查只管形式、答案一致與引用存在，不管理由對不對。
  - 24 題標為教材外，說明來自 AI 自己的知識，沒有對照任何外部資料查證；第 7 題的手冊、第 19 題的個資法都沒有讀原文。
  - 必看清單是 AI 自己挑的，挑漏了也不會知道；抽查 5 題就是用來量這件事，但 5 題的樣本很小。
  - 解析會提到各選項的內容大意，沒有引用題目原文；這樣放進版控是否合適，轉 public 前要再看一次。
  - 本次修改尚未 commit。
- 已確認決策與待確認事項：已確認第二輪的三項（做什麼、怎麼產生、誰判定）。待確認：複核範圍與候選 AC、是否詢問主辦單位、合併方式。
- 階段變動與依據：第二輪由定義直接到實作；方法只有一個合理選項（AI 在對話中撰寫），理由是使用者排除付費 API。
- 下一步與需要的資料：使用者複核 14 題並填紀錄；依結果修正解析，或擴大複核。

### 2026-11-16 第八筆（版本：分支 chore/init-and-exploration-1-setup，1fcff63 加上既有未提交修改與本次 progress 紀錄）
- 完成事項與證據：依序讀完 AGENTS、guide、brief、progress，並讀人工複核紀錄與 review 規則；以 git status、git log、git diff 確認分支、HEAD 與 brief／progress 的既有修改。指定的解析 JSON、產生的 Markdown、複核紀錄、explain.py 與 test_explain.py 均存在，尚未追蹤；複核 14 題判定皆空白。git ls-files data 無輸出，git check-ignore 確認複核對照檔被排除。
- 未完成、失敗與限制：本次僅接手盤點，未重新執行測試或解析檢查，19 個測試與 50 題檢查通過沿用第七筆的歷史結果；未審定解析內容、未代填人工判定。git 讀取使用者全域 ignore 檔出現權限警告；repo 的 data/ 排除檢查有結果。未 commit、push、合併、公開或呼叫付費 API。
- 已確認決策與待確認事項：沿用使用者本次交接限制。依序待決定：本批是否 commit（須先展示完整 diff 並取得同意）、複核範圍與 AC-03 至 AC-05、是否詢問授權、分支合併方式；本次未替使用者決定。
- 階段變動與依據：開始與結束皆無階段變動。探索一、二已有結果，限制保留；第二輪留在實作待人工複核；授權確認留在探索。上方表格探索一、二的「未 commit」及探索二「決定第二輪」為過期文字，以 git HEAD、本輪任務表與第六、七筆紀錄為準；不修改歷史探索結果。
- 下一步與需要的資料：先逐項確認待決定事項的第一項。人工複核填寫後才依意見修改 JSON、重新檢查與產生文件、回填結果摘要及更新進度；抽查 5 題任一有錯即提議擴大複核，不推定其餘題目正確。

### 2026-11-16 第九筆（版本：1fcff63 加上既有未提交修改與本次 brief、progress 修改）
- 完成事項與證據：使用者表示已填完必看題；本次讀取 validation/2026-11-16-explanation-review.md，磁碟上 14 題判定與意見仍空白，尚無可據以修改 JSON 的意見。說明抽查與必看採相同判定方式，無把握可填不確定。brief H-03 補記使用者提出的跨科教材假設與「教材外」的單科資料邊界。
- 未完成、失敗與限制：使用者填寫位置或儲存狀態待確認；未代填判定、未修改解析、未重跑程式或測試、未取得或查證科目 2 教材。
- 已確認決策與待確認事項：跨科依據仍為待驗證假設，不擴大本輪範圍；commit、AC 與複核範圍、授權詢問、合併方式仍待決定。
- 階段變動與依據：開始與結束皆維持第二輪實作待人工複核；探索一、二既有結果不變，授權仍在探索。
- 下一步與需要的資料：確認必看意見的實際檔案與儲存狀態；使用者對抽查 18、28、32、40、49 填正確／有錯／不確定及必要意見。取得意見後再依交接規則修正與重驗。

### 2026-11-16 第十筆（版本：1fcff63 加上既有未提交修改與本次 progress 紀錄）
- 完成事項與證據：使用者確認填寫位置為 data/review/115-3-subject1-review.md；本次已讀取該檔，磁碟內容僅見既有題目、解析與列入原因，未找到使用者新增的判定或意見，因此尚未轉錄至正式複核紀錄。
- 未完成、失敗與限制：填寫內容的儲存狀態待確認；未把既有解析中的對錯當作人工判定，未修改 JSON、產生文件或執行測試。重新產生對照檔可能覆寫使用者筆記，取得並保存筆記前先不執行產生指令。
- 已確認決策與待確認事項：已確認使用者填寫的檔案路徑，其餘待決定事項不變。
- 階段變動與依據：開始與結束皆維持第二輪實作待人工複核；其他任務階段不變。
- 下一步與需要的資料：使用者儲存對照檔後再讀取；若已儲存，請提供一筆新增註記的內容供定位。取得明確判定與意見後再轉錄與修正。

### 2026-11-16 第十一筆（版本：1fcff63 加上既有未提交修改與本次複核摘要、progress 修改）
- 完成事項與證據：重新讀取對照檔仍未見筆記，接著讀正式複核紀錄發現使用者判定已儲存在該處：必看正確 7 題、不確定 2 題（23、47），抽查 5 題空白。已同步紀錄開頭與結果摘要，保留使用者逐題判定。以 .venv/Scripts/python.exe -m ipas_hub.explain 重新檢查並產生文件：50 題通過、26 題有教材依據、已做頁面比對；以同一 Python 執行 pytest：19 passed。
- 未完成、失敗與限制：uv 執行遭存取拒絕，改用現有虛擬環境。嘗試精準替換解析時唯一性檢查失敗，寫檔前中止，JSON 未修改，前述檢查針對原解析；未宣稱內容正確。pytest 有快取目錄寫入警告。未 commit、push 或合併。
- 已確認決策與待確認事項：使用者已提供必看判定；23、47 仍不確定，未改成正確。其他待決定事項維持。
- 階段變動與依據：開始與結束皆維持第二輪實作待人工複核；已取得部分人工證據，仍未滿足交付條件，其他任務階段不變。
- 下一步與需要的資料：先在對話說明第 23、47 題供使用者確認理解與後續修訂；抽查可填不確定，不要求使用者猜測。抽查任一有錯則提議擴大複核。

### 2026-11-16 第十二筆（版本：1fcff63 加上既有未提交修改與本輪解析、程式、測試、brief、progress、複核紀錄修改）
- 完成事項與證據：
  - 開始盤點仍是第二輪實作待人工複核；使用者表示抽查已填在 data/review/115-3-subject1-review.md。本輪讀取對照檔並與產生器內容比對，未找到新增判定；正式紀錄仍為必看 7 正確、2 不確定，抽查 5 題空白。未將此差異視為使用者未做，亦未代填結果。
  - 使用者指示從原官方頁下載科目 2 教材，授權限補查現有 50 題跨科依據。來源：https://ipd.nat.gov.tw/ipas/certification/AIAP/learning-resources 的科目 2 連結；實際下載位於 www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/。檔名、版本識別與 SHA-256 登記在解析 JSON additional_guides；存放 data/raw/guide-subject2/，5,041,118 bytes、62 PDF 頁、57 個可辨識頁碼。SHA-256：142d9dadbbfd35020875a640beaa15f6e7ad86b3fe91920048df59123fd7ea5f。
  - 擷取結果只寫入 data/index/subject2-pages.json，讀取相關完整頁面後，18、32、44 題補科目 2 的概念依據；15、19、42、43、50 題補相關頁並註明未支持的部分。跨科後解析 29 題有概念依據、21 題無直接依據，與探索一分類／探索二分母是不同用途，舊數字保留。
  - 第 23 題補充兩張影像比對與序列建模差異；47 題補充共享參數、MoE 不必按語言分工，以及輕量模型與翻譯方案的限制。保留使用者原「不確定」，未當作已接受修正版。
  - 程式引用新增來源識別，避免相同頁碼跨科混用；缺少引用教材或未知來源會報錯，科目 1 PDF 不再依排序任選。對照檔重產時如與既有內容不同，另存 .generated.md，避免覆寫筆記；本輪重產前已備份至 data/review/115-3-subject1-review-before-cross-subject.md。
  - 本輪測法：引用以正確科目的頁碼與詞核對；合成測試覆蓋同頁碼跨科辨識、未知／未載入來源拒絕、對照檔筆記保留。執行 .venv/Scripts/python.exe -m ipas_hub.explain：檢查通過 50 題、有依據 29 題、頁面內容已比對；.venv/Scripts/python.exe -m pytest -p no:cacheprovider：22 passed。git diff --check 無錯誤；git check-ignore 確認新 PDF、擷取檔與備份被排除；git ls-files data 無輸出。
- 未完成、失敗與限制：
  - 一般沙箱無法連線下載，經工具自動審核核准後成功下載；未呼叫付費 API。uv 先前存取遭拒，本輪用現有虛擬環境，未另安裝依賴。
  - 科目 2 本輪只讀取相關文字頁，未逐頁目視；有些標題擷取不完整。勘誤未完整套用至科目 2，本次新增引用不含已知勘誤頁 3-32。沒有重跑探索二，也沒有改探索一依據頁碼或分類。
  - 引用詞存在及測試通過不代表完整理由正確。第 7 題政府手冊與第 19 題臺灣個資法原文仍未查；科目 2 一般授權原則不是臺灣法的法律依據。未完整查證所有未命中概念，不能斷言兩科均無內容。
  - 尚未取得可讀的抽查判定；本次修改內容未經使用者重驗，未判定抽查無錯或其餘 36 題正確。未 commit、push、合併、公開或驗收結案。
- 已確認決策與待確認事項：已確認補下載科目 2 查證；使用者只審核解析，來源查證交由 AI。候選 AC、複核範圍、commit、授權詢問與合併方式仍待逐項決定。變更後版本不繼承原版人工判定為已通過。
- 階段變動與依據：第二輪開始及結束皆在實作待人工複核與修正後重驗；跨科補查為探索已有部分證據，已回用於解析修訂。第一輪結果與授權確認階段不變。
- 下一步與需要的資料：取得抽查 18、28、32、40、49 的實際判定與意見；若仍有儲存差異，可直接在對話回覆五題判定，由 AI 整理。抽查任一有錯就提議擴大範圍，不自行宣告其餘題目正確；重看 23、47 與本輪修改內容後再記人工結論。

### 2026-11-16 第十三筆（版本：1fcff63 加上既有未提交修改與本輪複核紀錄、brief、progress 更新）
- 完成事項與證據：使用者於對話逐列提供抽查 18、28、32、40、49 題皆正確及兩筆意見；讀取正式複核紀錄時五列已存在且與對話一致，未重複新增。更新開頭、結果摘要、來源說明及 brief／progress 的當前狀態：必看 7 正確、0 有錯、2 不確定；抽查 5 正確、0 有錯、0 不確定，合計 12／0／2。
- 未完成、失敗與限制：23、47 題仍為不確定，補充說明未取得新的人工判定；不推定其餘 36 題正確。此輪無解析修正需求，未修改 JSON 或產生文件，未重跑程式與測試；22 passed 是第十二筆的歷史結果。本輪僅做文件一致性與實際 diff 檢查。
- 已確認決策與待確認事項：確認五題抽查判定與原意見，未觸發抽查有錯即提議擴大範圍的條件；未推定跨科引用均經人工驗證。AC 與複核範圍、commit、授權詢問及合併方式仍待逐項決定。未 commit、push、合併或公開。
- 階段變動與依據：開始為實作待人工複核與重驗；結束仍在實作，抽查已取得人工證據，剩餘不確定題與未確認修訂阻止宣稱驗收通過。探索一、二及授權確認階段不變。
- 下一步與需要的資料：使用者確認 23、47 題補充說明是否解答疑問；若仍不確定，指出卡住處，由 AI 再補充並保留原判定。

### 2026-11-16 第十四筆（版本：1fcff63 加上既有未提交修改與本輪雙科參照整理）
- 完成事項與證據：
  - 開始階段為第二輪實作待不確定題確認；使用者要求兩份教材相互參照，幫助理解題目來源。沿用現有 50 題，不新增試題或檢索實驗。
  - 閱讀用解析新增 50 題雙科教材對照索引，逐題分科列出依據與相關頁；所有逐題引用明列科目與頁碼，不再以 subject2 技術識別作閱讀標示。沒有引用顯示「尚未列入」，不把未找到視為沒有內容，也不宣稱確認命題者實際來源。
  - 閱讀科目 2 相關完整頁後，新增 4、7、13、25、26、33、34、35、38、39、45、46、49 題相關頁，保守註明支持範圍。現行 21 題有科目 2 的依據或相關頁；29 題有概念依據的計數未變，相關頁不當成直接依據。
  - 原 outside 欄位保留，閱讀標示改為「依據限制／補充知識」；舊單科查找說法加註科目 1 邊界。未更動選項判定或官方答案，未改使用者的 12 正確、2 不確定紀錄。brief 補記本次方向並更新 H-03 的新證據，歷史探索結果保持不變。
  - 本輪測法：新增合成測試確認雙科同頁碼與依據／相關頁分欄呈現；重跑來源驗證、現有測試與產生器，並人工檢視產生文件開頭的 50 列索引。最初檢查發現 39 題科目 2 引用誤植 3-20，修正為實際有該詞的 3-21 後重驗。
  - 最終執行 .venv/Scripts/python.exe -m ipas_hub.explain：50 題檢查通過、有教材依據 29 題、頁面內容比對已做。執行 .venv/Scripts/python.exe -m pytest -p no:cacheprovider：23 passed。git diff --check 通過；git diff --exit-code HEAD -- 探索一紀錄表與探索二結果無差異。
- 未完成、失敗與限制：新增引用未經使用者人工重驗，程式只檢查來源頁與詞存在，不證明整段理由正確。未做兩科逐頁目視，也未宣稱所有未列入引用的題目均已完整排除兩科內容。科目 2 勘誤未完整套用，本次新增引用不涉及已知 3-32 勘誤。第 7 題政府手冊及第 19 題臺灣法原文仍未查；第 23、47 題仍不確定。未重跑探索二、未 commit、push、合併或公開。
- 已確認決策與待確認事項：確認在現有 50 題中採雙科相互參照的方向，來源與支持範圍由 AI 補查。這不是採用候選 AC 或認定命題來源；AC／複核範圍、commit、授權詢問與合併方式仍待逐項決定。
- 階段變動與依據：結束仍為第二輪實作待審查與不確定題確認；雙科整理已有可閱讀索引與程式證據，可供學習及後續審查，不代表內容驗收。探索一、二與授權確認階段不變。
- 下一步與需要的資料：使用者可從解析開頭的雙科索引對照閱讀；含題目原文的新版對照在 data/review/115-3-subject1-review.generated.md，原檔未覆寫。23、47 補充說明待使用者確認，未列依據或僅有相關頁的部分由 AI 依實際疑問繼續查證。

### 2026-11-16 第十五筆（版本：1fcff63 加上既有未提交修改與本輪人工確認紀錄）
- 完成事項與證據：使用者表示已看目前解析文件與審查紀錄，明確回覆「通過!!!!」。記為接受第十四筆後的雙科參照解析與補充說明；本輪讀取時第 23 題欄位為「確定」、第 47 題仍為「不確定」，依本次整體確認統一為正確，保留原意見與歷史判定。結果摘要為必看 9／0／0、抽查 5／0／0，合計 14／0／0；brief 與當前階段表同步。
- 未完成、失敗與限制：本輪只更新文件，未改解析 JSON 或程式、未重產文件或重跑測試。50 題檢查與 23 passed 沿用第十四筆，不冒充當次重跑；本輪驗證為文件一致性與 diff 檢查。其餘 36 題仍無逐題人工判定，外部原文、授權及科目 2 勘誤限制不因本次通過而視為解決。
- 已確認決策與待確認事項：已確認目前解析及審查紀錄通過，23、47 補充說明已接受。候選 AC 與複核範圍未逐項確認採用，保留定義狀態。commit 須先展示 diff 並另獲使用者同意；未 commit、push、合併或公開，未將內容接受當作專案結案。
- 階段變動與依據：開始為實作待不確定題確認，結束進入審查與交付，人工內容審查通過、尚未提交。跨科整理結果一併接受；探索一、二結果與授權確認階段不變。
- 下一步與需要的資料：準備本批完整 diff 供使用者檢視，再逐項決定 commit、候選 AC 與複核範圍、授權詢問與分支合併方式；本輪不自行執行 git 寫入操作。

### 2026-11-16 第十六筆（版本：1fcff63 加上本次待提交的 8 個檔案）
- 完成事項與證據：使用者提出可以提交並開 PR，並要求說明下一階段。依先前「commit 之前先看 diff，同意才 commit」的明確順序，先完成提交前檢查與完整 diff 預覽，尚未執行 git 寫入或遠端寫入。同步 README 的第二輪狀態與解析入口；準備本次 8 檔相對 HEAD 的 diff、整個分支相對 main 的 PR diff，以及 PR 說明草稿，存放在已排除的 data/review/ 下。
- 驗證與證據：本輪執行 .venv/Scripts/python.exe -m ipas_hub.explain：50 題檢查通過、有教材依據 29 題；.venv/Scripts/python.exe -m pytest -p no:cacheprovider：23 passed；git diff --check 通過。原始 data/ 不列入提交。GitHub connector 確認 Cheryl33990/ipas-learning-hub 為 private、預設分支 main，沒有本分支的既有 open PR。PR 會包含先前初始化與探索 commit，不能描述成只有第二輪變更。
- 未完成、失敗與限制：本輪未 commit、推送或建立 PR，原因是尚未展示本次完整 diff 後取得最後確認；不是程式檢查失敗。gh auth status 回報本機 CLI token 無效，GitHub connector 的讀取則成功，後續優先採可用 connector，必要時再驗證 git 推送管道；未要求使用者重登入。人工審查通過的範圍與未查證限制維持第十五筆。
- 已確認決策與待確認事項：使用者已提出提交與開 PR 的方向；開 PR 所需的工作分支發布屬本次請求範圍，正式執行仍以本次 diff 確認為前提。採專案 review 規則先建 Draft PR，base main、head chore/init-and-exploration-1-setup；不合併、不公開、不呼叫付費 API。候選 AC 與複核範圍、授權詢問、合併方式仍待逐項決定。
- 階段變動與依據：開始與結束皆為審查與交付，內容已接受，提交與 PR 的具體預覽已準備，發布步驟待使用者看過 diff 確認；合併、公開、驗收定義與結案分開。
- 下一步與需要的資料：使用者確認 data/review/ 下兩份 diff 後，提交本次 8 檔、發布工作分支並建立 Draft PR。其後先做 PR diff／證據審查與合併決定；下一輪建議再定義最小自用查題閱讀流程，未獲確認前不新增介面或其他科目試題。對外分享仍需另外處理教材與試題授權。

### 2026-11-16 第十七筆（版本：已推送 commit 4d52df6496ee29e5067b5571ad6e6b214b44245e，本筆 progress 更新尚未提交）
- 完成事項與證據：使用者對兩份完整 diff 與 commit／推送／Draft PR 的確認問題回覆「同意」。先以預覽 manifest 核對 HEAD 與 8 個檔案 SHA-256 全部一致，暫存後核對 staged 檔案清單、git diff --cached --check 與 data/ 無已追蹤檔案；建立 commit 4d52df6（feat: add reviewed explanations with cross-subject references），8 檔、2283 行新增、6 行刪除。已推送 origin/chore/init-and-exploration-1-setup 並設定 upstream。
- PR 與遠端確認：透過 GitHub connector 建立 https://github.com/Cheryl33990/ipas-learning-hub/pull/1，標題「建立 iPAS 備考探索與雙科參照逐選項解析」，Draft、open、base main、head chore/init-and-exploration-1-setup。重新讀取 PR 確認遠端 head SHA 為 4d52df6，4 個 commit、29 個變更檔案、尚未合併；repo 仍 private。GitHub 回報 mergeable=true 只表示目前沒有文字衝突，不代表審查或驗收通過。PR 觸發的 workflow_runs 查詢為空，未宣稱 CI 通過。
- 未完成、失敗與限制：沙箱預設 git add 因 .git/index.lock 權限被拒，經工具自動審核核准後成功 add、commit 與 push；未出現自動審核拒絕。一般沙箱 git ls-remote 因網路限制失敗，改以 connector 的 PR head SHA 驗證遠端。23 個測試與 50 題檢查證據沿用第十六筆，本輪未重跑，批准後程式與解析無變動。本筆 progress 是例行結果紀錄，留在本機，不在已批准的 8 檔 diff 之外另行 commit。其餘 36 題人工判定、外部原文、授權與勘誤限制維持原紀錄。
- 已確認決策與待確認事項：提交、推送與開 Draft PR 已取得授權並完成；未合併、部署或公開。候選 AC／複核範圍採用、是否詢問授權與合併方式仍待逐項決定；不因 PR 已建立而自動接受這些定義或宣稱專案結案。
- 階段變動與依據：開始為審查與交付、待發布；結束為審查與交付、分支與 Draft PR 已發布。人工內容接受、Git 提交、PR 建立、合併與對外公開分開記錄，探索一、二結果不變。
- 下一步與需要的資料：先依 review 規則檢查 PR 實際 diff 與證據、處理發現，再由使用者決定合併方式。之後建議另開一輪定義最小自用查題閱讀流程（按題號看解析與雙科依據），確認範圍與成功條件後才實作。未自行擴充介面或其他試題。這筆本機進度紀錄於下一次經確認的文件提交納入。

### 2026-11-16 第十八筆（版本：main 合併 commit af2a9ceae12d8dcb172a0cffe68a0b1876961186 加上本機 progress 補記）
- 完成事項與證據：使用者表示已先合併 PR #1，並發現 progress 尚未提交。GitHub connector 確認 PR #1 為 closed、merged=true，合併 commit af2a9ce，合併時間 2026-11-16 16:05:30（Asia/Taipei）。本機 origin/main 同為 af2a9ce，父 commit 是原 main c6f651c 與工作成果 4d52df6，為 merge commit。git diff --exit-code origin/main HEAD 在切分支前通過，證明合併結果與已發布成果的檔案內容完全一致，缺漏僅為本機提交後新增的 progress 紀錄。
- 保全與處理：先將原未提交 progress 備份在已排除的 data/review/progress-before-pr1-merge-record.md；從 origin/main 建立 docs/record-pr-1-merge，工作目錄修改保留。同步進度開頭、階段與任務表，保留第十七筆當時事實，再追加本筆合併狀態。不回滾合併、不改寫 commit、不刪除原分支，也不直接提交至 main。
- 驗證與限制：本輪僅文件補記，檢查實際 diff、合併 commit／父 commit、內容一致與 git diff --check；沒有程式變更，未重跑測試。23 passed 與 50 題檢查仍是第十六筆的歷史證據，不將合併視為補做獨立程式 review、逐題人工驗證、授權確認或專案結案。
- 已確認決策與待確認事項：合併是使用者已執行的操作，依遠端事實記錄，不再要求重新批准該次合併。本分支僅更新 progress，仍遵守新 commit 前先展示 diff 並取得同意；本輪未 commit、推送或建立新的 PR。未變更候選 AC、既有探索結果或公開設定。
- 階段變動與依據：開始為審查與交付、發現遠端已合併；結束為審查與交付、已合併且文件補記備妥。原始成果沒有遺失，不需要撤銷 PR #1。下一輪功能尚未開始。
- 下一步與需要的資料：使用者檢視 data/review/2026-11-16-progress-merge-followup.patch；確認後只提交 progress、推送 docs/record-pr-1-merge 並開文件 PR，補齊提交與合併紀錄。之後再討論下一輪最小自用查題閱讀流程，不自行開始實作。

### 2026-11-16 第十九筆（版本：af2a9ce 加上 docs/record-pr-1-merge 的 progress 補記）
- 完成事項與證據：使用者對已展示的單檔補記 diff 回覆「OK」，同意提交、推送與另開文件 PR。核對本分支基於 af2a9ce，工作目錄僅 progress 修改；保留第十七、十八筆提交與合併事實，更新當前摘要的授權狀態。本輪紀錄與補記一併納入提交，不在完成後另產生未提交紀錄。
- 驗證與限制：本輪只檢查文件 diff、一致性與 git diff --check，沒有程式或解析變更，不重跑應用測試。原 23 個測試及 50 題檢查的版本與限制沿用第十六筆；沒有把文件提交當作新的內容驗證。
- 已確認決策與待確認事項：本文件分支的 commit、推送與建立 Draft PR 已授權；不自動合併文件 PR，不改寫 PR #1 的歷史或公開設定。接續發布的 commit SHA、PR 編號與最終狀態以 Git／GitHub 的實際結果為準，不在本筆預填成功結果。
- 階段變動與依據：開始與結束皆為審查與交付的合併後文件收尾；本次補記已具備明確 diff 與使用者同意，可發布供審查。整個專案未結案，下一輪功能尚未開始。
- 下一步與需要的資料：完成本分支 commit、推送與文件 PR，於 PR 說明及對話回報實際結果；文件 PR 由使用者決定是否合併。之後再確認最小自用查題閱讀流程的範圍與成功條件。

### 2026-11-16 第二十筆（版本：main 5cf7d964f656ea34bbb5658b4df49c99ac4f1d0b 加上本輪 brief、progress 規劃）
- 完成事項與證據：使用者表示已合併 PR #2，並確認長期目標是「RAG 系統，結合知識庫跟 LLM，讓解題跟搜尋更容易」。GitHub connector 確認 PR #2 merged=true，merge commit 5cf7d96，本機 main 起始亦為同一版本且乾淨。已建立 docs/rag-next-iteration-plan，只更新 brief 與 progress，區分已確認目標及待確認的下一輪範圍。
- 現有能力與缺口：既有程式可擷取、套用勘誤、切塊與比較 BM25／BAAI/bge-m3，但探索程式只讀科目 1、每次執行重新編碼，沒有一般查詢或生成回答流程。雙科引用目前主要是解析的人工整理，尚未形成雙科自動檢索與 LLM 回答。PATH 未找到 ollama、lmstudio、lms 指令，僅代表指令查找未命中，不推定其他模型服務不存在。
- 候選方向與測法：建議先完成雙科可追溯檢索，接著以少量案例接本機 LLM 產生帶引用回答，再加簡單自用介面。測試分開看找回依據、回答是否被依據支持、證據不足是否明說與本機延遲；先量基準，不設定虛構百分比。測試時不把完整解析或官方答案混入教材索引，避免答案洩漏；舊解析只作具限制的參考。原探索一、二結果不變。
- 來源與驗證限制：參閱 RAG 原始論文摘要 https://arxiv.org/abs/2005.11401 確認檢索片段結合生成的流程；本輪為專案規劃，不選定框架或模型、不安裝相依、不下載模型、不呼叫付費 API、不重跑測試或探索二。只做文件一致性與 diff 檢查。未將建議方案或候選測法寫成已採用 AC。
- 已確認決策與待確認事項：已確認長期 RAG 方向；既有費用、資料與公開限制沿用。首要使用流程待使用者選擇貼題解題或自由概念查詢；LLM 環境、資源邊界、下一輪正式範圍與成功條件未定。未 commit、推送或開新 PR。
- 階段變動與依據：開始為前輪合併後待定下一輪；結束為下一輪定義，已有現況、候選方案與測法，等待最小流程確認。第二輪內容與補記均已合併，不推定整個專案結案。
- 下一步與需要的資料：建議優先貼題解題，沿用現有題目與教材依據，讓少量案例跑完整的查找—生成—引用流程。由使用者確認第一個流程後，再制定可執行的本輪範圍、探索邊界與測法；尚未開始實作。

### 2026-11-16 第二十一筆（版本：5cf7d96 加上 docs/rag-next-iteration-plan 的未提交原型）
- 完成事項與證據：
  - 使用者接受上一輪規劃，新增整體 Docker 控管、CI/CD 與 MLOps 概念；本輪中再明確選「先完成檢索，下一步再選 LLM」。開始先在 brief 記操作邊界與測法，依此完成雙科索引／查詢／評估 CLI，不交付網頁介面或真實生成回答。
  - 新索引只讀來源清單的兩份教材；PDF 雜湊與所有勘誤都需核對，科目 1 六筆、科目 2 一筆套用成功，合計 123 個有頁碼頁面、266 塊。來源、勘誤、切塊、程式檔案／commit、uv.lock、embedding revision／向量雜湊寫入版本化 manifest；查詢及評估寫 data/runs/，原文不進版控。大型 sentence-transformers 相依改成 embeddings extra，uv lock --offline 成功，既有探索二使用方式在 README 同步。
  - 新增 Dockerfile（Python、uv digest 固定）、allowlist .dockerignore、Compose 應用與可選 llm profile；原始 PDF 掛唯讀、不包入映像。CI 跑合成測試、Compose config、容器測試與斷網啟動；delivery 是手動交付檢查，不推 Registry 或部署，不冒充完整生產 CD。
  - 依使用者提供 Docker Desktop 捷徑，發現在一般沙箱與正常使用者環境顯示的路徑不同；改用經工具審核的使用者環境成功找到並使用 Docker Desktop 4.83.0／Engine 29.6.2／Compose 5.3.1。未更動既有其他專案容器或服務。
  - 本機 Python 3.14.7 執行 pytest：37 passed。首次 Docker 測試為 36 passed、1 failed（容器無 git 指令）；修正版本回報的 fallback 後重跑 Docker test stage，Linux Python 3.12.16：37 passed。Compose config、runtime build、斷網 --help、容器雙科建索引／搜尋／八題評估均實測成功。runtime 約 98.4 MB，ID 與逐項證據見 validation/2026-11-16-docker-retrieval.md；檢查映像無 PDF、Git 或 tests，prompt 有包入。
  - 新基準由既有解析 basis 選 8 題（3、4、18、23、28、32、40、49），題目原文只存 data/evaluation/；索引不含答案或解析。以同一主機向量索引比較前 5 筆，BM25 5／8、向量 5／8、混合 5／8，各方法未命中題目不同。向量僅使用本機快取 BAAI/bge-m3 snapshot 5617a9f61b028005a4858fdac845db406aefb181，未重新下載。原探索一、二結果不變。
- 未完成、失敗與限制：
  - 37 個合成測試包含假生成器，不代表實際 LLM 已執行；生成 adapter 與 prompt 僅草案，本輪未啟動 llm profile、未下載生成模型。Docker embeddings 大型映像未建置或實測；主機向量通過不替代此項。
  - Hosted GitHub CI 與 delivery workflow 尚未觸發；本機對應步驟成功不等於遠端 CI 綠燈。未推送映像、部署、呼叫付費 API、commit、push 或新建 PR。
  - 8 題的預期頁來自既有參考，並非新做逐頁獨立複核，頁集合可能不完整；第 4 題有相關頁但未符合原預期集合，仍照規則記未命中，不補到通過。尚無語意支持判定或向量拒答閾值，不能把 5／8 當產品驗收。既有外部原文與授權限制保留；本輪未更動已接受解析。
  - 最初硬體與 Docker 路徑查詢在沙箱失敗，已用不同使用者環境補查 Docker；未把找不到 PATH 視為未安裝。舊資料索引可能出現在 data/index/kb/，各版本保留，不自動覆寫或刪除。
- 已確認決策與待確認事項：已確認 Docker 控管及先檢索後選 LLM；CI／交付不使用真實原文、不對外發布。生成模型／平台、品質門檻與後續介面範圍仍待決定。既有其他專案已有 vLLM 等映像，只讀清單，未擅自沿用或重啟。本輪工作維持未提交，commit 仍須先展示 diff 並獲使用者同意。
- 階段變動與依據：開始由定義進設計與測法規劃；結束為檢索／Docker 原型實作可送審，有真實雙科與容器證據、亦保留失敗與未跑項。生成與介面仍在後續規劃，不宣稱 RAG 系統或 CI/CD／MLOps 全部完成。
- 下一步與需要的資料：先審查未命中題目的檢索片段與預期頁完整性、固定本輪基準；再決定檢索改善或 LLM 選型。使用者若要提交，先看本輪完整 diff，再 commit／PR；推送後才能驗證 hosted CI。所有新執行紀錄與原始案例只在 data/。

### 2026-11-16 第二十二筆（版本：5cf7d96 加上既有未提交原型與本輪確認紀錄）
- 完成事項與證據：使用者回覆「當前的內容 OK」，記為接受目前雙科檢索、Docker 與 CI／交付設定原型；更新 progress 開頭及驗證文件的確認來源。
- 未完成、失敗與限制：本輪只有確認紀錄變更，未改程式或資料、未重跑測試；37 passed 與三種檢索各 5／8 沿用第二十一筆的實測，沒有當作本輪重跑或正式品質驗收。hosted CI、Docker embeddings 與真實 LLM 未跑項保留。
- 已確認決策與待確認事項：目前原型內容已接受；未收到另行 commit／推送／PR 指示，故維持未提交，不自行部署或公開。LLM 選型仍留下一步，檢索品質門檻未定。
- 階段變動與依據：開始為原型實作可送審；結束為審查與交付、使用者已接受目前原型，提交與後續品質工作分開記錄。
- 下一步與需要的資料：若使用者要保存這批成果，沿用已展示的完整 diff，確認提交與開 PR 後才發布；功能方面接續判讀未命中與預期頁完整性，再決定檢索改善及 LLM 選型。

### 2026-11-16 第二十三筆（版本：5cf7d96 加上既有未提交原型與本輪交接紀錄）
- 完成事項與證據：使用者要求另開對話分析檢索未命中；重新核對 git status、HEAD 與本輪驗證文件，整理可直接貼入新對話的交接 prompt，包含來源檔案、索引版本、8 題基準與 5 題未命中聯集。
- 未完成、失敗與限制：本輪只整理交接，未分析未命中原因、改程式、重建索引、改案例或重跑測試。37 passed 與三方法各 5／8 是第二十一筆的歷史實測；不能宣稱目前重跑。未 commit、推送或開 PR。
- 已確認決策與待確認事項：接續任務為未命中診斷，先保留原基準，區分檢索排序、切塊／擷取與預期頁集合問題；不得事後補預期頁或改 k 將原結果改成通過。若需修訂評估集或檢索方案，先提出理由、影響與新版本比較方式，再確認採用；LLM 仍延後選型。
- 階段變動與依據：開始與結束皆為第三輪原型已接受、未提交；接續工作進入探索／診斷，不因交接而視為品質驗收或新增發布授權。
- 下一步與需要的資料：新對話依序讀 AGENTS、guide、brief、progress（本筆最新）、設計與驗證，盤點未提交修改後分析 4、18、32、40、49 題。原文及片段證據只留 data/，進版控文件只放題號、頁碼、方法、排名與自寫判讀。最終給逐題原因、證據限制與下一個最小改善提案。

### 2026-11-16 第二十四筆（版本：5cf7d96 加上既有未提交原型與本輪診斷文件）
- 開始階段與最小動作：依指定順序讀取規則、brief、progress 第二十三筆、設計與前輪驗證；以 git status、diff、未追蹤檔清單核對分支與 HEAD，既有 5 個修改檔、13 個未追蹤檔均在。先更新階段表為探索／診斷，再固定來源與原案例，未重新釐清大目標。
- 完成事項與證據：
  - [未命中診斷](validation/2026-11-16-retrieval-miss-analysis.md) 保存 5 題、9 個題號×方法的預期頁支持範圍、前五逐片段判讀、預期片段實際排名與融合算式。原文、腳本、完整排名及來源雜湊只在 data/diagnostics/2026-11-16-misses/；review.md 已整理原題、現行解析、完整預期頁及檢索片段，供最小人工介入。
  - 依 config 的來源雜湊重讀 PDF，套用科目 1 六筆、科目 2 一筆勘誤；123 頁切出的 266 塊與主機索引逐字及順序一致。8 題 query 與題幹＋選項、expected 與 basis 逐筆一致。索引 payload、vectors、uv.lock 核對成功。
  - 主機索引固定 19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108；依 index_id／method／k 明確選三份歷史 run，未混用 Docker 或舊索引。離線 BAAI/bge-m3 原 revision、CPU 重現，24 組前五來源頁序列與命中值全部相同，三方法仍各 5／8；用正式 search 核對前 20 片段順序，額外完整排名只定位預期片段，原 k=5 不變。
  - 第 4 題三方法皆找回未列 expected 的跨科公平性片段；第 18 題 BM25 概念塊在第 7，有重複情境詞加分證據；第 32 題向量第 6，前兩名同頁重疊；第 40 題為 16／6／7，原預期頁僅列術語、模型上下文在前頁；第 49 題融合將兩路各自命中片段降為第 7／12，且前五仍有概念支持。內容支持與因果解釋皆標 AI 判讀，不冒充人工確認。
- 限制與修正：
  - 主機索引記錄的 knowledge.py 雜湊與現檔不同，現檔與 Docker 索引記錄相同；其餘 11 個 Python 檔相符。歷史 fallback 修正是可能背景，沒有舊程式全文可證明只改那段。歷史 evaluate 未存 query 雜湊或片段 ID，本輪只能證明目前重現的前五頁序列相同，不能反推歷史每個位元相同。
  - 索引未另載入公告試題／答案或本專案解析，但教材自帶的練習題與解答確實被切入，且有進前五。補充此邊界，不把「只索引教材」說成完全沒有題目或解答；本輪未移除頁面。
  - 本輪讀完整相關文字頁，未找到 pdftoppm、未做影像目視，不能排除圖像／特殊字型遺漏；沒有為此安裝工具。未重跑 pytest、Docker、CI 或 LLM，37 passed 仍是歷史。未做查詢消融、去重或融合調整實驗。
  - 初次診斷腳本因缺一個括號而語法失敗，修正後完成上述核對與重現；後續只增 --output 防覆寫介面並做語法檢查，沒有宣稱重新跑完整檢索。首次本機對照的 PowerShell 管線使自寫中文標頭損失，改由 UTF-8 檔案腳本重產並讀回確認；原資料不受影響。
- 自查與保全：依 review 規則檢查新增文件、progress 差異、連結與數值，git diff --check 通過；git check-ignore 確認診斷原文與腳本被排除，git ls-files data 無輸出。診斷執行結束時輸入雜湊全未變；後續只更新本輪 progress 與新增文件／data 診斷產物。原程式、解析、案例、索引、run 與探索一／二結果保留。這是 AI 作者自查，不是獨立真人批准。
- 已確認決策與待確認事項：沿用本輪只診斷、先完成檢索後選 LLM 的授權。提出一個最小改善：另建支持範圍標註版評估 v2，先分清核心概念／背景／不足支持，原 v1 5／8 及所有原結果保留；方案與預期頁修訂均未採用。待使用者確認第 4、40、49 題的關鍵判讀與 v2 方案，不要求自行找資料或重寫解析。
- 結束階段與前進判斷：探索已有可審查診斷，證據足以提出評估改善選擇；未達條件為關鍵人工判讀及新方案接受。原型內容接受、診斷交付、品質驗收、提交與發布分開記錄。未 commit、push、開 PR、合併、公開或改動其他服務。
- 下一步：若採用 v2，AI 先按固定標註規則補齊全 8 題（含其餘 3 題，避免只修未命中），新檔記 parent 雜湊與理由，再獨立呈現支持範圍；不覆寫原案例或把分數提升當檢索進步。排序改善另開單因素比較，仍不開始 LLM 選型。

### 2026-11-16 第二十五筆（版本：5cf7d96 加上既有未提交成果與獨立 v2）
- 開始階段與授權：使用者同意建立獨立支持範圍評估 v2；核對原分支、HEAD、既有檔案後，階段表先記設計與標註執行中。先寫[分類與驗證契約](design/retrieval-support-v2.md)，沒有把同意方法當作全部 AI 判讀已通過。
- 實際工作與產出：補讀原命中的 3、23、28 題完整預期頁、三方法前五及其他題尚未判讀的命中片段。沿用前輪凍結結果，對全 8 題三方法前五聯集、原預期頁全部塊及前輪補查候選，建立 90 筆題號×片段標註；三方法共 24 組／120 個前五位置均覆蓋。每筆記分類、理由、支持／未支持範圍、正文或教材練習題／解答性質、原文雜湊及 pending 人工狀態。原 query 與 expected 只作 parent 對照，不改寫。
- 檔案與來源版本：data/evaluation/rag-retrieval-support-v2.json 為新主來源；同前綴 results.json、review.md、receipt.json 保存計數、全八題原文對照及輸出雜湊。build_support_v2.py 建立，verify_support_v2.py 獨立讀回；均只存 data/。parent SHA-256 為 197e8aa3e7e5725ba720ea1a3b34b790e5034cb92e26ef85ffb5b9b3572eca86，主機 index_id 仍為 19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108。完整版本、數值與限制見[v2 結果](validation/2026-11-16-retrieval-support-v2.md)。
- 實際結果：原 v1 三方法各 5／8 不變。依本批 AI 核心判準，前五含核心片段的題數為 BM25 5、向量 4、混合 6；這是不同評估視角，不是排序提升。第 3 題概述頁與方法依據的差別也納入，沒有只替未命中題放寬標準。24 組集合均另記尚不足直接完整支持現行解析及具體缺口，不把核心片段當完整解題驗收。
- 驗證與限制：執行兩支腳本成功；讀回驗證題號、池覆蓋、無重複、片段雜湊、前五序列、同片段跨方法分類、每組合計五筆、原 v1 命中及舊輸入雜湊保全。未知片段維持 unjudged。依 review 規則檢查文件與差異，git diff --check、相對連結及 data 排除檢查通過，git ls-files data 無輸出。沒有重跑檢索模型、pytest、Docker、CI 或 LLM；37 passed 仍是歷史。有限標註池、非盲審、AI 自查、文字擷取與舊索引程式雜湊差異限制維持。
- 結束階段與前進判斷：審查與交付，v2 資料及結果已可審查；未達條件為關鍵內容人工確認，不能宣稱正式品質驗收。原案例、原結果、索引、程式、解析、探索一／二及前輪診斷未改；只有 brief／progress 同步與新增 v2 文件、data 產物。未 commit、push、PR、合併、公開或操作其他服務。
- 下一步：使用者只需確認第 4 題部分支持、第 40 題未有完整現象定義、第 49 題未中原頁仍有核心支持，並留意新增第 3 題判準的區分。AI 已備妥原文與理由；如有不同意見，另版記修訂與理由，保留 v1／v2.0。內容確認後再另提單因素排序比較，不自行啟動 LLM 選型。


### 2026-11-16 第二十六筆（版本：5cf7d96 加既有未提交成果與同頁上限實驗）
- 開始階段與授權：使用者同意接續建議；先記探索執行中，固定 v2 與各方法原前 20 候選，只在 data/ 做離線同來源同頁保留第一塊的比較。沒有把概括同意視為逐筆標註批准或正式排序採用。
- 實際產出：[實驗報告](validation/2026-11-16-page-dedup.md)；data/evaluation/experiment_page_dedup.py、page-dedup-experiment.json、verify_page_dedup.py。輸出記原案例、v2、診斷排名 SHA-256，來源索引為 19a8fa4bc06d4f90c6fa53b77dac71a063afcae279ed91522f291e1d603d3108。新增十筆 AI 標註只隨實驗保存，未改原九十筆。
- 結果：八題三方法共 24 組中 12 組輸出改變；核心題數 BM25 5→5、向量 4→5、混合 6→6。向量唯一新增為第 32 題原第六名進入第五位；第 28 題向量及混合各損失一個核心片段，其他組亦有背景支持減少。不能宣稱整體品質提升，不採用同頁上限為預設。原 v1 與 v2、索引及生產程式均保留。
- 實際驗證：建立腳本完成；獨立重播 24 組順序、標註套用、計數與摘要，原輸入雜湊未變；再次執行 verify_support_v2.py 通過。後處理微量測中位數取五塊約 0.068 微秒、同頁上限約 0.586 微秒，非端到端延遲。未重跑模型、pytest、Docker、CI 或 LLM，歷史 37 passed 不冒充本輪通過。
- 結束階段與限制：探索已完成可供審查；AI 自查不等於人工驗收。新舊標註待關鍵確認，有限八題、非盲審、教材練習題被索引及未逐頁影像複核限制保留。未 commit、push、開 PR、合併、公開或操作其他服務。
- 下一步：先確認第 28 題獨立支持被移除及第 32 題新增核心支持的判讀，原文對照已在 data/。下一最小候選是依實際內容重疊排除冗餘，而非同頁一律刪除；先量測再固定單一規則比較，尚未選門檻或執行。不改預期頁來追求通過，不開始 LLM 選型。


### 2026-11-16 第二十七筆（版本：5cf7d96 加既有未提交成果；關鍵判讀審查準備）
- 授權與開始階段：使用者要求整理第 28、32 題精簡對照；先記審查準備執行中，僅整理既有證據。
- 產出：data/evaluation/review-28-32.md，含兩題完整查詢、三方法實驗前後片段 ID、六個關鍵完整片段、AI 判讀與三個確認項；原文只放 data/。六塊文字 SHA-256 與原 v2 標註一致。
- 重要補充：重新並讀第 28 題保留與移除的核心片段，發現核心概念高度重疊；現有證據僅確認核心標註數下降，尚未證明必要的獨立資訊流失。第 28 題被移除片段開頭截斷，其 core 分類亦列入待審。不覆寫原實驗或原標註。第 32 題新片段明列核心關係，仍待人工確認。
- 結束階段：審查材料完成，內容判讀仍 pending；AI 意見不是使用者批准。未改排序、評估集或執行新實驗，未跑應用測試；本輪驗證為片段雜湊、對照位置與文件檢查。
- 下一步：使用者可直接回覆 28-A、28-B、32-A；修訂時另存版本，之後才固定實際內容去重規則做單因素比較。未 commit、push 或開 PR。


### 2026-11-16 第二十八筆（版本：5cf7d96 加既有未提交成果；兩題人工確認）
- 開始與實際步驟：收到使用者針對第 28、32 題的審查回覆，進入審查紀錄同步；核對目前進度及工作樹，另存原話與受審資料雜湊，不修改原標註。
- 結果：[人工確認](validation/2026-11-16-support-review-28-32.md)；data/evaluation/review-28-32-human.json 保存使用者原話及三份輸入 SHA-256。使用者認為兩題找到部分的判定皆正確，並確認第 28 題 MAE 未提及、需外部支持。相對超綱為使用者意見，未冒充官方考綱查證。
- 結束與限制：兩題所審支持判讀已獲人工確認；不擴張為全批 v2 通過或同頁上限採用。第 28 題必要獨立資訊流失仍未證明，MAE 外部依據尚未取得。未改排序、模型、案例或歷史結果；未執行新檢索實驗或應用測試。
- 下一步：量測實際內容重疊後固定單一去重規則，沿用全八題做離線比較；完整解析支持仍須另外補足 MAE 等缺口。未 commit、push、開 PR 或公開。


### 2026-11-16 第二十九筆（版本：5cf7d96 加既有未提交成果；實際內容重疊）
- 開始階段：使用者授權實際內容重疊分析；延續已讀規則與第 28、32 題人工確認，先記探索執行中。固定八題三方法前 20 候選，未調排序。
- 實際產出：[重疊分析](validation/2026-11-16-content-overlap.md)；data/evaluation/analyze_content_overlap.py、content-overlap-analysis.json、content-overlap-verification.json。來源診斷 SHA-256 f6cca96f29d53d61fa9e1d9f96c898b073432268a2458b4003f0df3d2d07aa04，主機索引與前輪一致。
- 結果：150 塊、4,560 次成對比較、2,727 個不同片段對；47 對同來源同頁，完全相同及完整包含均為零。第 28 題兩個概念接近核心塊最長共同文字僅 18 字；第 32 題同頁兩塊重疊 99 字，仍各有其餘內容。原前五最高短塊覆蓋率約 42.2%。人工查看最高五對的未重疊尾端由 AI 執行，並非使用者新審查。
- 驗證：獨立以子字串集合核對 2,727 對最大長度、24 組各 190 對及來源雜湊；未改原輸入、未重跑模型或應用測試。原始文字與輸出只在 data/。
- 結束與前進判斷：分析完成；只刪同來源同頁被高排名片段全文包含的低排名塊，是可測的保守單一規則，但本批零觸發，不預期提高命中。未套用正式流程，不為分數降低門檻。字面不同不等於語意不同，必要資訊流失不能由未重疊字數推定。
- 下一步：結束整塊文字去重作為主要改善方向；若繼續改善檢索排名，另選單一查詢因素驗證。上下文拼接與 MAE 外部證據另議，不同時改多項。未 commit、push、開 PR、公開或選 LLM。


### 2026-11-16 第三十筆（版本：5cf7d96 加既有未提交成果；題幹查詢實驗）
- 開始與授權：使用者同意單一查詢因素實驗；先記探索執行中，唯一變因是截去第一個選項標記及其後文字。固定八題、主機索引、三方法、k=5 與 v2 判準。
- 執行：本機快取 BAAI/bge-m3 固定 revision、CPU 離線；先重現原查詢全部 24 組前20，再測題幹。data/evaluation/experiment_stem_query.py 及 stem-query/ 下 queries.json、results.json 保存原文、48組結果與輸入雜湊；evaluation-annotated.json 為補標後結果，annotate.py 保存43筆 AI 新標註分類，人工狀態 pending。evaluation.json／review.md 為補標前待判階段，保留不覆寫。
- 結果：[報告](validation/2026-11-16-stem-query.md)。頁碼命中 BM25 5→3、向量5→4、混合5→4；核心題數5→3、4→2、6→4，皆以八題為分母。第18題混合核心塊降至6；第28題向量兩核心塊降至18、13；第32題 BM25 降至7；第49題三方法失去前五核心支持。未有新增核心命中。
- 驗證：另行讀回核對八組查詢截取、48組排名唯一連續、片段原文與索引一致、頁碼命中、核心存在計數及43筆文字雜湊；來源雜湊未變。收據 verification.json。未跑 pytest、Docker、CI、LLM，未宣稱端到端延遲改善。
- 結束：探索完成，不採用一律去除選項；新增標註尚未人工確認，原28／32的人工批准未擴張。保留原正式查詢與全部歷史結果。下一步建議整理教材可支持範圍與排序／內容缺口，避免持續在同八題選規則；獨立案例與外部依據另議。未 commit、push、開 PR 或公開。


### 2026-11-16 第三十一筆（版本：5cf7d96 加既有成果；缺口清單）
- 開始階段：使用者要求整理教材依據存在但排名不足與教材內容不足；先記整理中，以原完整查詢及原 v2 為基準，未混用題幹實驗排名。
- 完成：[八題缺口清單](validation/2026-11-16-retrieval-gap-register.md)。直接核對資料中的核心塊與三方法排名：第3題向量16、第18題 BM25 7、第32題向量6；另分第4／40題已查核心內容不足、第49題混合原頁集合落差。全八題完整解析限制逐項記錄，情境推論不一概當成教材遺漏。
- 證據與限制：來源為既有 diagnostic.json、v2 標註及28／32人工審查；未新增片段分類或宣稱其他題人工通過。沒有全書不存在性查證，MAE 相對超綱仍為使用者意見，非官方考綱結論。未搜尋外部來源、重跑模型、pytest或Docker。
- 結束與下一步：清單完成可審查，優先建議小範圍 MAE 外部補證，再處理第4／40題核心缺口；排序改善與獨立案例另議。原查詢、索引、v1／v2、探索結果與解析保留，未 commit、push、PR 或發布。


### 2026-11-16 第三十二筆（版本：5cf7d96 加既有成果；MAE 外部補證）
- 開始階段：使用者同意接續 MAE 小範圍外部補證；先記探索執行中，依官方框架技術文件查定義與適用邊界。
- 產出：[獨立補證筆記](validation/2026-11-16-mae-external-evidence.md)；data/evaluation/mae-external-sources.json 保存五份來源網址、查閱日期、顯示版本與短摘記，未保存整頁快照。來源為 scikit-learn 的 MAE、Accuracy、Confusion matrix、LinearRegression 及 Keras 迴歸損失文件。
- 結果：外部證據支持 MAE 定義、連續預測用途及分類指標的差異；綜合推論可說明平方誤差訓練的線性迴歸可用 MAE 評估。沒有推論 MAE 唯一最佳，也未將本題全部選項排除理由標為查證完成。
- 驗證：實際開啟五份官方頁面核對；自造數值的 MAE 以標準 Python 計算為2。未安裝相依、重跑檢索、模型、pytest或Docker；未查官方考綱。外部補證由 AI 判讀待審，不冒充使用者批准。
- 結束與下一步：MAE 缺口更新為外部來源已備妥、待審與整合；原教材索引仍不含此證據，原 v1／v2 成績不變。下一步可審查來源筆記，再議外部知識的獨立索引版本或第4／40題補證。未改原解析、標準答案、語料或排序，未 commit、push、PR 或發布。


### 2026-11-16 第三十三筆（版本：5cf7d96 加既有成果；第4／40題外部補證）
- 開始：使用者同意延續補證；先記探索執行中，核對兩題原查詢與解析，再查第一手技術文件。
- 產出：[外部證據筆記](validation/2026-11-16-fairness-mode-collapse-evidence.md)；data/evaluation/fairness-mode-collapse-sources.json 保存六份來源網址、版本／更新資訊、短摘記及原解析雜湊。來源為 Fairlearn FAQ／指標／前處理、Google GAN問題／詞彙表及 MathWorks GAN診斷。
- 結果：第4題代理特徵機制與公平性評估已有直接支持；具體措施優先性仍是題目推論。原解析 B 把資料改善說成必然加重代理效果、D 把結果群體標籤等同訓練敏感欄位，均列最小措辭修訂建議，未直接改寫。第40題模式崩潰現象定義與其餘三概念比較已有外部來源；不把各故障視為互斥。
- 驗證與限制：已開啟六份官方技術頁相關段落；原解析 SHA-256 與 v2 所記一致；未保存整頁快照。AI 補證待審，不冒充人工接受；未作法規／官方考綱查證或實際模型診斷，未重跑檢索、pytest或Docker。
- 結束與下一步：筆記完成；外部證據可供審查但尚未納入索引。先審查第4題B／D修訂及兩題支持邊界，再另版修訂解析或規劃外部來源整合。原 v1／v2、索引、標準答案、解析保留，未 commit、push、PR 或公開。


### 2026-11-16 第三十四筆（版本：5cf7d96 加既有成果；交付收斂）
- 授權與階段：使用者要求繼續直到需本人介入，沿用上一輪建議做交付整理、實測及試用準備；目前為審查與交付準備，不代替使用者批准內容或提交。
- 產出：[交付與試用入口](validation/2026-11-16-handoff-readiness.md)、README入口、三組本機完整片段與查詢檔。第10題不在八題基準但已在50題解析，明列非獨立泛化測試。data/review/prepare_trial.py 保存建立步驟，trial結果未填人工評分。
- 本輪驗證：Windows 37 passed；Docker test建置快取後，另啟斷網容器實跑37 passed；Compose config及runtime斷網help成功。Docker沙箱不可見，核准使用正常環境CLI後成功。未跑embeddings容器、hosted CI或LLM，不影響其他服務。
- 整理：保留歷史檔案，以最新入口解決舊待辦混淆；保存所有變更的完整diff與雜湊清單於data/review/handoff-trial/。data排除、連結及diff空白檢查；尚未完成獨立程式review或人工品質驗收。
- 結束與下一步：等待使用者對三組試用回覆有幫助／部分／無幫助及理由。收到後處理必要修正、審查最終diff，再請提交授權。原第4題解析修訂建議、外部筆記內容仍待審；未改解析或入庫。未stage、commit、push或開PR。


### 2026-11-16 第三十五筆（版本：5cf7d96 加既有成果；試用第1組回饋）
- 開始與回饋：使用者表示部分有幫助，但未清楚列出 Z-score 概念及公式，認為超出教材範圍。依內容對應第1組第10題；其餘兩組尚未評分。
- 實際核對：讀取原試用五塊及既有完整頁擷取；第一名 S1:3-40:0 已有概述及公式符號，第四名同頁另一塊亦有公式符號，但分數結構已攤平，閱讀困難。因此保留使用者部分有幫助的評分，另記 AI 判讀為公式呈現／解釋不足，不當成教材全無依據。尚未 PDF 影像目視確認原版式。
- 證據：data/review/handoff-trial/feedback-01.json 保存原意、試用結果雜湊、對應假設及核對結論。未修改原檢索結果、索引、解析或使用者意見。此次文件修改已晚於 manifest-final.json，該 manifest／diff 為上一輪快照，提交前必須重產。
- 結束與下一步：第1組已有人工可用性回饋；新增公式可讀性問題待查。優先對照原 PDF，確認是否需公式擷取或閱讀呈現修正；第2／3組仍待使用者回覆。未以此宣告整體驗收或超綱，未提交發布。


### 2026-11-16 第三十六筆（版本：5cf7d96 加既有成果；第1組試用接受）
- 開始與確認：使用者釐清先前未注意到已取回的內容，回覆這樣的測試 OK。依本段對話記第1組試用接受，不代填其他組結果。
- 產出：data/review/handoff-trial/feedback-01-confirmed.json 保存原話、確認範圍及前一回饋雜湊；feedback-01.json 與原結果保留。
- 結束：第1組使用者可用性確認完成；公式扁平化仍為已觀察到的呈現限制，不宣稱已修正。第2／3組尚未明確回覆；提交授權仍未取得。
- 下一步：請使用者確認其餘兩組可用性；之後完成最終diff審查、重產差異與manifest，再請commit／push／Draft PR授權。本輪僅記錄審查，不重跑應用測試或改程式。


### 2026-11-16 第三十七筆（版本：5cf7d96 加既有成果；試用回覆完成與提交準備）
- 使用者確認第2組概念查詢有幫助；第3組回傳MSE仍不足以支持MAE。原話保存在data/review/handoff-trial/feedback-02-03.json，不將限制確認視為完整解題通過。
- 完成作者自查：重讀新增程式、prompt、合成測試、Docker／workflow與相依diff，保留公式排版、外部補證未入庫、hosted CI與LLM未實測等限制。沒有新增程式變更，沿用第三十四筆本輪Windows／Docker各37 passed，不虛構再次測試。
- 交付入口補記三組結果與自查範圍；PR正文草稿、包含未追蹤檔案的最終diff及29檔SHA-256清單保存data/review/handoff-trial/。舊快照保留。data無已追蹤內容；diff空白檢查通過。
- 結束階段：已具備Draft PR候選內容，非獨立真人批准。下一步請使用者審閱full-working-tree-final.patch及pr-body.md，授權commit／push／Draft PR；尚未stage或對外寫入，不含合併與公開。


### 2026-11-16 第三十八筆（版本：b38e031；Draft PR 交付）

- 開始：使用者明確同意最終清單的 commit、push 與 Draft PR；進入審查交付階段，授權不含合併、部署或公開。
- 實際步驟：核對 manifest-for-approval.json 的分支、HEAD 與 29 檔 SHA-256；只 stage 清單檔案，核對 staged 路徑並通過 diff --cached --check。提交 b38e0315bb8a555d651ebed9098425cbd32d356f，推送 docs/rag-next-iteration-plan，建立 Draft PR #3，base 為 main／5cf7d96。
- 結果：GitHub 回傳 Draft=true、merged=false、29 changed files，遠端 PR head 與本機提交一致。資料未納入提交；原案例、索引及評估結果保留。本輪未重跑測試，沿用第三十四筆對同一程式內容實跑的 Windows／Docker 各 37 passed。
- 限制與下一步：首次查詢此提交的 PR workflow runs 為空；再次查詢已取得 CI run 43849133563，狀態 in_progress，尚不能宣稱 hosted CI 通過或失敗。下一步確認 CI 結果，再完成獨立程式審查。MAE 依據不足、公式呈現及其他既有待辦仍保留，不代表整體品質驗收。未合併、未部署。
- 本筆與目前階段摘要為提交後的本機補記，尚未提交；已批准的 29 檔快照保持原樣，不追加未展示的提交。


### 2026-11-16 第三十九筆（版本：main 7376873；PR #3 合併查證與交接收尾）

- 開始：接手時在 docs/rag-next-iteration-plan（b38e031），工作樹僅 progress.md 有第三十八筆補記未提交，無未追蹤檔案。階段為審查與交付，待確認合併與 CI。
- 使用者告知：已合併 PR #3。
- 本輪實際查證（gh 與 git fetch）：PR #3 狀態 MERGED，mergedAt 2026-11-16T10:30:32Z，合併者為 repo 擁有者帳號，合併提交 7376873d61d61af6d3ab04ab41355b38bf25dfaa，父提交為 5cf7d96 與 b38e031；b38e031 與 7376873 的檔案樹無差異。CI run 43849133563（pull_request，b38e031）completed／success，工作 test-and-container 於 10:28:57Z 完成；合併後 main 的 CI run 43849483100（push，7376873）completed／success。第三十八筆記的 in_progress 是當時狀態，原文保留。
- 同步方式：先把 progress.md 與其 diff 備份到工作階段暫存目錄；以 fetch 將本機 main 由 5cf7d96 快轉到 7376873；再從 origin/main 建立 docs/record-pr-3-merge 並帶著未提交修改切換。未使用 reset、clean、強制切換或 stash；切換前後 progress.md 的 SHA-256 相同，無衝突。原分支 docs/rag-next-iteration-plan 本機與遠端都保留。
- 歷史驗證（非本輪）：Windows／Docker 各 37 passed 為第三十四筆實跑。本輪未跑 pytest、Docker、檢索或模型；hosted CI 的 success 是 GitHub 回報的結果，範圍限 ci.yaml 的合成測試與容器檢查。delivery workflow、embeddings 容器、真實 LLM 仍未實測。
- 本輪唯讀檢查：讀 MAE 補證筆記、config/knowledge-base.json、knowledge.py 的 build_index，及本機 mae-external-sources.json 的欄位。現況：五份來源只記 stable 網址、顯示版本與短摘記，full_snapshot_saved 為 false，無內容雜湊，人工審查狀態為待審；build_index 只接受帶雜湊的 PDF 與勘誤檔，外部來源無法也不應直接放進現行來源清單。
- 提出的最小後續工作（未執行，待使用者決定）：為 MAE 建立獨立的外部補證登錄與檢查程式，不入索引。內容為五份來源各記版本化網址、查閱日期、本機快照雜湊與授權標示；逐條主張記支持類型（直接支持／推論／不支持）、對應來源與題號、人工審查狀態。測法：合成測試覆蓋缺版本、缺雜湊、缺審查狀態、來源識別與教材相同、直接支持卻無出處等失敗情境；真實資料檢查每條直接支持的短摘記確實出現在對應快照；隔離檢查確認來源清單、主機索引識別與 v1／v2 評估檔雜湊不變。完成條件：檢查程式對 MAE 登錄通過、既有 37 項測試仍通過、使用者逐條審過主張並留下判定、教材限定基準數字不變。納入檢索須另建索引版本與評估，屬下一個決定。
- 限制：本輪沒有新增來源、下載頁面、重建索引、改評估集或解析；第 4 題措辭修訂、第 4／40 題補證整合、公式呈現、v2 其餘 AI 標註的人工審查都維持未完成。AI 自查不是獨立真人審查。
- 結束階段：PR #3 交付為已合併；MAE 可追溯化在選擇階段等使用者決定。本筆與第三十八筆補記均未 commit、push 或開 PR。


### 2026-11-16 第四十筆（版本：main 7376873 加未提交變更；MAE 外部補證登錄）

- 開始與授權：使用者回覆「接受方案」。依第三十九筆方案執行，並把當時列出的兩個建議一併視為接受：公開文件頁面快照存 data/、進版控的登錄檔不放外部原文。提交、推送與 PR 不在此授權內。階段由選擇進入設計與實作。
- 先定測法：合成測試覆蓋缺版本、缺或錯雜湊、缺授權標示、日期格式、非 https、kind 非 external、id 不以 ext- 開頭或與教材來源相同、快照路徑不在 data/、來源重複、缺審查狀態、支持類型錯誤、直接支持無來源或引用未登錄來源、推論缺推導依據、登錄檔夾帶原文、非 pending 卻無人工審查者或記為 AI、快照被改動、摘記缺漏或不在快照可見文字內、版本字樣不在快照內。先確認測試因模組不存在而失敗，再實作。
- 產出（進版控候選，均未提交）：config/external-evidence.json，5 個來源、13 條主張（直接支持 7、推論 3、來源不支持的限制 3），人工審查狀態全為 pending；src/ipas_hub/evidence.py 檢查程式，`python -m ipas_hub.evidence` 執行，加 `--structure-only` 可不讀 data/；tests/test_evidence.py 共 25 個測試案例。MAE 補證筆記與缺口清單各加一段後續補記，原文未改。
- 產出（只在 data/）：data/external/mae/snapshots/ 五份頁面快照，下載自 scikit-learn 1.9 版本化網址與 keras.io，HTTP 200，使用一般用戶端名稱，未帶任何個人或專案資訊；data/external/mae/excerpts.json 為 7 條直接支持的原文摘記；data/review/mae-evidence/review.md 為 13 條主張的人工審查對照。
- 本輪實跑結果：Windows Python 3.14.7 全套 62 passed（原 37 加新 25）；沙箱無法寫入系統暫存目錄時有 7 個 PermissionError，改指定可寫暫存目錄後全數通過，與程式無關。Docker test 目標建置成功，另以斷網容器實跑 62 passed。真實資料檢查通過：5 個快照雜湊相符、版本字樣存在、7 條直接支持的摘記都在對應快照的可見文字中。另做一次反向確認：把一句摘記改成頁面沒有的句子，檢查以失敗結束，還原後通過。
- 隔離檢查：config/knowledge-base.json 與 knowledge.py 無差異，教材來源仍只有 subject1、subject2；data/index/kb/ 的三個索引目錄未動，主機索引 19a8fa4b… 仍在；評估檔與解析未修改；未重建索引、未跑檢索或模型。git ls-files data 為空。
- 限制：檢查程式只證明可追溯，不證明主張正確；13 條主張與支持類型是 AI 判讀，未經人工審查。Keras 沒有版本化網址，僅以查閱日期與快照雜湊鎖定，快照頁面也未見授權標示，記為未查證；scikit-learn 只核對到頁尾的 BSD License 字樣，條款全文未讀。快照是 HTML 原始檔，未含頁面另外載入的資源。外部補證不進檢索，查詢時仍找不到 MAE 依據；第 28 題教材限定缺口不變。hosted CI 未跑過新測試；README 未更新這個指令。
- 結束階段：實作完成，進入審查與交付，等待兩件事：使用者逐條審 13 條主張；使用者看 diff 後決定是否提交。之後若要讓檢索用到外部補證，須另建索引版本與評估，尚未規劃。


### 2026-11-17 第四十一筆（版本：main 7376873 加未提交變更；端到端 RAG）

- 開始與方向：使用者指出近期偏重八題內部判定，RAG 本身未前進。確認：vLLM 容器＋Qwen 7–8B；外部搜尋先用維基百科、介面可換（日後可接 OpenAI API）；向量儲存先沿用現有檔案式索引跑通，pgvector 列下一步；優先串接電腦既有模型，不下載。已記入 brief 第四輪。MAE 外部補證登錄暫緩，config/external-evidence.json 與 evidence.py 留在工作樹未提交，待使用者決定保留或刪除。
- 既有資源（唯讀查證）：本機已有 vllm/vllm-openai:v0.26.0 映像；另一專案的 volume dev_infra_qwen_trial_cache 存有 Qwen/Qwen3-VL-8B-Instruct-FP8（revision 9cdc6310…，2 個權重檔 9.86 GiB，張量無缺漏，視覺部分 1.07 GiB）。只以唯讀掛載使用，未修改該 volume，也未啟動該專案的服務。GPU 為 RTX 5070 Ti 16 GB，桌面程式約佔 5.4 GB。
- 啟動除錯：第一次啟動失敗，根因是 vLLM 偵測到 WSL2 時預設關閉 pinned memory，而此版需要 UVA；核心 6.18 符合條件，設 VLLM_WSL2_ENABLE_PIN_MEMORY=1 後成功。設定：只載入文字模型、上下文 6144、KV cache fp8、顯存使用率 0.62、enforce-eager。實測權重 9.12 GiB、KV cache 可放 6,608 個 token，啟動約 125–130 秒。
- 實作（未提交）：src/ipas_hub/llm.py（OpenAI 相容介面，預設拒絕遠端端點，金鑰只讀環境變數）；src/ipas_hub/websearch.py（搜尋介面、維基百科 zh-TW、網址固定 oldid、429 重試一次）；rag.py v0.2（搜尋詞規劃、輪流取外部結果、由程式標教材／外部、引用錯誤修正一次後仍錯即拒絕）；prompts/answer.txt 改寫、新增 prompts/web_queries.txt；cli.py 的 ask 改用新流程並加 --format text；compose.yaml 以 vllm 服務取代 ollama，映像以 digest 固定，模型 volume 由 .env 的 LLM_MODEL_VOLUME 指定。README 與設計文件新增 v0.2 契約，v0.1 描述保留並標註已取代。
- 測試：先寫合成測試（假 LLM、假搜尋，不連網）。Windows 82 passed；Docker test 目標建置內 82 passed，另以斷網容器實跑 82 passed；compose config 通過。
- 實機結果（主機 CLI＋容器 vLLM，BM25 k=5，主機索引 19a8fa4b…）：8 題基準全部跑完，最終選項與官方答案 8/8 一致，每題 7–19 秒，約 2,000–4,100 tokens。依據類型：只用教材 4 題、教材＋外部 4 題（含第 18 題重跑）。第 28 題取得維基百科「平均絕對誤差」條目並引用。另以 Compose 的 app 容器呼叫 vllm 服務跑第 28 題，成功。輸出與摘要只在 data/evaluation/e2e/ 與 data/runs/。
- 實跑發現與處理：第一次第 28 題模型寫出不存在的 id（subject1:3-3-3:1）被拒絕，因此加入一次修正重試；外部結果上限被前兩個搜尋詞佔滿，改為輪流取；第 18 題維基百科回 429，加入等待後重試，重跑成功。
- 限制：8 題都在既有 50 題解析範圍內，模型也可能本來就會答，答案一致只代表流程跑得通，不代表品質或泛化；選項由 AI 讀答案判定，未經人工確認。引用只檢查 id 存在：第 28 題首次執行曾把 MAE 掛在沒有 MAE 的教材塊上；最新一次則把引用全放在答案末尾，看不出哪句來自哪個來源；外部搜尋會帶回無關條目（如第 4 題的 Anthropic、第 40 題的社會崩潰），這次模型沒有引用它們。hosted CI 未跑新測試；未用向量或混合檢索做端到端；pgvector 未做。vLLM 已停止以釋放顯存。未 commit、push 或開 PR。
- 結束階段：第四輪在實作，已有可審查原型與實跑證據。下一步：使用者試用 ask 並回饋；決定是否提交，以及下一項改進（引用逐句化與語意檢查、pgvector、或用 8 題以外的題目測試）。


### 2026-11-17 第四十二筆（版本：同第四十一筆，未提交；使用者試用）

- 使用者依設定步驟自行以 Compose 試用，回覆：「我剛剛試用了 成果我非常滿意 都有答對且解析完整」。
- data/runs/ 對應 6 筆執行紀錄（AI 讀紀錄整理，未逐題核對內容）：4 道情境考題與 1 個 Transformer 概念問題皆為 supported，其中 4 筆用教材＋維基百科、1 筆只用教材；「台北今天天氣如何」回 insufficient、未呼叫生成，符合預期。5 筆需生成者約 8.8–20.9 秒，均無修正重試、無搜尋錯誤。
- 記為使用者可用性試用接受。答案正確與解析完整是使用者判斷；是否逐一核對引用內容，使用者未提及，因此引用語意正確性仍列為未驗證，不視為品質驗收或結案。
- 下一步：等待使用者決定是否提交（需先看完整 diff）及 MAE 登錄檔去留；之後再選下一項改進。


### 2026-11-17 第四十三筆（版本：提交前工作樹；提交授權與 MAE 登錄刪除）

- 使用者回覆：「我覺得先提交與 PR merge／MAE登錄檔刪除／下一步我想開另一個對話接續」。授權本批 commit、push、開 PR 及 CI 通過後合併。
- 刪除未提交的 config/external-evidence.json、src/ipas_hub/evidence.py、tests/test_evidence.py；兩份 validation 文件中描述該登錄的補記一併還原。本機 data/external/mae/ 的快照與 data/review/mae-evidence/ 不進版控，保留未動。原 MAE 補證筆記（已在 main）不改。
- 提交前驗證：Windows 57 passed（原 37＋RAG 新增 20）；Docker test 目標與斷網容器結果見本筆末行；git diff --check 通過、data/ 無已追蹤檔案。
- 實際結果：Docker test 目標建置內 57 passed，斷網容器實跑 57 passed，compose config 通過。分支由 docs/record-pr-3-merge 更名為 feat/end-to-end-rag，以符合內容。


### 2026-11-17 第四十四筆（版本：main 7c74cbe；PR #4 合併）

- 依使用者授權：提交 ef67cea（13 檔，739 行新增、81 行刪除），推送 feat/end-to-end-rag，建立 PR #4（https://github.com/Cheryl33990/ipas-learning-hub/pull/4）。提交前完整 diff 存於 data/review/pr4-full.patch，並掃描無個人資訊、題目原文或金鑰。
- 實際查證：PR CI（run 44004865608，test-and-container）pass；以 merge commit 合併，mergedAt 2026-11-17T02:42:34Z，合併提交 7c74cbea3c7e3296ca5326cfe1959ed96f4742b8；合併後 main 的 CI（run 44004961566）completed／success；ef67cea 與 7c74cbe 檔案樹相同。本機 main 已快轉並切回 main；feat/end-to-end-rag 本機與遠端分支保留。
- 本筆與階段表更新為合併後的本機補記，尚未提交。
- 下一步：使用者將開新對話接續；建議先把本筆補記以小 PR 提交，再選下一項改進。


### 2026-11-17 第四十五筆（版本：637944a 加未提交變更；逐句引用與字詞核對）

- 接手核對：PR #4 為 MERGED、合併提交 7c74cbe，PR 與 main CI 皆 success；本機 main 與 origin 一致。Windows 重跑 57 passed（本輪實跑，非沿用）。
- 使用者看過 diff 後同意：第四十四筆補記提交為 637944a，推送 docs/record-pr-4-merge，開 [PR #5](https://github.com/Cheryl33990/ipas-learning-hub/pull/5)，CI（run 44005526281）pass；使用者同意後以 merge commit 合併，mergedAt 2026-11-17T03:00:22Z，合併提交 add04c59c09fd87c2610497c124f56d9c3a13a89。
- 使用者同意 AI 建議的下一步「引用逐句標示＋簡單內容核對」；pgvector、網頁介面延後，候選 4（8 題以外題目）併入本項實跑。契約見設計文件的生成契約 v0.3。
- 實作（未提交，分支 feat/sentence-citations）：模型改回傳 segments（每句 text＋citations）；程式產生 [教材n]／[外部n] 標記並清除模型自寫的 id；同頁多片段標第幾段；字詞核對標出句中英文詞／數字不在所引片段、或中文二元組重疊低於 0.1 的句子（只標 ⚠，不拒絕）；insufficient 且無 segments 時接受並由程式補說明；修正後仍不合格的錯誤訊息列出具體原因。prompt、README 同步更新。
- 測試：先改寫／新增合成測試再實作；Windows 67 passed。Docker test 目標與 hosted CI 本輪未跑。
- 實機（主機 CLI＋容器 vLLM，BM25 k=5，索引 19a8fa4b…，最終程式版本重跑一次）：第 28 題＋8 題以外的第 7、15、22、36、45 題。輸出只在 data/evaluation/e2e-v03/。
  - 答對 3 題（28、22、36）；答錯 1 題（15：官方 C 為 k-匿名化，模型選差分隱私，且最後未寫選項字母。使用者說明錯因：題目要避免以間接識別資訊交叉比對後重新識別特定個人，正是 k-匿名化針對的情境。維基「K-匿名性」條目已取回並被引用，屬模型推理錯誤，不是檢索缺漏）；2 題回依據不足（7、45），模型未編造答案。第 45 題問 LIME，維基搜尋取回「青檸」與 Lime 消歧義頁，教材前 5 塊也不含 LIME。
  - 逐句：supported 的 4 題共 22 句、17 句帶引用；不再出現引用全堆在末句。第 36 題只有第一句帶引用，其餘選項分析未引用。
  - 字詞核對：第 28 題標出 2 句（K-means、SVC 不在所引教材片段），屬合理提示。重疊門檻先試 0.3：首次實跑 17 句帶引用，重疊在 0.14–0.58，合理改寫與掛錯的句子分不開，標出過半，因此暫定改為 0.1，主要依英文詞缺漏。漏標：第 15 題「隨機抽樣」句掛到維基「隨機抽樣一致」（RANSAC），未被標出。
  - 每題 3–16 秒；無修正重試。AI 依官方答案判讀對錯，引用內容未經人工逐句核對。vLLM 已停止。
- 限制：6 題樣本小，只說明行為，不當品質比例；字詞比對不是語意驗證；外部搜尋的詞歧義（Lime／青檸）與教材檢索漏召回是 2 題依據不足的原因，第 15 題則是證據在手仍推理錯誤；本輪皆未處理。
- 使用者回覆：接受本批提交與開 PR、同意合併 PR #5；本輪不自行試用。
- 結束階段：第五輪實作完成並提交開 PR（合併另行確認）。下一步：之後候選為搜尋詞消歧義（如在搜尋詞加領域詞）、網頁介面、pgvector。


### 2026-11-17 第四十六筆（版本：877feb4 加未提交變更；外部搜尋前後文與英文維基備援）

- 使用者同意合併 PR #6：CI（run 44007121622）pass，以 merge commit 合併，mergedAt 2026-11-17T03:05:46Z，合併提交 877feb4。
- 使用者提出以前後文判斷同名詞，並接受引進英文來源。實作見設計文件「外部搜尋 v0.4」：中英概念詞＋必要時的領域詞、相關性與消歧義頁過濾、取含概念詞的段落、中文無結果或出錯時改查英文維基、請求間隔與逐詞失敗隔離；字詞核對對無中文的片段不算重疊。
- 未採用 bge-m3 篩選：本機實測載入約 19 秒、計算約 3 秒；第 7、15、22、28、45 題的外部條目相似度，無關條目 0.33–0.39，有用條目 0.52–0.72，掛錯的 RANSAC 0.54，無法單靠分數區分。
- 測試：先寫合成測試；Windows 77 passed。Docker 與 hosted CI 本輪未跑。
- 實機（主機 CLI＋容器 vLLM，BM25 k=5，索引 19a8fa4b…）：同第四十五筆 6 題，輸出在 data/evaluation/e2e-v04/。過程中改了四次：(1) 第一次加入領域詞時，搜尋過嚴，第 7 題變為依據不足，且多詞請求觸發 429，第 22、36 題沒有外部結果；(2) 英文詞改完整字比對（ChromiumOS 因 timeline 被當成 LIME），並在英文加領域詞查不到時改用概念詞重查，中文出錯時改查英文；(3) 有領域詞時要求導言或段落含領域詞（排除 Chromium OS Lime）；(4) 第 45 題最後一次先遇 429，等待 90 秒單題重跑成功。第 45 題的 v0.3 輸出被這次誤寫入後移到 v0.4 目錄，v0.3 的結果只留在 data/evaluation/e2e-v03/summary.json。
- 最終結果（28、22、15、7、36 為最終程式前一版的整批執行，45 為單題重跑；核對結果以最終程式對已存輸出重算）：6 題最後一句的選項都與官方答案一致（AI 判讀，未經人工逐題核對）。
  - 第 7 題：中文無相關條目，改查英文維基 Human-in-the-loop，選 B（v0.3 為依據不足）。
  - 第 36 題：中文無相關條目，英文取到 Feature Importance 與 Random forest 中講打亂特徵值的段落，選 C。
  - 第 45 題：取到英文維基 Explainable artificial intelligence 中的 LIME 段落，選 D（v0.3 為依據不足）。
  - 第 15 題：選 C（v0.3 選 A）。證據相同類型、結果不同，表示模型在此題不穩定，不視為已修正。
  - 字詞核對共標出 3 句：第 28 題 K-means、SVC 兩句（合理提示），第 15 題一句重疊 0.09。
- 限制：只有 6 題，而且搜尋規則是看著這 6 題調整的，結果偏樂觀，不代表泛化；中文相關性規則仍放過「匿名者（黑客組織）」；連續實跑容易遇到 429。使用者同意後，User-Agent 加上 repo 網址作為聯絡方式（AI 評估：維基媒體只在內部記錄 IP 與 User-Agent，不公開；不含密碼或金鑰；repo 為私人）。是否因此減少 429 尚未驗證。
- 使用者同意本批提交與開 PR。
- 結束階段：提交並開 PR，合併另行確認。


### 2026-11-17 第四十七筆（版本：main 7ecb211；PR #7 合併）

- 使用者同意提交與開 PR，並同意 User-Agent 附 repo 網址：提交 c0f88cb，開 [PR #7](https://github.com/Cheryl33990/ipas-learning-hub/pull/7)，PR CI（run 44009954603）pass。
- 使用者同意合併：以 merge commit 合併，mergedAt 2026-11-17T03:26:28Z，合併提交 7ecb211fff079168b33c903317cefdd0d659c61d；合併後 main CI（run 44010228232）success。本機 main 已快轉。
- 本筆為合併後本機補記，尚未提交。
- 使用者決定（已記入 brief 第四輪）：網頁介面採現成開源 LLM 平台當介面、背後接本專案 RAG；平台須可商用、無使用人數限制，選型時與平台內建 RAG 以相同題目並排比較，判斷自建部分的實際效益。pgvector 目前不需要，保留給日後其他主題或大量文件。
- AI 回顧（供參考，未經使用者確認）：勘誤、教材頁碼、來源區分、中英維基備援與依據不足處理是平台內建 RAG 不易提供的部分；多輪 8 題人工判定、支持範圍 v2、同頁上限實驗與 MAE 登錄偏研究性質，對好用貢獻小。從未以相同題目比較平台內建 RAG，自建是否較好尚無證據。
- 使用者指出：引用直接給 PDF 第幾頁最好用，教材章節頁碼（如 3-36）不算亮點。查證：索引只存章節頁碼，未存 PDF 頁序（guide.read_pages 未保留）。使用者決定先不補，併入下一輪：並排比較以「引用能否對回 PDF 頁碼」為首要項目，比較後再決定是否保留自建檢索及補 PDF 頁碼（兩者並列，並可連到 檔案.pdf#page=N）。
- 下一步：使用者將開新對話進行網頁介面選型；建議先以小 PR 提交本筆補記與 brief 修訂。


### 2026-11-17 第四十八筆（版本：main cac0f1c；平台授權查證與候選比較）

- 接手核對：PR #5–#7 皆 MERGED，本機與 origin main 同為 7ecb211，main CI（run 44010228232）success。本輪未跑 pytest、vLLM 或任何題目。
- 使用者同意後：第四十七筆補記與 brief 修訂提交為 8ffe2d5，開 [PR #8](https://github.com/Cheryl33990/ipas-learning-hub/pull/8)，PR CI（run 44025786830）pass，以 merge commit 合併，mergedAt 2026-11-17T05:41:47Z，合併提交 cac0f1c；合併後 main CI（run 44025899215）success。
- 授權查證（2026-11-17，以 GitHub API 讀各 repo 預設分支的 LICENSE 原文）：
  - 通過：AnythingLLM v1.19.0（MIT）、LibreChat v0.8.8（MIT）、RAGFlow v1.0.0（Apache-2.0）、Kotaemon v0.12.0（Apache-2.0，最後 commit 2026-05-30）。Onyx v5.1.3 為 ee 目錄企業授權、其餘 MIT。
  - 不通過：Open WebUI v0.13.3（第 4 條：30 天內使用者超過 50 人不得移除或更改品牌）、Dify 1.19.0（多租戶需授權、不得移除 LOGO）、LobeHub v2.3.3（衍生作品需商業授權）、FastGPT v4.17.4（多租戶 SaaS 需授權、不得移除 LOGO）。Chainlit repo 已封存，排除。
- 功能（只讀原始碼與 README，未實跑）：AnythingLLM 匯入 PDF 時把各頁合併、不保留頁碼；LibreChat 檔案引用帶 pages 並顯示頁碼，原始碼找不到 `#page=` 連結，且檔案檢索是 agent 工具，需要 tool calling；Open WebUI 的引用視窗會連到 `檔案#page=N`（授權不通過，僅供參考做法）；RAGFlow 官方建議 4 核／16 GB RAM／50 GB 磁碟；所有平台的內建 RAG 都需要嵌入模型。
- 環境查證：compose.yaml 的 vLLM 未開 tool calling，max-model-len 為 6144；本機 Hugging Face 快取有 models--BAAI--bge-m3。
- 映像壓縮後大小（docker manifest inspect，尚未下載）：LibreChat 0.99 GB、其 RAG API lite 0.59 GB、mongo 8.0.20 0.31 GB、meilisearch v1.35.1 0.11 GB、pgvector 0.8.0-pg15 0.16 GB；AnythingLLM 1.19 GB。
- 使用者決定：嵌入模型用本機已快取的 bge-m3，不下載新模型。
- AI 建議（待使用者確認）：實測 LibreChat 與 AnythingLLM，兩者是分開實測、並排比較的兩個候選，不是合併使用；最後只留一個當介面。
- 結束階段：選擇（第一步）。下一步：使用者選定實測平台並同意映像下載與 vLLM 開 tool calling。


### 2026-11-17 第四十九筆（版本：分支 chore/platform-compare，cac0f1c 加未提交變更；平台內建 RAG 並排實測）

- 使用者同意：實測 LibreChat 與 AnythingLLM、下載六個映像、替 vLLM 加 tool calling。compose.yaml 的 vllm 新增 `--enable-auto-tool-choice`、`--tool-call-parser=hermes`（未提交）。
- 環境：vLLM（Qwen3-VL-8B-Instruct-FP8）與本專案相同；嵌入用本機快取 bge-m3，以臨時腳本包成只綁 127.0.0.1 的 /v1/embeddings（CPU，不下載）。臨時腳本、平台設定與全部輸出只在 data/evaluation/platform-compare/ 與 data/platforms/librechat/，不進版控。
- 平台版本與設定：AnythingLLM `mintplexlabs/anythingllm:latest`（預設工作區設定：topN 4、相似度門檻 0.25、chat 模式）；LibreChat `librechat:latest`＋rag-api lite＋mongo＋pgvector（未啟用 meilisearch），agent 只開 file_search，temperature 0。兩者皆用預設切塊，未調參。映像解壓後大小：AnythingLLM 5.15 GB、LibreChat 4.3 GB、rag-api 2.52 GB、mongo 1.28 GB。記憶體約 AnythingLLM 0.64 GB、LibreChat 四個容器合計約 0.84 GB。
- 題目：與第四十五、四十六筆相同的 6 題（28、7、15、22、36、45），各跑一次；另加一題勘誤探針（平均差定義，科目 1 頁 3-25）。本專案 6 題沿用 data/evaluation/e2e-v04/out/ 的既有輸出，本輪只重跑勘誤探針（--web none）。
- 結果（AI 依官方答案與字串比對判讀，未經人工逐題核對）：
  1. PDF 頁碼：LibreChat 每個來源帶 PDF 頁序（如 3-36 回報第 42 頁，已用 pypdf 核對相符）；介面上是否能點開到該頁只讀過原始碼（顯示頁碼、無 `#page=`），未在畫面驗證。AnythingLLM 來源只有檔名，無頁碼。本專案只有章節頁碼。
  2. 選項：AnythingLLM 6／6 與官方一致，但 5 題只回一行選項、沒有理由。LibreChat 4／6 一致（7、22、36、45）；第 28、15 題把問題改寫成檢索詞後寫成概念說明，沒有選出選項。本專案 v0.4 為 6／6（既有結果）。
  3. 教材與外部來源：兩個平台都沒有外部來源，也沒有行內引用標記（LibreChat 的回答 0 個引用錨點）；本專案逐句標 [教材n]／[外部n]。
  4. 依據不足：兩個平台取回的片段多半不含題目關鍵詞（MAE、Human-in-the-loop、LIME、Permutation、半監督、k-匿名皆 0 個片段命中），仍直接作答且未說明依據不足；LibreChat 第 15 題還寫「ipas-subject1.pdf 提到 k-匿名化技術」，但取回片段沒有這個詞。本專案對同樣缺口改查維基並標為外部。
  5. 勘誤：AnythingLLM 回答勘誤前的舊定義（片段為舊文字）；LibreChat 取回舊文字片段，回答只有「根據教材內容，」即中斷（原因未查）；本專案回答勘誤後文字並標 3-25。
  - 耗時：AnythingLLM 1–10 秒；LibreChat 3–21 秒；本專案 3–22 秒（既有紀錄）。
- 限制：只有 6 題加 1 題探針、各跑一次；平台用預設設定，未嘗試調整提示詞、切塊或 topN；以 API 呼叫，未檢視實際畫面；經 Git Bash 上傳造成 AnythingLLM 中文檔名亂碼，屬操作問題，不是平台缺陷；選項一致不代表理由正確。
- 驗證：compose config 通過；Windows 77 passed（本輪實跑）；勘誤探針確認加上 tool calling 參數後 ask 仍可正常執行。Docker test 目標與 hosted CI 本輪未跑。
- 收尾：vLLM 與嵌入端點已停止；兩個平台的容器仍在執行，供使用者檢視。
- AI 建議（待使用者決定）：保留自建檢索；補 PDF 頁序（與章節頁碼並列，可連到 檔案.pdf#page=N）；第二步的介面建議 LibreChat。
- 結束階段：選擇（第一步比較完成，等使用者決定）。


### 2026-11-17 第五十筆（版本：分支 chore/platform-compare；使用者決定與清理）

- 使用者決定：第二步的介面用 AnythingLLM；沒選上的平台移除以釋放記憶體與容量；同意提交 compose.yaml 與 progress 變更並開 PR（合併另行確認）。
- 使用者指出官方學習資源頁還有其他素材當時未下載，現在可以擴充，用來改善「樣本小」的限制。要下載哪些檔案尚未確認。
- 清理：LibreChat 的四個容器、四個資料卷、網路與五個映像（librechat、rag-api lite、mongo、meilisearch、pgvector）已移除；本機設定目錄 data/platforms/librechat 已刪除。實測輸出保留在 data/evaluation/platform-compare/。AnythingLLM 容器與資料卷保留。
- 未決：是否補 PDF 頁碼，使用者尚未明確回覆。


### 2026-11-17 第五十一筆（版本：分支 feat/rag-chat-endpoint，基於 chore/platform-compare；聊天介面端點）

- PR：第四十八至五十筆與 compose 的 tool calling 參數已提交為 [PR #9](https://github.com/Cheryl33990/ipas-learning-hub/pull/9)，PR CI（run 44033195042）pass，尚未合併（待使用者同意）。
- 官方學習資源頁（2026-11-17 讀取）：初級公告試題共 8 份（114 年第四梯次、115 年第一、二、三次，各兩科），本機只有 115 年第三次第一科；另有中級教材 3 份、中級試題 6 份、中級勘誤表。頁面未顯示試題的下載網址。尚未下載任何檔案，待使用者確認範圍。
- 第二步實作（未提交）：依使用者選定的 AnythingLLM，新增 src/ipas_hub/server.py 與 `serve` 指令、cli.answer_text、tests/test_server.py；compose.yaml 新增 `ui` 服務（映像以 digest 固定）；設計文件新增「聊天介面端點 v0.5」；README 新增聊天介面一節。先寫合成測試再實作。
- 測試：Windows 92 passed（原 77＋新增 15，本輪實跑）；`docker compose --profile llm --profile ui config -q` 通過。Docker test 目標與 hosted CI 本輪未跑。
- 實機（主機 serve＋容器 vLLM＋容器 AnythingLLM，經 AnythingLLM 的 API 提問，輸出在 data/evaluation/ui-endpoint/）：
  - vLLM 尚未就緒時直接呼叫端點：回覆「⚠ 無法產生有依據的解答」與原因，沒有冒充解答。
  - 第 28 題 15.8 秒、第 45 題 10.6 秒、勘誤探針 3.6 秒，皆回傳與 CLI 相同格式的文字（狀態、逐句標記、⚠、依據清單）；平台自身來源數為 0，表示平台沒有另外做檢索。第 28 題選 C、第 45 題選 D，與官方一致；勘誤探針為勘誤後文字。
- 限制：只跑 3 則；維基 429、格式不合格兩種失敗只有合成測試，未在實機重現；聊天畫面的實際排版未檢視（瀏覽器自動化工具本輪連不上）；沒有多輪對話；引用仍只有章節頁碼。
- 收尾：vLLM 與 serve 已停止；`ui` 容器仍在執行。原先以 docker run 建立的實測用 AnythingLLM 容器與資料卷已移除，改由 compose 管理。
- 未決：PR #9 合併；本批變更的提交；是否補 PDF 頁碼；要下載哪些官方試題。
- 結束階段：實作（第二步），待使用者試用與審查 diff。


### 2026-11-17 第五十二筆（版本：main 222013a 加 feat/rag-chat-endpoint 未提交變更；使用者試用與下一輪決定）

- 使用者同意合併 PR #9：以 merge commit 合併，mergedAt 2026-11-17T06:58:51Z，合併提交 222013a；本機 main 已更新。
- 使用者試用 AnythingLLM＋本專案端點後決定：
  1. 補上 PDF 頁碼，並希望引用能連到教材的該頁。
  2. 下載官方學習資源頁的其他試題。
  3. 加入 PostgreSQL＋pgvector 向量資料庫，讓他人可以重現本專案。這修訂了 brief 第四輪「向量儲存（修訂）」列的「目前不需要」。
- 第五十一筆的第二步變更（端點、ui 服務、測試、設計 v0.5、README）仍未提交；使用者沒有另外表示提交授權。
- 下一步：使用者將開新對話接續，先處理第二步變更的提交，再做 PDF 頁碼、試題下載與 pgvector。


### 2026-11-17 第五十三筆（版本：main 222013a 加 feat/rag-chat-endpoint 未提交變更；新對話接手核對與提案）

- 接手核對（本輪實際查證）：PR #9 為 MERGED，本機與 origin main 同為 222013a，main CI（run 44035189553）success。本機在 feat/rag-chat-endpoint（55901b3，已含於 main），未提交變更為 6 個修改檔與 2 個新檔，與交接所述一致。
- 本輪實跑：Windows 92 passed（.venv，pytest -p no:cacheprovider）；`docker compose --profile llm --profile ui config -q` 通過。vLLM、AnythingLLM、任何題目、Docker test 目標與 hosted CI 本輪未跑；第五十一筆的實機結果是上一輪的。
- 本筆變更：只更新 progress（開頭進度、階段表第七輪列、本筆），程式與其他文件未動。
- 已向使用者提出（皆待確認，尚未實作）：
  1. 第二步變更提交與開 PR。
  2. PDF 頁碼：索引每塊加 PDF 頁序，引用顯示「3-36（PDF 第 42 頁）」；`serve` 同一個埠以唯讀方式提供索引所列教材 PDF，依據清單改為帶 `#page=N` 的 Markdown 連結。
  3. 試題下載：先找出下載網址並列出檔名、來源與大小，確認後才下載。
  4. pgvector：檢索包成可替換的儲存介面，檔案索引保留；BM25 維持在程式內、預設方法不變。
- 使用者回覆（2026-11-17）：「我都同意，而 D 的部分按照你的建議」。即同意第二步變更提交與開 PR（合併另行確認）；同意 PDF 由 `serve` 同埠提供、依據清單改 Markdown 連結；pgvector 的重現路徑採「Postgres 存片段、預設 BM25、不需下載嵌入模型，向量檢索為選用」。
- 結束階段：第二步為審查與交付（已獲提交與開 PR 授權）；PDF 頁碼進入實作；試題下載與 pgvector 依序進行，下載範圍與映像仍須先列出再確認。


### 2026-11-17 第五十四筆（版本：分支 feat/pdf-page-links，9814af5 加未提交變更；PDF 頁碼與教材連結）

- 第二步交付：提交 9814af5 並推送 feat/rag-chat-endpoint，開 [PR #10](https://github.com/Cheryl33990/ipas-learning-hub/pull/10)；PR CI（run 44037657582）pass。尚未合併，合併前需使用者同意。
- 實作（未提交，先寫合成測試）：guide.py 的 Page／Chunk 加 `pdf_page`，`read_pages()` 記 PDF 頁序；knowledge.py 把 `pdf_page` 寫入片段、`pdf` 路徑寫入來源；rag.py 的 sources 帶來源識別與 PDF 頁，`render_text` 顯示「（PDF 第 N 頁）」並可輸出 Markdown 連結；server.py 新增唯讀的 `/files/<名稱>` 允許清單；cli.py 新增 `source_files`、`textbook_link` 與 `serve --link-base`。送給模型的 evidence 未變。設計文件新增 v0.6，README 與 brief 同步。
- 測試：Windows 98 passed（原 92＋新增 6，本輪實跑）。Docker test 目標與 hosted CI 未跑。
- 新索引（舊的三個目錄未動）：BM25 版 data/index/kb/8e487281…、含 bge-m3 向量版 a0ff519f…（本機快取，建置 72 秒）。兩者由未提交的工作樹建立，提交後 code_version 會不同，必要時重建。
- 核對（本輪實跑）：新索引 266 塊的 id 與文字與原 19a8fa4b… 完全相同，全部帶 `pdf_page`；科目 1 的 3-36 = PDF 第 42 頁、3-25 = 第 31 頁，與上一輪 pypdf 核對一致；科目 1 片段涵蓋 PDF 第 5–70 頁、科目 2 第 5–61 頁。
- 實機（另開 8101 埠的 serve、`--web none`，既有 vLLM；輸出在 data/evaluation/pdf-links/）：勘誤探針 3.8 秒，依據為「[教材1] [教材 初級科目 1 人工智慧基礎概論 3-25（PDF 第 31 頁）](http://127.0.0.1:8101/files/subject1.pdf#page=31)」；`/files/subject1.pdf` 回 200、application/pdf，下載內容的 SHA-256 與設定檔相同；`/files/../../.env` 回 404。
- 未驗證：AnythingLLM 畫面是否把依據渲染成可點的連結、瀏覽器是否跳到該頁（Chrome 擴充功能本輪未連線）；經 AnythingLLM 的完整來回本輪未跑，因為 8100 埠是使用者自己啟動的舊版 serve，未去動它。維基搜尋的題目本輪未跑。
- 收尾：我啟動的 8101 serve 已停止。vLLM、`ui` 容器與 8100 的 serve 在本輪開始前就在執行，未更動；vLLM 仍佔用顯存，用完需 stop。
- 下一步：使用者看 diff；以新索引重啟 serve 後在畫面點一次連結；同意後提交並開 PR。之後進行試題下載（先列檔名、網址、大小）。
- 結束階段：審查與交付（PDF 頁碼，待提交授權與畫面驗證）。
- 補記（同日，使用者畫面驗證）：使用者第一次重啟 serve 時仍用舊索引 19a8fa4b…，`/files/` 回 404（舊索引沒有 PDF 頁序與教材路徑，屬預期行為）；改用新索引 8e487281… 重啟後，使用者回覆「都可以點!!! OK 沒有問題」，即 AnythingLLM 畫面的教材連結可點並開到教材頁。這是使用者親自操作的結果，AI 未檢視畫面。使用者同意提交並開 PR（合併另行確認），並指示接續試題下載。


### 2026-11-17 第五十五筆（版本：分支 feat/pdf-page-links，135e1a1 加本筆未提交；試題下載範圍探查）

- PDF 頁碼交付：提交 135e1a1 並推送，開 [PR #11](https://github.com/Cheryl33990/ipas-learning-hub/pull/11)（疊在 PR #10 之上）；提交前 Windows 98 passed。PR #10、#11 皆未合併，合併前需使用者同意。
- 官方學習資源頁探查（2026-11-17，只讀頁面 HTML 並對各檔送 HEAD 查大小，未下載任何檔案內容）：頁面原始碼內含 21 個資源檔網址，全部在 `https://www.ipas.org.tw/api/proxy/uploads/certification_resource/bf93f438f7be48d295c1b40a34d79f3d/` 之下，HEAD 皆回 200，合計約 36.3 MB。上一輪「頁面未顯示試題下載網址」的說法更正為：網址在頁面原始碼內。
  - 初級試題 8 份（0.38–0.59 MB）：114 年第四梯次、115 年第一、二、三次，各兩科。115 年第三次第一科大小 590,445 bytes，與本機既有檔相同（未比對雜湊）。
  - 中級試題 6 份（0.40–1.60 MB）：114 年第二梯次、115 年第一次，各三科。
  - 中級學習指引 3 份（4.5、6.4、4.7 MB）與中級勘誤表 1 份（0.38 MB）。
  - 初級學習指引 2 份與初級勘誤表 1 份：本機已有，大小與本機檔相同。
- AI 建議的下載範圍（待使用者確認）：初級其餘 7 份試題，合計約 3.3 MB，存 data/raw/exam/；中級教材、試題與勘誤先不下載，因知識庫目前只有初級兩科。
- 結束階段：試題下載為定義（待使用者確認範圍）。


### 2026-11-17 第五十六筆（版本：分支 chore/more-exams，main 7371408 加未提交的 progress、brief；合併、下載與新題試跑）

- 合併（使用者同意「照順序合併」）：PR #10 以 merge commit 合併為 37770a3（2026-11-17T07:49:04Z），PR #11 合併為 7371408（07:49:13Z）；合併後 main CI（run 44041640929）success。本機 main 已更新。合併不等於驗收或結案；兩個 PR 皆無獨立真人程式審查。
- 下載（使用者確認範圍：初級其餘試題，加上中級試題、教材、勘誤）：17 份、合計 25.18 MB，全部來自第五十五筆所列網址，下載後檢查為 PDF 且大小與 HEAD 相同。放在新子目錄，未動既有的 exam/、guide/（既有探索程式假設這兩個目錄各只有一份 PDF）：
  - data/raw/exam-beginner/ 7 份（3.34 MB）、data/raw/exam-intermediate/ 6 份（5.82 MB）、data/raw/guide-intermediate/ 3 份（15.64 MB）、data/raw/errata-intermediate/ 1 份（0.38 MB）。
  - 清單（檔名、來源網址、大小、SHA-256、時間）在 data/raw/download-manifest-2026-11-17.json。全部不進版控（已用 git check-ignore 確認）。
- 現有切題程式（exam.py）對新試題的結果（只看題數，未逐題核對內容）：初級 7 份中 6 份切出 50 題，114 年第四梯次第一科切出 49 題（缺第 4 題，原因未查）。中級 6 份切出 39–50 題，有缺題，現有規則不完全適用；中級教材與勘誤尚未開檔檢查，也未納入知識庫。
- 新題試跑（檢查搜尋規則是否過度貼合原本 6 題）：
  - 做法：固定亂數種子 20261117，初級 7 份新試題各抽 1 題再加抽 1 題，共 8 題（科目 1 三題、科目 2 五題），都是先前沒跑過的題目；`ask` 預設設定（BM25、k=5、維基百科），索引 8e487281…，vLLM Qwen3-VL-8B-FP8，各跑一次，題間隔 6 秒。題目與輸出在 data/evaluation/new-exams/。
  - 結果（AI 讀回答後與官方答案比對，未經人工核對，理由是否正確未判定）：8 題選出的選項皆與官方答案一致；全部回 supported，依據為只用教材 4 題、教材＋外部 2 題、只用外部 2 題；耗時 8.7–17.8 秒；沒有執行錯誤，沒有遇到維基 429。
  - 觀察到的問題：
    1. 8 題中 5 題沒有明寫「答案：X」，其中 2 題只講概念、沒提選項代號，需對照題目才知道選哪個。
    2. 外部來源掛錯一例：「Chunking」配到英文維基的心理學條目（Chunking (psychology)），不是文件切塊；回答的結論與官方一致，但引用不支持該句的技術內容，字詞核對只標出其中一句。
    3. 字詞核對的誤標：8 題共 7 句被標 ⚠，多數是句中的英文詞（SOP、LLM、KPI、MVP、API）來自題目本身而不在教材片段內。
    4. 2 題完全靠外部資料（MCP、Chunking），教材檢索前五筆沒有相關內容。
  - 限制：8 題、各一次；選項一致不代表理由正確；沒有與調整前的規則對照，只能說「未見明顯變差」，不能量化泛化能力。
- 結束階段：試題下載為收尾（待使用者確認）；pgvector 為設計與測試規劃（細部設計待提）。


### 2026-11-17 第五十七筆（版本：分支 chore/more-exams，main 7371408 加未提交變更；答案選項與核對註記）

- 使用者決定：先修第五十六筆的問題 1（沒寫答案選項）與 3（⚠ 誤標）再做 pgvector；progress 連同修改一起提交並開 PR；同意下載 pgvector 映像與 psycopg 套件。
- 問題 3 的做法調整（AI 判斷，與第五十六筆的原提議不同）：原提議「略過題目裡出現過的詞」。用既有輸出檢查後發現，第 28 題被標的 K-means、SVC，以及當初掛錯的 MAE 都在題目內；新題第 4 題被標的「AI」也是真的掛錯（引到心理學條目）。略過會藏掉這些，因此改為保留標記、註明「題目中的詞」。
- 實作（先寫測試）：prompt 要求最後一句為「答案：X」；rag.py 新增 has_options、answer_choice，缺答案選項併入唯一一次修正，仍缺則註記不拒絕；check_segment 新增 question_terms；_strip_ids 也清除圓括號內的 id。設計見 v0.3.1。
- 測試：Windows 105 passed（原 98＋新增 7，本輪實跑）。Docker test 目標未跑。
- 實機（同 8 題重跑一次，vLLM 與索引同第五十六筆，輸出在 data/evaluation/new-exams/out-v2/）：
  - 8 題都寫了「答案：X」，answer_choice 皆與官方答案一致；沒有觸發修正（只靠 prompt）。耗時 7.0–17.2 秒。
  - ⚠ 共 11 句，其中 5 句只因題目用詞並已註明。第 5 題的 5 句中 3 句是模型把 id 寫在圓括號內造成；修正 _strip_ids 後用同一份輸出離線重算為 2 句（都是題目用詞）。依此推算目前為 8 句、7 句已註明題目用詞，但這是離線重算，未重跑模型。
  - 引用來源與第一次不同（例如第 1、6 題改為教材＋維基），顯示同題重跑結果會變動。
- 限制：8 題、各一次；選項一致不代表理由正確；Chunking 掛到心理學條目的問題未處理，仍在。
- 結束階段：審查與交付（待提交與開 PR，使用者已授權）；pgvector 進入設計與測試規劃。


### 2026-11-17 第五十八筆（版本：分支 feat/pgvector，基於 chore/more-exams f6f61a5，未提交；pgvector 準備）

- 交付：第五十五至五十七筆與答案選項修正提交為 f6f61a5，開 [PR #12](https://github.com/Cheryl33990/ipas-learning-hub/pull/12)，PR CI（run 44043609321）pass；未合併，合併前需使用者同意。
- 下載（使用者同意）：映像 `pgvector/pgvector:0.8.6-pg17`，digest `sha256:cf134a767f474095eeba57e0117be8e568e011a63f33fbf252f14c9b760f8e6f`，解壓後 158 MB（未選 5 天前發布的 0.8.7）；Python 套件 psycopg 3.3.9（含 psycopg-binary、tzdata），以 `uv add --optional pg` 加入 pyproject 的選用相依 `pg` 並更新 uv.lock。sentence-transformers 仍在。
- 本機 5432、5433 埠目前無服務；本機另有其他專案的 postgres:17.10 映像，未啟動、未使用。
- 細部設計已提給使用者，待確認後實作。
- 結束階段：設計與測試規劃（pgvector）。


### 2026-11-17 第五十九筆（版本：分支 feat/pgvector，f6f61a5 加未提交變更；三種檢索方法端到端比較）

- 使用者討論與決定：使用者過去用全文檢索的經驗是「找到關鍵字，但不一定回答到問題」，希望用向量檢索處理語意相近、用詞不同的情況。AI 說明關鍵字與向量各自的長處、為何 BM25 計算留在程式內、為何先建檔案索引再載入資料庫後，使用者同意三點：(1) 用 Postgres 時預設混合檢索，重現步驟包含下載 bge-m3（本機快取實際 4.3 GB，更正先前「約 2 GB」）；(2) 檔案索引為版本來源，另提供一次做完的 `index --to-pg`；(3) 先做三種方法比較再實作。這取代第五十三筆使用者所選的「預設 BM25、不需下載模型」。
- 比較做法：14 題（第五十六筆的新題 8 題＋第四十五、四十六筆的舊題 6 題）×（bm25、vector、hybrid），k=5，共 42 次完整回答。同一份含向量索引 a0ff519f…、同一個 vLLM（Qwen3-VL-8B-FP8）、`--web none`（關閉維基，只看教材檢索的差別），各跑一次。程式在同一個程序內載入索引與 bge-m3 一次。輸出在 data/evaluation/method-compare/。
- 結果（答案選項由程式讀「答案：X」後比對官方答案；理由是否正確未判定）：

| 方法 | 選項與官方一致 | 選錯 | 依據不足 | ⚠ 句數 | 檢索耗時中位數 | 模型耗時中位數 |
|---|---|---|---|---|---|---|
| BM25 | 10／14 | 舊 15 | 新 04、舊 7、舊 45 | 9 | 3.9 毫秒 | 5.9 秒 |
| 向量 | 10／14 | 新 08、舊 15 | 舊 7、舊 45 | 13 | 222 毫秒 | 6.6 秒 |
| 混合 | 11／14 | 舊 15 | 新 04、舊 45 | 12 | 211 毫秒 | 6.0 秒 |

- 判讀：
  1. 三者差距只有一題，樣本小、各跑一次，不足以說哪個方法較好；混合沒有比另外兩者差，與使用者的方向一致。
  2. 向量檢索找回了 BM25 找不到的頁：新 04（Chunking，BM25 前五沒有相關頁、向量找到 3-49）與舊 7（混合找到 3-7、3-49）。向量單獨使用時新 08 選錯，混合沒有。
  3. 舊 15 三種方法都選 A（官方 C），舊 45 三種都依據不足：這兩題教材本身沒有足夠內容（先前紀錄已知），開外部搜尋時才會補上。
  4. 混合與向量每題多約 0.2 秒算查詢向量（CPU）；載入索引與 bge-m3 共 5.7 秒（模型檔已在系統快取，冷啟動可能較久）。
- 限制：14 題、各一次、關閉外部搜尋，所以不等於實際使用（實際使用預設開維基）；選項一致不代表理由正確。
- 結論：依使用者決定，pgvector 路徑預設混合檢索；BM25 保留給沒有模型的人。檔案索引的 CLI 預設暫不改（仍為 bm25），避免影響既有用法，於 pgvector 交付時一併詢問。
- 結束階段：pgvector 進入實作。


### 2026-11-17 第六十筆（版本：分支 feat/pgvector，基於 f6f61a5，未提交；PostgreSQL＋pgvector）

- 依使用者確認的設計實作（見[設計 v0.7](design/rag-prototype.md)），先寫測試：
  - 新增 src/ipas_hub/pgstore.py（資料表、資料列互轉、載入、讀回驗證、資料庫向量近鄰）；KnowledgeBase 的向量來源可替換（記憶體或資料庫）並新增 attach_encoder。
  - cli：`--store file|pg`、依儲存決定預設方法（file 為 bm25、pg 為 hybrid）、`pg-load`、`index --to-pg`；pg 未指定 --index 時取最近載入且含向量的索引。
  - knowledge：設定檔的來源可不指定勘誤檔，索引記錄 `errata: not_applied`；新增 config/knowledge-base.no-errata.json。原因：勘誤替換檔含教材原文、不在 repo，他人重現時沒有，原程式會直接無法建索引。
  - compose 新增 `db` 服務（映像以 digest 固定、127.0.0.1:5433、volume pg-data、密碼取 .env 的 PG_PASSWORD）；app 服務加 PG_DSN／PGPASSWORD；Dockerfile 一律安裝 pg 選用相依；CI 加 pgvector service container 與 PG_TEST_DSN，Compose 驗證加 ui、db profile。
  - README 新增「從零重現」一節；brief 更新向量儲存列。
- 本機設定：AI 在 repo 根目錄 .env（不進版控，已確認被忽略）新增隨機產生的 PG_PASSWORD（32 字元，只用於本機 db 容器，未在對話中顯示）。
- 測試（本輪實跑）：Windows 118 passed（含 3 個需資料庫的測試，連本機 db 容器執行）；沒有 PG_TEST_DSN 時這 3 個略過。`docker compose --profile llm --profile ui --profile db config -q` 通過；Docker test 階段（含 pg 選用相依，容器內跑合成測試，資料庫測試略過）本機建置成功。
- 實機：
  - 啟動 db 容器（healthy）；pg-load 兩個新索引：含向量 a0ff519f… 0.44 秒、BM25 版 8e487281… 0.16 秒；重複載入回 already_loaded。
  - 從資料庫讀回並驗證 266 塊 0.07 秒。14 題 × 3 方法的前 5 筆，資料庫與檔案索引完全相同（42／42）；檢索耗時中位數兩者相近（約 0.16 秒，主要是 CPU 算查詢向量）。
  - `serve --store pg`（預設 hybrid、開維基）6 秒就緒，自動選到含向量的索引；新 04 題 6.3 秒回答，選 B 與官方一致，教材 PDF 連結回 200。這題的外部依據是維基「速讀」條目，與 Chunking 的技術意義不符，屬外部搜尋的既有問題，與資料庫無關。
  - 以無勘誤設定檔建索引 db777a29…，兩科都記為 not_applied；README 的 PowerShell 讀密碼與 `search --store pg` 指令照寫可用。
- 未驗證：README 步驟由一個全新環境從頭執行（含 hf download）未做；AnythingLLM 畫面經 `--store pg` 的操作未做（端點 API 已測）；hosted CI 的 service container 與耗時待 PR 實跑。
- 收尾：我啟動的 8101 serve 已停止；db 容器保持執行（供使用者試用）；vLLM、ui 與使用者的 8100 serve 未更動。
- 結束階段：實作完成、待審查（未提交）。


### 2026-11-17 第六十一筆（版本：分支 feat/pgvector，main 96d91cb；預設方法改為混合與交付）

- 使用者指示：先合併 PR #12，再提交 feat/pgvector 並開 PR，預設方法改成混合。
- 合併：PR #12 以 merge commit 合併為 96d91cb（2026-11-17T08:33:19Z）；本機 main 已更新。
- 預設方法（先寫測試）：`--store file` 與 `pg` 都預設 hybrid。為了不讓沒有向量的索引（例如 BM25 版 8e487281…、Docker 預設映像建的索引）直接失敗，未指定 --method 時改用 bm25 並在 stderr 提醒；明確指定 vector／hybrid 仍報錯。pgstore 新增 has_vectors。
- 影響：使用者目前 8100 的 serve 若用 8e487281…（無向量），重啟後會退回 BM25 並提醒；要用混合須改指 a0ff519f…（含向量），或改用 `--store pg`。
- 測試（本輪實跑）：有資料庫時 121 passed；沒有 PG_TEST_DSN 時 117 passed、4 skipped。一個資料庫測試起初失敗，原因是本機資料庫 public schema 已有真實資料表、測試 schema 建表前查到它；改為建表後才判斷（CI 的資料庫是空的，不受影響）。
- 實機（只檢索、不呼叫 LLM）：檔案索引含向量 → hybrid；檔案索引無向量 → bm25 並印提醒；`--store pg` 預設 → hybrid；`--store pg` 指定無向量索引 → bm25 並印提醒。四者第一筆皆為 3-25。
- 結束階段：審查與交付（PR 待使用者同意合併）。
- 交付：提交 3dd706c 並推送 feat/pgvector，開 [PR #13](https://github.com/Cheryl33990/ipas-learning-hub/pull/13)；PR CI（run 44048061078）success。CI 主機上 121 passed（4 個資料庫測試在 service container 實際執行，未略過），容器內 117 passed、4 skipped（容器內沒有資料庫，屬預期）。整個 job 57 秒，PR #9 時為 31 秒，多約 26 秒。本筆補記在提交後寫入，尚未提交。


### 2026-11-17 第六十二筆（版本：main a8b085f；分支 docs/repro-verification 未提交；重現驗證）

- 使用者同意提交與合併並開始驗證：progress 補記提交為 PR #13 的第二個 commit 後合併，合併提交 a8b085f（2026-11-17T08:45:23Z）。補記 commit 推送後、其 PR CI 開始前即合併（只改文件）；合併後 main CI（run 44049450895）success。
- 全新環境重現（照 README「從零重現」逐步執行，AI 操作）：
  - 做法：在暫存目錄以 `gh repo clone` 取得 main a8b085f（沒有 data/、.env），用全新的 uv 環境；沒有勘誤替換檔，模擬他人重現。偏離 README 兩處：資料庫埠改 5434（避免與使用者 5433 的資料庫衝突）、serve 埠改 8102（使用者 8100 在用）；LLM 共用已在執行的 vLLM，未另起一份。
  - 步驟 1：從官方網址下載兩份初級學習指引，SHA-256 與 config/knowledge-base.json 完全相同（科目 1 5,237,777 bytes、科目 2 5,041,118 bytes）。先前只比對過大小，這次才實際比對雜湊。
  - 步驟 3：`uv sync --extra pg --extra embeddings` 6 秒（套件已在 uv 快取）；`hf download BAAI/bge-m3` 31 秒。
  - 步驟 5：db 容器啟動；`index --config config/knowledge-base.no-errata.json --embedding-model BAAI/bge-m3 --to-pg` 95 秒，產生並載入 1a470628…（含向量）。與使用者的勘誤版索引 a0ff519f… 比對：266 塊 id 相同、PDF 頁相同，只有 12 塊文字不同，全在勘誤頁（科目 1 的 3-25、3-26、3-27、3-30、3-31，科目 2 的 3-32）。
  - 步驟 6：`serve --store pg` 7 秒就緒；README 的 `ask --store pg --format text` 12 秒回答勘誤探針（無勘誤，依更正前文字，屬預期）；經端點問新 04、舊 28 題，分別選 B、C，與官方一致，舊 28 題帶 3 個教材連結；`/files/subject1.pdf` 回 200。
  - 證據（執行紀錄與無勘誤索引）複製到 data/evaluation/repro-2026-11-17/；副本、其資料庫容器與 volume 已刪除。
- 發現的問題與修正（未提交）：
  1. README 的 `hf download BAAI/bge-m3` 會下載整個 repo（4.6 GB），其中 ONNX 版本（onnx/model.onnx_data，2.27 GB）與圖片本專案用不到。改為加 `--exclude "onnx/*" --exclude "imgs/*" --exclude "*.jpg"`，依 Hugging Face 檔案清單計算約 2.3 GB；磁碟需求改為約 4 GB。第五十九筆所記「4.3 GB」是使用者原本快取的大小（含兩份相同權重），不是新使用者需要的下載量。
  2. README 補一行：5433 被占用時設 PG_PORT 並同步改 PG_DSN 的 port。
- 對使用者環境的影響：這次照 README 執行時，`hf download` 在使用者的 Hugging Face 快取新增了 bge-m3 的 ONNX 版本與圖片等檔案（約 2.3 GB，快取由 4.3 GB 變 6.4 GB），事先未徵求同意；模型版本未變（snapshot 5617a9f…，與索引記錄相同）。這些檔案本專案用不到，刪除與否待使用者決定。
- 未驗證：AnythingLLM 畫面經 `--store pg` 的操作；README 修正後的 `--exclude` 指令未在無快取的環境實際下載（只用 dry-run 與檔案清單核對）。
- 結束階段：重現驗證完成；README 修正待提交。


### 2026-11-17 第六十三筆（版本：分支 docs/repro-verification，main a8b085f 加未提交變更；刪除多餘模型檔、說明頁與排版）

- 使用者試用：`serve --store pg` 經 AnythingLLM 回答一題中級試題（詞性標註），選出 D；但回覆說「教材未涵蓋」。原因：知識庫只有初級兩科，中級三份教材已下載、尚未納入。畫面上逐句回答與 [外部1] 標記全部併成一段。使用者在瀏覽器開 8100/v1 看到「找不到此路徑」，以為服務有問題。
- 使用者決定：刪除多下載的模型檔；修正一起提交、開 PR 並合併；同意資料夾結構調整並把中級教材納入知識庫（先不套用中級勘誤，再整理勘誤後重建）。
- 刪除：bge-m3 快照 5617a9f… 中今天由 `hf download` 新增、本專案用不到的檔案（onnx/、imgs/、long.jpg、colbert_linear.pt、sparse_linear.pt、.gitattributes），共 2.29 GB；刪前確認這些檔案都是今天寫入。快取回到 4.3 GB。
- 刪除後發現的問題：huggingface_hub 2.4.0 會依 `hf download` 記下的檔案清單（trees/5617a9f….json）檢查快照是否完整，缺檔就拒絕離線載入，連帶使 README 的 `--exclude` 做法對新使用者同樣會失敗。修正：knowledge.local_encoder 載入時傳入 ignore_patterns（EMBEDDING_IGNORE：onnx、openvino、圖片、*.pt、.gitattributes），與 README 的 `--exclude` 一致；README 補 `--exclude "*.pt"`。修正後以目前已刪檔的快取實際載入成功（revision 5617a9f…，與索引相同）。
- 排版：`render_text(markdown=True)` 每句與每個 ⚠ 各自成段（段間空一行），依據清單維持清單；CLI 的純文字輸出不變。
- 說明頁：瀏覽器開端點的 `/` 或 `/v1` 時回 200 與一頁簡短說明（這是 API 端點、請從聊天介面使用），不再回 404。
- 測試（本輪實跑）：Windows 120 passed、4 skipped（未設 PG_TEST_DSN）。新增測試：載入時忽略不需下載的檔案、Markdown 分段、說明頁。
- 未驗證：新的分段排版在 AnythingLLM 畫面的效果（需重啟 serve 後由使用者檢視）；`--exclude` 加上 ignore_patterns 在完全沒有快取的環境實際下載後載入（只以已刪檔的本機快取驗證）。
- 結束階段：審查與交付（使用者已同意提交、開 PR 並合併）；接著進行資料夾調整與中級教材納入。


### 2026-11-17 第六十四筆（版本：分支 chore/data-layout-intermediate，main 127f204 加未提交變更；資料夾精簡與中級教材納入）

- 交付：第六十三筆的修正提交為 9bdf371，開 [PR #14](https://github.com/Cheryl33990/ipas-learning-hub/pull/14)，PR CI pass，以 merge commit 合併為 127f204（2026-11-17T09:13:34Z）。
- 資料夾（使用者同意）：data/raw 改為 beginner／intermediate 下各分 guides、errata、exams，檔名用官方原名。先前被改過名的 4 份（初級兩份教材、初級勘誤表、115 年第三次第一科試題）比對官方檔大小一致後改回原名（兩份教材另有雜湊比對）。22 個檔案只移動不刪除；舊的空資料夾移除；data/raw/manifest.json 記 21 份官方檔的網址、大小、SHA-256，取代舊的下載清單。勘誤替換檔移到 data/index/errata/（beginner-subject1.json、beginner-subject2.json）。
- 程式與文件：config 兩份改新路徑並加入中級三科；explore2.py、explain.py 改為明確的檔案路徑（原本假設資料夾只有一份 PDF）；docs/internal/project/explanations/115-3-subject1.json 的科目 2 路徑；README 的下載步驟改為從設定檔讀官方檔名組網址（以 HEAD 確認五個網址皆 200），其餘舊路徑一併更新。`explain` 以新路徑重新產生解析，內容與原本相同。
- 頁首規則可設定（先寫測試）：設定檔的教材可加 running_head（正規表示式）。中級三科的頁首是「圖示字元＋第幾章＋章名」，原本會出現在每頁開頭、讓同章各頁都因章名被關鍵字命中；設定後移除。未設定的教材沿用原規則。設定檔以 `\uf07d` 跳脫表示圖示字元（工具曾把跳脫寫成實際字元，已改正並檢查 src、tests、config、docs 皆無實際圖示字元）。
- 中級勘誤（使用者同意由 AI 整理）：依官方勘誤表 1150410 整理 24 筆替換字串，存 data/index/errata/intermediate-subject1.json（19 筆）、intermediate-subject3.json（5 筆），每筆確認只命中指定頁。無法套用：三科「職能基準」頁（無頁尾頁碼、不進知識庫）、科目 1 的 3-80 標題（PDF 擷取不到）。官方更正文字的兩處錯字（「這這在許多行業」「事項：：」）未套用，於替換檔註明。中級科目 2 因此沒有可套用的勘誤，索引記 not_applied。替換字串是 AI 整理，未經人工逐條核對。
- 新索引 ce5090f4…（五科、含勘誤與 bge-m3 向量，建置 5.6 分鐘）：1,389 塊（初級 266、中級 1,123）；初級 266 塊與 a0ff519f… 的 id、文字、PDF 頁完全相同；中級片段開頭已無章名頁首；勘誤套用頁如上。已載入本機資料庫（1.7 秒），成為「最近載入且含向量」的索引。
- 測試（本輪實跑）：Windows 125 passed（連本機資料庫）。
- 中級題目實跑（固定亂數，三科各 2 題，共 6 題；`--store pg` 預設混合、開維基；輸出在 data/evaluation/intermediate-trial/）：5 題引用了中級教材（2 題只用教材、3 題教材＋維基），1 題依據不足；4 題選出官方答案、1 題選錯（第一科第 19 題選 C，官方 B）。耗時 8.4–12.7 秒。限制：6 題都剛好抽自 114 年第二梯次；各跑一次；理由正確性未判定。
- 對使用者環境：8100 的 serve 需重啟才會改用新索引（`--store pg` 未指定 --index 時取最近載入且含向量的索引，即 ce5090f4…）。
- 結束階段：實作完成、待使用者審查與同意提交。

### 2026-11-17 第六十五筆（接手 AI review：資料夾與中級教材）

- 起始階段：審查與交付；使用者詢問這批變更能否提交、開 PR、合併。檢查基底 127f204 加工作樹 13 檔 diff，非獨立真人批准。
- 修正 README：Windows PowerShell 讀中文 JSON 補 `-Encoding UTF8`，避免解碼錯誤；原兩科／兩份替換檔的操作說明更新為五科／四份替換檔。
- 本輪實跑（本機 .venv、受審工作樹）：`python -m pytest -q`：121 passed、4 skipped（未設 PG_TEST_DSN），另有 pytest cache 寫入警告。不視為本輪資料庫測試通過。
- 真實教材回歸：五份 PDF 的 SHA-256 與設定一致；依目前頁首、勘誤與切塊規則重算，比對頁碼、文字與 PDF 頁，1,389 片段均與 ce5090f4… 一致。各科片段數 143／123／376／339／408；替換數 6／1／19／0／5，每筆各只命中一頁。初級 266 個完整片段物件與 a0ff519f… 完全一致。未下載或重算向量、未寫資料庫。
- `python -m ipas_hub.explain` 通過 50 題檢查，生成 Markdown 與版控無內容差異；`git diff --check` 通過。檢視程式、設定、測試與文件 diff，未混入 data 原文或模型。
- 限制：本輪未重新呼叫 LLM、未驗證 8100／AnythingLLM 畫面、未人工複核勘誤語意；既有 6 題試跑只作歷史探索證據。gh auth status 回報本機登入無效，本輪未操作遠端。
- 結束階段／前進判斷：可提交並開 PR；新 PR 的 CI（含資料庫與容器）通過後，再依負責人決定合併。PR #14 的 CI 不當成本批結果。尚未提交、開 PR、合併、部署或驗收。回復方式為回復本批程式與設定並還原本機 PDF 路徑；舊索引仍保留，需相容路徑才能開啟教材。

### 2026-11-17 第六十六筆（提交、PR 與合併）

- 使用者明確要求「請幫我提交、開PR、合併」。起始為審查與交付，沿用前筆驗證及 AI review，程式未再修改。
- 提交 e9bdd9e4ffd6069af5ff87a06f3b9bf693af3347：13 檔、+162／−40。推送 chore/data-layout-intermediate，建立 Draft PR #15；重新產生的 Markdown 無內容差異，未納入提交。
- 本批 [CI run 44057346093](https://github.com/Cheryl33990/ipas-learning-hub/actions/runs/44057346093) success：125 passed（含 PostgreSQL／pgvector），Docker 121 passed、4 skipped（容器無測試資料庫）；Compose、原始資料未追蹤及 runtime 啟動檢查均通過。
- CI 通過後轉 ready，依使用者授權以 merge commit 合併；預期 head SHA 鎖定 e9bdd9e，GitHub 確認 merged，合併版本 c4bd89df3fb6ae341f1a0f18ca0b159c5510cdf7（2026-11-17 17:39 台北時間）。本機 main 已同步；PR 說明已更新 CI 與合併證據。
- 環境：沙箱內 .git 為唯讀，透過核准的提權命令完成 commit／push／fetch／快轉；Git 遠端與 GitHub connector 正常，前筆 gh auth status 不代表這兩條路徑不可用。
- 結束階段：本輪提交、PR、合併完成。未重啟 8100，未部署或進行新一輪品質驗收；下一步仍為重啟 serve 後試用中級題目及排版。本筆為合併後本機補記，尚未提交；雲端交付結果已寫入 PR #15。

### 2026-11-17 第六十七筆（新手交接與品質／速度證據盤點）

- 起始階段：探索與文件設計。使用者確認已看到資料庫向量；這是資料可檢視的確認，不推定為 RAG 品質或新手安裝驗收。目標為評估專案完整度、提供完全新手及 AI 架設文件、釐清混合搜尋證據。
- 變更前測法：以實際 compose、CLI、pgstore、knowledge 程式核對命令／欄位；比對歷史驗證來源、檢查新文件本機連結與 diff。純文件工作不新增應用測試或重跑 GPU 模型。
- 新文件：`docs/setup.md`（安裝、教材雜湊、無勘誤重現、模型／資料庫、搜尋、UI、每日啟停、DBeaver 與排錯）、`docs/internal/project/ai_setup.md`（操作任務與逐步證據；AGENTS 仍為唯一共同規則）、`docs/evaluation.md`（完整度、歷史數字、宣稱界線與暫定評估方案）。README 加入口並修正首頁「尚無介面／未納入中級」的過時說法。
- 判斷：目前具備自用／展示原型流程與 CI，不能宣稱新手獨立安裝、五科混合搜尋品質優勢或多人產品已驗收。歷史 14 題單次比較為混合 11／14、BM25 與向量各 10／14，均為舊初級索引、web none；差一題不證明穩定優勢。未把舊 211 ms 檢索中位數當現行五科完整回答速度。
- 限制：新手手冊中以 helper 容器下載生成模型到新 volume 為候選命令，未在乾淨環境執行；既有重現共用了 vLLM，不能冒充從零端到端。安裝工具／Hugging Face CLI／AnythingLLM 連線欄位參考官方文件，查閱日期 2026-11-17。新評估資料尚未選題或人工標註，方案未提升為已確認 AC。
- 本輪實際檢查：README 與三份新文件的相對連結均存在、程式碼圍欄成對；`git diff --check` 通過，`python -m ipas_hub.cli evaluate --help` 與評估文件參數一致。未跑新下載、索引、資料庫寫入、LLM 或新手畫面操作。
- 收尾：文件審查中，未提交、開 PR 或合併。下一步由新使用者照手冊實測，優先驗證從零模型準備與 UI 來回；品質工作先確認現行五科保留測試集與人工判準，再公平比較 BM25／向量／混合。保留前筆合併補記，之後隨同一批文件提交，無需單開補記 PR。

### 2026-11-17 第六十八筆（產品方向：通用教材與知識補強）

- 起始／結束階段：定義。使用者確認希望教材可自行擴充且不限 iPAS、教材不足時以模型知識或 web search 補強，並成為可供參考且有優秀產品呈現的完整 side project。方向主來源更新至 brief；形式、預設政策與驗收尚未確認。
- 現況核對：資料庫欄位與來源設定已有通用基礎，但 guide.parse_page 依章節頁碼辨識，無這種頁碼的頁面會略過，不能宣稱一般 PDF 已可直接使用。rag.answer 在完全沒有 evidence 時直接回報不足；現有 supported 輸出要求引用，模型知識補充需新契約與測試，不能只改文案。
- 候選順序：一般文字 PDF 匯入與 PDF 頁引用 → 三類來源的回答與不足補強 → 乾淨環境／AI 架設與非 iPAS 示範 → 混合搜尋及端到端品質證據 → 專案展示與產品整理。OCR、其他文件格式、外搜供應者與多人管理仍待定，不一次擴充。
- 本輪只修 brief／progress；依已讀程式核對限制，未改程式、測試、檢索排序、索引或歷史結果，未提交發布。完成條件為保存使用者方向、未知與候選下一步；不把方向確認視為重大架構或新 AC 已批准。

### 2026-11-17 第六十九筆（通用文件與隔離的第一批規劃）

- 使用者補充：不限教材，也包含內部文件與法條等文字型 PDF；測試需要分割，避免混在一起；同意上一輪順序並詢問下一步。起始定義、結束設計待展開，方向記 brief。
- 查核：pgstore.read_index／nearest 依 index_id 篩選，並非所有已存索引都一起搜；但未指定 index 時會選全域最近符合條件索引，新測試索引可能改變預設選擇。資料庫單元測試已有 UUID schema 隔離，但真實文件評估仍需獨立資料邊界與固定 index_id。
- 第一批候選測法：一般 PDF 無 iPAS 章節頁碼仍可引用；A／B 庫相似文字互不召回；新增 B 不影響已選 A；未知庫回報錯誤；既有 iPAS 解析結果保持；評估答案不進文件語料。庫名／索引版本關係與舊 CLI 相容策略待設計，未直接改 schema。
- 只更新 brief／progress 並檢查 diff；未搬文件、建向量、下載法規或執行外搜。掃描 PDF、複雜圖表、法條更新、跨組織權限不是本輪已交付能力。下一步先完成通用匯入與隔離設計，再按已確認邊界實作。

### 2026-11-17 第七十筆（勞基法官方 PDF、一般文件與知識庫隔離）

- 使用者指定官方 URL 並明確要求接續加入勞基法。開始階段為設計與測試規劃，先寫 design/document_knowledge_bases.md 再改程式；新工作分支 feat/document-knowledge-bases，基底 main c4bd89d，保留先前未提交文件。
- 官方來源：LawAll.aspx?PCode=N0030001；頁面實際 PDF 入口為 FilesType.aspx?DataId=N0030001&md=m。下載原檔 302,061 bytes、19 頁，頁面與 PDF 皆標示民國113年07月31日修正；SHA-256 153819d3816fa033cfe2dadf2b4d246a512ce74976fc0ee23aa8223d75a67b9d。原文與取得 manifest 僅在 data/raw/labor-law；設定 config/knowledge-base.labor-law.json 只記來源、版本與識別，不收原文。
- 實作：guide 的 parser=pdf 收一般非空文字頁、預設仍為 ipas；來源保存 parser／URL／取得日。knowledge_base 寫入 manifest，歷史缺欄位索引解讀為 ipas，不改原索引。CLI --kb 限定資料庫庫名或核對 file／明確 index；多庫省略範圍拒絕；混合方法仍優先選同庫含向量版本。沿用現有 JSON manifest 無新資料表。一般來源顯示文件標記、版本與 PDF 頁；內部 source_type 沿用既有 textbook 契約，不改生成 JSON。
- 本輪實跑：132 passed（本機 pg，含 7 個資料庫測試、CLI 分庫與相似文字向量隔離），0 skipped。最初 pytest 預設暫存目錄權限造成 14 setup errors；第一次改 basetemp 漏建父目錄仍失敗；補建 data/test-tmp 並使用新 UUID 目錄後發現 2 個 FakeKB 缺 knowledge_base，更新測試替身後通過；再新增 CLI 實際路由測試，最後 132 項全通過。未將中途失敗寫成通過。
- 真實索引：6f1226f8141db00bb31356bbb69991263284768b0be4ca0f2a1564f5d27abadb；bge-m3、51 塊、1,024 維，CPU 建置約 21–25 秒（只作本機觀察，不當服務速度指標）。已載入 pg；索引 code_sha256 與目前所有正式程式檔一致。四題開發管線題（工時／出勤紀錄／特休／服務證明書）Top-5 都含預期 PDF 頁7／8／10／5，回傳僅屬 labor-law。沒有建立或採用保留品質測試集，不能宣稱4/4為泛化準確率。
- iPAS 回歸：指定 ce5090f4… 資料庫／檔案對「詞性標註」BM25 結果一致，既有索引保留。新增 law 後未選庫呼叫會明確拒絕，不用全域最新。原8100、vLLM、UI未重啟或改設定。
- LLM／HTTP：沿用已運作的 qwen3-vl-8b-fp8、--web none，工時1題 supported、引用PDF第7頁、字詞警告0；法律正確性未人工驗收。臨時測試 HTTP 回答含文件標記與 #page 連結，PDF HTTP 內容與原始檔相同；測試伺服器已停止，未佔用8100或8101。AnythingLLM畫面／工作區設定未操作，labor_law_setup.md 提供8101獨立端點與工作區設定指引。
- 證據：data/evaluation/labor-law/{verify_pipeline.py,pipeline_cases.json,pipeline_report.json,answer.json}；測試題／答案不進索引或版控。新文件連結與 code fences 已檢查、git diff --check 通過。未跑本批 hosted CI 或 Docker build；本機測試不冒充它們。
- AI review：查實際程式 diff、既有相容、無原文版控、選庫限制與證據。限制為400字／步長300的頁內切塊可能斷開跨頁條文，尚無條號metadata／OCR／法規自動更新；邏輯庫隔離不等於多人權限隔離。結束為可審查與試用，未提交／PR／合併。下一步使用者依案例建立獨立工作區試用，並針對條文切塊及引用品質提出下一批改善；原 iPAS serve 下次重啟要加 --kb ipas。

### 2026-11-17 第七十一筆（直接啟動與AnythingLLM工作區接線）

- 使用者要求直接執行並提供AnythingLLM可點選測試連結。起始為操作驗證；確認3001與vLLM存活，但8100／8101原本都沒有服務。先啟動8101單庫供接線，後因目前AnythingLLM架構修訂方案。
- 讀目前容器endpoints/workspaces.js、models/workspace.js與chat.js：workspace可更新chatProvider／chatModel，Generic OpenAI base URL為全域。前筆指引「每工作區不同URL」在此版本不可用；沒有默默改全域讓iPAS換庫。補設計document_knowledge_bases.md、設定config/rag-routes.json與CLI serve --routes；server以請求model選明列callback、缺／未知model拒絕，檔案連結依模型加前綴。嵌入模型版本相同的庫共用encoder，版本／維度不同拒絕共享。
- 共用8100已啟動（本輪exec session 47229），model rag→ipas／ce5090f4…／web wikipedia，model labor-law→labor-law／6f1226f8…／web none；未修改舊索引，索引的code_sha仍是建索引時版本。本輪先前8101程序PID82668核對命令後停止，避免重複載入；vLLM／ui／db沿用保持運作。
- 實際工作區：沿用使用者已建立的「勞基法」（id2、slug d4b98ca9-b52c-45ef-8b48-fad9c0991f6a），經本機API設chatProvider=generic-openai、chatModel=labor-law、chatMode=chat。原rag工作區(id1)的provider／model／mode／prompt前後一致，未變全域設定或上傳文件。設定前備份僅存data/evaluation/labor-law/workspace_before.json，不建立新的API key。
- 驗證：138 passed（含本機pg；串流／非串流模型隔離、未知模型400、同名PDF隔離、路由設定驗證與外搜政策）。經AnythingLLM實際stream-chat兩題，出勤紀錄回答五年、引用PDF8頁；data/runs確認labor-law與web none。工時題引用PDF7頁但變形工時補充概括過度，未被字詞警告抓出，保留失敗內容，非法律品質驗收。檢索與回答範圍無iPAS混入。
- UI連結 http://localhost:3001/workspace/d4b98ca9-b52c-45ef-8b48-fad9c0991f6a HTTP200；共用/v1/models列rag與labor-law；法規PDF回傳位元組完全相同、iPAS PDF也可讀。Browser host unavailable、native Chrome最小化無法還原，重試後停止CUA；因此未目視畫面，不冒稱實際點選引用。API工作區往返與PDF端點已核對。
- 證據：data/evaluation/labor-law/{enable_workspace.py,check_enabled.py,workspace_enabled.json,workspace_verified.json,workspace_chat.sse,workspace_records_chat.sse}；正式操作文件labor_law_setup.md已修正。結束為使用者可點連結試用，本機服務保持執行；未提交／PR／合併或對外發布。後續以條文完整切塊與語意支持檢查處理實測內容缺陷，不因路由啟用而宣稱答案正確。

### 2026-11-17 第七十二筆（使用者試用確認與向量設定說明）

- 使用者回報勞基法工作區能回答自己的問題，問機器學習不提供回應並表示OK；記為當次使用者試用確認，不宣稱所有越界題均拒答或法律品質已驗收。
- 使用者截圖詢問向量計數0是否使用pgvector。核對compose：AnythingLLM內建VECTOR_DB=lancedb，文件未上傳到該工作區；Generic OpenAI呼叫自建8100，依model選庫，再由程式執行BM25＋pgvector向量檢索。工作區內建向量設定不控制自建RAG。
- 本輪唯讀SQL：ipas當前索引ce5090f4…有1,389個片段與1,389個向量；labor-law的6f1226f8…有51個片段與51個向量，皆1,024維。CLI預設k=5；兩種排名各取前20、RRF常數60。UI的4段／0.25門檻不是這些參數。
- 起始與結束階段：操作說明／試用證據補記。未改UI、檢索、模型、資料或服務；未提交發布。後續若要在畫面顯示實際索引狀態與調整自建RAG參數，需另設本專案狀態介面，不能以修改AnythingLLM向量設定冒充完成。

### 2026-11-17 第七十三筆（本批提交與合併授權、交付前收尾）

- 使用者明確表示本次進展可提交、開PR與merge；起始為審查與交付。範圍包括第六十七至七十二筆的文件、一般PDF與分庫功能、勞基法設定及工作區路由；一併納入第六十六筆既有合併補記，不另開文件PR。
- 受審分支feat/document-knowledge-bases、基底c4bd89d。重新閱讀實際程式／測試diff及新設定／文件，AI review結論可送審，無新阻擋問題；非獨立真人批准。頁內切塊與工時補充語意缺陷沿用，不把使用者此次試用確認提升為全面法律／品質驗收。
- 本輪實跑：`.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider --basetemp=<data/test-tmp/新UUID>`，設定本機PG_TEST_DSN，138 passed、0 skipped（3.55秒）。正式程式未因交付再修改；原始資料不進Git，git diff --check通過，CI將另檢查pg、Compose、容器與runtime。
- 交付程序：本筆隨功能一起commit／push，建立同一Draft PR，確認受審head CI成功後轉ready，以既有merge commit慣例合併；使用者已授權。最終commit、PR、CI run與merge SHA直接寫入GitHub該PR及本輪回覆，避免為合併後補記反覆開PR。
- 限制與回復：新手從零生成模型下載仍未完整實測、hosted CI不跑真實PDF或LLM、已知變形工時補充概括過度。若回復程式到舊版，要固定原iPAS index_id，舊版不理解新分庫路由；目前本機索引／PDF／工作區設定與服務保持，合併不自動重啟或公開上線。

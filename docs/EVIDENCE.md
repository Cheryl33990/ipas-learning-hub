<!--
title: 主張與證據對照
status: in-review
updated: 2026-11-18
-->

# 主張與證據對照

README 的每項主張，以及證明它的程式與測試。測試名稱都在 [tests/](../tests/)，可用 `uv run pytest -k <名稱>` 單獨執行。

## 一句話

一套不綁定領域的本機 RAG 管線（附 iPAS 範例）：回答的每句話都要引用本次實際檢索到的 PDF 片段，引用不存在就拒答，數字或術語對不上就警告，而且能追溯到是哪一版文件、哪一版索引。

## 資料可追溯

| 主張 | 證據 |
|---|---|
| 索引 ID 是內容雜湊；任何片段被改過就拒絕載入 | `knowledge.py`；`test_modified_index_is_rejected`、demo `tampered-index` |
| 建索引前核對 PDF 的 SHA-256；勘誤沒套上就失敗，沒有勘誤檔則明確記為未套用 | `test_build_records_patches_and_fails_if_patch_does_not_apply`、`test_source_without_errata_file_is_indexed_and_marked_not_applied` |
| 向量檔與索引記錄的維度、雜湊必須一致；查詢模型 revision 必須相同 | `test_vector_artifact_mismatch_and_missing_model_are_rejected` |
| 載入 PostgreSQL 後讀回的內容與檔案索引逐位元一致；資料列被改過或不完整就拒絕 | `pgstore.py`；`test_rows_rebuild_the_identical_index_and_vectors`、`test_tampered_or_partial_rows_are_rejected`、`test_db_rows_changed_after_loading_are_rejected`¹ |
| 引用顯示的是 PDF 實際頁序，即使有頁面沒有頁碼也不會錯位 | `test_read_pages_keeps_pdf_page_order_even_when_unlabelled_pages_are_skipped`、`test_generic_pdf_keeps_numbered_pages_without_ipas_footer` |
| `fetch` 只用 https 下載，雜湊不符就不留下檔案，也不覆寫既有內容不同的檔案 | `fetch.py`；`test_hash_mismatch_leaves_no_file`、`test_existing_file_with_other_content_is_never_overwritten`、`test_plain_http_and_missing_url_are_rejected`、`test_target_outside_data_is_rejected` |
| 輸出原文的路徑不能跳出 `data/`（原文不進版控） | `test_original_text_outputs_cannot_escape_data_directory`、`test_cli_search_persists_run_only_under_data` |

## 檢索

| 主張 | 證據 |
|---|---|
| 中文以字元二元組斷詞，英數字整詞，BM25 偏好罕見詞 | `text.py`、`bm25.py`；`test_tokenize_cjk_bigrams_and_lowercased_words`、`test_bm25_ranks_document_with_rare_query_term_first` |
| 混合檢索以 RRF 融合 BM25 與向量排名，不直接相加兩種分數 | `knowledge.py:KnowledgeBase.search`；`test_hybrid_retrieval_routes_to_matching_vector_and_lexical_source` |
| 分數為 0 的片段不回傳；切塊不跨頁 | `test_cross_subject_search_returns_correct_source_and_no_zero_score_hits`、`test_chunks_never_cross_pages_and_cover_whole_page` |
| 檔案索引與 pgvector 的向量排名相同 | `test_db_vector_ranking_matches_the_file_index`¹ |
| 索引沒有向量時，預設的混合檢索退回 BM25 並告知；明確指定向量則直接失敗 | `test_default_hybrid_falls_back_to_bm25_with_a_notice_when_index_has_no_vectors`、`test_explicit_vector_method_on_index_without_vectors_still_fails` |

## 生成與引用

| 主張 | 證據 |
|---|---|
| 沒有檢索到任何依據時不呼叫模型，直接回報依據不足 | `test_no_evidence_does_not_call_model`、demo `out-of-scope` |
| 模型引用不存在的片段時，退回修正一次；仍錯就拒絕顯示為有依據的回答 | `rag.py:answer`；`test_invented_or_missing_citations_are_rejected_after_one_repair`、`test_repair_feedback_names_the_bad_id_and_good_retry_is_accepted`、demo `repaired-citation`、`fabricated-citation` |
| 模型少寫片段序號時，只對應到唯一教材片段才由程式補全並記錄；同頁多段或外部來源不補 | `rag.py:complete_chunk_ids`；`test_citation_missing_chunk_index_is_completed_when_unique_and_recorded`、`test_ambiguous_citation_without_chunk_index_is_still_rejected`、`test_external_ids_are_not_completed` |
| 來源類型與標記由程式依片段資料決定，不採信模型自稱的來源 | `test_sources_are_labelled_by_program_not_by_model`、`test_ids_the_model_writes_inside_text_are_removed` |
| 句子中的數字、英文術語不在被引用片段中時標 ⚠；只是提示，不拒答 | `test_missing_english_term_is_flagged_but_not_rejected`、`test_low_chinese_overlap_is_flagged_and_uncited_segments_are_not_checked`、demo `mis-cited-sentence` |
| 開啟核對時，模型逐句判斷引用片段是否直接支持該句，不支持或部分支持標 ⚠，只標示不改寫回答；呼叫失敗或漏句標為未核對，不當作通過；未引用的句子不送核對；`ask`／`serve` 預設開啟，評估流程不使用 | `rag.py:verify_segments`；`test_unsupported_and_partial_verdicts_are_recorded_and_shown_but_answer_is_unchanged`、`test_failed_or_incomplete_verification_is_shown_as_unverified_not_as_passing`、`test_verifier_sees_only_cited_sentences_with_their_own_evidence`、`test_ask_turns_verification_on_from_args`；合成負例結果見 [評估](evaluation.md#模型逐句核對引用2026-11-18) |
| 題目沒有 (A)(B) 選項時，模型多寫的「答案：X」由程式移除並記錄在 `removed_choice`；選擇題保留答案 | `rag.py:drop_unasked_choice`；`test_choice_written_for_a_question_without_options_is_removed_and_recorded`、`test_choice_inside_a_sentence_is_stripped_but_the_sentence_is_kept`、`test_multiple_choice_question_keeps_its_answer` |
| 輸出明寫「字詞核對，非語意驗證」，不把結構檢查包裝成正確性保證 | `test_valid_response_is_labelled_as_structural_not_semantic_verification` |
| 題目與證據在 prompt 中標為資料而非指令（降低提示注入風險） | `test_prompt_marks_question_and_evidence_as_data` |
| 維基來源標示 CC BY-SA 4.0 與授權連結，並註明句子經模型改寫；只用教材時不出現 | `test_wikipedia_sources_carry_license_and_modification_notice`、`test_textbook_only_answer_has_no_wikipedia_notice` |
| 外部搜尋（維基百科）會固定版本、跳過消歧義頁；搜尋失敗時仍用教材回答並記錄錯誤 | `test_wikipedia_parses_variant_title_and_pins_revision`、`test_wikipedia_skips_disambiguation_and_unrelated_pages`、`test_ask_records_web_failure_and_still_answers_from_textbook` |

## 換領域

| 主張 | 證據 |
|---|---|
| 證據規則所有領域共用，助理角色與領域規則來自 profile；iPAS profile 組出的 prompt 與抽出前逐字相同（雜湊比對） | `profile.py`；`test_ipas_profile_reproduces_the_previous_prompt_exactly` |
| 未指定 profile 時使用通用設定，不含 iPAS 身份或考試規則 | `test_default_profile_has_no_exam_identity_but_keeps_the_evidence_contract`、`test_missing_profile_path_means_default` |
| profile 欄位不齊、多欄或空值會被拒；路徑不能跳出專案目錄 | `test_profile_with_bad_fields_is_rejected`、`test_profile_missing_a_field_is_rejected`、`test_profile_path_cannot_escape_root` |
| 實際送給模型的是 profile 組好的提示，且執行紀錄保存其雜湊 | `test_answer_sends_the_given_prompt_and_records_its_hash`、`test_demo_uses_the_ipas_profile` |

## 評估

| 主張 | 證據 |
|---|---|
| 保留題依設定讀取，試題檔 SHA-256 不符就拒絕，排除開發期間用過的題號 | `exam_eval.py`；`test_cases_skip_excluded_numbers_and_keep_official_answers`、`test_changed_exam_file_is_rejected` |
| 每題每方法一筆結果、可中斷續跑且不重跑，方法順序逐題輪換 | `test_batch_records_each_method_and_resumes_without_repeating`、`test_method_order_rotates_between_questions` |
| 彙總要求各方法題目一致，報答對／答錯／依據不足／錯誤、延遲 p50／p95 與成對 bootstrap 信賴區間；報告不含題目原文 | `test_summary_counts_outcomes_latency_and_paired_changes`、`test_summary_rejects_methods_with_different_questions`、`test_report_is_markdown_without_question_text` |

## 服務與邊界

| 主張 | 證據 |
|---|---|
| 服務預設只綁 127.0.0.1，提供 OpenAI 相容端點，可直接接 AnythingLLM；只有指定 `--host` 才改綁（Compose 的 serve 容器用 0.0.0.0，主機端埠號限制在 127.0.0.1） | `server.py`、`compose.yaml`；`test_http_server_binds_loopback_and_serves_models_chat_and_stream`、`test_server_binds_loopback_by_default_and_another_address_only_when_asked`、`test_serve_command_defaults_to_loopback_host` |
| 用 model 名稱路由到指定的知識庫與外搜政策；未設定的名稱一律拒絕 | `test_http_model_routing_streaming_unknown_models_and_scoped_files`、`test_invalid_routes_rejected_before_loading` |
| 資料庫查詢必須明確指定知識庫，向量查詢不會跨到其他索引 | `test_knowledge_bases_are_explicit_and_vector_queries_stay_in_the_selected_index`¹、`test_pg_cli_routes_explicit_knowledge_base_and_rejects_ambiguity`¹ |
| PDF 只提供白名單內、且與索引記錄版本相符的檔案 | `test_only_listed_files_are_served_read_only`、`test_served_files_must_match_the_indexed_version` |
| 模型失敗時顯示警告而非假裝成回答 | `test_failures_are_shown_as_a_warning_not_as_an_answer` |
| 預設只連本機 LLM；遠端端點必須明確開啟且使用 HTTPS | `llm.py`；`test_remote_endpoint_needs_explicit_opt_in_and_https`、`test_local_vllm_request_shape_and_no_key_by_default` |

¹ 需要 PostgreSQL＋pgvector。本機未設定 `PG_TEST_DSN` 時會略過；CI 以 pgvector service container 執行。

## 測試不證明什麼

- **回答品質**：測試使用合成資料與替身模型，證明的是流程如何處理各種狀況，不是答對率。品質證據與限制見 [評估](evaluation.md)。
- **語意正確**：引用存在且字詞重疊，不代表片段真的支持那句話。
- **多人服務**：知識庫路由不是使用者授權；沒有負載、並行或對外部署的驗收。

## 一分鐘驗證

只需要 Python 3.11+ 與 [uv](https://docs.astral.sh/uv/)，不需要 GPU、教材或資料庫：

```sh
uv sync --locked
uv run python -m ipas_hub.demo      # 以 iPAS 範例重播六種情境（自寫筆記＋腳本化模型）
uv run pytest                       # 全部測試；pg 測試在沒有資料庫時略過
```

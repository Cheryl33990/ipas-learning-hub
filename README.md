# iPAS Learning Hub — local RAG where every sentence traces back to a PDF page

English | [繁體中文](README.zh-TW.md)

A RAG pipeline that runs on your own machine: it retrieves evidence from PDFs, a local LLM answers sentence by sentence, every sentence carries a citation, and each citation opens the original PDF page. The pipeline is domain-agnostic; the bundled example is exam preparation for Taiwan's **iPAS AI Application Planner** certification. Switching to your own documents means changing configuration, not code.

The point is not "plug in a vector database". It is: **catch the model when it fabricates citations, know which document version an answer came from, and say "I don't know" when there is no evidence.**

> [docs/EVIDENCE.md](docs/EVIDENCE.md) lists each claim and the test that proves it.
>
> **Language note:** this README is in English. The detailed documents under [docs/](docs/README.md) (setup, architecture, evaluation, evidence) are in Traditional Chinese, as are the prompts, answers and program messages, because the source material is Chinese. Code identifiers, `.env.example` and CI are in English.

## What it looks like

![Asking a question in AnythingLLM; every sentence of the answer cites the course material, and clicking a citation opens the matching PDF page](docs/assets/demo.gif)

Local vLLM (Qwen3-VL-8B) + an index of the five iPAS study guides + the iPAS profile, asked in AnythingLLM "What is the difference between differential privacy and homomorphic encryption?" (in Chinese). Each sentence is tagged [教材N] ("course material N"), and clicking a citation opens page 172 of the official study guide PDF. The wait for generation is sped up 4×; actual generation took about 16 seconds. The guide pages appear only to demonstrate citation linking; the guides themselves are not in this repo.

## Why

These problems keep coming up when you use an LLM to study course material:

| Common problem | What this project does |
|---|---|
| The model cites a source that does not exist | A citation ID must belong to a chunk actually retrieved for this question; the model gets one repair attempt, and if it still fails the answer is refused rather than shown as grounded |
| A citation is attached, but it does not match the sentence | A second local-model pass checks, sentence by sentence, whether the cited chunk actually states the sentence and flags ⚠ when it does not (on synthetic mismatched citations it caught 67%, vs. 54% for the lexical check); a lexical check of numbers and terms runs as well. Both are labelled as checks, not fact-checking |
| The model answers anyway when nothing relevant is found | If retrieval finds nothing, the model is not called; the answer reports insufficient evidence |
| After a revision or erratum, nobody knows which version an answer used | The PDF's SHA-256, errata and embedding revision are recorded; index IDs are content hashes, and a tampered index is refused at load time |
| Every new domain means rewriting prompts and code | Shared evidence rules are fixed; the assistant role and domain rules live in a profile file |
| "A vector database must be more accurate" | BM25 stays as the baseline and vector results are fused with RRF. On 243 held-out questions, hybrid scored 5.3 percentage points higher than BM25; vector alone vs. BM25 has a confidence interval that includes 0, so it cannot be called better |

## One-minute tour

All you need is Python 3.11+ and [uv](https://docs.astral.sh/uv/) — no GPU, course material, database or network:

```sh
uv sync --locked
uv run python -m ipas_hub.demo      # replay six scenarios with the iPAS example
uv run pytest                       # run all tests
```

The demo uses iPAS topic notes written by the author (not the official material), the iPAS profile, and a stand-in model that replies from a script. Everything else is the real code: index integrity check, BM25 retrieval, citation check and repair, lexical check, and output formatting. Below is the actual output of the multiple-choice scenario (the output is in Chinese; the question asks which option is a typical supervised-learning task: (A) clustering, (B) dimensionality reduction, (C) classification, (D) association rule mining):

```text
━━ grounded-answer ━━ 選擇題逐項說明並引用檢索到的頁面，最後給出答案
問題：下列何者屬於監督式學習的常見任務？(A) 分群 (B) 降維 (C) 分類 (D) 關聯規則探勘
檢索（BM25，前 3）：
  #1 notes:1-1:0　監督式學習：訓練資料附有標籤（正確答案），模型學習從…
  #2 notes:3-1:0　過擬合：模型在訓練資料上表現很好，在新資料上表現變差…
模型呼叫：1 次（腳本化替身）

狀態：有依據（只用教材）

(A) 分群是非監督式學習的常見任務。 [教材1]
(B) 降維也是非監督式學習的常見任務。 [教材1]
(C) 分類使用附有標籤的資料，屬於監督式學習。 [教材1]
(D) 關聯規則探勘不需要標籤，片段未提及，此為推論。
答案：C

依據：
- [教材1] 教材 iPAS 主題自寫筆記（示範用） 1-1
```

| Scenario | What happens | Result |
|---|---|---|
| `grounded-answer` | Each option of a multiple-choice question cites a page that was actually retrieved | Grounded, ending with "答案：C" (Answer: C) |
| `repaired-citation` | The first reply cites a chunk that does not exist | Passes after one repair; the repair count is recorded |
| `fabricated-citation` | The reply still fabricates a citation after repair | Refused; not shown as a grounded answer |
| `mis-cited-sentence` | The citation exists, but a term in the sentence is not in the chunk | Answer kept, sentence flagged with ⚠ |
| `out-of-scope` | The notes contain nothing relevant | Model not called; insufficient evidence reported |
| `tampered-index` | An index chunk has been modified | Hash mismatch; index refused |

## Architecture

```mermaid
flowchart LR
    PDF[PDF + source config] --> Index[Parse / chunk / versioned index]
    Index --> Search[BM25 + vector + RRF]
    UI[CLI / AnythingLLM] --> Route[Knowledge-base routing]
    Route --> Search
    Profile[Domain profile] --> LLM
    Search --> LLM[Local vLLM]
    Web[Optional Wikipedia] --> LLM
    LLM --> Answer[Citation check + answer + PDF links]
```

The file index can be used on its own or loaded into PostgreSQL + pgvector: the database handles vector distance queries, while BM25 and fusion run in Python. AnythingLLM is only the chat UI; no documents are uploaded to it. Module locations, data flow and design trade-offs are in the [architecture doc](docs/architecture.md) (Chinese).

**What I wrote myself:** document parsing and errata, the versioned index, retrieval fusion, citation checking, domain profiles, the OpenAI-compatible endpoint and knowledge-base routing. The chat UI (AnythingLLM), model server (vLLM), embedding model (BGE-M3) and generation model (Qwen3) are third-party work.

## The example and your own data

| Goal | Requires | Doc (Chinese) |
|---|---|---|
| See which files make up the iPAS example and how to run it | — | [examples/ipas](examples/ipas/README.md) |
| Set up all five iPAS subjects + hybrid retrieval + chat UI | NVIDIA GPU, Docker | [Full Windows setup](docs/setup.md); environment variables in [.env.example](.env.example) |
| Use your own PDFs and domain settings | Retrieval needs only a CPU | [Using your own data](docs/custom-data.md) |

Switching data means changing only three things: the **source config** (paths, versions, SHA-256, optional download URLs), the **profile** (assistant role, document names, domain rules), and optionally the **routing** (which knowledge base each chat-UI model name maps to).

The author's setup: Ryzen 7 9800X3D, 32 GiB RAM, RTX 5070 Ti 16 GB, Windows 11 + Docker Desktop; the BAAI/bge-m3 embedding model runs on CPU and Qwen3-VL-8B-Instruct-FP8 runs on the GPU through vLLM. This is **not** a minimum requirement; see [runtime environment](docs/environment.md).

## Course material, models and external content

| Material | What is in the repo | How to get it |
|---|---|---|
| iPAS study guides | Only the official URLs and SHA-256 hashes | `cli fetch` downloads them from the official site and verifies the hash; PDFs, chunk text and indexes are never committed |
| Example notes | Full text, written by the author | Shipped with the repo under MIT, like the code |
| Embedding and generation models | Only model names and pinned revisions | Download them yourself from Hugging Face; no weights are included |
| Wikipedia supplements | Nothing | Queried at run time; citations show CC BY-SA 4.0, a link to the article revision, and a note that the model paraphrased it |

Licenses and sources for each item are in [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).

## Evaluation and limitations

Using 243 official iPAS exam questions that were never used during development (5 exam papers covering all five subjects), full question answering was scored automatically against the official answer key:

| Retrieval | Accuracy | Insufficient evidence (refused) | Retrieval p50 | End-to-end generation p50 |
|---|---|---|---|---|
| BM25 | 81.9% | 37 | 21 ms | 6.8 s |
| Vector | 84.0% | 24 | 245 ms | 7.1 s |
| Hybrid (default) | **87.2%** | 22 | 242 ms | 7.1 s |

Hybrid is 5.3 percentage points above BM25, with a paired per-question bootstrap 95% confidence interval of +1.7 to +9.0; the interval for vector vs. BM25 includes 0. A question-parsing bug was found afterwards (5 questions had been merged into the previous one, and question-group context was attached to the wrong question); after fixing it and rerunning the 23 affected questions, the total is 248 questions: hybrid 87.9%, vector 83.5%, BM25 82.3%, with hybrid 5.6 points above BM25 (+2.4 to +9.7). This compares chosen options only. Separately, 20 questions were randomly sampled from those hybrid answered correctly and reviewed by hand: the reasoning was correct in 20, and the citations fully supported the answer in 18 and partially in 2 (they cited a page on a related topic that did not directly state the sentence). The sample is small, it was reviewed by the author, and it uses a single model and a single run. Questions, criteria, failure analysis and how to rerun are in the [evaluation doc](docs/evaluation.md#保留題評估2026-11-18) (Chinese).

Current limitations: only PDFs with extractable text (no OCR or chart understanding); answer quality outside the iPAS domain must be verified with your own questions; chat is single-turn, and SSE sends only after generation finishes; separate knowledge bases are not multi-user access control. Current status and next steps are in [STATUS](docs/STATUS.md) (Chinese).

## Design principles

- **Traceability over convenience:** every answer must lead back to which document, which version, which page.
- **Say "I don't know" when you don't:** with no evidence, refuse rather than fill the gap with the model's general knowledge.
- **Checks are enforced by code:** citation validity is verified by the program, not by a "please cite your sources" line in the prompt.
- **A domain is configuration, not code:** evidence rules are shared across domains; domain differences live only in the profile.
- **Baseline first, then improvements:** BM25 is the control; hybrid retrieval has to prove with data that its extra latency is worth it.
- **Be honest about what a check covers:** a lexical check is called a lexical check, not fact-checking.
- **Don't redistribute other people's content:** course material is recorded only as URLs and hashes, model weights are not bundled, and external content is labeled with its license.

## Repository layout

```text
src/ipas_hub/       Generic pipeline: retrieval, RAG, profiles, fetch, CLI, chat server and offline demo
examples/ipas/      iPAS example: source config, profile, author-written demo notes, eval sets
config/             Knowledge-base routing for the chat endpoint
tests/              Unit tests on synthetic data, HTTP routing tests, optional pgvector integration tests
docs/               Architecture, environment, setup, custom data, evaluation, evidence map and status (Chinese)
docs/internal/      Development history, past validation and AI-collaboration records (not required reading, Chinese)
```

## Verification and data safety

- `uv run pytest` runs all tests; tests that need a database are skipped when `PG_TEST_DSN` is not set.
- GitHub Actions runs on every PR: `ruff check` and `ruff format --check`, pgvector integration tests, the offline demo, a check that `data/` is not tracked, in-container tests, and building and smoke-starting the runtime image.
- Tests use only synthetic data and stand-in models: they prove pipeline behavior, not answer quality.
- What must never be committed, and where runtime data goes, is described in [SECURITY.md](SECURITY.md) (Chinese).

## License

The code and the author's own content in this repo (including the example notes and documentation) are under [MIT](LICENSE). MIT does not cover third-party content: course material, models and Wikipedia content each follow their own terms; see "Course material, models and external content" above and [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES.md).

This is an independent learning project and does not represent the official position of the iPAS organizers or any third-party tool.

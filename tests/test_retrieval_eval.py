import json

import pytest

from ipas_hub.retrieval_eval import QueryEncoder, load_cases, score_hits, summarize, validate_plan


@pytest.mark.parametrize("size,stride", [(200, 150), (400, 400), (400, 300), (800, 600)])
def test_experiment_windows_cover_each_page_without_crossing(size, stride):
    from ipas_hub.guide import Page, chunk_pages

    pages = [Page("1", "A" * 1053, 3), Page("2", "B" * 103, 4)]
    chunks = chunk_pages(pages, size, stride)
    for page in pages:
        own = [c for c in chunks if c.label == page.label]
        assert own[0].index == 0 and len(own[-1].text) > 0
        covered = set()
        for c in own:
            start = c.index * stride
            assert c.text == page.text[start : start + size]
            assert c.pdf_page == page.pdf_page
            covered.update(range(start, start + len(c.text)))
        assert covered == set(range(len(page.text)))


def hit(page, text="text", source="s"):
    return {"source": source, "page": page, "text": text}


def case(expected=None):
    return {"id": "q", "query": "question", "expected": expected or [{"source": "s", "page": "1"}]}


def test_duplicate_chunks_do_not_inflate_page_recall_or_remove_rank_cost():
    result = score_hits(
        case([{"source": "s", "page": "2"}, {"source": "s", "page": "3"}]), [hit("1"), hit("1"), hit("2")], 3
    )
    assert result["hit"] == 1
    assert result["page_recall"] == 0.5
    assert result["reciprocal_rank"] == pytest.approx(1 / 3)
    assert result["duplicate_page_fraction"] == pytest.approx(1 / 3)
    assert result["context_chars"] == 12


def test_source_identity_matters_and_k_is_chunk_budget():
    result = score_hits(case(), [hit("1", source="other"), hit("1")], 1)
    assert result["hit"] == result["page_recall"] == result["reciprocal_rank"] == 0


def test_no_answer_queries_are_excluded_from_recall_not_scored_as_perfect():
    negative = {"id": "n", "query": "none", "expected": []}
    a = score_hits(negative, [hit("1")], 5)
    b = score_hits(case(), [hit("1")], 5)
    assert a["page_recall"] is None and a["returned_any"]
    summary = summarize([a, b])
    assert summary["answerable_cases"] == 1 and summary["unanswerable_cases"] == 1
    assert summary["page_recall"] == 1
    assert summary["unanswerable_returned_any_rate"] == 1


def test_unknown_labels_are_not_silently_treated_as_no_answer(tmp_path):
    p = tmp_path / "cases.json"
    p.write_text(
        json.dumps({"split": "development", "label_status": "ai-provisional", "cases": [{"id": "q", "query": "x"}]})
    )
    with pytest.raises(ValueError, match="expected"):
        load_cases(p)


def test_duplicate_case_ids_and_reference_pages_are_rejected(tmp_path):
    p = tmp_path / "cases.json"
    for cases in ([case(), case()], [case([{"source": "s", "page": "1"}] * 2)]):
        p.write_text(json.dumps({"split": "development", "label_status": "ai-provisional", "cases": cases}))
        with pytest.raises(ValueError):
            load_cases(p)


def test_only_explicitly_reviewed_labels_can_be_called_test_data(tmp_path):
    p = tmp_path / "cases.json"
    p.write_text(json.dumps({"split": "test", "label_status": "ai-provisional", "cases": [case()]}))
    with pytest.raises(ValueError, match="review"):
        load_cases(p)


def test_query_adapter_applies_prefix_without_changing_normalization():
    class Encoder:
        def encode(self, texts, **kwargs):
            assert texts == ["query: question"]
            assert kwargs["normalize_embeddings"] is True
            return [[1.0, 0.0]]

    assert QueryEncoder(Encoder(), "query: ").encode(["question"], normalize_embeddings=True) == [[1.0, 0.0]]


def test_plan_rejects_invalid_overlap_and_incorrect_e5_prefix():
    plan = {
        "chunks": [{"id": "baseline", "size": 400, "stride": 300}],
        "models": [
            {
                "id": "e5",
                "name": "intfloat/multilingual-e5-small",
                "revision": "a" * 40,
                "query_prefix": "",
                "document_prefix": "",
            }
        ],
        "ks": [1, 3, 5],
        "repeats": 3,
    }
    with pytest.raises(ValueError, match="prefix"):
        validate_plan(plan)
    plan["models"][0].update(query_prefix="query: ", document_prefix="passage: ")
    validate_plan(plan)
    plan["chunks"][0]["stride"] = 401
    with pytest.raises(ValueError, match="stride"):
        validate_plan(plan)


def setup_runner(tmp_path, monkeypatch, budgets=None, evidence=None):
    import sys
    import types

    import numpy as np

    from ipas_hub import knowledge, retrieval_eval
    from ipas_hub.guide import Page

    (tmp_path / "data").mkdir()
    pdf = tmp_path / "data/source.pdf"
    pdf.write_bytes(b"synthetic PDF; reader replaced")
    (tmp_path / "uv.lock").write_text("test-lock")
    config = {
        "schema_version": 1,
        "chunk_size": 400,
        "chunk_stride": 300,
        "sources": [
            {
                "id": "s",
                "name": "Synthetic source",
                "version": "v1",
                "pdf": "data/source.pdf",
                "sha256": knowledge.digest(pdf.read_bytes()),
            }
        ],
    }
    (tmp_path / "source.json").write_text(json.dumps(config))
    monkeypatch.setattr(knowledge, "read_pages", lambda *a, **kw: [Page("1", "alpha", 1), Page("2", "beta", 2)])
    encoded = []

    class Encoder:
        max_seq_length = 512

        def __init__(self, *a, **kw):
            assert kw == {"device": "cpu", "local_files_only": True}

        def tokenizer(self, texts, **kwargs):
            assert kwargs == {"truncation": False, "padding": False}
            return {"input_ids": [[1] * len(t) for t in texts]}

        def encode(self, texts, **kwargs):
            assert kwargs["normalize_embeddings"]
            encoded.extend(texts)
            return np.asarray([[1.0, 0.0] if "alpha" in t else [0.0, 1.0] for t in texts])

    def snapshot(name, **kwargs):
        assert kwargs["local_files_only"] is True and kwargs["revision"] == "a" * 40
        return "fake-snapshot"

    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(snapshot_download=snapshot))
    monkeypatch.setitem(sys.modules, "sentence_transformers", types.SimpleNamespace(SentenceTransformer=Encoder))
    monkeypatch.setitem(sys.modules, "torch", types.SimpleNamespace(set_num_threads=lambda n: None))
    monkeypatch.setattr(retrieval_eval, "version", lambda name: "test-version")
    plan = {
        "source_config": "source.json",
        "chunks": [{"id": "c", "size": 400, "stride": 300}],
        "models": [
            {
                "id": "m",
                "name": "synthetic/model",
                "revision": "a" * 40,
                "query_prefix": "query: ",
                "document_prefix": "passage: ",
            }
        ],
        "ks": [1, 3],
        "repeats": 2,
        **({"budgets": budgets} if budgets else {}),
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan))
    cases_path = tmp_path / "data/cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "split": "development",
                "label_status": "ai-provisional",
                "cases": [{**case(), "query": "alpha", **({"evidence": evidence} if evidence else {})}],
            }
        )
    )
    return retrieval_eval, config, plan_path, cases_path, encoded


def test_full_runner_records_real_inputs_resumes_and_refuses_changed_cases(tmp_path, monkeypatch):
    retrieval_eval, config, plan_path, cases_path, encoded = setup_runner(tmp_path, monkeypatch)
    out = tmp_path / "data/out"
    retrieval_eval.run(tmp_path, plan_path, cases_path, out)
    result = json.loads((out / "c/m-hybrid.json").read_text())
    assert result["summary"]["1"]["hit"] == 1 and result["rankings_stable"]
    assert result["vector_bytes"] == 16 and result["retrieval_ms"]["samples"] == 2
    assert "passage: alpha" in encoded and "query: alpha" in encoded
    assert "Completed cells: 3/3" in (out / "report.md").read_text()
    assert json.loads((tmp_path / "source.json").read_text()) == config
    count = len(encoded)
    retrieval_eval.run(tmp_path, plan_path, cases_path, out)
    assert len(encoded) == count
    cases_path.write_text(cases_path.read_text() + "\n")
    with pytest.raises(ValueError, match="inputs changed"):
        retrieval_eval.run(tmp_path, plan_path, cases_path, out)
    cases_path.write_text(cases_path.read_text()[:-1])
    retrieval_eval.run(tmp_path, plan_path, cases_path, out)
    monkeypatch.setattr(retrieval_eval, "version", lambda name: "other-version")
    with pytest.raises(ValueError, match="inputs changed"):
        retrieval_eval.run(tmp_path, plan_path, cases_path, out)


def test_reused_vectors_skip_document_encoding_only_after_identity_checks(tmp_path, monkeypatch):
    import numpy as np

    retrieval_eval, _, plan_path, cases_path, encoded = setup_runner(tmp_path, monkeypatch, budgets=[4, 9])
    first = tmp_path / "data/first"
    retrieval_eval.run(tmp_path, plan_path, cases_path, first)
    encoded.clear()
    second = tmp_path / "data/second"
    retrieval_eval.run(tmp_path, plan_path, cases_path, second, reuse_vectors=first)
    assert not any(t.startswith("passage: ") for t in encoded) and "query: alpha" in encoded
    result = json.loads((second / "c/m-vector.json").read_text())
    assert result["vectors_reused_from"]["sha256"] == result["vector_sha256"]
    assert result["document_embedding_ms"] is None
    assert result["rankings"]["q"][0] == "s:1:0" and len(result["rankings"]["q"]) == 2
    assert set(result["budget_summary"]) == {"4", "9"}
    assert result["budget_summary"]["4"]["cases"] == 1
    vectors = np.load(first / "c/m-vectors.npy")
    np.save(first / "c/m-vectors.npy", vectors[::-1].copy())
    with pytest.raises(ValueError, match="reused vectors"):
        retrieval_eval.run(tmp_path, plan_path, cases_path, tmp_path / "data/third", reuse_vectors=first)


def evidence_case(requirements):
    return {"id": "q", "query": "question", "expected": [{"source": "s", "page": "1"}], "evidence": requirements}


def alt(quote, judgment="direct", page="1"):
    return {"source": "s", "page": page, "quote": quote, "judgment": judgment}


def chunk(index, text, page="1", stride=4):
    return {"id": f"s:{page}:{index}", "source": "s", "page": page, "text": text}


PAGE = {("s", "1"): "abcdefghij"}


def test_same_page_hit_without_the_supporting_span_is_not_evidence():
    from ipas_hub.retrieval_eval import locate_evidence, score_evidence

    c = evidence_case([{"id": "r", "claim": "x", "alternatives": [alt("ghi")]}])
    spans = locate_evidence(c, PAGE)
    page_only = score_evidence(c, spans, [chunk(0, "abcdef")], stride=4)
    assert score_hits(c, [chunk(0, "abcdef")], 1)["hit"] == 1
    assert page_only["complete"] == 0 and page_only["requirement_recall"] == 0


def test_span_split_across_chunks_is_complete_but_not_intact():
    from ipas_hub.retrieval_eval import locate_evidence, score_evidence

    c = evidence_case([{"id": "r", "claim": "x", "alternatives": [alt("defg")]}])
    spans = locate_evidence(c, PAGE)
    split = [chunk(0, "abcdef", stride=4), chunk(1, "efghij", stride=4)]
    both = score_evidence(c, spans, split, stride=4)
    assert both["complete"] == 1 and both["intact"] == 0
    assert both["first_complete_rank"] == 2
    one = score_evidence(c, spans, [chunk(0, "abcdefgh", stride=4)], stride=4)
    assert one["complete"] == one["intact"] == 1


def test_required_claims_must_all_be_met_but_alternatives_are_interchangeable():
    from ipas_hub.retrieval_eval import locate_evidence, score_evidence

    pages = {("s", "1"): "abcdefghij", ("s", "2"): "klmnopqrst"}
    c = evidence_case(
        [
            {"id": "r1", "claim": "x", "alternatives": [alt("abc"), alt("klm", page="2")]},
            {"id": "r2", "claim": "y", "alternatives": [alt("rst", page="2")]},
        ]
    )
    spans = locate_evidence(c, pages)
    first = score_evidence(c, spans, [chunk(0, "klmnop", page="2")], stride=4)
    assert first["requirement_recall"] == 0.5 and first["complete"] == 0
    full = score_evidence(c, spans, [chunk(0, "klmnop", page="2"), chunk(1, "opqrst", page="2")], stride=4)
    assert full["complete"] == 1 and full["reciprocal_rank"] == 0.5


def test_partial_evidence_is_kept_for_review_but_not_counted():
    from ipas_hub.retrieval_eval import locate_evidence, score_evidence

    c = evidence_case([{"id": "r", "claim": "x", "alternatives": [alt("abc", judgment="partial"), alt("hij")]}])
    result = score_evidence(c, locate_evidence(c, PAGE), [chunk(0, "abcdef")], stride=4)
    assert result["complete"] == 0


def test_evidence_labels_are_validated(tmp_path):
    p = tmp_path / "cases.json"
    bad = [
        [{"id": "r", "claim": "x", "alternatives": [alt("abc", judgment="partial")]}],
        [{"id": "r", "claim": "x", "alternatives": [alt("abc", judgment="maybe")]}],
        [{"id": "r", "claim": "x", "alternatives": [alt("")]}],
        [],
    ]
    for requirements in bad:
        p.write_text(
            json.dumps(
                {"split": "development", "label_status": "ai-provisional", "cases": [evidence_case(requirements)]}
            )
        )
        with pytest.raises(ValueError):
            load_cases(p)


def test_quotes_must_exist_in_the_parsed_corpus():
    from ipas_hub.retrieval_eval import locate_evidence

    c = evidence_case([{"id": "r", "claim": "x", "alternatives": [alt("zzz")]}])
    with pytest.raises(ValueError, match="quote"):
        locate_evidence(c, PAGE)


def test_context_budget_gives_large_chunks_fewer_slots():
    from ipas_hub.retrieval_eval import budget_prefix

    small = [hit("1", "a" * 200) for _ in range(20)]
    large = [hit("1", "a" * 800) for _ in range(20)]
    assert len(budget_prefix(small, 1600)) == 8
    assert len(budget_prefix(large, 1600)) == 2
    assert budget_prefix(large, 500) == []


def test_report_refuses_results_from_another_experiment(tmp_path):
    from ipas_hub.retrieval_eval import report

    (tmp_path / "c").mkdir()
    (tmp_path / "meta.json").write_text(json.dumps({"signature": "one"}))
    (tmp_path / "c/vector.json").write_text(json.dumps({"signature": "two", "summary": {}}))
    with pytest.raises(ValueError, match="mixed"):
        report(tmp_path)


def test_runner_scores_evidence_against_rebuilt_page_text(tmp_path, monkeypatch):
    requirement = {"id": "r", "claim": "alpha is defined", "alternatives": [alt("lph")]}
    retrieval_eval, _, plan_path, cases_path, _ = setup_runner(tmp_path, monkeypatch, [5], [requirement])
    out = tmp_path / "data/out"
    retrieval_eval.run(tmp_path, plan_path, cases_path, out)
    result = json.loads((out / "c/bm25.json").read_text())
    assert result["summary"]["1"]["evidence_complete"] == 1
    assert result["budget_summary"]["5"]["evidence_intact"] == 1
    assert "Evidence:" in (out / "report.md").read_text()
    requirement["alternatives"][0]["quote"] = "not in page"
    cases_path.write_text(
        json.dumps(
            {"split": "development", "label_status": "ai-provisional", "cases": [{**case(), "evidence": [requirement]}]}
        )
    )
    with pytest.raises(ValueError, match="quote"):
        retrieval_eval.run(tmp_path, plan_path, cases_path, tmp_path / "data/other")

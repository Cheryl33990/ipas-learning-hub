"""保留題評估：讀試題設定、可續跑的批次、彙總與報告。只用合成資料與替身。"""

import hashlib
import json

import pytest

from ipas_hub import exam_eval
from ipas_hub.exam import Question


def manifest(tmp_path, exclude=()):
    pdf = tmp_path / "data/raw/exam.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"synthetic exam")
    path = tmp_path / "heldout.json"
    path.write_text(
        json.dumps(
            {
                "name": "t",
                "sources": [
                    {
                        "id": "p1",
                        "name": "合成試題",
                        "pdf": "data/raw/exam.pdf",
                        "sha256": hashlib.sha256(b"synthetic exam").hexdigest(),
                        "expected_source": "subject1",
                        "exclude": list(exclude),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


QUESTIONS = [
    Question(1, "A", "題一 (A) 甲 (B) 乙"),
    Question(2, "B", "題二 (A) 甲 (B) 乙"),
    Question(3, "C", "題三 (A) 甲 (B) 乙 (C) 丙"),
]


def test_cases_skip_excluded_numbers_and_keep_official_answers(tmp_path, monkeypatch):
    monkeypatch.setattr(exam_eval, "read_questions", lambda _: QUESTIONS)
    cases = exam_eval.load_cases(tmp_path, manifest(tmp_path, exclude=[2]))
    assert [(c["id"], c["official"], c["expected_source"]) for c in cases] == [
        ("p1-01", "A", "subject1"),
        ("p1-03", "C", "subject1"),
    ]


def test_changed_exam_file_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(exam_eval, "read_questions", lambda _: QUESTIONS)
    path = manifest(tmp_path)
    (tmp_path / "data/raw/exam.pdf").write_bytes(b"other")
    with pytest.raises(ValueError, match="SHA-256"):
        exam_eval.load_cases(tmp_path, path)


class FakeKB:
    index_id = "idx"

    def search(self, query, k, method):
        source = "subject1" if method != "vector" else "subject2"
        return [{"id": f"{source}:1-1:0", "source": source, "page": "1-1", "pdf_page": 3, "text": "t"}]


def fake_ask(choices):
    def ask(question, hits):
        method = hits[0]["source"]
        choice = choices.get((question[:2], method))
        if choice == "error":
            raise ValueError("模型引用不存在")
        return {
            "status": "supported" if choice else "insufficient",
            "answer_choice": choice,
            "flagged_segments": 0,
            "repair_attempts": 0,
            "removed_choice": None,
            "citations": ["x"] if choice else [],
            "llm_elapsed_ms": 100.0,
        }

    return ask


CASES = [
    {"id": f"p1-0{n}", "paper": "p1", "number": n, "official": a, "question": f"題{t}", "expected_source": "subject1"}
    for n, a, t in [(1, "A", "一"), (2, "B", "二")]
]


def test_batch_records_each_method_and_resumes_without_repeating(tmp_path):
    out = tmp_path / "rows.jsonl"
    ask = fake_ask({("題一", "subject1"): "A", ("題一", "subject2"): "B", ("題二", "subject1"): "error"})
    rows = exam_eval.run_batch(CASES, FakeKB(), ["bm25", "vector", "hybrid"], ask, out)
    assert len(rows) == 6 and len(out.read_text(encoding="utf-8").splitlines()) == 6
    by = {(r["case"], r["method"]): r for r in rows}
    assert by[("p1-01", "bm25")]["outcome"] == "correct" and by[("p1-01", "vector")]["outcome"] == "wrong"
    assert by[("p1-02", "bm25")]["outcome"] == "error" and "引用不存在" in by[("p1-02", "bm25")]["error"]
    assert by[("p1-02", "vector")]["outcome"] == "insufficient"
    assert by[("p1-01", "vector")]["same_subject_top5"] is False

    def unexpected(question, hits):
        raise AssertionError("已完成的題目不應重跑")

    assert len(exam_eval.run_batch(CASES, FakeKB(), ["bm25", "vector", "hybrid"], unexpected, out)) == 6


def test_method_order_rotates_between_questions(tmp_path):
    seen = []

    def ask(question, hits):
        seen.append(hits[0]["source"])
        return {
            "status": "insufficient",
            "answer_choice": None,
            "flagged_segments": 0,
            "repair_attempts": 0,
            "removed_choice": None,
            "citations": [],
            "llm_elapsed_ms": 1.0,
        }

    exam_eval.run_batch(CASES, FakeKB(), ["bm25", "vector"], ask, tmp_path / "rows.jsonl")
    assert seen == ["subject1", "subject2", "subject2", "subject1"]


def row(case, method, outcome, paper="p1", retrieval=1.0, llm=100.0):
    return {
        "case": case,
        "paper": paper,
        "method": method,
        "outcome": outcome,
        "same_subject_top5": True,
        "retrieval_ms": retrieval,
        "llm_ms": llm,
    }


def test_summary_counts_outcomes_latency_and_paired_changes():
    rows = [
        row("q1", "bm25", "correct"),
        row("q1", "hybrid", "correct"),
        row("q2", "bm25", "wrong"),
        row("q2", "hybrid", "correct"),
        row("q3", "bm25", "correct"),
        row("q3", "hybrid", "insufficient"),
        row("q4", "bm25", "error"),
        row("q4", "hybrid", "correct", retrieval=9.0),
    ]
    s = exam_eval.summarize(rows, baseline="bm25")
    bm25, hybrid = s["methods"]["bm25"], s["methods"]["hybrid"]
    assert (bm25["n"], bm25["correct"], bm25["wrong"], bm25["error"]) == (4, 2, 1, 1)
    assert hybrid["accuracy"] == 0.75 and hybrid["insufficient"] == 1
    assert hybrid["retrieval_ms_p95"] == 9.0
    paired = s["paired"]["hybrid"]
    assert (paired["improved"], paired["regressed"], paired["same"]) == (2, 1, 1)
    low, high = paired["accuracy_diff_ci95"]
    assert low <= paired["accuracy_diff"] == 0.25 <= high


def test_summary_rejects_methods_with_different_questions():
    with pytest.raises(ValueError, match="題目"):
        exam_eval.summarize([row("q1", "bm25", "correct"), row("q2", "hybrid", "correct")], baseline="bm25")


def test_report_is_markdown_without_question_text():
    rows = [row("q1", "bm25", "correct"), row("q1", "hybrid", "wrong")]
    rows[0]["question"] = "不應出現的題目原文"
    text = exam_eval.render_report(exam_eval.summarize(rows, baseline="bm25"), {"index_id": "idx"})
    assert "| bm25 |" in text and "| hybrid |" in text and "不應出現" not in text

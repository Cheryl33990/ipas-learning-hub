"""一分鐘示範：iPAS 自寫筆記＋腳本化模型，走正式的檢索、引用檢查與輸出流程。"""
from pathlib import Path

import pytest

from ipas_hub import demo

ROOT = Path(__file__).resolve().parents[1]


def run(name):
    return demo.run(name, ROOT)


def test_each_scenario_reaches_its_documented_outcome():
    assert {name: run(name)["outcome"] for name in demo.SCENARIOS} == {
        name: s["expected"] for name, s in demo.SCENARIOS.items()}


def test_grounded_multiple_choice_cites_retrieved_page_and_states_the_choice():
    generation = run("grounded-answer")["generation"]
    assert generation["status"] == "supported" and generation["flagged_segments"] == 0
    assert generation["answer_choice"] == "C"
    assert {s["id"] for s in generation["sources"]} <= {h["id"] for h in run("grounded-answer")["hits"]}


def test_demo_uses_the_ipas_profile():
    seen = []
    original = demo.answer
    def spy(question, hits, external, generate, prompt=None):
        seen.append(prompt)
        return original(question, hits, external, generate, prompt)
    demo.answer = spy
    try:
        run("grounded-answer")
    finally:
        demo.answer = original
    assert "iPAS" in seen[0]


def test_fabricated_citation_is_refused_after_one_repair():
    result = run("fabricated-citation")
    assert result["model_calls"] == 2
    assert "不存在的 id" in result["text"] and "以上不是解答" in result["text"]


def test_repaired_citation_is_accepted_and_records_the_repair():
    result = run("repaired-citation")
    assert result["model_calls"] == 2 and result["generation"]["repair_attempts"] == 1


def test_out_of_scope_question_never_calls_the_model():
    result = run("out-of-scope")
    assert result["hits"] == [] and result["model_calls"] == 0
    assert result["generation"]["status"] == "insufficient"


def test_tampered_index_is_rejected_before_any_search():
    result = run("tampered-index")
    assert result["hits"] == [] and "雜湊不一致" in result["text"]


def test_demo_output_is_deterministic_and_offline():
    assert demo.render_all(root=ROOT) == demo.render_all(root=ROOT)


def test_unknown_scenario_is_rejected():
    with pytest.raises(KeyError):
        demo.run("no-such-scenario", ROOT)

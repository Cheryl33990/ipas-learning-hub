import copy

from ipas_hub.explain import render_question, render_source_overview, review_set, validate, write_review

GOOD = {
    "questions": [
        {
            "n": 1, "answer": "B", "key": "重點",
            "options": {"A": "錯。理由甲", "B": "對。", "C": "錯。理由丙", "D": "錯。理由丁"},
            "basis": [{"page": "3-5", "term": "半結構化 數據"}], "see_also": [], "outside": "",
            "review": "必看", "review_reason": "原因",
        },
        {
            "n": 2, "answer": "A", "key": "重點",
            "options": {"A": "對。", "B": "錯。理由", "C": "錯。理由", "D": "錯。理由"},
            "basis": [], "see_also": [{"page": "3-5", "term": "JSON", "note": "只有名稱"}], "outside": "教材沒有",
            "review": "", "review_reason": "",
        },
    ]
}
OFFICIAL = {1: "B", 2: "A"}
PAGES = {"3-5": "半結構化數據（Semi-structured Data）如 XML、json"}


def test_valid_data_has_no_problems_and_term_match_ignores_spacing_and_case():
    assert validate(GOOD, OFFICIAL, PAGES) == []


def test_answer_disagreeing_with_official_is_reported():
    assert any("第 1 題：答案 B 與官方答案 C 不一致" in p for p in validate(GOOD, {1: "C", 2: "A"}, PAGES))


def test_option_verdict_must_match_the_answer():
    bad = copy.deepcopy(GOOD)
    bad["questions"][0]["options"]["A"] = "對。其實也可以"
    assert any("第 1 題選項 A" in p for p in validate(bad, OFFICIAL, PAGES))


def test_wrong_option_without_a_reason_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["questions"][0]["options"]["C"] = "錯。"
    assert any("選項 C：沒有說明為什麼錯" in p for p in validate(bad, OFFICIAL, PAGES))


def test_cited_term_missing_from_page_and_unknown_page_are_reported():
    bad = copy.deepcopy(GOOD)
    bad["questions"][0]["basis"] = [{"page": "3-5", "term": "差分隱私"}, {"page": "9-9", "term": "x"}]
    problems = validate(bad, OFFICIAL, PAGES)
    assert any("3-5 找不到「差分隱私」" in p for p in problems)
    assert any("頁碼 9-9 不存在" in p for p in problems)


def test_question_with_neither_basis_nor_outside_note_is_reported():
    bad = copy.deepcopy(GOOD)
    bad["questions"][1]["outside"] = ""
    assert any("第 2 題：沒有教材依據，也沒有標示教材外" in p for p in validate(bad, OFFICIAL, PAGES))


def test_missing_option_is_reported():
    bad = copy.deepcopy(GOOD)
    del bad["questions"][0]["options"]["D"]
    assert any("選項不是 A、B、C、D 四個" in p for p in validate(bad, OFFICIAL, PAGES))


def test_page_checks_are_skipped_without_guide_pages():
    bad = copy.deepcopy(GOOD)
    bad["questions"][0]["basis"] = [{"page": "9-9", "term": "x"}]
    assert validate(bad, OFFICIAL, None) == []


def test_review_set_separates_flagged_from_sampled_and_is_repeatable():
    must, sample = review_set(GOOD)
    assert must == [1] and sample == [2]
    assert review_set(GOOD) == (must, sample)


def test_render_marks_outside_material_and_omits_question_text_by_default():
    text = render_question(GOOD["questions"][1])
    assert "**教材依據**：目前未找到" in text and "**依據限制／補充知識**：教材沒有" in text and "科目 1 3-5（JSON；只有名稱）" in text
    assert ">" not in text
    assert "> 題目" in render_question(GOOD["questions"][1], "題目")


def test_cross_subject_reference_uses_its_own_pages_even_with_identical_labels():
    data = copy.deepcopy(GOOD)
    data["additional_guides"] = {"subject2": {"name": "科目 2"}}
    data["questions"][0]["basis"] = [{"source": "subject2", "page": "3-5", "term": "差分隱私"}]
    assert validate(data, OFFICIAL, PAGES, {"subject2": {"3-5": "差分隱私"}}) == []
    assert any("找不到" in p for p in validate(data, OFFICIAL, PAGES, {"subject2": PAGES}))
    assert any("未讀取" in p for p in validate(data, OFFICIAL, PAGES))
    assert "科目 2 3-5" in render_question(data["questions"][0])


def test_unknown_reference_source_is_rejected():
    data = copy.deepcopy(GOOD)
    data["questions"][0]["basis"][0]["source"] = "typo"
    assert any("未知教材來源" in p for p in validate(data, OFFICIAL, PAGES))


def test_regeneration_preserves_user_review_notes(tmp_path):
    path = tmp_path / "review.md"
    assert write_review(path, "解析初稿") == path
    path.write_text("解析初稿\n人工判定：不確定", encoding="utf-8")
    generated = write_review(path, "新版解析")
    assert generated == tmp_path / "review.generated.md"
    assert path.read_text(encoding="utf-8") == "解析初稿\n人工判定：不確定"
    assert generated.read_text(encoding="utf-8") == "新版解析"


def test_source_overview_keeps_subjects_and_evidence_strength_separate():
    data = copy.deepcopy(GOOD)
    data["questions"][0]["see_also"] = [{"source": "subject2", "page": "3-5", "term": "其他概念"}]
    text = render_source_overview(data)
    assert "| 1 | 依據：3-5 | 相關：3-5 |" in text
    assert "| 2 | 相關：3-5 | 尚未列入 |" in text
    assert "不能據此判定該科沒有內容" in text
    assert "科目 1 3-5" in render_question(data["questions"][0])
    assert "科目 2 3-5" in render_question(data["questions"][0])

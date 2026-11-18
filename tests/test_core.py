from ipas_hub.bm25 import BM25
from ipas_hub.exam import parse_questions
from ipas_hub.guide import Page, apply_patches, chunk_pages, parse_page
from ipas_hub.text import normalize, tokenize


def test_normalize_removes_linebreak_spaces_between_cjk_but_keeps_english_spaces():
    assert normalize("監督式\n學習（Supervised  Learning）\n是") == "監督式學習（Supervised Learning）是"


def test_tokenize_cjk_bigrams_and_lowercased_words():
    assert tokenize("主成分分析 PCA") == ["主成", "成分", "分分", "分析", "pca"]
    assert tokenize("Z-Score 值") == ["z-score", "值"]


def test_parse_page_takes_footer_label_and_drops_running_head():
    page = parse_page(" 第三章 人工智慧基礎概論 \n3-25 \n眾數（Mode）：指\n出現頻率最高的值。")
    assert page == Page("3-25", "眾數（Mode）：指出現頻率最高的值。")
    assert parse_page("序\n本手冊為學習指引") is None


def test_running_head_rule_can_be_set_per_textbook():
    raw = "\uf07d\uf07d\uf07d 第三章 AI 相關技術應用 \n3-34 \n第三章的重點是資料偏見\n常見方法："
    head = r"^\s*\uf07d+\s*第.{1,3}章.*$"
    page = parse_page(raw, 40, head)
    assert page == Page("3-34", "第三章的重點是資料偏見常見方法：", 40)  # 內文中提到「第三章」的句子保留
    assert parse_page(raw, 40).text.startswith("\uf07d")  # 未設定時沿用原本規則，不影響初級


def test_chunks_never_cross_pages_and_cover_whole_page():
    pages = [Page("3-1", "甲" * 700), Page("3-2", "乙" * 100)]
    chunks = chunk_pages(pages, size=400, stride=300)
    assert [(c.label, c.index, len(c.text)) for c in chunks] == [
        ("3-1", 0, 400),
        ("3-1", 1, 400),
        ("3-2", 0, 100),
    ]
    assert all(set(c.text) == ({"甲"} if c.label == "3-1" else {"乙"}) for c in chunks)


def test_apply_patches_reports_where_each_patch_landed():
    pages = [Page("3-27", normalize("拒絕 H0 Type II 錯誤（α）正確")), Page("3-28", "無關")]
    new, report = apply_patches(
        pages,
        [
            {"id": "a", "old": "拒絕 H0 Type II 錯誤（α）", "new": "拒絕 H0 Type I 錯誤（α）"},
            {"id": "b", "old": "不存在的字串", "new": "x"},
        ],
    )
    assert new[0].text == normalize("拒絕 H0 Type I 錯誤（α）正確")
    assert report == [{"id": "a", "applied_on": ["3-27"]}, {"id": "b", "applied_on": []}]


def test_bm25_ranks_document_with_rare_query_term_first():
    docs = [tokenize("監督式學習使用標記資料"), tokenize("擴散模型逐步去除雜訊"), tokenize("監督式學習與分類")]
    assert BM25(docs).top(tokenize("擴散模型"), 1) == [1]


def test_parse_questions_splits_on_answer_and_number_and_drops_page_furniture():
    raw = (
        "115 年第三次 AI 應用規劃師-初級能力鑑定【公告試題】 \n第一科：人工智慧基礎概論 \n"
        " 考試日期：115 年 08 月 15 日 \n第 1 頁，共 15 頁 \n \n一、選擇題 \n答案 題目 \n"
        "A 1.  題幹一第一行\n第二行？ \n(A)甲； \n(B)乙 \n"
        "第 2 頁，共 15 頁 \n答案 題目 \n(C)丙； \n(D)丁 \n"
        "D 2.  題幹二 1. 不是新題 \n(A)子 \n"
    )
    qs = parse_questions(raw)
    assert [(q.number, q.answer) for q in qs] == [(1, "A"), (2, "D")]
    assert qs[0].text == "題幹一第一行第二行？(A)甲；(B)乙(C)丙；(D)丁"
    assert qs[1].text == "題幹二1.不是新題(A)子"


def test_read_pages_keeps_pdf_page_order_even_when_unlabelled_pages_are_skipped(monkeypatch):
    import pypdf
    from ipas_hub.guide import apply_patches, read_pages

    class FakeReader:
        def __init__(self, path):
            raw = ["封面沒有頁碼", "序", "第一頁內文\n1-1\n", "第二頁舊詞\n1-2\n"]
            self.pages = [type("P", (), {"extract_text": lambda self, t=t: t})() for t in raw]
    monkeypatch.setattr(pypdf, "PdfReader", FakeReader)
    pages = read_pages("fake.pdf")
    assert [(p.label, p.pdf_page) for p in pages] == [("1-1", 3), ("1-2", 4)]
    patched, _ = apply_patches(pages, [{"id": "x", "old": "舊詞", "new": "新詞"}])
    assert [p.pdf_page for p in patched] == [3, 4]  # 套用勘誤不能弄丟 PDF 頁序
    assert {c.pdf_page for c in chunk_pages(patched, 4, 3) if c.label == "1-2"} == {4}


def test_parse_questions_accepts_fullwidth_answer_letters_and_reversed_header():
    raw = (
        "題目 答案 \nA 1.  題幹一 \n(A)甲；\n(B)乙；\n(C)丙；\n(D)丁 \n"
        "Ｂ 2.  題幹二 \n(A)子；\n(B)丑 \n題目 答案 \nＤ 3.  題幹三 \n(A)寅 \n"
    )
    qs = parse_questions(raw)
    assert [(q.number, q.answer) for q in qs] == [(1, "A"), (2, "B"), (3, "D")]
    assert qs[0].text == "題幹一(A)甲；(B)乙；(C)丙；(D)丁"
    assert "題目" not in qs[1].text and "答案" not in qs[1].text


def test_group_context_after_header_moves_to_each_question_in_the_group():
    raw = (
        "A 1.  題幹一 \n(A)甲；\n(B)乙；\n(C)丙；\n(D)丁的選項\n跨行 \n"
        "答案 題目 \n  請依據下方資訊回答第 2~3 題。 \n資料表欄位有 X 與 Y。 \n \n"
        "B 2.  依上表，何者正確？ \n(A)子 \n"
        "C 3.  承上，何者錯誤？ \n(A)丑 \n"
        "D 4.  獨立題 \n(A)寅 \n"
    )
    qs = {q.number: q.text for q in parse_questions(raw)}
    assert qs[1] == "題幹一(A)甲；(B)乙；(C)丙；(D)丁的選項跨行"
    assert qs[2] == "資料表欄位有X與Y。依上表，何者正確？(A)子"
    assert qs[3] == "資料表欄位有X與Y。承上，何者錯誤？(A)丑"
    assert qs[4] == "獨立題(A)寅"


def test_group_context_before_header_moves_to_each_question_in_the_group():
    raw = (
        "A 1.  題幹一 \n(D)丁 \n"
        "  某團隊正在開發檢測系統。 \n● 資料不平衡。 \n \n請根據上述情境，回答第 2~3 題。 \n"
        "B 2.  題幹二 \n(A)子 \n"
        "C 3.  題幹三 \n(A)丑 \n"
    )
    qs = {q.number: q.text for q in parse_questions(raw)}
    assert qs[1] == "題幹一(D)丁"
    assert qs[2] == "某團隊正在開發檢測系統。●資料不平衡。題幹二(A)子"
    assert qs[3] == "某團隊正在開發檢測系統。●資料不平衡。題幹三(A)丑"


def test_header_split_across_lines_and_later_section_titles_are_removed():
    raw = (
        "一、選擇題 \nA 1.  題幹一 \n(D)丁 \n二、程式題 \n"
        "B 2.  題幹二 \n(D)戊 \n  下圖為一段程式片段。請回答\n第 3~3 題。 \n \n"
        "C 3.  題幹三 \n(A)己 \n"
    )
    qs = {q.number: q.text for q in parse_questions(raw)}
    assert qs[1] == "題幹一(D)丁"
    assert qs[2] == "題幹二(D)戊"
    assert qs[3] == "下圖為一段程式片段。題幹三(A)己"

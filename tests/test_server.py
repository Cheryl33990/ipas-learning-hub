"""OpenAI 相容端點的合成測試：不連 LLM、不連網路。"""

import json
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ipas_hub import cli
from ipas_hub.server import HOST, chat_response, last_user_message, make_server, sse_chunks


def body(*messages, **extra):
    return {"model": "rag", "messages": [{"role": r, "content": c} for r, c in messages], **extra}


def test_takes_the_last_user_message_and_ignores_platform_prompts():
    payload = body(("system", "平台自己的提示"), ("user", "舊問題"), ("assistant", "舊回答"), ("user", "新問題"))
    assert last_user_message(payload) == "新問題"


def test_accepts_content_given_as_text_parts():
    payload = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": "甲"}, {"type": "text", "text": "乙"}]}]
    }
    assert last_user_message(payload) == "甲\n乙"


@pytest.mark.parametrize("payload", [{}, {"messages": []}, body(("system", "只有系統訊息")), body(("user", "   "))])
def test_missing_or_blank_question_is_a_client_error(payload):
    status, result = chat_response(payload, lambda q: "不應被呼叫", "rag")
    assert status == 400 and "error" in result


def test_answer_text_is_returned_unchanged_in_openai_shape():
    status, result = chat_response(body(("user", "題目")), lambda q: f"狀態：有依據\n{q} [教材1]", "rag")
    assert status == 200 and result["object"] == "chat.completion" and result["model"] == "rag"
    choice = result["choices"][0]
    assert choice["message"] == {"role": "assistant", "content": "狀態：有依據\n題目 [教材1]"}
    assert choice["finish_reason"] == "stop"


@pytest.mark.parametrize(
    "exc",
    [
        ValueError("無法連線 LLM 服務：連線被拒"),
        ValueError("模型引用不存在或回答缺少引用，修正一次後仍不合格"),
        OSError("索引檔不存在"),
    ],
)
def test_failures_are_shown_as_a_warning_not_as_an_answer(exc):
    def failing(question):
        raise exc

    status, result = chat_response(body(("user", "題目")), failing, "rag")
    text = result["choices"][0]["message"]["content"]
    assert status == 200  # 讓聊天畫面顯示原因，而不是平台的通用錯誤
    assert text.startswith("⚠ 無法產生有依據的解答") and str(exc) in text and "不是解答" in text
    assert "狀態：有依據" not in text


def test_stream_chunks_carry_the_whole_text_then_done():
    lines = list(sse_chunks("第一行\n第二行", "rag"))
    assert lines[-1] == "data: [DONE]\n\n"
    chunks = [json.loads(line[6:]) for line in lines[:-1]]
    assert all(c["object"] == "chat.completion.chunk" for c in chunks)
    assert "".join(c["choices"][0]["delta"].get("content", "") for c in chunks) == "第一行\n第二行"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


@pytest.fixture
def running():
    server = make_server(lambda q: f"回覆：{q}", 0, "rag")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://{HOST}:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def post(url, payload):
    req = Request(url, json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as res:
        return res.headers.get("Content-Type"), res.read().decode()


def test_http_server_binds_loopback_and_serves_models_chat_and_stream(running):
    assert HOST == "127.0.0.1"
    with urlopen(running + "/v1/models", timeout=10) as res:
        assert [m["id"] for m in json.loads(res.read())["data"]] == ["rag"]
    _, text = post(running + "/v1/chat/completions", body(("user", "你好")))
    assert json.loads(text)["choices"][0]["message"]["content"] == "回覆：你好"
    ctype, text = post(running + "/v1/chat/completions", body(("user", "你好"), stream=True))
    assert ctype.startswith("text/event-stream") and "回覆：你好" in "".join(
        json.loads(line[6:])["choices"][0]["delta"].get("content", "")
        for line in text.split("\n\n")
        if line.startswith("data: {")
    )
    assert text.rstrip().endswith("data: [DONE]")


def test_browser_visit_to_root_or_v1_gets_an_explanation_not_an_error(running):
    for path in ("/", "/v1", "/v1/"):
        with urlopen(running + path, timeout=10) as res:
            page = res.read().decode()
            assert res.status == 200 and res.headers.get("Content-Type").startswith("text/html")
            assert "API" in page and "/v1/models" in page and "聊天介面" in page


def test_http_server_rejects_bad_json_and_unknown_paths(running):
    with pytest.raises(HTTPError) as bad:
        urlopen(
            Request(running + "/v1/chat/completions", b"{not json", {"Content-Type": "application/json"}), timeout=10
        )
    assert bad.value.code == 400
    with pytest.raises(HTTPError) as missing:
        urlopen(running + "/v1/other", timeout=10)
    assert missing.value.code == 404


class FakeKB:
    knowledge_base = "ipas"
    index_id = "idx"

    def search(self, question, k, method):
        return [{"id": "s1:1-1:0"}]


def test_answer_text_reuses_ask_and_render_and_reports_search_failure(monkeypatch, tmp_path):
    seen = {}

    def fake_ask(question, hits, args):
        seen.update(question=question, hits=hits)
        return {"web": {"error": "維基百科 HTTP 429"}, "generation": {"marker": "g"}}

    monkeypatch.setattr(cli, "ask", fake_ask)
    monkeypatch.setattr(cli, "render_text", lambda generation, *a, **k: f"rendered:{generation['marker']}")
    args = SimpleNamespace(k=5, method="bm25")
    text = cli.answer_text(FakeKB(), "題目", args, tmp_path)
    assert seen == {"question": "題目", "hits": [{"id": "s1:1-1:0"}]}
    assert text.startswith("rendered:g")
    assert "⚠ 外部搜尋未完整" in text and "維基百科 HTTP 429" in text
    assert len(list((tmp_path / "data/runs").glob("*.json"))) == 1


def test_answer_text_has_no_warning_when_search_is_fine(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "ask", lambda q, h, a: {"web": {"error": None}, "generation": {}})
    monkeypatch.setattr(cli, "render_text", lambda generation, *a, **k: "rendered")
    assert cli.answer_text(FakeKB(), "題目", SimpleNamespace(k=5, method="bm25"), tmp_path) == "rendered"


def test_only_listed_files_are_served_read_only(tmp_path):
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-synthetic")
    (tmp_path / "secret.txt").write_text("不可外流")
    server = make_server(lambda q: "", 0, "rag", files={"s1.pdf": pdf})
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://{HOST}:{server.server_address[1]}"
    try:
        with urlopen(base + "/files/s1.pdf", timeout=10) as res:
            assert res.headers.get("Content-Type") == "application/pdf"
            assert res.headers.get("Content-Disposition") == "inline"
            assert res.read() == b"%PDF-synthetic"
        for path in (
            "/files/secret.txt",
            "/files/../secret.txt",
            "/files/book.pdf",
            "/files/s1.pdf/../secret.txt",
            "/files/%2e%2e/secret.txt",
            "/files/",
        ):
            with pytest.raises(HTTPError) as err:
                urlopen(base + path, timeout=10)
            assert err.value.code == 404
        with pytest.raises(HTTPError) as err:  # 唯讀：不接受寫入
            urlopen(Request(base + "/files/s1.pdf", b"x", method="PUT"), timeout=10)
        assert err.value.code in (405, 501)
    finally:
        server.shutdown()
        server.server_close()


def test_served_files_must_match_the_indexed_version(tmp_path, capsys):
    (tmp_path / "data").mkdir()
    good, bad = tmp_path / "data/good.pdf", tmp_path / "data/bad.pdf"
    good.write_bytes(b"good")
    bad.write_bytes(b"changed")
    from ipas_hub.knowledge import digest

    sources = [
        {"id": "s1", "pdf": "data/good.pdf", "sha256": digest(b"good")},
        {"id": "s2", "pdf": "data/bad.pdf", "sha256": digest(b"original")},
        {"id": "s3", "pdf": "data/missing.pdf", "sha256": "x"},
        {"id": "old-index-without-path", "sha256": "x"},
    ]
    files = cli.source_files(tmp_path, sources)
    assert files == {"s1.pdf": good.resolve()}
    assert "s2" in capsys.readouterr().err
    link = cli.textbook_link("http://127.0.0.1:8100/", files)
    assert (
        link({"source_type": "textbook", "source": "s1", "pdf_page": 42})
        == "http://127.0.0.1:8100/files/s1.pdf#page=42"
    )
    assert link({"source_type": "textbook", "source": "s2", "pdf_page": 42}) is None
    assert link({"source_type": "textbook", "source": "s1"}) is None
    assert link({"source_type": "external", "url": "https://example.org/a"}) == "https://example.org/a"

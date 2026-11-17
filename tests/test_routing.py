"""多知識庫聊天路由：模型不可靜默改搜其他庫。"""
import json
import threading
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from ipas_hub import cli
from ipas_hub.server import make_server


def test_http_model_routing_streaming_unknown_models_and_scoped_files(tmp_path):
    first, second = tmp_path / "first.pdf", tmp_path / "second.pdf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    calls = []
    def callback(name):
        return lambda q: calls.append(name) or name
    server = make_server(None, 0, "rag", {"rag--doc.pdf": first, "labor-law--doc.pdf": second},
                         models={"rag": callback("ipas"), "labor-law": callback("law")})
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with urlopen(base + "/v1/models", timeout=5) as r:
            assert [m["id"] for m in json.load(r)["data"]] == ["rag", "labor-law"]
        for name, expected in (("rag", "ipas"), ("labor-law", "law")):
            for streaming in (False, True):
                data = {"model": name, "stream": streaming, "messages": [{"role": "user", "content": "same query"}]}
                with urlopen(Request(base + "/v1/chat/completions", json.dumps(data).encode(),
                                     {"Content-Type": "application/json"}), timeout=5) as r:
                    result = r.read().decode()
                if streaming:
                    assert f'"content": "{expected}"' in result and f'"model": "{name}"' in result
                else:
                    result = json.loads(result)
                    assert result["model"] == name and result["choices"][0]["message"]["content"] == expected
        assert calls == ["ipas", "ipas", "law", "law"]
        for name in (None, "unknown", ["rag"]):
            with pytest.raises(HTTPError) as err:
                urlopen(Request(base + "/v1/chat/completions", json.dumps({"model": name, "messages": [
                    {"role": "user", "content": "same query"}]}).encode(), {"Content-Type": "application/json"}), timeout=5)
            assert err.value.code == 400
        assert len(calls) == 4
        for name, content in (("rag--doc.pdf", b"first"), ("labor-law--doc.pdf", b"second")):
            with urlopen(base + "/files/" + name, timeout=5) as r:
                assert r.read() == content
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_route_callbacks_keep_kb_policy_and_namespaced_links(tmp_path, monkeypatch):
    config = tmp_path / "routes.json"
    config.write_text(json.dumps({"rag": {"knowledge_base": "ipas", "web": "wikipedia"},
                                  "labor-law": {"knowledge_base": "labor-law", "web": "none"}}))
    args = SimpleNamespace(routes=config, store="pg", kb=None, index=None, model="test", llm_url=None,
                           allow_remote=False, link_base=None, port=0, method="hybrid")
    encoder = object()
    loaded, called = [], []
    def fake_open(root, selected, shared):
        loaded.append((selected.kb, shared))
        return SimpleNamespace(knowledge_base=selected.kb, index_id=selected.kb, encoder=encoder,
                               payload={"sources": [], "embedding": {"name": "same", "revision": "rev", "dimensions": 2}})
    monkeypatch.setattr(cli, "open_kb", fake_open)
    monkeypatch.setattr(cli, "source_files", lambda *a: {"doc.pdf": tmp_path / "fake.pdf"})
    def fake_answer(kb, question, selected, root, link):
        called.append((kb.knowledge_base, selected.web, link({"source_type": "textbook", "source": "doc", "pdf_page": 2})))
        return "ok"
    monkeypatch.setattr(cli, "answer_text", fake_answer)
    import ipas_hub.server
    monkeypatch.setattr(ipas_hub.server, "make_server", lambda *a, **kw: kw)
    server = cli.routed_server(tmp_path, args)
    server["models"]["rag"]("question")
    server["models"]["labor-law"]("question")
    assert loaded == [("ipas", None), ("labor-law", encoder)]
    assert called == [("ipas", "wikipedia", "http://127.0.0.1:0/files/rag--doc.pdf#page=2"),
                      ("labor-law", "none", "http://127.0.0.1:0/files/labor-law--doc.pdf#page=2")]


@pytest.mark.parametrize("content", ['{}', '{"bad/name":{"knowledge_base":"ipas","web":"none"}}',
    '{"rag":{"knowledge_base":"ipas","web":"unknown"}}',
    '{"rag":{"knowledge_base":"ipas","web":"none"},"rag":{}}'])
def test_invalid_routes_rejected_before_loading(tmp_path, content):
    config = tmp_path / "routes.json"
    config.write_text(content)
    with pytest.raises(ValueError):
        cli.routed_server(tmp_path, SimpleNamespace(routes=config))

import json

import numpy as np
import pytest

from ipas_hub.cli import evaluate, main
from ipas_hub.guide import Page
from ipas_hub.knowledge import KnowledgeBase, build_index, canonical, data_path, digest
from ipas_hub.rag import answer


def payload(embedding=None):
    data = {
        "schema_version": 1,
        "embedding": embedding,
        "sources": [{"id": "s1", "name": "科目一", "version": "v1"}, {"id": "s2", "name": "科目二", "version": "v2"}],
        "chunks": [
            {"id": "s1:3-1:0", "source": "s1", "page": "3-1", "text": "合成例子：分類模型辨識圖像"},
            {"id": "s2:3-1:0", "source": "s2", "page": "3-1", "text": "合成例子：差分隱私加入雜訊保護資料"},
        ],
    }
    return {"index_id": digest(canonical(data)), **data}


def test_cross_subject_search_returns_correct_source_and_no_zero_score_hits():
    kb = KnowledgeBase(payload())
    hits = kb.search("差分隱私")
    assert len(hits) == 1
    assert hits[0]["source"] == "s2" and hits[0]["page"] == "3-1"
    assert hits[0]["version"] == "v2"
    assert kb.search("zzzz_unknown") == []


def test_modified_index_is_rejected():
    data = payload()
    data["chunks"][0]["text"] = "被修改"
    with pytest.raises(ValueError, match="雜湊"):
        KnowledgeBase(data)


def test_vector_artifact_mismatch_and_missing_model_are_rejected():
    vectors = np.eye(2, dtype=np.float32)
    meta = {"dimensions": 2, "sha256": digest(vectors.tobytes())}
    with pytest.raises(ValueError, match="向量檔"):
        KnowledgeBase(payload(meta), vectors[:, :1])
    with pytest.raises(ValueError, match="向量模型"):
        KnowledgeBase(payload()).search("差分", method="hybrid")


def test_hybrid_retrieval_routes_to_matching_vector_and_lexical_source():
    class Encoder:
        def encode(self, texts, **kwargs):
            return [[0.0, 1.0]]

    vectors = np.eye(2, dtype=np.float32)
    meta = {"dimensions": 2, "sha256": digest(vectors.tobytes())}
    kb = KnowledgeBase(payload(meta), vectors, Encoder())
    assert kb.search("差分隱私", method="hybrid")[0]["source"] == "s2"


def test_local_encoder_ignores_files_the_project_does_not_download(monkeypatch, tmp_path):
    # 新版 huggingface_hub 會依下載時記下的檔案清單檢查快照是否完整；README 排除的檔案不能被當成缺漏
    import sys
    import types
    from ipas_hub import knowledge

    seen = {}

    def fake_snapshot_download(model, **kwargs):
        seen.update(kwargs)
        return str(tmp_path / "rev123")

    monkeypatch.setitem(sys.modules, "huggingface_hub", types.SimpleNamespace(snapshot_download=fake_snapshot_download))
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(SentenceTransformer=lambda path, **kw: ("encoder", path)),
    )
    encoder, revision = knowledge.local_encoder("org/model", "abc")
    assert revision == "rev123" and seen["local_files_only"] is True and seen["revision"] == "abc"
    assert {"onnx/*", "imgs/*", "*.jpg"} <= set(seen["ignore_patterns"])


def test_original_text_outputs_cannot_escape_data_directory(tmp_path):
    with pytest.raises(ValueError, match="data/"):
        data_path(tmp_path, "docs/leak.json")
    with pytest.raises(ValueError, match="data/"):
        data_path(tmp_path, "data/../../leak.json")


def test_build_records_patches_and_fails_if_patch_does_not_apply(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    pdf = tmp_path / "data/fake.pdf"
    pdf.write_bytes(b"synthetic_pdf")
    patch = tmp_path / "data/patch.json"
    patch.write_text(json.dumps([{"id": "fix", "old": "舊詞", "new": "新詞"}]), encoding="utf-8")
    (tmp_path / "uv.lock").write_text("synthetic lock")
    config = {
        "schema_version": 1,
        "chunk_size": 40,
        "chunk_stride": 30,
        "sources": [
            {
                "id": "s1",
                "name": "合成",
                "version": "v1",
                "pdf": "data/fake.pdf",
                "sha256": digest(pdf.read_bytes()),
                "patches": "data/patch.json",
            }
        ],
    }
    file = tmp_path / "config.json"
    file.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setattr("ipas_hub.knowledge.read_pages", lambda *_, **__: [Page("3-1", "合成舊詞", 9)])
    path = build_index(tmp_path, file, tmp_path / "data/index")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["chunks"][0]["text"] == "合成新詞"
    assert data["chunks"][0]["pdf_page"] == 9 and data["sources"][0]["pdf"] == "data/fake.pdf"
    assert KnowledgeBase.load(path).search("合成新詞")[0]["pdf_page"] == 9
    assert data["sources"][0]["patch_report"][0]["applied_on"] == ["3-1"]
    monkeypatch.setattr("ipas_hub.knowledge.read_pages", lambda *_, **__: [Page("3-1", "無法套用")])
    with pytest.raises(ValueError, match="勘誤"):
        build_index(tmp_path, file, tmp_path / "data/index")
    assert data["sources"][0]["errata"] == "applied"


def test_source_without_errata_file_is_indexed_and_marked_not_applied(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    pdf = tmp_path / "data/fake.pdf"
    pdf.write_bytes(b"synthetic_pdf")
    (tmp_path / "uv.lock").write_text("synthetic lock")
    config = {
        "schema_version": 1,
        "chunk_size": 40,
        "chunk_stride": 30,
        "sources": [
            {"id": "s1", "name": "合成", "version": "v1", "pdf": "data/fake.pdf", "sha256": digest(pdf.read_bytes())}
        ],
    }
    file = tmp_path / "config.json"
    file.write_text(json.dumps(config), encoding="utf-8")
    seen = []
    monkeypatch.setattr(
        "ipas_hub.knowledge.read_pages",
        lambda path, running_head=None: seen.append(running_head) or [Page("3-1", "合成舊詞", 3)],
    )
    data = json.loads(build_index(tmp_path, file, tmp_path / "data/index").read_text(encoding="utf-8"))
    source = data["sources"][0]
    assert source["errata"] == "not_applied" and source["patch_sha256"] is None and source["patch_report"] == []
    assert data["chunks"][0]["text"] == "合成舊詞"
    assert seen == [None] and "running_head" not in source  # 未設定時沿用預設規則，索引內容不變
    config["sources"][0]["running_head"] = r"^第.章.*$"
    file.write_text(json.dumps(config), encoding="utf-8")
    data = json.loads(build_index(tmp_path, file, tmp_path / "data/index").read_text(encoding="utf-8"))
    assert seen[-1] == r"^第.章.*$" and data["sources"][0]["running_head"] == r"^第.章.*$"


def test_no_evidence_does_not_call_model():
    def unexpected(_):
        pytest.fail("不應呼叫模型")

    assert answer("合成問題", [], [], unexpected)["status"] == "insufficient"


@pytest.mark.parametrize(
    "output",
    [
        {"status": "supported", "answer": "合成回答", "citations": ["fake"]},
        {"status": "supported", "answer": "合成回答", "citations": []},
        {"status": "supported", "answer": "", "citations": ["s2:3-1:0"]},
    ],
)
def test_invalid_model_citations_and_empty_answers_are_rejected(output):
    hits = KnowledgeBase(payload()).search("差分隱私")
    with pytest.raises(ValueError):
        answer("合成問題", hits, [], lambda *_: {"output": output})


def test_valid_response_is_labelled_as_structural_not_semantic_verification():
    hits = KnowledgeBase(payload()).search("差分隱私")
    result = answer(
        "合成問題",
        hits,
        [],
        lambda *_: {
            "model": "fake-test-only",
            "output": {"status": "supported", "segments": [{"text": "合成回答", "citations": ["s2:3-1:0"]}]},
        },
    )
    assert result["prompt_sha256"]
    assert result["validation"] == "citation_ids_and_lexical_check_not_semantic_verification"


def test_evaluation_matches_subject_and_page_together():
    kb = KnowledgeBase(payload())
    cases = [{"id": "a", "query": "差分隱私", "expected": [{"source": "s1", "page": "3-1"}]}]
    assert evaluate(kb, cases, "bm25", 1)["hits"] == 0
    cases[0]["expected"][0]["source"] = "s2"
    assert evaluate(kb, cases, "bm25", 1)["hits"] == 1


def test_cli_search_persists_run_only_under_data(tmp_path, capsys):
    folder = tmp_path / "data/index"
    folder.mkdir(parents=True)
    (folder / "index.json").write_bytes(canonical(payload()))
    assert main(["--root", str(tmp_path), "search", "--index", "data/index/index.json", "--query", "差分隱私"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["hits"][0]["source"] == "s2"
    assert (tmp_path / result["run_file"]).is_file()


def test_default_hybrid_falls_back_to_bm25_with_a_notice_when_index_has_no_vectors(tmp_path, capsys):
    folder = tmp_path / "data/index"
    folder.mkdir(parents=True)
    (folder / "index.json").write_bytes(canonical(payload()))
    assert main(["--root", str(tmp_path), "search", "--index", "data/index/index.json", "--query", "差分隱私"]) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out)["method"] == "bm25"
    assert "沒有向量" in captured.err and "BM25" in captured.err


def test_explicit_vector_method_on_index_without_vectors_still_fails(tmp_path, capsys):
    folder = tmp_path / "data/index"
    folder.mkdir(parents=True)
    (folder / "index.json").write_bytes(canonical(payload()))
    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "search",
                "--index",
                "data/index/index.json",
                "--query",
                "差分隱私",
                "--method",
                "hybrid",
            ]
        )
        == 1
    )
    assert "向量" in capsys.readouterr().err

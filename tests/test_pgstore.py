"""PostgreSQL＋pgvector 儲存的測試。

前半不需要資料庫：資料列與索引內容互轉、竄改拒絕、向量檢索介面。
後半需要資料庫：設定 PG_TEST_DSN 才執行（CI 以 service container 提供），每個測試用獨立 schema。
"""
import os
import uuid

import numpy as np
import pytest

from ipas_hub import cli, pgstore
from ipas_hub.knowledge import KnowledgeBase, canonical, digest

VEC = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=np.float32)


def payload(vectors=None, extra_chunk=False):
    chunks = [{"id": "s1:3-1:0", "source": "s1", "page": "3-1", "pdf_page": 9, "text": "合成：分類模型辨識圖像"},
              {"id": "s1:3-2:0", "source": "s1", "page": "3-2", "pdf_page": 10, "text": "合成：迴歸預測連續數值"},
              {"id": "s2:3-1:0", "source": "s2", "page": "3-1", "pdf_page": 7, "text": "合成：差分隱私加入雜訊"}]
    if extra_chunk:
        chunks.append({"id": "s2:3-2:0", "source": "s2", "page": "3-2", "text": "合成：舊索引沒有 PDF 頁"})
    data = {"schema_version": 1, "chunk_size": 40, "chunk_stride": 30, "code_version": "test",
            "code_sha256": {"a.py": "h"}, "lock_sha256": "l",
            "embedding": None if vectors is None else {"name": "fake", "revision": "r1", "dimensions": vectors.shape[1],
                                                       "sha256": digest(vectors.tobytes())},
            "sources": [{"id": "s1", "name": "科目一", "version": "v1", "sha256": "a", "pdf": "data/a.pdf", "pages": 2,
                         "patch_sha256": "p", "patch_report": [{"id": "fix", "applied_on": ["3-1"]}]},
                        {"id": "s2", "name": "科目二", "version": "v2", "sha256": "b", "pdf": "data/b.pdf", "pages": 2,
                         "patch_sha256": "q", "patch_report": []}],
            "chunks": chunks}
    return {"index_id": digest(canonical(data)), **data}


class Encoder:
    def __init__(self, vector):
        self.vector = vector

    def encode(self, texts, **kwargs):
        return [self.vector]


# ---- 不需要資料庫 ----

def test_rows_keep_generic_columns_and_put_document_details_in_metadata():
    rows = pgstore.rows_from_index(payload(VEC), VEC)
    assert rows["index"]["index_id"] == payload(VEC)["index_id"]
    assert rows["index"]["embedding_model"] == "fake" and rows["index"]["dimensions"] == 3
    assert "chunks" not in rows["index"]["manifest"] and "sources" not in rows["index"]["manifest"]
    assert rows["sources"][0]["metadata"]["patch_report"] == [{"id": "fix", "applied_on": ["3-1"]}]
    chunk = rows["chunks"][0]
    assert (chunk["ord"], chunk["chunk_id"], chunk["source_id"]) == (0, "s1:3-1:0", "s1")
    assert chunk["metadata"] == {"page": "3-1", "pdf_page": 9} and chunk["embedding"] == [1.0, 0.0, 0.0]


def test_rows_rebuild_the_identical_index_and_vectors():
    original = payload(VEC)
    rows = pgstore.rows_from_index(original, VEC)
    back, vectors = pgstore.index_from_rows(rows["index"], rows["sources"], list(reversed(rows["chunks"])))
    assert back == original and np.array_equal(vectors, VEC) and vectors.dtype == np.float32
    KnowledgeBase(back, vectors)  # 雜湊與向量檢查都通過


def test_index_without_vectors_round_trips_without_embeddings():
    original = payload(extra_chunk=True)
    rows = pgstore.rows_from_index(original, None)
    assert all(c["embedding"] is None for c in rows["chunks"])
    back, vectors = pgstore.index_from_rows(rows["index"], rows["sources"], rows["chunks"])
    assert back == original and vectors is None


def test_tampered_or_partial_rows_are_rejected():
    rows = pgstore.rows_from_index(payload(VEC), VEC)
    rows["chunks"][1]["text"] = "被改過"
    back, vectors = pgstore.index_from_rows(rows["index"], rows["sources"], rows["chunks"])
    with pytest.raises(ValueError, match="雜湊"):
        KnowledgeBase(back, vectors)
    rows = pgstore.rows_from_index(payload(VEC), VEC)
    rows["chunks"][2]["embedding"] = None
    with pytest.raises(ValueError, match="向量"):
        pgstore.index_from_rows(rows["index"], rows["sources"], rows["chunks"])


def test_rows_from_index_refuses_an_unverified_index():
    bad = payload(VEC)
    bad["chunks"][0]["text"] = "改過但沒重算 index_id"
    with pytest.raises(ValueError, match="雜湊"):
        pgstore.rows_from_index(bad, VEC)


def test_vector_and_hybrid_search_use_the_vector_backend_when_given():
    calls = []

    def nearest(query_vector, n):
        calls.append((list(query_vector), n))
        return [2, 0, 1]
    kb = KnowledgeBase(payload(VEC), VEC, Encoder([0.0, 0.0, 1.0]), vector_search=nearest)
    assert kb.search("任意", method="vector")[0]["id"] == "s2:3-1:0"
    assert kb.search("差分隱私", method="hybrid")[0]["id"] == "s2:3-1:0"
    assert [n for _, n in calls] == [20, 20] and calls[0][0] == [0.0, 0.0, 1.0]
    assert kb.search("差分隱私", method="bm25")[0]["id"] == "s2:3-1:0" and len(calls) == 2


def test_default_method_is_hybrid_for_both_stores():
    assert cli.default_method("file") == "hybrid" and cli.default_method("pg") == "hybrid"


def test_pg_store_without_dsn_fails_clearly(monkeypatch, capsys):
    monkeypatch.delenv("PG_DSN", raising=False)
    assert cli.main(["search", "--store", "pg", "--query", "差分隱私"]) == 1
    assert "PG_DSN" in capsys.readouterr().err


def test_file_store_still_requires_an_index_path(capsys):
    assert cli.main(["search", "--query", "差分隱私"]) == 1
    assert "--index" in capsys.readouterr().err


# ---- 需要資料庫（PG_TEST_DSN） ----

needs_db = pytest.mark.skipif(not os.getenv("PG_TEST_DSN"), reason="未設定 PG_TEST_DSN，略過需要資料庫的測試")


@pytest.fixture
def conn():
    psycopg = pytest.importorskip("psycopg")
    connection = psycopg.connect(os.environ["PG_TEST_DSN"], autocommit=True)
    connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
    schema = f"test_{uuid.uuid4().hex[:10]}"
    connection.execute(f"CREATE SCHEMA {schema}")
    connection.execute(f"SET search_path TO {schema}, public")
    yield connection
    connection.execute(f"DROP SCHEMA {schema} CASCADE")
    connection.close()


@needs_db
def test_db_load_is_idempotent_and_reads_back_identical_content(conn):
    first, second = payload(VEC), payload(extra_chunk=True)
    assert pgstore.load_index(conn, first, VEC) is True
    assert pgstore.load_index(conn, first, VEC) is False  # 同一個 index_id 不重複載入
    assert pgstore.load_index(conn, second, None) is True
    back, vectors = pgstore.read_index(conn, first["index_id"])
    assert back == first and np.array_equal(vectors, VEC)
    latest, none = pgstore.read_index(conn)
    assert latest == second and none is None
    with_vectors, vectors = pgstore.read_index(conn, with_vectors=True)  # 預設混合檢索要用含向量的那份
    assert with_vectors == first and np.array_equal(vectors, VEC)
    with pytest.raises(ValueError, match="找不到"):
        pgstore.read_index(conn, "0" * 64)


@needs_db
def test_db_vector_ranking_matches_the_file_index(conn):
    rng = np.random.default_rng(0)
    vectors = rng.normal(size=(4, 8)).astype(np.float32)
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    data = payload(vectors, extra_chunk=True)
    pgstore.load_index(conn, data, vectors)
    query = vectors[1] * 0.6 + vectors[3] * 0.4
    file_kb = KnowledgeBase(data, vectors, Encoder(query))
    db_kb = pgstore.open_knowledge_base(conn, data["index_id"], vector=True, encoder=Encoder(query))
    for method in ("vector", "hybrid", "bm25"):
        assert ([h["id"] for h in db_kb.search("差分隱私", 4, method)]
                == [h["id"] for h in file_kb.search("差分隱私", 4, method)])
    assert db_kb.vectors is None  # 驗證完就不留在記憶體，查詢交給資料庫


@needs_db
def test_db_reports_whether_an_index_has_vectors(conn):
    # 建表前查詢會落到 public schema（本機可能已有真實資料），所以從載入第一份之後才判斷
    pgstore.load_index(conn, payload(extra_chunk=True), None)
    assert pgstore.has_vectors(conn) is False
    pgstore.load_index(conn, payload(VEC), VEC)
    assert pgstore.has_vectors(conn) is True
    assert pgstore.has_vectors(conn, payload(VEC)["index_id"]) is True
    assert pgstore.has_vectors(conn, payload(extra_chunk=True)["index_id"]) is False


@needs_db
def test_db_rows_changed_after_loading_are_rejected(conn):
    data = payload(VEC)
    pgstore.load_index(conn, data, VEC)
    conn.execute("UPDATE kb_chunk SET text = '被改過' WHERE ord = 0")
    with pytest.raises(ValueError, match="雜湊"):
        pgstore.open_knowledge_base(conn, data["index_id"])


@needs_db
def test_knowledge_bases_are_explicit_and_vector_queries_stay_in_the_selected_index(conn):
    first = payload(VEC)
    second = payload(VEC)
    second.pop("index_id")
    second["knowledge_base"] = "labor-law"
    second["sources"][0]["name"] = "另一組相似文件"
    second = {"index_id": digest(canonical(second)), **second}
    pgstore.load_index(conn, first, VEC)
    pgstore.load_index(conn, second, VEC)
    with pytest.raises(ValueError, match="多個知識庫"):
        pgstore.select_index(conn)
    with pytest.raises(ValueError, match="找不到"):
        pgstore.select_index(conn, kb="missing")
    with pytest.raises(ValueError, match="不屬於"):
        pgstore.select_index(conn, second["index_id"], "ipas")
    assert pgstore.select_index(conn, kb="ipas", prefer_vectors=True) == first["index_id"]
    assert pgstore.select_index(conn, kb="labor-law") == second["index_id"]
    for name, data in (("ipas", first), ("labor-law", second)):
        selected = pgstore.select_index(conn, kb=name)
        kb = pgstore.open_knowledge_base(conn, selected, True, Encoder(VEC[1]))
        hits = kb.search("差分隱私", method="hybrid")
        assert hits and all(h["index_id"] == data["index_id"] for h in hits)
        assert kb.knowledge_base == name


@needs_db
def test_prefer_vectors_does_not_pick_newer_vectorless_version(conn):
    first = payload(VEC)
    pgstore.load_index(conn, first, VEC)
    pgstore.load_index(conn, payload(extra_chunk=True), None)
    assert pgstore.select_index(conn, kb="ipas", prefer_vectors=True) == first["index_id"]


@needs_db
def test_pg_cli_routes_explicit_knowledge_base_and_rejects_ambiguity(conn, tmp_path, monkeypatch, capsys):
    import json
    first = payload()
    second = payload()
    second.pop("index_id")
    second["knowledge_base"] = "labor-law"
    second = {"index_id": digest(canonical(second)), **second}
    pgstore.load_index(conn, first, None)
    pgstore.load_index(conn, second, None)
    monkeypatch.setattr(pgstore, "connect", lambda: conn)
    base = ["--root", str(tmp_path), "search", "--store", "pg", "--query", "差分隱私", "--method", "bm25"]
    assert cli.main(base + ["--kb", "labor-law"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["knowledge_base"] == "labor-law"
    assert all(h["index_id"] == second["index_id"] for h in result["hits"])
    assert cli.main(base) == 1
    assert "多個知識庫" in capsys.readouterr().err
    assert cli.main(base + ["--kb", "ipas", "--index", second["index_id"]]) == 1
    assert "不屬於" in capsys.readouterr().err

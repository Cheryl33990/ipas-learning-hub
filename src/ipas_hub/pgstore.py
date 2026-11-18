"""PostgreSQL＋pgvector 知識庫儲存。

檔案索引（index.json＋vectors.npy）是版本來源；這裡把驗證過的索引載入資料庫，讀回時重建相同內容並重算
index_id 與向量雜湊，被改過就拒絕。通用欄位放成欄，文件專屬資訊（章節頁碼、PDF 頁、勘誤報告等）放在 jsonb，
換成其他主題或公司文件時不必改表。關鍵字排序（BM25）仍在程式內計算；向量近鄰由資料庫計算。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from .knowledge import KnowledgeBase, knowledge_base_id

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS kb_index (
    index_id text PRIMARY KEY,
    loaded_at timestamptz NOT NULL DEFAULT now(),
    embedding_model text,
    embedding_revision text,
    dimensions integer,
    manifest jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS kb_source (
    index_id text NOT NULL REFERENCES kb_index (index_id) ON DELETE CASCADE,
    ord integer NOT NULL,
    source_id text NOT NULL,
    name text NOT NULL,
    version text NOT NULL,
    sha256 text NOT NULL,
    metadata jsonb NOT NULL,
    PRIMARY KEY (index_id, source_id)
);
CREATE TABLE IF NOT EXISTS kb_chunk (
    index_id text NOT NULL REFERENCES kb_index (index_id) ON DELETE CASCADE,
    ord integer NOT NULL,
    chunk_id text NOT NULL,
    source_id text NOT NULL,
    text text NOT NULL,
    metadata jsonb NOT NULL,
    embedding vector,
    PRIMARY KEY (index_id, ord),
    UNIQUE (index_id, chunk_id)
);
"""
SOURCE_COLUMNS = ("id", "name", "version", "sha256")
CHUNK_COLUMNS = ("id", "source", "text")


def rows_from_index(payload: dict, vectors) -> dict:
    """把（已含 index_id 的）索引內容拆成三張表的資料列；先驗證，未通過不產生資料列。"""
    KnowledgeBase(payload, vectors)  # 雜湊、向量維度與向量雜湊都不符就拋錯
    meta = payload["embedding"] or {}
    manifest = {k: v for k, v in payload.items() if k not in {"index_id", "chunks", "sources"}}
    index = {
        "index_id": payload["index_id"],
        "embedding_model": meta.get("name"),
        "embedding_revision": meta.get("revision"),
        "dimensions": meta.get("dimensions"),
        "manifest": manifest,
    }
    sources = [
        {
            "ord": n,
            "source_id": s["id"],
            "name": s["name"],
            "version": s["version"],
            "sha256": s["sha256"],
            "metadata": {k: v for k, v in s.items() if k not in SOURCE_COLUMNS},
        }
        for n, s in enumerate(payload["sources"])
    ]
    chunks = [
        {
            "ord": i,
            "chunk_id": c["id"],
            "source_id": c["source"],
            "text": c["text"],
            "metadata": {k: v for k, v in c.items() if k not in CHUNK_COLUMNS},
            "embedding": None if vectors is None else [float(x) for x in vectors[i]],
        }
        for i, c in enumerate(payload["chunks"])
    ]
    return {"index": index, "sources": sources, "chunks": chunks}


def index_from_rows(index: dict, sources: list[dict], chunks: list[dict]):
    """由資料列重建索引內容與向量；呼叫端再交給 KnowledgeBase 驗證 index_id。"""
    manifest = index["manifest"] if isinstance(index["manifest"], dict) else json.loads(index["manifest"])
    payload = {
        "index_id": index["index_id"],
        **manifest,
        "sources": [
            {"id": s["source_id"], "name": s["name"], "version": s["version"], "sha256": s["sha256"], **s["metadata"]}
            for s in sorted(sources, key=lambda s: s["ord"])
        ],
        "chunks": [],
    }
    ordered = sorted(chunks, key=lambda c: c["ord"])
    if [c["ord"] for c in ordered] != list(range(len(ordered))):
        raise ValueError("資料庫中的片段順序不連續")
    payload["chunks"] = [
        {"id": c["chunk_id"], "source": c["source_id"], "text": c["text"], **c["metadata"]} for c in ordered
    ]
    embedded = [c["embedding"] is not None for c in ordered]
    if any(embedded) and not all(embedded):
        raise ValueError("資料庫中只有部分片段有向量")
    vectors = np.asarray([c["embedding"] for c in ordered], dtype=np.float32) if all(embedded) and ordered else None
    return payload, vectors


def connect(dsn: str | None = None):
    """連線字串只讀參數或 PG_DSN；密碼可放在 PGPASSWORD，不寫進執行紀錄。"""
    dsn = dsn or os.getenv("PG_DSN")
    if not dsn:
        raise ValueError("使用 --store pg 需設定環境變數 PG_DSN，例如 host=127.0.0.1 port=5433 dbname=ipas user=ipas")
    try:
        import psycopg
    except ImportError as exc:
        raise ImportError("缺少 psycopg，請先安裝選用相依：uv sync --extra pg") from exc
    try:
        return psycopg.connect(dsn, autocommit=True)
    except psycopg.Error as exc:
        raise ValueError(f"無法連線資料庫：{exc}") from exc


def _db_errors():
    import psycopg

    return psycopg.Error


def ensure_schema(conn) -> None:
    conn.execute(SCHEMA)


def load_index(conn, payload: dict, vectors) -> bool:
    """載入一份索引；同一個 index_id 已存在就略過並回傳 False。整份在同一個交易內寫入。"""
    rows = rows_from_index(payload, vectors)
    try:
        ensure_schema(conn)
        with conn.transaction():
            if conn.execute("SELECT 1 FROM kb_index WHERE index_id = %s", (payload["index_id"],)).fetchone():
                return False
            i = rows["index"]
            conn.execute(
                "INSERT INTO kb_index (index_id, embedding_model, embedding_revision, dimensions, manifest)"
                " VALUES (%s, %s, %s, %s, %s::jsonb)",
                (
                    i["index_id"],
                    i["embedding_model"],
                    i["embedding_revision"],
                    i["dimensions"],
                    json.dumps(i["manifest"], ensure_ascii=False),
                ),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO kb_source (index_id, ord, source_id, name, version, sha256, metadata)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                    [
                        (
                            i["index_id"],
                            s["ord"],
                            s["source_id"],
                            s["name"],
                            s["version"],
                            s["sha256"],
                            json.dumps(s["metadata"], ensure_ascii=False),
                        )
                        for s in rows["sources"]
                    ],
                )
                cur.executemany(
                    "INSERT INTO kb_chunk (index_id, ord, chunk_id, source_id, text, metadata, embedding)"
                    " VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::real[]::vector)",
                    [
                        (
                            i["index_id"],
                            c["ord"],
                            c["chunk_id"],
                            c["source_id"],
                            c["text"],
                            json.dumps(c["metadata"], ensure_ascii=False),
                            c["embedding"],
                        )
                        for c in rows["chunks"]
                    ],
                )
        return True
    except _db_errors() as exc:
        raise ValueError(f"載入資料庫失敗：{exc}") from exc


def select_index(
    conn, index_id: str | None = None, kb: str | None = None, with_vectors: bool = False, prefer_vectors: bool = False
) -> str:
    """先限定庫，再選版本；多庫未指定範圍時不採用全域最新。"""
    try:
        return _select_index(conn, index_id, kb, with_vectors, prefer_vectors)
    except _db_errors() as exc:
        raise ValueError(f"選擇知識庫失敗：{exc}") from exc


def _select_index(conn, index_id, kb, with_vectors, prefer_vectors):
    if not conn.execute("SELECT to_regclass('kb_index')").fetchone()[0]:
        raise ValueError("資料庫中找不到索引，請先執行 pg-load")
    if kb is not None:
        knowledge_base_id({"knowledge_base": kb})
    if index_id is not None:
        row = conn.execute("SELECT manifest FROM kb_index WHERE index_id = %s", (index_id,)).fetchone()
        if not row:
            raise ValueError(f"資料庫中找不到索引 {index_id}")
        if kb is not None and knowledge_base_id(row[0]) != kb:
            raise ValueError("指定索引不屬於選定知識庫")
        return index_id
    names = [
        r[0]
        for r in conn.execute("SELECT DISTINCT COALESCE(manifest->>'knowledge_base', 'ipas') FROM kb_index").fetchall()
    ]
    if kb is None:
        if len(names) > 1:
            raise ValueError("有多個知識庫，請指定 --kb 或 --index，拒絕自動跨庫選擇")
        kb = names[0] if names else "ipas"
    row = conn.execute(
        "SELECT index_id FROM kb_index WHERE COALESCE(manifest->>'knowledge_base', 'ipas') = %s"
        " AND (%s OR dimensions IS NOT NULL)"
        " ORDER BY (%s AND dimensions IS NOT NULL) DESC, loaded_at DESC, index_id LIMIT 1",
        (kb, not with_vectors, prefer_vectors),
    ).fetchone()
    if not row:
        raise ValueError(f"知識庫 {kb} 找不到適用索引，請先建立並載入")
    return row[0]


def read_index(conn, index_id: str | None = None, with_vectors: bool = False, kb: str | None = None):
    """讀回一份索引；未指定 index_id 時取最近載入的（with_vectors 時只考慮含向量的）。

    回傳（索引內容, 向量或 None），尚未驗證。
    """
    try:
        index_id = select_index(conn, index_id, kb, with_vectors)
        index = conn.execute("SELECT index_id, manifest FROM kb_index WHERE index_id = %s", (index_id,)).fetchone()
        if not index:
            raise ValueError(f"資料庫中找不到索引 {index_id}")
        sources = conn.execute(
            "SELECT ord, source_id, name, version, sha256, metadata FROM kb_source WHERE index_id = %s ORDER BY ord",
            (index_id,),
        ).fetchall()
        chunks = conn.execute(
            "SELECT ord, chunk_id, source_id, text, metadata, embedding::real[] FROM kb_chunk"
            " WHERE index_id = %s ORDER BY ord",
            (index_id,),
        ).fetchall()
    except _db_errors() as exc:
        raise ValueError(f"讀取資料庫失敗：{exc}") from exc
    return index_from_rows(
        {"index_id": index[0], "manifest": index[1]},
        [dict(zip(("ord", "source_id", "name", "version", "sha256", "metadata"), r)) for r in sources],
        [dict(zip(("ord", "chunk_id", "source_id", "text", "metadata", "embedding"), r)) for r in chunks],
    )


def has_vectors(conn, index_id: str | None = None) -> bool:
    """指定的索引（或未指定時，資料庫中任一索引）是否含向量。"""
    try:
        if index_id:
            row = conn.execute(
                "SELECT dimensions IS NOT NULL FROM kb_index WHERE index_id = %s", (index_id,)
            ).fetchone()
            return bool(row and row[0])
        if not conn.execute("SELECT to_regclass('kb_index')").fetchone()[0]:
            return False
        return bool(conn.execute("SELECT 1 FROM kb_index WHERE dimensions IS NOT NULL LIMIT 1").fetchone())
    except _db_errors() as exc:
        raise ValueError(f"讀取資料庫失敗：{exc}") from exc


def nearest(conn, index_id: str):
    """回傳「查詢向量 → 最近片段的序號」函式；向量已正規化，以餘弦距離排序，距離相同時依序號。"""

    def search(query_vector, n: int) -> list[int]:
        try:
            rows = conn.execute(
                "SELECT ord FROM kb_chunk WHERE index_id = %s AND embedding IS NOT NULL"
                " ORDER BY embedding <=> %s::real[]::vector, ord LIMIT %s",
                (index_id, [float(x) for x in query_vector], n),
            ).fetchall()
        except _db_errors() as exc:
            raise ValueError(f"資料庫向量檢索失敗：{exc}") from exc
        return [r[0] for r in rows]

    return search


def open_knowledge_base(conn, index_id: str | None = None, vector: bool = False, encoder=None) -> KnowledgeBase:
    """讀回並驗證索引；需要向量時載入對應模型，查詢交給資料庫。驗證後不把向量留在記憶體。"""
    payload, vectors = read_index(conn, index_id, with_vectors=vector)
    kb = KnowledgeBase(payload, vectors if vector else None)
    if vector:
        if vectors is None:
            raise ValueError("此索引沒有向量，請改用 --method bm25，或以 --embedding-model 重建後再載入")
        if encoder is None:
            kb.attach_encoder()
        else:
            kb.encoder = encoder
        kb.vectors = None
        kb.vector_search = nearest(conn, kb.index_id)
    return kb


def read_index_files(index_path: Path):
    """讀檔案索引與（若有）向量檔，供 pg-load 使用。"""
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    vectors = None
    if payload.get("embedding"):
        vectors = np.load(index_path.with_name("vectors.npy"), allow_pickle=False)
    return payload, vectors

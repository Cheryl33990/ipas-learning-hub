"""雙科知識庫：只收教材，版本化保存來源、勘誤與可選本機向量。"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np

from .bm25 import BM25
from .guide import apply_patches, chunk_pages, read_pages
from .text import tokenize

SCHEMA_VERSION = 1
VECTOR_POOL = 20  # k 上限與混合檢索各取前 20；外部向量儲存只需回傳這麼多


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def data_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to((root / "data").resolve()):
        raise ValueError("原始資料、索引與評估輸出必須位於 data/ 下")
    return path


# 句向量模型用不到的檔案（ONNX 版本、圖片、附加的稀疏／多向量權重）。README 的下載指令排除同一組，
# 載入時也忽略它們，避免 huggingface_hub 依下載清單把它們當成缺漏而拒絕離線載入。
EMBEDDING_IGNORE = ["onnx/*", "openvino/*", "imgs/*", "*.jpg", "*.png", "*.webp", "*.pt", ".gitattributes"]


def local_encoder(model: str, revision: str | None = None):
    """只使用本機 HF 快取；索引與查詢固定使用相同 snapshot。"""
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer

    path = snapshot_download(model, revision=revision, local_files_only=True, ignore_patterns=EMBEDDING_IGNORE)
    encoder = SentenceTransformer(path, device="cpu", local_files_only=True)
    return encoder, Path(path).name


def build_index(root: Path, config_path: Path, output: Path,
                embedding_model: str | None = None) -> Path:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("不支援的來源設定版本")
    size, stride = config["chunk_size"], config["chunk_stride"]
    if not (isinstance(size, int) and isinstance(stride, int) and 0 < stride <= size):
        raise ValueError("切塊設定須為 0 < stride <= size")
    chunks, sources, ids = [], [], set()
    for spec in config["sources"]:
        source = spec["id"]
        if source in ids:
            raise ValueError(f"重複來源：{source}")
        ids.add(source)
        pdf = data_path(root, spec["pdf"])
        sha = digest(pdf.read_bytes())
        if sha != spec["sha256"]:
            raise ValueError(f"教材版本雜湊不一致：{source}")
        if spec.get("patches"):
            patch_bytes = data_path(root, spec["patches"]).read_bytes()
            patches, patch_sha = json.loads(patch_bytes), digest(patch_bytes)
        else:  # 勘誤替換檔含教材原文、不進版控；他人重現時可能沒有，此時明確記錄未套用
            patches, patch_sha = [], None
        # 頁首規則屬教材專屬設定；未設定時沿用預設，索引內容與先前相同
        pages, report = apply_patches(read_pages(pdf, running_head=spec.get("running_head")), patches)
        if not pages or any(not p["applied_on"] for p in report):
            raise ValueError(f"教材頁面或勘誤套用失敗：{source}")
        labels = [p.label for p in pages]
        if len(labels) != len(set(labels)):
            raise ValueError(f"教材頁碼重複：{source}")
        sources.append({"id": source, "name": spec["name"], "version": spec["version"], "pdf": spec["pdf"],
                        "sha256": sha, "patch_sha256": patch_sha, "patch_report": report,
                        "errata": "applied" if patches else "not_applied", "pages": len(pages),
                        **({"running_head": spec["running_head"]} if spec.get("running_head") else {})})
        for chunk in chunk_pages(pages, size, stride):
            chunks.append({"id": f"{source}:{chunk.label}:{chunk.index}", "source": source,
                           "page": chunk.label, "text": chunk.text,
                           **({"pdf_page": chunk.pdf_page} if chunk.pdf_page else {})})
    if not chunks:
        raise ValueError("知識庫不可為空")
    model_meta, vectors = None, None
    if embedding_model:
        encoder, revision = local_encoder(embedding_model)
        vectors = np.asarray(encoder.encode([c["text"] for c in chunks],
                             normalize_embeddings=True, batch_size=8,
                             show_progress_bar=False), dtype=np.float32)
        if vectors.ndim != 2 or len(vectors) != len(chunks) or not np.isfinite(vectors).all():
            raise ValueError("模型輸出向量無效")
        model_meta = {"name": embedding_model, "revision": revision,
                      "dimensions": vectors.shape[1], "sha256": digest(vectors.tobytes())}
    code_version = os.getenv("IPAS_CODE_VERSION", "unavailable")
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        if result.returncode == 0:
            code_version = result.stdout.strip()
    except FileNotFoundError:
        pass  # runtime 映像不需要安裝 Git，仍保存實際程式檔案雜湊。
    code_hashes = {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}
    payload = {"schema_version": SCHEMA_VERSION, "sources": sources, "chunks": chunks,
               "chunk_size": size, "chunk_stride": stride, "embedding": model_meta,
               "code_version": code_version,
               "code_sha256": code_hashes,
               "lock_sha256": digest((root / "uv.lock").read_bytes())}
    index_id = digest(canonical(payload))
    folder = data_path(root, str(output)) / index_id
    folder.mkdir(parents=True, exist_ok=True)
    if vectors is not None:
        np.save(folder / "vectors.npy", vectors, allow_pickle=False)
    (folder / "index.json").write_bytes(canonical({"index_id": index_id, **payload}))
    return folder / "index.json"


class KnowledgeBase:
    def __init__(self, payload: dict, vectors=None, encoder=None, vector_search=None):
        """vector_search(查詢向量, n) 回傳最近片段的序號；未提供時用記憶體中的向量計算（檔案索引）。"""
        payload = dict(payload)
        self.index_id = payload.pop("index_id")
        if digest(canonical(payload)) != self.index_id:
            raise ValueError("索引內容與版本雜湊不一致")
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("不支援的索引版本")
        self.payload, self.chunks = payload, payload["chunks"]
        self.sources = {s["id"]: s for s in payload["sources"]}
        self.bm25 = BM25([tokenize(c["text"]) for c in self.chunks])
        self.vectors, self.encoder, self.vector_search = vectors, encoder, vector_search
        meta = payload["embedding"]
        if vectors is not None:
            if (not meta or vectors.shape != (len(self.chunks), meta["dimensions"])
                    or not np.isfinite(vectors).all()
                    or digest(vectors.tobytes()) != meta["sha256"]):
                raise ValueError("向量檔與索引版本不一致")

    @classmethod
    def load(cls, path: Path, vector: bool = False):
        payload = json.loads(path.read_text(encoding="utf-8"))
        vectors = np.load(path.with_name("vectors.npy"), allow_pickle=False) if vector else None
        kb = cls(payload, vectors)
        if vector:
            kb.attach_encoder()
        return kb

    def attach_encoder(self) -> None:
        """載入索引記錄的嵌入模型（只用本機快取，revision 須相同）。"""
        meta = self.payload["embedding"]
        if not meta:
            raise ValueError("此索引沒有向量，無法使用向量或混合檢索")
        self.encoder, revision = local_encoder(meta["name"], meta["revision"])
        if revision != meta["revision"]:
            raise ValueError("查詢模型 revision 與索引不同")

    def search(self, query: str, k: int = 5, method: str = "bm25") -> list[dict]:
        if not query.strip() or not (1 <= k <= 20):
            raise ValueError("問題不可空白，k 須介於 1 至 20")
        if method not in {"bm25", "vector", "hybrid"}:
            raise ValueError("不支援的檢索方法")
        lexical = self.bm25.scores(tokenize(query))
        keyword = sorted((i for i, s in enumerate(lexical) if s > 0),
                         key=lambda i: (-lexical[i], i))
        ranks = keyword
        if method in {"vector", "hybrid"}:
            if (self.vectors is None and self.vector_search is None) or self.encoder is None:
                raise ValueError("本索引或查詢未載入向量模型")
            qv = np.asarray(self.encoder.encode([query], normalize_embeddings=True))[0]
            if qv.shape != (self.payload["embedding"]["dimensions"],) or not np.isfinite(qv).all():
                raise ValueError("查詢向量維度不符或數值無效")
            if self.vector_search is not None:
                vector_rank = self.vector_search(qv, VECTOR_POOL)
            else:
                similarities = self.vectors @ qv
                vector_rank = sorted(range(len(self.chunks)), key=lambda i: (-similarities[i], i))
            if method == "vector":
                ranks = vector_rank
            else:
                fused = {}
                for ranking in (keyword[:20], vector_rank[:20]):
                    for rank, i in enumerate(ranking, 1):
                        fused[i] = fused.get(i, 0) + 1 / (60 + rank)
                ranks = sorted(fused, key=lambda i: (-fused[i], i))
        return [{**self.chunks[i], "name": self.sources[self.chunks[i]["source"]]["name"],
                 "version": self.sources[self.chunks[i]["source"]]["version"],
                 "rank": rank, "index_id": self.index_id}
                for rank, i in enumerate(ranks[:k], 1)]

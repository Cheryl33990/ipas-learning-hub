"""探索二：同一批題目、同一份切塊，比較 BM25 與向量檢索找回依據頁的能力。

用法：uv run python -m ipas_hub.explore2
輸入都在 data/raw/（不進版控）；輸出 data/index/explore2_results.json（不進版控）
與 docs/project/discovery/exploration-2-results.md（只含題號與頁碼，不含題目或教材原文）。
判準見 docs/project/brief.md 的探索二。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from .bm25 import BM25
from .exam import read_questions
from .guide import apply_patches, chunk_pages, read_pages
from .record import parse_record
from .scoring import first_hit_rank, hit_at_k
from .text import tokenize

KS = (1, 3, 5)
TOP_N = 5
DEFAULT_MODEL = "BAAI/bge-m3"


def _one(folder: Path) -> Path:
    files = sorted(folder.glob("*.pdf"))
    if len(files) != 1:
        sys.exit(f"{folder} 應該只有一個 PDF，找到 {len(files)} 個")
    return files[0]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vector_rank(model_name: str, chunk_texts: list[str], queries: list[str], top_n: int) -> list[list[int]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    doc = model.encode(chunk_texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
    qry = model.encode(queries, normalize_embeddings=True, batch_size=8, show_progress_bar=False)
    sims = qry @ doc.T
    return [sorted(range(len(chunk_texts)), key=lambda i: (-row[i], i))[:top_n] for row in sims]


def run(root: Path, model_name: str) -> dict:
    guide_pdf, exam_pdf = _one(root / "data/raw/guide"), _one(root / "data/raw/exam")
    record_path = root / "docs/project/discovery/exploration-1-record.md"
    patch_path = root / "data/index/errata_patches.json"

    pages = read_pages(guide_pdf)
    patches = json.loads(patch_path.read_text(encoding="utf-8")) if patch_path.exists() else []
    pages, patch_report = apply_patches(pages, patches)
    chunks = chunk_pages(pages)
    questions = read_questions(exam_pdf)
    gold = parse_record(record_path.read_text(encoding="utf-8"))

    numbers = [q.number for q in questions]
    if numbers != list(range(1, 51)):
        sys.exit(f"試題切分結果不是 1–50 題：{numbers}")
    mismatched = [q.number for q in questions if gold[q.number].answer != q.answer]
    if mismatched:
        sys.exit(f"紀錄表的答案與試題答案欄不一致：{mismatched}")

    texts = [c.text for c in chunks]
    queries = [q.text for q in questions]
    bm25 = BM25([tokenize(t) for t in texts])
    ranked = {
        "bm25": [bm25.top(tokenize(q), TOP_N) for q in queries],
        "vector": vector_rank(model_name, texts, queries, TOP_N),
    }

    per_question = []
    for qi, q in enumerate(questions):
        g = gold[q.number]
        row = {"number": q.number, "type": g.type, "gold_pages": sorted(g.pages)}
        for method, ranks in ranked.items():
            labels = [chunks[i].label for i in ranks[qi]]
            row[method] = {
                "top_pages": labels,
                "first_hit_rank": first_hit_rank(labels, g.pages) if g.pages else None,
                **{f"hit@{k}": hit_at_k(labels, g.pages, k) for k in KS},
            }
        per_question.append(row)

    scored = [r for r in per_question if r["type"] in ("A", "B")]
    summary = {
        method: {f"hit@{k}": sum(r[method][f"hit@{k}"] for r in scored) for k in KS}
        for method in ranked
    }
    return {
        "inputs": {
            "guide_sha256": _sha(guide_pdf),
            "exam_sha256": _sha(exam_pdf),
            "record_sha256": _sha(record_path),
            "model": model_name,
            "chunk_size": 400,
            "chunk_stride": 300,
            "pages": len(pages),
            "chunks": len(chunks),
            "patches": patch_report,
        },
        "scored_questions": len(scored),
        "summary": summary,
        "questions": per_question,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    result = run(args.root, args.model)
    out = args.root / "data/index/explore2_results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("inputs", "scored_questions", "summary")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

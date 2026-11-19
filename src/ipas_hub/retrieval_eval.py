"""離線切塊／embedding 實驗。結果只供比較，不寫入正式索引或服務。

python -m ipas_hub.retrieval_eval --plan examples/ipas/eval/retrieval-plan.json
    --cases data/evaluation/retrieval-dev.json --out data/evaluation/retrieval-study
"""

from __future__ import annotations

import argparse
import gc
import json
import platform
import re
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np

from .knowledge import EMBEDDING_IGNORE, KnowledgeBase, build_index, canonical, data_path, digest


def load_cases(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("split") not in {"development", "test"}:
        raise ValueError("split must be development or test")
    if data.get("label_status") not in {"ai-provisional", "human-reviewed"}:
        raise ValueError("label_status must explicitly describe review")
    if data["split"] == "test" and data["label_status"] != "human-reviewed":
        raise ValueError("test requires human-reviewed labels; review alone does not prove no leakage")
    if data["label_status"] == "human-reviewed" and not data.get("review_record"):
        raise ValueError("human-reviewed labels require review_record")
    if not data.get("cases"):
        raise ValueError("cases must not be empty")
    ids = set()
    for c in data["cases"]:
        if not isinstance(c.get("id"), str) or not c["id"] or c["id"] in ids:
            raise ValueError("case ids must be unique nonempty strings")
        ids.add(c["id"])
        if not isinstance(c.get("query"), str) or not c["query"].strip():
            raise ValueError("query must not be empty")
        if not isinstance(c.get("expected"), list):
            raise ValueError("expected must be explicit; [] means known unanswerable, not unjudged")
        pages = []
        for p in c["expected"]:
            if any(not isinstance(p.get(k), str) or not p[k] for k in ("source", "page")):
                raise ValueError("expected pages require source and page strings")
            pages.append((p["source"], p["page"]))
        if len(set(pages)) != len(pages):
            raise ValueError("duplicate reference pages")
        if "evidence" in c:
            validate_evidence(c)
    return data


JUDGMENTS = {"direct", "partial", "unsupported", "uncertain"}


def validate_evidence(case: dict) -> None:
    """evidence 是「全部 requirement 都要滿足」；每個 requirement 內的 alternatives 互為等價替代。"""
    requirements = case["evidence"]
    if not case["expected"] or not isinstance(requirements, list) or not requirements:
        raise ValueError("evidence requires an answerable case and at least one requirement")
    ids = set()
    for r in requirements:
        if not isinstance(r.get("id"), str) or not r["id"] or r["id"] in ids or not isinstance(r.get("claim"), str):
            raise ValueError("evidence requirements need unique ids and a claim")
        ids.add(r["id"])
        alternatives = r.get("alternatives")
        if not isinstance(alternatives, list) or not alternatives:
            raise ValueError("evidence requirements need alternatives")
        for a in alternatives:
            if any(not isinstance(a.get(k), str) or not a[k] for k in ("source", "page", "quote")):
                raise ValueError("evidence alternatives need source, page and quote")
            if a.get("judgment") not in JUDGMENTS:
                raise ValueError("evidence judgment must be direct, partial, unsupported or uncertain")
        if not any(a["judgment"] == "direct" for a in alternatives):
            raise ValueError("each requirement needs direct evidence; partial evidence alone is not scored")


def chunk_start(chunk: dict, stride: int) -> int:
    return int(chunk["id"].rsplit(":", 1)[1]) * stride


def page_texts(chunks: list[dict], stride: int) -> dict:
    """由不跨頁的固定視窗片段還原每頁全文，並核對片段位移。"""
    pages = {}
    for ch in chunks:
        key, start = (ch["source"], ch["page"]), chunk_start(ch, stride)
        text = pages.get(key, "")
        if start > len(text) or text[start:] != ch["text"][: len(text) - start]:
            raise ValueError("chunk offsets are inconsistent with the stride")
        pages[key] = text + ch["text"][len(text) - start :]
    return pages


def locate_evidence(case: dict, pages: dict) -> list[dict]:
    """每段引文都必須逐字存在於解析頁；只有 direct 引文參與計分，其他判定只供複核。"""
    located = []
    for r in case["evidence"]:
        spans = []
        for a in r["alternatives"]:
            text = pages.get((a["source"], a["page"]))
            if text is None or a["quote"] not in text:
                raise ValueError(f"evidence quote not found in parsed page: {case['id']}/{r['id']}")
            if a["judgment"] != "direct":
                continue
            start = text.find(a["quote"])
            while start >= 0:
                spans.append((a["source"], a["page"], start, start + len(a["quote"])))
                start = text.find(a["quote"], start + 1)
        located.append({"id": r["id"], "spans": spans})
    return located


def score_evidence(case: dict, located: list[dict], hits: list[dict], stride: int) -> dict:
    covered, singles, first = {}, [], None
    met = [False] * len(located)
    for rank, h in enumerate(hits, 1):
        start = chunk_start(h, stride)
        interval = (h["source"], h["page"], start, start + len(h["text"]))
        singles.append(interval)
        covered.setdefault(interval[:2], set()).update(range(interval[2], interval[3]))
        met = [any(set(range(a, b)) <= covered.get((s, p), set()) for s, p, a, b in r["spans"]) for r in located]
        if first is None and all(met):
            first = rank
    intact = all(
        any(s == hs and p == hp and ha <= a and b <= hb for s, p, a, b in r["spans"] for hs, hp, ha, hb in singles)
        for r in located
    )
    return {
        "complete": int(all(met)),
        "intact": int(intact),
        "requirement_recall": sum(met) / len(located),
        "first_complete_rank": first,
        "reciprocal_rank": 1 / first if first else 0.0,
    }


def budget_prefix(hits: list[dict], budget: int) -> list[dict]:
    """固定上下文字元預算：依排名累加，超過預算就停止，避免大切塊用同一 k 取得更多原文。"""
    used, prefix = 0, []
    for h in hits:
        used += len(h["text"])
        if used > budget:
            break
        prefix.append(h)
    return prefix


def validate_plan(plan: dict) -> None:
    if not plan.get("chunks") or not plan.get("models"):
        raise ValueError("chunks and models must not be empty")
    for group in (plan["chunks"], plan["models"]):
        ids = [x.get("id", "") for x in group]
        if len(set(ids)) != len(ids) or any(not re.fullmatch(r"[a-z0-9_-]+", x) for x in ids):
            raise ValueError("variant ids must be unique safe names")
    for c in plan["chunks"]:
        if not (type(c.get("size")) is int and type(c.get("stride")) is int and 0 < c["stride"] <= c["size"]):
            raise ValueError("chunk stride must be > 0 and <= size")
    for m in plan["models"]:
        if not re.fullmatch(r"[a-f0-9]{40}", m.get("revision", "")):
            raise ValueError("model revision must be pinned to a commit")
        if any(not isinstance(m.get(k), str) for k in ("name", "query_prefix", "document_prefix")):
            raise ValueError("model name and prefixes must be explicit strings")
        if m["name"].startswith("intfloat/multilingual-e5") and (m["query_prefix"], m["document_prefix"]) != (
            "query: ",
            "passage: ",
        ):
            raise ValueError("E5 requires query: / passage: prefixes")
    ks = plan.get("ks", [])
    if not ks or len(set(ks)) != len(ks) or any(type(k) is not int or not 1 <= k <= 20 for k in ks):
        raise ValueError("ks must be unique integers between 1 and 20")
    if type(plan.get("repeats")) is not int or plan["repeats"] < 1:
        raise ValueError("repeats must be positive")
    budgets = plan.get("budgets", [])
    if len(set(budgets)) != len(budgets) or any(type(b) is not int or b < 1 for b in budgets):
        raise ValueError("budgets must be unique positive character counts")


def score_hits(case: dict, hits: list[dict], k: int) -> dict:
    hits = hits[:k]
    expected = {(p["source"], p["page"]) for p in case["expected"]}
    pages = [(h["source"], h["page"]) for h in hits]
    first = next((i for i, p in enumerate(pages, 1) if p in expected), None)
    return {
        "case": case["id"],
        "k": k,
        "answerable": bool(expected),
        "hit": int(first is not None) if expected else None,
        "page_recall": len(set(pages) & expected) / len(expected) if expected else None,
        "reciprocal_rank": (1 / first if first else 0.0) if expected else None,
        "duplicate_page_fraction": 1 - len(set(pages)) / len(pages) if pages else 0.0,
        "context_chars": sum(len(h["text"]) for h in hits),
        "chunks_returned": len(hits),
        "returned_any": bool(hits),
        "pages": [{"source": s, "page": p} for s, p in pages],
    }


def summarize(rows: list[dict]) -> dict:
    positive = [r for r in rows if r["answerable"]]
    evidence = [r for r in rows if r.get("evidence")]
    negative = [r for r in rows if not r["answerable"]]

    def mean(items, key):
        return float(np.mean([r[key] for r in items])) if items else None

    return {
        "cases": len(rows),
        "answerable_cases": len(positive),
        "unanswerable_cases": len(negative),
        **{key: mean(positive, key) for key in ("hit", "page_recall", "reciprocal_rank")},
        **{key: mean(rows, key) for key in ("duplicate_page_fraction", "context_chars", "chunks_returned")},
        "unanswerable_returned_any_rate": mean(negative, "returned_any"),
        "evidence_cases": len(evidence),
        **{
            f"evidence_{key}": mean([r["evidence"] for r in evidence], key)
            for key in ("complete", "intact", "requirement_recall", "reciprocal_rank")
        },
    }


class QueryEncoder:
    def __init__(self, encoder, prefix: str):
        self.encoder, self.prefix = encoder, prefix

    def encode(self, texts, **kwargs):
        return self.encoder.encode([self.prefix + t for t in texts], **kwargs)


def token_stats(encoder, texts: list[str]) -> dict:
    lengths = []
    for start in range(0, len(texts), 32):
        tokens = encoder.tokenizer(texts[start : start + 32], truncation=False, padding=False)["input_ids"]
        lengths.extend(len(t) for t in tokens)
    limit = encoder.max_seq_length
    return {
        "max_seq_length": limit,
        "texts": len(lengths),
        "max_tokens": max(lengths),
        "truncated_texts": sum(n > limit for n in lengths),
    }


DEPTH = 20  # KnowledgeBase.search 的上限；保存完整排名供固定預算與日後重評，不需重跑模型。


def score_cutoff(case, hits, k, evidence, stride, **extra) -> dict:
    row = {**score_hits(case, hits, k), **extra}
    if case["id"] in evidence:
        row["evidence"] = score_evidence(case, evidence[case["id"]], hits[:k], stride)
    return row


def evaluate(kb, cases, method: str, ks: list[int], repeats: int, budgets=(), evidence=None) -> dict:
    # Warmup excluded; every measured search includes query encoding for vector/hybrid.
    evidence, stride = evidence or {}, kb.payload["chunk_stride"]
    kb.search(cases[0]["query"], k=DEPTH, method=method)
    rows, budget_rows, latency, rankings = [], [], [], {}
    stable = True
    for repeat in range(repeats):
        ordered = cases[repeat % len(cases) :] + cases[: repeat % len(cases)]
        for c in ordered:
            start = time.perf_counter()
            hits = kb.search(c["query"], k=DEPTH, method=method)
            latency.append((time.perf_counter() - start) * 1000)
            ids = [h["id"] for h in hits]
            if repeat == 0:
                rankings[c["id"]] = ids
                rows.extend(score_cutoff(c, hits, k, evidence, stride) for k in ks)
                for b in budgets:
                    prefix = budget_prefix(hits, b)
                    budget_rows.append(score_cutoff(c, prefix, len(prefix), evidence, stride, budget=b))
            else:
                stable = stable and rankings[c["id"]] == ids
    return {
        "method": method,
        "rows": rows,
        "budget_rows": budget_rows,
        "rankings": rankings,
        "rankings_stable": stable,
        "summary": {str(k): summarize([r for r in rows if r["k"] == k]) for k in ks},
        "budget_summary": {str(b): summarize([r for r in budget_rows if r["budget"] == b]) for b in budgets},
        "retrieval_ms": {
            "p50": float(np.percentile(latency, 50)),
            "p95": float(np.percentile(latency, 95)),
            "samples": len(latency),
        },
    }


def write_json(path: Path, data) -> None:
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def reused_vectors(old_dir: Path, model: dict, base) -> tuple[np.ndarray, dict]:
    """沿用先前實驗的文件向量：片段全文、模型 revision、前綴與向量雜湊都相同才接受。"""
    try:
        old = json.loads((old_dir / f"{model['id']}-vector.json").read_text(encoding="utf-8"))
        vectors = np.load(old_dir / f"{model['id']}-vectors.npy", allow_pickle=False)
    except FileNotFoundError as error:
        raise ValueError(f"reused vectors missing: {error.filename}") from error
    same_chunks = any(
        json.loads(p.read_text(encoding="utf-8"))["chunks"] == base.chunks for p in old_dir.glob("indexes/*/index.json")
    )
    keys = ("name", "revision", "query_prefix", "document_prefix")
    if (
        not same_chunks
        or any(old["model"].get(k) != model[k] for k in keys)
        or vectors.shape != (len(base.chunks), old["dimensions"])
        or digest(vectors.tobytes()) != old["vector_sha256"]
        or not np.isfinite(vectors).all()
    ):
        raise ValueError("reused vectors do not match chunks, model contract or recorded hash")
    return vectors.astype(np.float32, copy=False), {
        "path": str(old_dir),
        "signature": old["signature"],
        "sha256": old["vector_sha256"],
    }


def run(
    root: Path,
    plan_path: Path,
    cases_path: Path,
    output: Path,
    selected_models=(),
    selected_chunks=(),
    reuse_vectors: Path | None = None,
) -> None:
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    validate_plan(plan)
    dataset = load_cases(cases_path)
    cases = dataset["cases"]
    out = data_path(root, str(output))
    config_path = root / plan["source_config"]
    config = json.loads(config_path.read_text(encoding="utf-8"))
    # Verify input files on every invocation, including resumed runs.
    source_hashes = {}
    for s in config["sources"]:
        sha = digest(data_path(root, s["pdf"]).read_bytes())
        if sha != s["sha256"]:
            raise ValueError("source PDF hash mismatch")
        source_hashes[s["id"]] = {
            "pdf": sha,
            "patch": digest(data_path(root, s["patches"]).read_bytes()) if s.get("patches") else None,
        }
    code = {p.name: digest(p.read_bytes()) for p in Path(__file__).parent.glob("*.py")}
    inputs = {
        "plan": plan,
        "cases_sha256": digest(cases_path.read_bytes()),
        "config_sha256": digest(config_path.read_bytes()),
        "sources": source_hashes,
        "code_sha256": code,
        "lock_sha256": digest((root / "uv.lock").read_bytes()),
        # 續跑時環境不同（套件或 Python 版本）就拒絕混寫，延遲與向量才可比。
        "python": platform.python_version(),
        "packages": {n: version(n) for n in ("numpy", "sentence-transformers", "torch")},
        "reuse_vectors": str(reuse_vectors) if reuse_vectors else None,
    }
    signature = digest(canonical(inputs))
    out.mkdir(parents=True, exist_ok=True)
    meta_path = out / "meta.json"
    if meta_path.exists():
        if json.loads(meta_path.read_text(encoding="utf-8"))["signature"] != signature:
            raise ValueError("experiment inputs changed; choose a new output directory")
    else:
        write_json(
            meta_path,
            {
                "signature": signature,
                **inputs,
                "split": dataset["split"],
                "label_status": dataset["label_status"],
                "platform": platform.platform(),
            },
        )
    chunks = [c for c in plan["chunks"] if not selected_chunks or c["id"] in selected_chunks]
    models = [m for m in plan["models"] if not selected_models or m["id"] in selected_models]
    if (
        not chunks
        or not models
        or set(selected_chunks) - {c["id"] for c in chunks}
        or set(selected_models) - {m["id"] for m in models}
    ):
        raise ValueError("unknown chunk or model selection")
    bases = {}
    for c in chunks:
        variant_dir = out / c["id"]
        variant_dir.mkdir(exist_ok=True)
        variant_config = {**config, "chunk_size": c["size"], "chunk_stride": c["stride"]}
        cfg = variant_dir / "source-config.json"
        write_json(cfg, variant_config)
        start = time.perf_counter()
        index = build_index(root, cfg, variant_dir / "indexes")
        parse_ms = (time.perf_counter() - start) * 1000
        kb = KnowledgeBase.load(index)
        available = {(h["source"], h["page"]) for h in kb.chunks}
        for case in cases:
            if any((p["source"], p["page"]) not in available for p in case["expected"]):
                raise ValueError(f"reference page not in corpus: {case['id']}")
        pages = page_texts(kb.chunks, c["stride"])
        evidence = {case["id"]: locate_evidence(case, pages) for case in cases if "evidence" in case}
        bases[c["id"]] = (kb, parse_ms, evidence)
        budgets = plan.get("budgets", [])
        result_path = variant_dir / "bm25.json"
        if not result_path.exists():
            result = evaluate(kb, cases, "bm25", plan["ks"], plan["repeats"], budgets, evidence)
            write_json(
                result_path,
                {
                    "signature": signature,
                    "chunk": c,
                    "model": None,
                    "chunks": len(kb.chunks),
                    "parse_chunk_ms": parse_ms,
                    **result,
                },
            )
            print(f"completed {c['id']}/bm25", flush=True)
    from huggingface_hub import snapshot_download
    from sentence_transformers import SentenceTransformer
    import torch

    torch.set_num_threads(plan.get("cpu_threads", 4))
    for model in models:
        pending = [
            c
            for c in chunks
            if any(not (out / c["id"] / f"{model['id']}-{m}.json").exists() for m in ("vector", "hybrid"))
        ]
        if not pending:
            continue
        start = time.perf_counter()
        cache = data_path(root, model["cache_dir"]) if model.get("cache_dir") else None
        snapshot = snapshot_download(
            model["name"],
            revision=model["revision"],
            cache_dir=cache,
            local_files_only=True,
            ignore_patterns=EMBEDDING_IGNORE,
        )
        encoder = SentenceTransformer(snapshot, device="cpu", local_files_only=True)
        load_ms = (time.perf_counter() - start) * 1000
        query_tokens = token_stats(encoder, [model["query_prefix"] + c["query"] for c in cases])
        for c in pending:
            base, parse_ms, evidence = bases[c["id"]]
            texts = [model["document_prefix"] + h["text"] for h in base.chunks]
            document_tokens = token_stats(encoder, texts)
            provenance, embed_ms = None, None
            if reuse_vectors:
                vectors, provenance = reused_vectors(data_path(root, str(reuse_vectors)) / c["id"], model, base)
            else:
                start = time.perf_counter()
                vectors = np.asarray(
                    encoder.encode(texts, normalize_embeddings=True, batch_size=8, show_progress_bar=False),
                    dtype=np.float32,
                )
                embed_ms = (time.perf_counter() - start) * 1000
            if vectors.ndim != 2 or len(vectors) != len(texts) or not np.isfinite(vectors).all():
                raise ValueError("invalid document embeddings")
            # Prefix contract is experiment-only. Never export these as a production vector index.
            payload = {
                **base.payload,
                "embedding": {
                    "name": model["name"],
                    "revision": model["revision"],
                    "dimensions": vectors.shape[1],
                    "sha256": digest(vectors.tobytes()),
                },
            }
            kb = KnowledgeBase(
                {"index_id": digest(canonical(payload)), **payload},
                vectors,
                QueryEncoder(encoder, model["query_prefix"]),
            )
            np.save(out / c["id"] / f"{model['id']}-vectors.npy", vectors, allow_pickle=False)
            for method in ("vector", "hybrid"):
                result_path = out / c["id"] / f"{model['id']}-{method}.json"
                if result_path.exists():
                    continue
                result = evaluate(kb, cases, method, plan["ks"], plan["repeats"], plan.get("budgets", []), evidence)
                write_json(
                    result_path,
                    {
                        "signature": signature,
                        "chunk": c,
                        "model": model,
                        "chunks": len(kb.chunks),
                        "dimensions": vectors.shape[1],
                        "vector_bytes": vectors.nbytes,
                        "vector_sha256": digest(vectors.tobytes()),
                        "model_load_ms": load_ms,
                        "parse_chunk_ms": parse_ms,
                        "document_embedding_ms": embed_ms,
                        "vectors_reused_from": provenance,
                        "document_tokens": document_tokens,
                        "query_tokens": query_tokens,
                        **result,
                    },
                )
                print(f"completed {c['id']}/{model['id']}/{method}", flush=True)
            del kb, vectors
        del encoder
        gc.collect()
    report(out)


def report(out: Path) -> None:
    meta = json.loads((out / "meta.json").read_text(encoding="utf-8"))
    results = []
    for path in sorted(out.glob("*/*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if "summary" in row:
            if row["signature"] != meta["signature"]:
                raise ValueError("mixed experiment signatures")
            results.append(row)
    expected = len(meta["plan"]["chunks"]) * (1 + 2 * len(meta["plan"]["models"]))
    lines = [
        "# Retrieval experiment",
        "",
        f"Split: {meta['split']}; labels: {meta['label_status']}",
        f"Completed cells: {len(results)}/{expected}; no production settings changed.",
        "",
        "Page relevance is provisional unless reviewed. Page hits do not establish sentence support.",
        "k counts chunks, not deduplicated pages; repeated pages consume rank and context budget.",
        "",
        "| Chunk | Model | Method | k | Hit | Page recall | MRR | Duplicate pages | Context chars | p50 ms | p95 ms |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    def fmt(s, key):
        return f"{s[key]:.3f}" if s.get(key) is not None else "N/A"

    def name(r):
        return [r["chunk"]["id"], r["model"]["id"] if r["model"] else "none", r["method"]]

    for r in results:
        for k, s in r["summary"].items():
            values = [
                *name(r),
                k,
                *[
                    fmt(s, key)
                    for key in ("hit", "page_recall", "reciprocal_rank", "duplicate_page_fraction", "context_chars")
                ],
                f"{r['retrieval_ms']['p50']:.1f}",
                f"{r['retrieval_ms']['p95']:.1f}",
            ]
            lines.append("| " + " | ".join(values) + " |")
    evidence_keys = ("evidence_complete", "evidence_intact", "evidence_requirement_recall", "evidence_reciprocal_rank")
    if any(s.get("evidence_cases") for r in results for s in r["summary"].values()):
        lines += [
            "",
            "Evidence: complete = every required claim is covered by retrieved text; intact = each claim fits in one chunk.",
            "",
            "| Chunk | Model | Method | Cutoff | Cases | Complete | Intact | Claim recall | Evidence MRR | Chunks | Context chars |",
            "|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for r in results:
            cutoffs = [(f"k={k}", s) for k, s in r["summary"].items()]
            cutoffs += [(f"{b} chars", s) for b, s in r.get("budget_summary", {}).items()]
            for label, s in cutoffs:
                values = [*name(r), label, str(s["evidence_cases"]), *[fmt(s, key) for key in evidence_keys]]
                lines.append("| " + " | ".join(values + [fmt(s, "chunks_returned"), fmt(s, "context_chars")]) + " |")
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model", action="append", default=[])
    parser.add_argument("--chunk", action="append", default=[])
    parser.add_argument(
        "--reuse-vectors", type=Path, help="earlier output under data/ whose vectors are verified and reused"
    )
    args = parser.parse_args(argv)
    run(Path.cwd(), args.plan, args.cases, args.out, args.model, args.chunk, args.reuse_vectors)


if __name__ == "__main__":
    main()

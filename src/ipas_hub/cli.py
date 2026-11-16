"""RAG 技術原型 CLI；真實資料與執行紀錄只寫入 data/。"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

from .knowledge import KnowledgeBase, build_index, data_path
from .rag import answer, ollama_generate


def save_run(root: Path, payload: dict) -> Path:
    path = data_path(root, f"data/runs/{time.time_ns()}-{uuid.uuid4().hex[:8]}.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def evaluate(kb: KnowledgeBase, cases: list[dict], method: str, k: int) -> dict:
    rows = []
    for case in cases:
        if not case.get("expected"):
            raise ValueError("檢索評估案例須列出經選定的來源與頁碼；無依據案例另做人工評估")
        started = time.perf_counter()
        hits = kb.search(case["query"], k=k, method=method)
        found = {(h["source"], h["page"]) for h in hits}
        expected = {(e["source"], e["page"]) for e in case["expected"]}
        rows.append({"id": case["id"], "hit": bool(found & expected),
                     "retrieved": [{"source": h["source"], "page": h["page"]} for h in hits],
                     "elapsed_ms": round((time.perf_counter() - started) * 1000, 2)})
    return {"index_id": kb.index_id, "method": method, "k": k, "cases": rows,
            "hits": sum(r["hit"] for r in rows), "total": len(rows),
            "limitation": "只量檢索基準，不代表理由正確或 RAG 內容驗收通過"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    index = sub.add_parser("index", help="建立雙科索引，模型僅使用本機快取")
    index.add_argument("--config", type=Path, default=Path("config/knowledge-base.json"))
    index.add_argument("--output", type=Path, default=Path("data/index/kb"))
    index.add_argument("--embedding-model")
    for name in ("search", "ask", "evaluate"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--index", required=True, type=Path)
        cmd.add_argument("--method", choices=("bm25", "vector", "hybrid"), default="bm25")
        cmd.add_argument("--k", type=int, default=5)
        if name == "evaluate":
            cmd.add_argument("--cases", type=Path, required=True)
        else:
            query = cmd.add_mutually_exclusive_group(required=True)
            query.add_argument("--query")
            query.add_argument("--query-file", type=Path)
        if name == "ask":
            cmd.add_argument("--model", required=True, help="本機已安裝模型，不自動下載")
            cmd.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    args = parser.parse_args(argv)
    root = args.root.resolve()
    started = time.perf_counter()
    try:
        if args.command == "index":
            path = build_index(root, root / args.config, args.output, args.embedding_model)
            result = {"index": str(path.relative_to(root)), "status": "built"}
        else:
            kb = KnowledgeBase.load(data_path(root, str(args.index)), args.method != "bm25")
            if args.command == "evaluate":
                cases = json.loads(data_path(root, str(args.cases)).read_text(encoding="utf-8"))
                result = evaluate(kb, cases, args.method, args.k)
            else:
                question = args.query if args.query is not None else data_path(root, str(args.query_file)).read_text(encoding="utf-8")
                hits = kb.search(question, args.k, args.method)
                result = {"index_id": kb.index_id, "method": args.method, "question": question,
                          "hits": hits}
                if args.command == "ask":
                    result["generation"] = answer(question, hits,
                        lambda prompt: ollama_generate(prompt, args.model, args.ollama_url))
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["run_file"] = str(save_run(root, result).relative_to(root))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
        print(f"執行失敗：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

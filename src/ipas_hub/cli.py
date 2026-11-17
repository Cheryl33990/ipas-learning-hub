"""RAG 技術原型 CLI；真實資料與執行紀錄只寫入 data/。"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from .knowledge import KnowledgeBase, build_index, data_path, digest
from .llm import LLMConfig, chat_json, check_config
from .rag import answer, gather_external, plan_web_queries, render_text
from .websearch import make_search


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


def ask(question: str, hits: list[dict], args) -> dict:
    cfg = LLMConfig.from_env(args.llm_url, args.model, args.allow_remote)
    generate = lambda system, user: chat_json(cfg, system, user)
    record = {"llm": cfg.describe(), "web": {"provider": args.web, "queries": [], "error": None}}
    external = []
    if args.web != "none":
        if not 1 <= args.web_k <= 10:
            raise ValueError("--web-k 須介於 1 至 10")
        record["web"]["queries"] = plan_web_queries(question, generate)
        errors = []  # 搜尋失敗不中止，但逐詞明確記錄；全部失敗時只用教材回答
        external = gather_external(record["web"]["queries"], make_search(args.web), 2, args.web_k, errors)
        record["web"]["error"] = "；".join(errors) or None
    record["external_hits"] = external
    record["generation"] = answer(question, hits, external, generate)
    return record


def source_files(root: Path, sources: list[dict]) -> dict:
    """serve 可提供的教材檔：只收索引列出、位於 data/ 且雜湊與索引相同的檔案。"""
    files = {}
    for source in sources:
        if not source.get("pdf"):  # 舊索引沒有記錄檔案位置
            continue
        try:
            path = data_path(root, source["pdf"])
            same = digest(path.read_bytes()) == source["sha256"]
        except (ValueError, OSError):
            same = False
        if same:
            files[f"{source['id']}{path.suffix.lower()}"] = path
        else:
            print(f"提醒：{source['id']} 的教材檔不存在或與索引版本不同，引用不提供連結", file=sys.stderr)
    return files


def textbook_link(base: str, files: dict):
    """回傳「來源 → 網址」的函式：教材連到本機提供的檔案該頁，外部沿用自帶網址。"""
    def link(source: dict) -> str | None:
        if source.get("source_type") != "textbook":
            return source.get("url")
        name = next((n for n in files if n.rsplit(".", 1)[0] == source.get("source")), None)
        if not name or not source.get("pdf_page"):
            return None
        return f"{base.rstrip('/')}/files/{name}#page={source['pdf_page']}"
    return link


def answer_text(kb: KnowledgeBase, question: str, args, root: Path, link_for=None) -> str:
    """serve 用：與 ask 指令走同一流程，回傳給人看的文字（依據清單為 Markdown 連結）；外部搜尋失敗時在文末說明。"""
    started = time.perf_counter()
    result = {"index_id": kb.index_id, "method": args.method, "question": question,
              "hits": kb.search(question, args.k, args.method)}
    result.update(ask(question, result["hits"], args))
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    save_run(root, result)
    text = render_text(result["generation"], link_for, markdown=True)
    if result["web"]["error"]:
        text += f"\n\n⚠ 外部搜尋未完整（{result['web']['error']}），本次可能只依教材回答。"
    return text


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    index = sub.add_parser("index", help="建立雙科索引，模型僅使用本機快取")
    index.add_argument("--config", type=Path, default=Path("config/knowledge-base.json"))
    index.add_argument("--output", type=Path, default=Path("data/index/kb"))
    index.add_argument("--embedding-model")
    for name in ("search", "ask", "evaluate", "serve"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--index", required=True, type=Path)
        cmd.add_argument("--method", choices=("bm25", "vector", "hybrid"), default="bm25")
        cmd.add_argument("--k", type=int, default=5)
        if name == "evaluate":
            cmd.add_argument("--cases", type=Path, required=True)
        elif name == "serve":
            cmd.add_argument("--port", type=int, default=8100, help="只綁 127.0.0.1")
            cmd.add_argument("--served-name", default="rag", help="聊天介面看到的模型名稱")
            cmd.add_argument("--link-base", help="引用連結的網址開頭（給瀏覽器開，不是給容器）；預設 http://127.0.0.1:<port>")
        else:
            query = cmd.add_mutually_exclusive_group(required=True)
            query.add_argument("--query")
            query.add_argument("--query-file", type=Path)
        if name in ("ask", "serve"):
            cmd.add_argument("--model", help="OpenAI 相容服務上的模型名稱；預設讀 LLM_MODEL")
            cmd.add_argument("--llm-url", help="OpenAI 相容端點；預設讀 LLM_BASE_URL，否則本機 vLLM")
            cmd.add_argument("--allow-remote", action="store_true",
                             help="允許本機以外的 LLM 端點（可能收費）；金鑰只讀 LLM_API_KEY")
            cmd.add_argument("--web", choices=("wikipedia", "none"), default="wikipedia")
            cmd.add_argument("--web-k", type=int, default=4, help="外部片段上限")
            if name == "ask":
                cmd.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    started = time.perf_counter()
    try:
        if args.command == "index":
            path = build_index(root, root / args.config, args.output, args.embedding_model)
            result = {"index": str(path.relative_to(root)), "status": "built"}
        else:
            kb = KnowledgeBase.load(data_path(root, str(args.index)), args.method != "bm25")
            if args.command == "serve":
                from .server import HOST, make_server
                check_config(LLMConfig.from_env(args.llm_url, args.model, args.allow_remote))  # 設定錯誤在啟動時就報
                files = source_files(root, kb.payload["sources"])
                link_for = textbook_link(args.link_base or f"http://{HOST}:{args.port}", files)
                server = make_server(lambda q: answer_text(kb, q, args, root, link_for), args.port,
                                     args.served_name, files)
                print(f"OpenAI 相容端點：http://{HOST}:{server.server_address[1]}/v1（模型名稱 {args.served_name}）；Ctrl+C 結束",
                      flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
                finally:
                    server.server_close()
                return 0
            if args.command == "evaluate":
                cases = json.loads(data_path(root, str(args.cases)).read_text(encoding="utf-8"))
                result = evaluate(kb, cases, args.method, args.k)
            else:
                question = args.query if args.query is not None else data_path(root, str(args.query_file)).read_text(encoding="utf-8")
                hits = kb.search(question, args.k, args.method)
                result = {"index_id": kb.index_id, "method": args.method, "question": question,
                          "hits": hits}
                if args.command == "ask":
                    result.update(ask(question, hits, args))
        result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result["run_file"] = str(save_run(root, result).relative_to(root))
        if args.command == "ask" and args.format == "text":
            print(render_text(result["generation"]))
            print(f"\n執行紀錄：{result['run_file']}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
        print(f"執行失敗：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

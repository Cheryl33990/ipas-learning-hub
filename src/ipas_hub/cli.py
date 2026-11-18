"""RAG 技術原型 CLI；真實資料與執行紀錄只寫入 data/。"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import time
import uuid
from pathlib import Path

from .knowledge import KnowledgeBase, build_index, data_path, digest, knowledge_base_id
from .llm import LLMConfig, chat_json, check_config
from .profile import answer_prompt, load_profile
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
    def generate(system, user):
        return chat_json(cfg, system, user)

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
    record["generation"] = answer(question, hits, external, generate, getattr(args, "answer_prompt", None))
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


def textbook_link(base: str, files: dict, file_prefix: str = ""):
    """回傳「來源 → 網址」的函式：教材連到本機提供的檔案該頁，外部沿用自帶網址。"""
    def link(source: dict) -> str | None:
        if source.get("source_type") != "textbook":
            return source.get("url")
        name = next((n for n in files if n.rsplit(".", 1)[0] == source.get("source")), None)
        if not name or not source.get("pdf_page"):
            return None
        return f"{base.rstrip('/')}/files/{file_prefix}{name}#page={source['pdf_page']}"
    return link


def answer_text(kb: KnowledgeBase, question: str, args, root: Path, link_for=None) -> str:
    """serve 用：與 ask 指令走同一流程，回傳給人看的文字（依據清單為 Markdown 連結）；外部搜尋失敗時在文末說明。"""
    started = time.perf_counter()
    result = {"index_id": kb.index_id, "method": args.method, "question": question,
              "knowledge_base": kb.knowledge_base,
              "hits": kb.search(question, args.k, args.method)}
    result.update(ask(question, result["hits"], args))
    result["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 2)
    save_run(root, result)
    text = render_text(result["generation"], link_for, markdown=True)
    if result["web"]["error"]:
        text += f"\n\n⚠ 外部搜尋未完整（{result['web']['error']}），本次可能只依教材回答。"
    return text


def default_method(store: str) -> str:
    """兩種儲存都預設混合檢索（使用者 2026-11-17 決定）；索引沒有向量時見 open_kb 的退回規則。"""
    return "hybrid"


def _fall_back_to_bm25(args) -> None:
    args.method = "bm25"
    print("提醒：此索引沒有向量，改用 BM25 關鍵字檢索。要用混合檢索，請以 --embedding-model 重建索引"
          "（--store pg 時再載入資料庫）。", file=sys.stderr, flush=True)


def open_kb(root: Path, args, encoder=None) -> KnowledgeBase:
    """依 --store 開啟知識庫：file 讀 index.json；pg 從資料庫讀回並驗證，--index 為 index_id（省略取最近載入）。

    未指定 --method 時預設混合檢索；索引沒有向量就退回 BM25 並提醒。明確指定向量或混合時不退回，照常報錯。
    """
    defaulted = getattr(args, "method_defaulted", False)
    if args.store == "pg":
        from . import pgstore
        conn = pgstore.connect()
        index_id = str(args.index) if args.index else None
        selected_kb = getattr(args, "kb", None)
        # --kb 選範圍後再處理退回 BM25；混合預設仍優先選該庫含向量版本。
        if selected_kb is not None or index_id is None:
            index_id = pgstore.select_index(conn, index_id, selected_kb,
                                           prefer_vectors=args.method != "bm25")
        if args.method != "bm25" and defaulted and not pgstore.has_vectors(conn, index_id):
            _fall_back_to_bm25(args)
        if encoder is not None:
            return pgstore.open_knowledge_base(conn, index_id, args.method != "bm25", encoder=encoder)
        return pgstore.open_knowledge_base(conn, index_id, args.method != "bm25")
    if not args.index:
        raise ValueError("使用檔案索引（--store file）時須指定 --index <index.json>")
    path = data_path(root, str(args.index))
    if args.method != "bm25" and not json.loads(path.read_text(encoding="utf-8")).get("embedding"):
        if not defaulted:
            raise ValueError("此索引沒有向量，無法使用向量或混合檢索；請改用 --method bm25，或以 --embedding-model 重建索引")
        _fall_back_to_bm25(args)
    kb = KnowledgeBase.load(path, args.method != "bm25")
    if getattr(args, "kb", None) is not None and kb.knowledge_base != args.kb:
        raise ValueError("指定索引不屬於選定知識庫")
    return kb


def load_to_pg(index_path: Path) -> dict:
    from . import pgstore
    payload, vectors = pgstore.read_index_files(index_path)
    loaded = pgstore.load_index(pgstore.connect(), payload, vectors)
    return {"index_id": payload["index_id"], "pg": "loaded" if loaded else "already_loaded",
            "vectors": vectors is not None}


def routed_server(root: Path, args):
    """共用聊天入口依明列模型選庫；設定不含可由問題決定的動態路徑。"""
    from .server import HOST, make_server
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"路由設定含重複名稱：{key}")
            result[key] = value
        return result
    config = json.loads((root / args.routes).read_text(encoding="utf-8"), object_pairs_hook=unique_keys)
    if not isinstance(config, dict) or not config:
        raise ValueError("模型路由設定須為非空物件")
    for name, spec in config.items():
        knowledge_base_id({"knowledge_base": name})
        if (not isinstance(spec, dict) or not {"knowledge_base", "web"} <= set(spec) <= {"knowledge_base", "web", "profile"}
                or not isinstance(spec.get("profile", ""), str)):
            raise ValueError("每個路由須指定 knowledge_base 與 web，可選 profile（路徑字串）")
        knowledge_base_id(spec)
        if spec["web"] not in {"none", "wikipedia"}:
            raise ValueError("路由 web 須為 none 或 wikipedia")
    if getattr(args, "profile", None):
        raise ValueError("使用 --routes 時，請在路由設定中為每個模型指定 profile，不另用 --profile")
    if args.store != "pg" or args.index or args.kb:
        raise ValueError("--routes 需搭配 --store pg，且不能另指定 --kb／--index")
    check_config(LLMConfig.from_env(args.llm_url, args.model, args.allow_remote))
    callbacks, files, encoder, encoder_meta = {}, {}, None, None
    base = args.link_base or f"http://{HOST}:{args.port}"
    for name, spec in config.items():
        selected = copy.copy(args)
        selected.kb, selected.web = spec["knowledge_base"], spec["web"]
        selected.answer_prompt = answer_prompt(load_profile(root, Path(spec["profile"]) if spec.get("profile") else None))
        kb = open_kb(root, selected, encoder)
        if kb.encoder is not None:
            meta = kb.payload["embedding"]
            if encoder_meta is not None and any(meta[key] != encoder_meta[key] for key in ("name", "revision", "dimensions")):
                raise ValueError("共用路由的嵌入模型版本或維度不一致，請使用獨立端點")
            encoder, encoder_meta = kb.encoder, meta
        local_files = source_files(root, kb.payload["sources"])
        prefix = name + "--"
        files.update({prefix + key: path for key, path in local_files.items()})
        link = textbook_link(base, local_files, prefix)
        callbacks[name] = lambda q, kb=kb, selected=selected, link=link: answer_text(kb, q, selected, root, link)
        print(f"模型 {name} → 知識庫 {kb.knowledge_base}；索引 {kb.index_id}；web {selected.web}；"
              f"profile {spec.get('profile', '通用')}", flush=True)
    return make_server(None, args.port, next(iter(callbacks)), files, models=callbacks)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    index = sub.add_parser("index", help="建立雙科索引，模型僅使用本機快取")
    index.add_argument("--config", type=Path, default=Path("examples/ipas/knowledge-base.json"))
    index.add_argument("--output", type=Path, default=Path("data/index/kb"))
    index.add_argument("--embedding-model")
    index.add_argument("--to-pg", action="store_true", help="建好後載入 PostgreSQL（連線讀 PG_DSN）")
    fetch = sub.add_parser("fetch", help="依來源設定從發布者下載文件並核對 SHA-256（只用 https）")
    fetch.add_argument("--config", type=Path, required=True)
    load = sub.add_parser("pg-load", help="把檔案索引驗證後載入 PostgreSQL＋pgvector（連線讀 PG_DSN）")
    load.add_argument("--index", required=True, type=Path)
    for name in ("search", "ask", "evaluate", "serve"):
        cmd = sub.add_parser(name)
        cmd.add_argument("--store", choices=("file", "pg"), default="file",
                         help="file：讀 index.json；pg：讀 PostgreSQL（連線讀 PG_DSN）")
        cmd.add_argument("--kb", help="知識庫名稱；pg 限定該庫，file 時核對指定索引")
        cmd.add_argument("--index", type=Path,
                         help="file 時為 index.json 路徑（必填）；pg 時為 index_id，省略則用最近載入的")
        cmd.add_argument("--method", choices=("bm25", "vector", "hybrid"),
                         help="預設 hybrid；索引沒有向量時自動改用 bm25 並提醒")
        cmd.add_argument("--k", type=int, default=5)
        if name == "evaluate":
            cmd.add_argument("--cases", type=Path, required=True)
        elif name == "serve":
            cmd.add_argument("--routes", type=Path, help="模型名稱到知識庫／外搜政策的 JSON 設定（pg）")
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
            cmd.add_argument("--profile", type=Path,
                             help="領域設定 JSON（角色與領域規則），例如 examples/ipas/profile.json；省略則用通用設定")
            if name == "ask":
                cmd.add_argument("--format", choices=("json", "text"), default="json")
    args = parser.parse_args(argv)
    if getattr(args, "store", None) and args.method is None:
        args.method, args.method_defaulted = default_method(args.store), True
    root = args.root.resolve()
    started = time.perf_counter()
    try:
        if args.command in ("ask", "serve") and not getattr(args, "routes", None):
            args.answer_prompt = answer_prompt(load_profile(root, args.profile))
        if args.command == "index":
            path = build_index(root, root / args.config, args.output, args.embedding_model)
            result = {"index": str(path.relative_to(root)), "status": "built"}
            if args.to_pg:
                result.update(load_to_pg(path))
        elif args.command == "fetch":
            from .fetch import fetch_sources
            print(json.dumps({"sources": fetch_sources(root, root / args.config)}, ensure_ascii=False, indent=2))
            return 0
        elif args.command == "pg-load":
            result = load_to_pg(data_path(root, str(args.index)))
        elif args.command == "serve" and args.routes:
            server = routed_server(root, args)
            print(f"多知識庫端點：http://127.0.0.1:{server.server_address[1]}/v1；Ctrl+C 結束", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        else:
            kb = open_kb(root, args)
            if args.command == "serve":
                from .server import HOST, make_server
                check_config(LLMConfig.from_env(args.llm_url, args.model, args.allow_remote))  # 設定錯誤在啟動時就報
                files = source_files(root, kb.payload["sources"])
                link_for = textbook_link(args.link_base or f"http://{HOST}:{args.port}", files)
                server = make_server(lambda q: answer_text(kb, q, args, root, link_for), args.port,
                                     args.served_name, files)
                print(f"OpenAI 相容端點：http://{HOST}:{server.server_address[1]}/v1（模型名稱 {args.served_name}）；Ctrl+C 結束",
                      flush=True)
                print(f"知識庫：{kb.knowledge_base}；索引：{kb.index_id}", flush=True)
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
                result["knowledge_base"] = kb.knowledge_base
            else:
                question = args.query if args.query is not None else data_path(root, str(args.query_file)).read_text(encoding="utf-8")
                hits = kb.search(question, args.k, args.method)
                result = {"index_id": kb.index_id, "method": args.method, "question": question,
                          "knowledge_base": kb.knowledge_base,
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

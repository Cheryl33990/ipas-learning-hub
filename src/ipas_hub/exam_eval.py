"""保留題評估：用官方公告試題與官方答案，比較 BM25、向量、混合三種檢索下的整題問答結果。

每題以相同索引、模型、profile 與 k 跑每種方法，外搜關閉，只看檢索差異。答案由官方答案自動比對，
不需人工標註；但「答對」不代表理由與引用正確，「前五含同科教材」也不是頁碼層級的召回率。
結果逐筆附加到 data/ 下的 jsonl，可中斷後續跑；彙總報告不含題目原文。

用法（repo 根目錄，需 PG_DSN 與本機 LLM）：
  uv run python -m ipas_hub.exam_eval --manifest examples/ipas/eval/heldout.json --out data/evaluation/heldout
  uv run python -m ipas_hub.exam_eval ... --limit 3        # 試跑前 3 題
  uv run python -m ipas_hub.exam_eval ... --report-only    # 只依既有結果產生報告
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
import sys
import time
from argparse import Namespace
from pathlib import Path

from .exam import read_questions
from .knowledge import data_path

METHODS = ("bm25", "vector", "hybrid")
K = 5
OUTCOMES = ("correct", "wrong", "no_choice", "insufficient", "error")
FAILURES = (ValueError, OSError, KeyError, TypeError)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cases(root: Path, manifest_path: Path) -> list[dict]:
    """依設定讀試題；核對 SHA-256，排除開發期間用過的題號。"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = []
    for spec in manifest["sources"]:
        pdf = data_path(root, spec["pdf"])
        if _sha256(pdf) != spec["sha256"]:
            raise ValueError(f"{spec['id']} 試題檔與設定的 SHA-256 不符")
        excluded = set(spec.get("exclude", []))
        for q in read_questions(pdf):
            if q.number in excluded:
                continue
            cases.append(
                {
                    "id": f"{spec['id']}-{q.number:02d}",
                    "paper": spec["id"],
                    "number": q.number,
                    "official": q.answer,
                    "question": q.text,
                    "expected_source": spec["expected_source"],
                }
            )
    return cases


def _done(out: Path) -> dict:
    if not out.is_file():
        return {}
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {(r["case"], r["method"]): r for r in rows}


def run_one(case: dict, kb, method: str, ask) -> dict:
    started = time.perf_counter()
    hits = kb.search(case["question"], k=K, method=method)
    retrieval_ms = round((time.perf_counter() - started) * 1000, 2)
    row = {
        "case": case["id"],
        "paper": case["paper"],
        "number": case["number"],
        "method": method,
        "official": case["official"],
        "retrieval_ms": retrieval_ms,
        "top5": [{"source": h["source"], "page": h["page"], "pdf_page": h.get("pdf_page")} for h in hits],
        "same_subject_top5": any(h["source"] == case["expected_source"] for h in hits),
    }
    try:
        generation = ask(case["question"], hits)
    except FAILURES as exc:
        return {**row, "outcome": "error", "error": str(exc), "llm_ms": None}
    choice = generation.get("answer_choice")
    if generation["status"] != "supported":
        outcome = "insufficient"
    elif choice is None:
        outcome = "no_choice"
    else:
        outcome = "correct" if choice == case["official"] else "wrong"
    return {
        **row,
        "outcome": outcome,
        "choice": choice,
        "llm_ms": generation.get("llm_elapsed_ms"),
        "cited": len(generation.get("citations", [])),
        "flagged": generation.get("flagged_segments"),
        "repairs": generation.get("repair_attempts"),
        "removed_choice": generation.get("removed_choice"),
        "completed_ids": len(generation.get("completed_citations", [])),
    }


def run_batch(cases: list[dict], kb, methods, ask, out: Path, progress=None) -> list[dict]:
    """每題輪換方法順序，避免快取或順序造成系統性偏差；每完成一筆就附加寫入。"""
    done = _done(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    methods = list(methods)
    with out.open("a", encoding="utf-8") as f:
        for i, case in enumerate(cases):
            shift = i % len(methods)
            for method in methods[shift:] + methods[:shift]:
                if (case["id"], method) in done:
                    continue
                row = run_one(case, kb, method, ask)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                done[(case["id"], method)] = row
                if progress:
                    progress(row)
    return [done[(c["id"], m)] for c in cases for m in methods if (c["id"], m) in done]


def _percentile(values: list[float], p: float) -> float | None:
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return values[max(0, math.ceil(p * len(values)) - 1)]


def summarize(rows: list[dict], baseline: str = "bm25", resamples: int = 2000) -> dict:
    by_method: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_method.setdefault(r["method"], {})[r["case"]] = r
    case_sets = {m: set(v) for m, v in by_method.items()}
    if len({frozenset(s) for s in case_sets.values()}) != 1:
        raise ValueError("各方法完成的題目不一致，請先跑完再彙總")
    cases = sorted(next(iter(case_sets.values())))
    methods = {}
    for m, rs in by_method.items():
        counts = {o: sum(r["outcome"] == o for r in rs.values()) for o in OUTCOMES}
        n = len(rs)
        papers = {}
        for r in rs.values():
            papers.setdefault(r["paper"], []).append(r["outcome"] == "correct")
        methods[m] = {
            "n": n,
            **counts,
            "accuracy": round(counts["correct"] / n, 4),
            "same_subject_top5": round(sum(r["same_subject_top5"] for r in rs.values()) / n, 4),
            "retrieval_ms_p50": _percentile([r["retrieval_ms"] for r in rs.values()], 0.5),
            "retrieval_ms_p95": _percentile([r["retrieval_ms"] for r in rs.values()], 0.95),
            "llm_ms_p50": _percentile([r["llm_ms"] for r in rs.values()], 0.5),
            "llm_ms_p95": _percentile([r["llm_ms"] for r in rs.values()], 0.95),
            "by_paper": {p: {"n": len(v), "accuracy": round(sum(v) / len(v), 4)} for p, v in sorted(papers.items())},
        }
    paired = {}
    if baseline in by_method:
        base = [by_method[baseline][c]["outcome"] == "correct" for c in cases]
        rng = random.Random(0)
        for m in by_method:
            if m == baseline:
                continue
            other = [by_method[m][c]["outcome"] == "correct" for c in cases]
            diffs = [o - b for o, b in zip(other, base)]
            boot = sorted(sum(diffs[rng.randrange(len(diffs))] for _ in diffs) / len(diffs) for _ in range(resamples))
            paired[m] = {
                "improved": diffs.count(1),
                "regressed": diffs.count(-1),
                "same": diffs.count(0),
                "accuracy_diff": round(sum(diffs) / len(diffs), 4),
                "accuracy_diff_ci95": [
                    round(boot[int(0.025 * resamples)], 4),
                    round(boot[int(0.975 * resamples) - 1], 4),
                ],
            }
    return {"cases": len(cases), "baseline": baseline, "methods": methods, "paired": paired}


def _ms(v):
    return "—" if v is None else f"{v:,.0f}"


def _s(v):
    return "—" if v is None else f"{v / 1000:.1f}"


def render_report(summary: dict, meta: dict) -> str:
    lines = [
        "| 方法 | 答對 | 答錯 | 依據不足 | 未給選項 | 錯誤 | 答對率 | 前五含同科教材 | 檢索 p50／p95 (ms) | 生成 p50／p95 (s) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for m, s in summary["methods"].items():
        lines.append(
            f"| {m} | {s['correct']} | {s['wrong']} | {s['insufficient']} | {s['no_choice']} | {s['error']} "
            f"| {s['accuracy']:.1%} | {s['same_subject_top5']:.1%} "
            f"| {_ms(s['retrieval_ms_p50'])}／{_ms(s['retrieval_ms_p95'])} "
            f"| {_s(s['llm_ms_p50'])}／{_s(s['llm_ms_p95'])} |"
        )
    if summary["paired"]:
        lines += [
            "",
            f"與 {summary['baseline']} 逐題比較（以題為單位的成對 bootstrap，2,000 次，seed 0）：",
            "",
            "| 方法 | 改善 | 退步 | 相同 | 答對率差 | 95% 信賴區間 |",
            "|---|---|---|---|---|---|",
        ]
        for m, p in summary["paired"].items():
            low, high = p["accuracy_diff_ci95"]
            lines.append(
                f"| {m} | {p['improved']} | {p['regressed']} | {p['same']} "
                f"| {p['accuracy_diff']:+.1%} | {low:+.1%} ~ {high:+.1%} |"
            )
    papers = sorted({p for s in summary["methods"].values() for p in s["by_paper"]})
    methods = list(summary["methods"])
    lines += [
        "",
        "各卷答對率：",
        "",
        "| 試卷 | 題數 | " + " | ".join(methods) + " |",
        "|---|---|" + "---|" * len(methods),
    ]
    for p in papers:
        n = summary["methods"][methods[0]]["by_paper"][p]["n"]
        lines.append(
            f"| {p} | {n} | "
            + " | ".join(f"{summary['methods'][m]['by_paper'][p]['accuracy']:.1%}" for m in methods)
            + " |"
        )
    head = [
        f"- 題數：{summary['cases']}；每題每方法跑一次，temperature 0，外搜關閉，k={K}",
        *[f"- {k}：{v}" for k, v in meta.items()],
    ]
    return "\n".join(head + [""] + lines) + "\n"


def _git_head(root: Path) -> str:
    """未提交的修改會加上 +dirty，避免報告記錄的版本與實際執行的程式不符。"""
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
        if r.returncode != 0:
            return "unavailable"
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--", "src"], cwd=root, capture_output=True, text=True
        ).stdout.strip()
        return r.stdout.strip() + ("+dirty" if dirty else "")
    except FileNotFoundError:
        return "unavailable"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="以官方試題比較三種檢索下的問答結果")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="data/ 下的輸出資料夾")
    parser.add_argument("--methods", default=",".join(METHODS))
    parser.add_argument("--limit", type=int, help="只跑前 N 題（試跑用，請另用一個 --out）")
    parser.add_argument("--report-only", action="store_true")
    parser.add_argument("--kb", default="ipas")
    parser.add_argument("--profile", type=Path, default=Path("examples/ipas/profile.json"))
    parser.add_argument("--model", help="預設讀 LLM_MODEL")
    parser.add_argument("--llm-url", help="預設讀 LLM_BASE_URL，否則本機 vLLM")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path.cwd().resolve()
    out_dir = data_path(root, str(args.out))
    rows_path, meta_path = out_dir / "rows.jsonl", out_dir / "meta.json"
    methods = [m for m in args.methods.split(",") if m]
    if not set(methods) <= set(METHODS):
        parser.error(f"--methods 只能是 {', '.join(METHODS)}")
    if not args.report_only:
        from .cli import ask as cli_ask, open_kb
        from .llm import LLMConfig, check_config
        from .profile import answer_prompt, load_profile

        cases = load_cases(root, root / args.manifest)
        cases = cases[: args.limit] if args.limit else cases
        prompt = answer_prompt(load_profile(root, args.profile))
        cfg = LLMConfig.from_env(args.llm_url, args.model, False)
        check_config(cfg)
        kb = open_kb(root, Namespace(store="pg", index=None, kb=args.kb, method="hybrid"))
        ask_args = Namespace(
            llm_url=args.llm_url, model=args.model, allow_remote=False, web="none", web_k=4, answer_prompt=prompt
        )
        meta = {
            "index_id": kb.index_id,
            "llm": cfg.describe(),
            "profile": str(args.profile),
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "manifest": str(args.manifest),
            "code_version": _git_head(root),
            "cases": len(cases),
            "methods": methods,
        }
        out_dir.mkdir(parents=True, exist_ok=True)
        if meta_path.is_file():
            previous = json.loads(meta_path.read_text(encoding="utf-8"))
            keys = ("index_id", "prompt_sha256", "llm", "methods")
            if any(previous.get(k) != meta[k] for k in keys):
                raise SystemExit("既有結果的索引、prompt、模型或方法與本次不同；請換一個 --out，不要混在同一份結果")
        else:
            meta["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        total = len(cases) * len(methods)

        def progress(row, count=[len(_done(rows_path))]):
            count[0] += 1
            print(f"[{count[0]}/{total}] {row['case']} {row['method']} → {row['outcome']}", flush=True)

        run_batch(cases, kb, methods, lambda q, hits: cli_ask(q, hits, ask_args)["generation"], rows_path, progress)
    rows = list(_done(rows_path).values())
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    summary = summarize(rows)
    (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    report = render_report(
        summary,
        {k: meta[k] for k in ("index_id", "prompt_sha256", "code_version", "manifest") if k in meta}
        | {"llm": meta["llm"].get("model")},
    )
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

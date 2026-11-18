"""一分鐘示範：不需 GPU、網路、教材或資料庫，以 iPAS 範例重播六種問答情境。

語料是 examples/ipas/sample/notes.json 的自寫 iPAS 主題筆記（不是官方教材），
領域設定是 examples/ipas/profile.json，模型是照腳本回覆的替身；其餘都是正式程式：
索引完整性雜湊（KnowledgeBase）、BM25 檢索、引用 ID 檢查與一次修正（rag.answer）、
字詞核對與輸出（rag.render_text）、失敗訊息（server.failure_text）。
示範的是「流程如何處理模型與資料的各種狀況」，不是回答品質；品質見 docs/evaluation.md。

用法（在 repo 根目錄）：uv run python -m ipas_hub.demo [情境名稱 ...]   （不指定則全部；--list 列出情境）
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

from .knowledge import SCHEMA_VERSION, KnowledgeBase, canonical, digest
from .profile import answer_prompt, load_profile
from .rag import answer, render_text
from .server import failure_text

SAMPLE = Path("examples/ipas/sample/notes.json")
PROFILE = Path("examples/ipas/profile.json")
K = 3


def cid(page: str) -> str:
    return f"notes:{page}:0"


def payload(root: Path) -> dict:
    """與 build_index 相同結構的索引內容；index_id 由內容雜湊算出，竄改任何片段都會被拒。"""
    sample = json.loads((root / SAMPLE).read_text(encoding="utf-8"))
    source = sample["source"]
    body = {
        "schema_version": SCHEMA_VERSION,
        "knowledge_base": "ipas-sample",
        "sources": [
            {
                **source,
                "pdf": str(SAMPLE),
                "sha256": "sample",
                "patch_sha256": None,
                "patch_report": [],
                "errata": "not_applied",
                "pages": len(sample["pages"]),
            }
        ],
        "chunks": [
            {"id": cid(p["page"]), "source": source["id"], "page": p["page"], "text": p["text"]}
            for p in sample["pages"]
        ],
        "chunk_size": 400,
        "chunk_stride": 300,
        "embedding": None,
        "code_version": "demo",
        "code_sha256": {},
        "lock_sha256": "demo",
    }
    return {"index_id": digest(canonical(body)), **body}


def said(*segments: tuple[str, list[str]], status: str = "supported") -> dict:
    return {"status": status, "segments": [{"text": t, "citations": c} for t, c in segments]}


SCENARIOS = {
    "grounded-answer": {
        "summary": "選擇題逐項說明並引用檢索到的頁面，最後給出答案",
        "question": "下列何者屬於監督式學習的常見任務？(A) 分群 (B) 降維 (C) 分類 (D) 關聯規則探勘",
        "replies": [
            said(
                ("(A) 分群是非監督式學習的常見任務。", [cid("1-1")]),
                ("(B) 降維也是非監督式學習的常見任務。", [cid("1-1")]),
                ("(C) 分類使用附有標籤的資料，屬於監督式學習。", [cid("1-1")]),
                ("(D) 關聯規則探勘不需要標籤，片段未提及，此為推論。", []),
                ("答案：C", []),
            )
        ],
        "expected": "supported",
    },
    "repaired-citation": {
        "summary": "第一次引用不存在的片段，程式退回修正一次後通過",
        "question": "MAE 與 MSE 哪一個對離群值比較敏感？",
        "replies": [
            said(("MSE 對離群值較敏感。", ["notes:9-9:0"])),
            said(("MSE 先將差距平方再平均，因此對離群值較敏感。", [cid("2-1")])),
        ],
        "expected": "supported-after-repair",
    },
    "fabricated-citation": {
        "summary": "修正後仍捏造引用，拒絕顯示為有依據的回答",
        "question": "如何降低過擬合？",
        "replies": [said(("可以增加訓練資料。", ["notes:8-8:0"]))] * 2,
        "expected": "refused",
    },
    "mis-cited-sentence": {
        "summary": "引用存在但術語對不上，句子加上 ⚠ 警告",
        "question": "RAG 如何降低幻覺？",
        "replies": [said(("RAG 透過 fine-tuning 更新模型參數來降低幻覺。", [cid("4-1")]))],
        "expected": "flagged",
    },
    "out-of-scope": {
        "summary": "筆記沒有相關內容，不呼叫模型，直接回報依據不足",
        "question": "量子電腦的量子位元是什麼？",
        "replies": [],
        "expected": "insufficient",
    },
    "tampered-index": {
        "summary": "索引片段被改過，載入時雜湊不符而拒絕，不進入檢索",
        "question": "下列何者屬於監督式學習的常見任務？(A) 分群 (B) 降維 (C) 分類 (D) 關聯規則探勘",
        "replies": [],
        "expected": "index-rejected",
    },
}


def run(name: str, root: Path | None = None) -> dict:
    root = root or Path.cwd()
    scenario = SCENARIOS[name]
    replies, calls = list(scenario["replies"]), []

    def generate(system: str, user: str) -> dict:
        calls.append(user)
        return {"output": copy.deepcopy(replies.pop(0)), "model": "scripted-demo"}

    index = payload(root)
    if name == "tampered-index":
        index["chunks"][0]["text"] = index["chunks"][0]["text"].replace("分類與迴歸", "分群與迴歸")
    try:
        kb = KnowledgeBase(index)
    except ValueError as exc:
        return {
            "hits": [],
            "model_calls": 0,
            "generation": None,
            "text": failure_text(exc),
            "outcome": "index-rejected",
        }
    hits = kb.search(scenario["question"], k=K)
    prompt = answer_prompt(load_profile(root, PROFILE))
    try:
        generation = answer(scenario["question"], hits, [], generate, prompt)
    except ValueError as exc:
        return {
            "hits": hits,
            "model_calls": len(calls),
            "generation": None,
            "text": failure_text(exc),
            "outcome": "refused",
        }
    if generation["status"] != "supported":
        outcome = "insufficient"
    elif generation["flagged_segments"]:
        outcome = "flagged"
    elif generation["repair_attempts"]:
        outcome = "supported-after-repair"
    else:
        outcome = "supported"
    return {
        "hits": hits,
        "model_calls": len(calls),
        "generation": generation,
        "text": render_text(generation),
        "outcome": outcome,
    }


def render(name: str, root: Path | None = None) -> str:
    scenario, result = SCENARIOS[name], run(name, root)
    hits = [f"  #{h['rank']} {h['id']}　{h['text'][:26]}…" for h in result["hits"]]
    if result["outcome"] == "index-rejected":
        retrieval = "未執行（索引未載入）"
    else:
        retrieval = "" if hits else "無命中"
    verdict = "符合預期" if result["outcome"] == scenario["expected"] else f"預期 {scenario['expected']}"
    return "\n".join(
        [
            f"━━ {name} ━━ {scenario['summary']}",
            f"問題：{scenario['question']}",
            f"檢索（BM25，前 {K}）：{retrieval}",
            *hits,
            f"模型呼叫：{result['model_calls']} 次（腳本化替身）",
            "",
            result["text"],
            "",
            f"結果：{result['outcome']}（{verdict}）",
        ]
    )


def render_all(names=None, root: Path | None = None) -> str:
    return "\n\n".join(render(n, root) for n in (names or SCENARIOS))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="離線重播 iPAS 範例問答情境（自寫筆記＋腳本化模型）")
    parser.add_argument("scenarios", nargs="*", metavar="scenario", help="情境名稱；不指定則全部")
    parser.add_argument("--list", action="store_true", help="列出情境")
    args = parser.parse_args(argv)
    unknown = [n for n in args.scenarios if n not in SCENARIOS]
    if unknown:
        parser.error(f"未知情境：{', '.join(unknown)}；可用：{', '.join(SCENARIOS)}")
    if hasattr(sys.stdout, "reconfigure"):  # Windows 主控台預設編碼不是 UTF-8
        sys.stdout.reconfigure(encoding="utf-8")
    if args.list:
        print("\n".join(f"{n:22} {s['summary']}" for n, s in SCENARIOS.items()))
        return 0
    if not (Path.cwd() / SAMPLE).is_file():
        parser.error(f"找不到 {SAMPLE}；請在 repo 根目錄執行")
    print(render_all(args.scenarios))
    return 0 if all(run(n)["outcome"] == SCENARIOS[n]["expected"] for n in (args.scenarios or SCENARIOS)) else 1


if __name__ == "__main__":
    raise SystemExit(main())

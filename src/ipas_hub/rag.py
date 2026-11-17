"""RAG 流程：教材檢索＋外部搜尋 → LLM 帶引用回答。

引用只能指向本次實際提供的片段；每個引用由程式依片段資料標成教材或外部，不採信模型自稱的來源。
檢查只確認引用存在與格式，不代表內容正確。
"""
from __future__ import annotations

import json
from pathlib import Path

from .knowledge import digest

PROMPTS = Path(__file__).with_name("prompts")
ANSWER_PROMPT = PROMPTS / "answer.txt"
QUERY_PROMPT = PROMPTS / "web_queries.txt"
MAX_WEB_QUERIES = 3


def textbook_label(hit: dict) -> str:
    return f"教材 {hit.get('name', hit['source'])} {hit['page']}"


def external_label(hit: dict) -> str:
    provider = {"wikipedia": "維基百科"}.get(hit.get("provider"), hit.get("provider", "外部"))
    return f"外部 {provider}：{hit['title']}"


def build_evidence(textbook: list[dict], external: list[dict]) -> list[dict]:
    evidence = [{"id": h["id"], "source_type": "textbook", "label": textbook_label(h), "text": h["text"]}
                for h in textbook]
    evidence += [{"id": h["id"], "source_type": "external", "label": external_label(h),
                  "url": h.get("url"), "text": h["text"]} for h in external]
    ids = [e["id"] for e in evidence]
    if len(ids) != len(set(ids)):
        raise ValueError("教材與外部片段的 id 重複，無法區分來源")
    return evidence


def plan_web_queries(question: str, generate) -> list[str]:
    """請模型列出要查證的概念詞；回覆不合格就拋錯，不改用猜測的搜尋詞。"""
    output = generate(QUERY_PROMPT.read_text(encoding="utf-8"), question)["output"]
    queries = output.get("queries")
    if not isinstance(queries, list) or not all(isinstance(q, str) for q in queries):
        raise ValueError("搜尋詞規劃回覆不符合格式")
    cleaned = []
    for q in (q.strip() for q in queries):
        if q and q not in cleaned and len(q) <= 40:
            cleaned.append(q)
    return cleaned[:MAX_WEB_QUERIES]


def gather_external(queries: list[str], search, per_query: int, limit: int) -> list[dict]:
    """每個搜尋詞輪流取結果，避免前面的詞佔滿上限。"""
    results = [search.search(query, per_query) for query in queries]
    hits, seen = [], set()
    for rank in range(per_query):
        for found in results:
            if rank < len(found) and found[rank]["id"] not in seen:
                seen.add(found[rank]["id"])
                hits.append(found[rank])
    return hits[:limit]


def _check_output(output, by_id: dict) -> list[str]:
    """回傳問題清單；空清單代表格式與引用 id 都合格。"""
    if not isinstance(output, dict) or output.get("status") not in {"supported", "insufficient"}:
        return ["status 須為 supported 或 insufficient"]
    problems = []
    if not isinstance(output.get("answer"), str) or not output["answer"].strip():
        problems.append("answer 不可空白")
    citations = output.get("citations")
    if not isinstance(citations, list) or not all(isinstance(c, str) for c in citations):
        return problems + ["citations 須為字串清單"]
    unknown = [c for c in citations if c not in by_id]
    if unknown:
        problems.append("引用了 evidence 中不存在的 id：" + "、".join(unknown))
    if output["status"] == "supported" and not citations:
        problems.append("supported 的回答至少要有一個引用")
    return problems


def answer(question: str, textbook: list[dict], external: list[dict], generate) -> dict:
    evidence = build_evidence(textbook, external)
    if not evidence:
        return {"status": "insufficient", "answer": "教材與外部搜尋都沒有取得依據，無法解答。",
                "citations": [], "sources": [], "basis": "none", "validation": "no_evidence",
                "prompt_sha256": None}
    template = ANSWER_PROMPT.read_text(encoding="utf-8")
    user = json.dumps({"question": question, "evidence": evidence}, ensure_ascii=False)
    by_id = {e["id"]: e for e in evidence}
    generated = generate(template, user)
    problems = _check_output(generated["output"], by_id)
    repairs = 0
    if problems:  # 只給一次修正機會；仍不合格就拒絕，不自行刪改引用
        repairs = 1
        feedback = ("你上一次的回覆不合格：" + "；".join(problems)
                    + "。請只使用 evidence 中實際存在的 id，依相同規則重新回覆完整 JSON。")
        generated = generate(template, user + "\n\n" + feedback)
        if _check_output(generated["output"], by_id):
            raise ValueError("模型引用不存在或回答缺少引用，修正一次後仍不合格，拒絕顯示為有依據回答")
    output = generated["output"]
    citations = list(dict.fromkeys(output["citations"]))
    sources = [{"id": c, "source_type": by_id[c]["source_type"], "label": by_id[c]["label"],
                **({"url": by_id[c]["url"]} if by_id[c].get("url") else {})} for c in citations]
    types = {s["source_type"] for s in sources}
    basis = ("mixed" if types == {"textbook", "external"} else
             "textbook_only" if types == {"textbook"} else
             "external_only" if types == {"external"} else "none")
    return {"status": output["status"], "answer": output["answer"], "citations": citations,
            "sources": sources, "basis": basis, "model": generated.get("model"),
            "usage": generated.get("usage"), "llm_elapsed_ms": generated.get("elapsed_ms"),
            "prompt_sha256": digest(template.encode()), "repair_attempts": repairs,
            "validation": "citation_ids_only_not_semantic_verification"}


def render_text(result: dict) -> str:
    """給人看的版本：答案在前，依據逐條標明教材或外部。"""
    basis = {"textbook_only": "只用教材", "external_only": "只用外部資料（教材未涵蓋）",
             "mixed": "教材＋外部資料", "none": "無依據"}[result["basis"]]
    lines = [f"狀態：{'有依據' if result['status'] == 'supported' else '依據不足'}（{basis}）", "",
             result["answer"], "", "依據："]
    for s in result["sources"]:
        lines.append(f"- [{s['id']}] {s['label']}" + (f"  {s['url']}" if s.get("url") else ""))
    if not result["sources"]:
        lines.append("- （無）")
    lines += ["", "提醒：程式只檢查引用確實存在，不保證解答正確。"]
    return "\n".join(lines)

"""RAG 流程：教材檢索＋外部搜尋 → LLM 帶引用回答。

引用只能指向本次實際提供的片段；每個引用由程式依片段資料標成教材或外部，不採信模型自稱的來源。
檢查確認引用存在、格式，並以字詞比對標出可能掛錯的引用；不是語意驗證，不代表內容正確。
"""
from __future__ import annotations

import json
import re
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
    """回傳問題清單；空清單代表結構與引用 id 都合格。"""
    if not isinstance(output, dict) or output.get("status") not in {"supported", "insufficient"}:
        return ["status 須為 supported 或 insufficient"]
    segments = output.get("segments")
    if not isinstance(segments, list) or (not segments and output["status"] == "supported"):
        return ["segments 須為非空清單，每項含 text 與 citations"]
    problems, unknown = [], []
    for n, item in enumerate(segments, 1):
        if not isinstance(item, dict) or not isinstance(item.get("text"), str) or not item["text"].strip():
            problems.append(f"第 {n} 個 segment 的 text 不可空白")
            continue
        citations = item.get("citations", [])
        if not isinstance(citations, list) or not all(isinstance(c, str) for c in citations):
            problems.append(f"第 {n} 個 segment 的 citations 須為字串清單")
            continue
        unknown += [c for c in citations if c not in by_id and c not in unknown]
    if unknown:
        problems.append("引用了 evidence 中不存在的 id：" + "、".join(unknown))
    if (not problems and output["status"] == "supported"
            and not any(item.get("citations") for item in segments)):
        problems.append("supported 的回答至少要有一個 segment 帶引用")
    return problems


# ---- 字詞核對：只標示可能掛錯的引用，不是語意驗證 ----

# 暫定：2026-11-17 實跑 6 題中 17 句帶引用，合理改寫與掛錯的句子重疊都落在 0.14–0.58，分不開；
# 因此只標近乎無交集的極端情況，主要靠英文詞／數字缺漏。見 progress，不是品質門檻。
LOW_OVERLAP = 0.1
TERM = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*|\d+(?:\.\d+)?")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")
BRACKET = re.compile(r"\s*\[([^\[\]]+)\]")


def _terms(text: str) -> list[str]:
    found = []
    for t in TERM.findall(text):
        if (len(t) >= 2 or t.isdigit()) and t.lower() not in [f.lower() for f in found]:
            found.append(t)
    return found


def _bigrams(text: str) -> set[str]:
    return {run[i:i + 2] for run in CJK_RUN.findall(text) for i in range(len(run) - 1)}


def check_segment(text: str, cited_texts: list[str]) -> dict:
    """比對句子與被引用片段：英文詞與數字是否出現、中文二元組重疊比例。"""
    joined = "\n".join(cited_texts)
    lower = joined.lower()
    missing = [t for t in _terms(text) if t.lower() not in lower]
    grams = _bigrams(text)
    overlap = round(len(grams & _bigrams(joined)) / len(grams), 2) if grams else None
    reasons = []
    if missing:
        reasons.append("引用片段中找不到：" + "、".join(missing))
    if overlap is not None and overlap < LOW_OVERLAP:
        reasons.append(f"與引用片段的中文字詞重疊低（{overlap}）")
    return {"missing_terms": missing, "overlap": overlap, "flagged": bool(reasons), "reasons": reasons}


def _strip_ids(text: str, by_id: dict) -> str:
    """模型若自行在句中寫 [id]，移除；標記一律由程式產生。"""
    def drop(match):
        parts = [p for p in re.split(r"[,，、\s]+", match.group(1)) if p]
        return "" if parts and all(p in by_id for p in parts) else match.group(0)
    return BRACKET.sub(drop, text).strip()


def answer(question: str, textbook: list[dict], external: list[dict], generate) -> dict:
    evidence = build_evidence(textbook, external)
    if not evidence:
        text = "教材與外部搜尋都沒有取得依據，無法解答。"
        return {"status": "insufficient", "answer": text,
                "segments": [{"text": text, "citations": [], "markers": [], "check": None}],
                "citations": [], "sources": [], "basis": "none", "flagged_segments": 0,
                "validation": "no_evidence", "prompt_sha256": None}
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
        still = _check_output(generated["output"], by_id)
        if still:
            raise ValueError("模型引用不存在或回答缺少引用，修正一次後仍不合格，拒絕顯示為有依據回答："
                             + "；".join(still))
    output = generated["output"]
    if not output["segments"]:  # 模型判定依據不足卻未說明時，由程式補一句，不視為格式錯誤
        output = {**output, "segments": [{"text": "教材與外部資料不足以判定此題，模型未說明缺少的內容。",
                                          "citations": []}]}

    markers, counts = {}, {"textbook": 0, "external": 0}
    segments = []
    for item in output["segments"]:
        cited = list(dict.fromkeys(item.get("citations", [])))
        for c in cited:
            if c not in markers:
                kind = by_id[c]["source_type"]
                counts[kind] += 1
                markers[c] = ("教材" if kind == "textbook" else "外部") + str(counts[kind])
        text = _strip_ids(item["text"], by_id)
        segments.append({"text": text, "citations": cited, "markers": [markers[c] for c in cited],
                         "check": check_segment(text, [by_id[c]["text"] for c in cited]) if cited else None})
    citations = list(markers)
    sources = [{"id": c, "marker": markers[c], "source_type": by_id[c]["source_type"], "label": by_id[c]["label"],
                **({"url": by_id[c]["url"]} if by_id[c].get("url") else {})} for c in citations]
    labels = [s["label"] for s in sources]
    for s in sources:  # 同頁多個片段時標出第幾段，避免兩個標記看起來指向同一處
        if labels.count(s["label"]) > 1 and s["id"].rsplit(":", 1)[-1].isdigit():
            s["label"] += f" 第{int(s['id'].rsplit(':', 1)[-1]) + 1}段"
    types = {s["source_type"] for s in sources}
    basis = ("mixed" if types == {"textbook", "external"} else
             "textbook_only" if types == {"textbook"} else
             "external_only" if types == {"external"} else "none")
    lines = [s["text"] + (" " + "".join(f"[{m}]" for m in s["markers"]) if s["markers"] else "")
             for s in segments]
    return {"status": output["status"], "answer": "\n".join(lines), "segments": segments,
            "citations": citations, "sources": sources, "basis": basis,
            "flagged_segments": sum(1 for s in segments if s["check"] and s["check"]["flagged"]),
            "model": generated.get("model"), "usage": generated.get("usage"),
            "llm_elapsed_ms": generated.get("elapsed_ms"), "prompt_sha256": digest(template.encode()),
            "repair_attempts": repairs, "low_overlap_threshold": LOW_OVERLAP,
            "validation": "citation_ids_and_lexical_check_not_semantic_verification"}


def render_text(result: dict) -> str:
    """給人看的版本：每句後標明教材或外部，可能掛錯的引用加 ⚠。"""
    basis = {"textbook_only": "只用教材", "external_only": "只用外部資料（教材未涵蓋）",
             "mixed": "教材＋外部資料", "none": "無依據"}[result["basis"]]
    lines = [f"狀態：{'有依據' if result['status'] == 'supported' else '依據不足'}（{basis}）", ""]
    for s in result["segments"]:
        lines.append(s["text"] + (" " + "".join(f"[{m}]" for m in s["markers"]) if s["markers"] else ""))
        if s["check"] and s["check"]["flagged"]:
            lines.append("  ⚠ 引用可能不支持此句：" + "；".join(s["check"]["reasons"]))
    lines += ["", "依據："]
    for s in result["sources"]:
        lines.append(f"- [{s['marker']}] {s['label']}" + (f"  {s['url']}" if s.get("url") else ""))
    if not result["sources"]:
        lines.append("- （無）")
    cited = sum(1 for s in result["segments"] if s["citations"])
    lines += ["", f"核對：{cited} 句有引用，其中 {result['flagged_segments']} 句可能不支持"
              "（字詞比對，非語意驗證；未引用的句子不檢查）。",
              "提醒：程式只檢查引用存在與字詞重疊，不保證解答正確。"]
    return "\n".join(lines)

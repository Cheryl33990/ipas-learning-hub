"""RAG 流程：教材檢索＋外部搜尋 → LLM 帶引用回答。

引用只能指向本次實際提供的片段；每個引用由程式依片段資料標成教材或外部，不採信模型自稱的來源。
檢查確認引用存在、格式，並以字詞比對標出可能掛錯的引用；不是語意驗證，不代表內容正確。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .knowledge import digest
from .profile import DEFAULT_PROFILE, answer_prompt

PROMPTS = Path(__file__).with_name("prompts")
QUERY_PROMPT = PROMPTS / "web_queries.txt"
MAX_WEB_QUERIES = 3
# 維基百科文字通常以 CC BY-SA 4.0 授權；回答是模型改寫，需標示來源、授權與「經改寫」
WIKIPEDIA_LICENSE = "CC BY-SA 4.0"
WIKIPEDIA_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0/"


def textbook_label(hit: dict) -> str:
    if hit.get("document_type") == "document":
        return f"文件 {hit.get('name', hit['source'])}，版本：{hit.get('version', '未提供')}"
    return f"教材 {hit.get('name', hit['source'])} {hit['page']}"


def external_label(hit: dict) -> str:
    provider = {"wikipedia": "維基百科", "wikipedia-en": "英文維基百科"}.get(
        hit.get("provider"), hit.get("provider", "外部")
    )
    return f"外部 {provider}：{hit['title']}"


def build_evidence(textbook: list[dict], external: list[dict]) -> list[dict]:
    evidence = [
        {"id": h["id"], "source_type": "textbook", "label": textbook_label(h), "text": h["text"]} for h in textbook
    ]
    evidence += [
        {"id": h["id"], "source_type": "external", "label": external_label(h), "url": h.get("url"), "text": h["text"]}
        for h in external
    ]
    ids = [e["id"] for e in evidence]
    if len(ids) != len(set(ids)):
        raise ValueError("教材與外部片段的 id 重複，無法區分來源")
    return evidence


def plan_web_queries(question: str, generate) -> list[dict]:
    """請模型列出要查證的概念（中英概念詞，必要時加領域詞）；回覆不合格就拋錯，不改用猜測的搜尋詞。"""
    output = generate(QUERY_PROMPT.read_text(encoding="utf-8"), question)["output"]
    queries = output.get("queries")
    if not isinstance(queries, list):
        raise ValueError("搜尋詞規劃回覆不符合格式")
    cleaned, seen = [], set()
    for item in queries:
        if isinstance(item, str):  # 容許只給中文詞
            item = {"zh": item}
        if not isinstance(item, dict) or not isinstance(item.get("zh"), str):
            raise ValueError("搜尋詞規劃回覆不符合格式")

        def text(key, limit, item=item):
            return (item[key].strip()[:limit] or None) if isinstance(item.get(key), str) else None

        zh = item["zh"].strip()
        if zh and zh not in seen and len(zh) <= 40:
            seen.add(zh)
            cleaned.append(
                {"zh": zh, "en": text("en", 60), "domain_zh": text("domain_zh", 20), "domain_en": text("domain_en", 40)}
            )
    return cleaned[:MAX_WEB_QUERIES]


def gather_external(queries: list[dict], search, per_query: int, limit: int, errors: list | None = None) -> list[dict]:
    """每個搜尋詞輪流取結果，避免前面的詞佔滿上限。

    傳入 errors 時，單一搜尋詞失敗只記錄並略過，不影響其他詞；未傳入則直接拋出。
    """
    results = []
    for q in queries:
        try:
            results.append(
                search.search(
                    q["zh"],
                    per_query,
                    context=q.get("domain_zh"),
                    fallback_query=q.get("en"),
                    fallback_context=q.get("domain_en"),
                )
            )
        except ValueError as exc:
            if errors is None:
                raise
            errors.append(f"{q['zh']}：{exc}")
            results.append([])
    hits, seen = [], set()
    for rank in range(per_query):
        for found in results:
            if rank < len(found) and found[rank]["id"] not in seen:
                seen.add(found[rank]["id"])
                hits.append(found[rank])
    return hits[:limit]


def complete_chunk_ids(output, by_id: dict, completed: list) -> None:
    """模型常把教材片段 id「來源:頁:序號」少寫最後的「:序號」；只對應到唯一一個教材片段時由程式補全。

    同頁有多個片段（無法判斷是哪一段）或外部來源時不補，照常交給 _check_output 判為不存在。
    補全紀錄附加到 completed，寫進執行紀錄以便追查。結構不合格的回覆不處理，交給 _check_output。
    """
    if not isinstance(output, dict) or not isinstance(output.get("segments"), list):
        return
    for item in output["segments"]:
        citations = item.get("citations") if isinstance(item, dict) else None
        if not isinstance(citations, list):
            continue
        for n, c in enumerate(citations):
            if not isinstance(c, str) or c in by_id:
                continue
            matches = [
                i for i in by_id if by_id[i]["source_type"] == "textbook" and re.fullmatch(re.escape(c) + r":\d+", i)
            ]
            if len(matches) == 1:
                citations[n] = matches[0]
                completed.append({"cited": c, "completed": matches[0]})


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
    if not problems and output["status"] == "supported" and not any(item.get("citations") for item in segments):
        problems.append("supported 的回答至少要有一個 segment 帶引用")
    return problems


# ---- 字詞核對：只標示可能掛錯的引用，不是語意驗證 ----

# 暫定：2026-11-17 實跑 6 題中 17 句帶引用，合理改寫與掛錯的句子重疊都落在 0.14–0.58，分不開；
# 因此只標近乎無交集的極端情況，主要靠英文詞／數字缺漏。見 progress，不是品質門檻。
LOW_OVERLAP = 0.1
TERM = re.compile(r"[A-Za-z][A-Za-z0-9]*(?:[-_.][A-Za-z0-9]+)*|\d+(?:\.\d+)?")
CJK_RUN = re.compile(r"[\u3400-\u9fff]+")
BRACKET = re.compile(r"\s*(?:\[([^\[\]]+)\]|[(（]([^()（）]+)[)）])")
OPTION = re.compile(r"[(（]\s*([A-D])\s*[)）]")
CHOICE = re.compile(r"答案\s*[:：]\s*[(（]?\s*([A-D])(?![A-Za-z])")


def has_options(question: str) -> bool:
    """題目含 (A)(B) 這類選項標記時，視為選擇題。"""
    return len(set(OPTION.findall(question))) >= 2


STRAY_CHOICE = re.compile(r"\s*答案\s*[:：]\s*[(（]?\s*([A-D])\s*[)）]?(?![A-Za-z])[。.]?")


def drop_unasked_choice(segments: list[dict]) -> tuple[list[dict], str | None]:
    """題目沒有選項時，模型仍可能照選擇題習慣補一句「答案：X」；由程式移除，不靠 prompt 約束。

    回傳移除後的 segments 與被移除的最後一個選項代號；只剩答案的 segment 整個刪除。
    """
    kept, removed = [], None
    for item in segments:
        found = STRAY_CHOICE.findall(item["text"])
        if not found:
            kept.append(item)
            continue
        removed = found[-1]
        text = STRAY_CHOICE.sub("", item["text"]).strip()
        if text:
            kept.append({**item, "text": text})
    return kept, removed


def answer_choice(segments: list[dict]) -> str | None:
    """從最後一句往前找「答案：X」；找不到回傳 None。"""
    for item in reversed(segments):
        found = CHOICE.findall(item.get("text", "")) if isinstance(item, dict) else []
        if found:
            return found[-1]
    return None


def _terms(text: str) -> list[str]:
    found = []
    for t in TERM.findall(text):
        if (len(t) >= 2 or t.isdigit()) and t.lower() not in [f.lower() for f in found]:
            found.append(t)
    return found


def _bigrams(text: str) -> set[str]:
    return {run[i : i + 2] for run in CJK_RUN.findall(text) for i in range(len(run) - 1)}


def check_segment(text: str, cited_texts: list[str], question: str = "") -> dict:
    """比對句子與被引用片段：英文詞與數字是否出現、中文二元組重疊比例。

    被引用片段沒有中文（如英文維基）時不算重疊，只檢查英文詞，避免中文句引英文來源被誤標。
    缺漏的詞若出現在題目中，另列 question_terms 並在原因註明；仍算標記，因為題目的詞也可能是真的掛錯。
    """
    joined = "\n".join(cited_texts)
    lower = joined.lower()
    missing = [t for t in _terms(text) if t.lower() not in lower]
    from_question = [t for t in missing if t.lower() in question.lower()]
    grams, cited_grams = _bigrams(text), _bigrams(joined)
    overlap = round(len(grams & cited_grams) / len(grams), 2) if grams and cited_grams else None
    reasons = []
    others = [t for t in missing if t not in from_question]
    if others:
        reasons.append("引用片段中找不到：" + "、".join(others))
    if from_question:
        reasons.append("引用片段中找不到題目中的詞（可能只是重述題目）：" + "、".join(from_question))
    if overlap is not None and overlap < LOW_OVERLAP:
        reasons.append(f"與引用片段的中文字詞重疊低（{overlap}）")
    return {
        "missing_terms": missing,
        "question_terms": from_question,
        "overlap": overlap,
        "flagged": bool(reasons),
        "reasons": reasons,
    }


def _strip_ids(text: str, by_id: dict) -> str:
    """模型若自行在句中寫 [id] 或（id），移除；標記一律由程式產生。括號內不全是 id 的保留。"""

    def drop(match):
        parts = [p for p in re.split(r"[,，、\s]+", match.group(1) or match.group(2)) if p]
        return "" if parts and all(p in by_id for p in parts) else match.group(0)

    return BRACKET.sub(drop, text).strip()


def _generate_checked(
    template: str, user: str, by_id: dict, choice_expected: bool, generate, completed: list
) -> tuple[dict, int]:
    """呼叫模型並檢查引用；不合格只給一次修正機會，仍不合格就拒絕，不自行刪改引用。

    選擇題只缺「答案：X」時也會要求修正一次，但修正後仍缺只照常顯示並註明，不拒絕。
    回傳 (generated, 修正次數)。
    """
    generated = generate(template, user)
    complete_chunk_ids(generated["output"], by_id, completed)
    problems = _check_output(generated["output"], by_id)
    if (
        not problems
        and choice_expected
        and generated["output"]["status"] == "supported"
        and not answer_choice(generated["output"]["segments"])
    ):
        problems = ["選擇題的最後一個 segment 須為「答案：X」（X 為 A、B、C 或 D）"]
    if not problems:
        return generated, 0
    feedback = (
        "你上一次的回覆不合格："
        + "；".join(problems)
        + "。請只使用 evidence 中實際存在的 id，依相同規則重新回覆完整 JSON。"
    )
    generated = generate(template, user + "\n\n" + feedback)
    complete_chunk_ids(generated["output"], by_id, completed)
    still = _check_output(generated["output"], by_id)
    if still:
        raise ValueError("模型引用不存在或回答缺少引用，修正一次後仍不合格，拒絕顯示為有依據回答：" + "；".join(still))
    return generated, 1


def _mark_segments(raw_segments: list[dict], by_id: dict, question: str) -> tuple[list[dict], dict]:
    """依首次出現順序替引用編號（教材N／文件N／外部N），去掉模型寫進句中的 id，並逐句做字詞核對。"""
    markers, counts = {}, {"textbook": 0, "external": 0}
    segments = []
    for item in raw_segments:
        cited = list(dict.fromkeys(item.get("citations", [])))
        for c in cited:
            if c not in markers:
                kind = by_id[c]["source_type"]
                counts[kind] += 1
                label = "文件" if by_id[c]["label"].startswith("文件 ") else "教材"
                markers[c] = (label if kind == "textbook" else "外部") + str(counts[kind])
        text = _strip_ids(item["text"], by_id)
        segments.append(
            {
                "text": text,
                "citations": cited,
                "markers": [markers[c] for c in cited],
                "check": check_segment(text, [by_id[c]["text"] for c in cited], question) if cited else None,
            }
        )
    return segments, markers


def _build_sources(markers: dict, by_id: dict, located: dict, licensed: set) -> list[dict]:
    """每個被引用的片段一筆來源；來源類型、網址、授權與 PDF 頁都由程式依片段資料填入。"""
    sources = [
        {
            "id": c,
            "marker": markers[c],
            "source_type": by_id[c]["source_type"],
            "label": by_id[c]["label"],
            **({"url": by_id[c]["url"]} if by_id[c].get("url") else {}),
            **({"license": WIKIPEDIA_LICENSE} if c in licensed else {}),
            **{key: located[c][key] for key in ("source", "pdf_page") if located.get(c, {}).get(key)},
        }
        for c in markers
    ]
    labels = [s["label"] for s in sources]
    for s in sources:  # 同頁多個片段時標出第幾段，避免兩個標記看起來指向同一處
        if labels.count(s["label"]) > 1 and s["id"].rsplit(":", 1)[-1].isdigit():
            s["label"] += f" 第{int(s['id'].rsplit(':', 1)[-1]) + 1}段"
    return sources


def _basis(sources: list[dict]) -> str:
    types = {s["source_type"] for s in sources}
    return (
        "mixed"
        if types == {"textbook", "external"}
        else "textbook_only"
        if types == {"textbook"}
        else "external_only"
        if types == {"external"}
        else "none"
    )


def answer(question: str, textbook: list[dict], external: list[dict], generate, prompt: str | None = None) -> dict:
    """prompt 是 profile 組好的系統提示；未指定時用通用設定（見 profile.py）。"""
    evidence = build_evidence(textbook, external)
    if not evidence:
        text = "教材與外部搜尋都沒有取得依據，無法解答。"
        return {
            "status": "insufficient",
            "answer": text,
            "segments": [{"text": text, "citations": [], "markers": [], "check": None}],
            "citations": [],
            "sources": [],
            "basis": "none",
            "flagged_segments": 0,
            "validation": "no_evidence",
            "prompt_sha256": None,
        }
    template = prompt if prompt is not None else answer_prompt(DEFAULT_PROFILE)
    user = json.dumps({"question": question, "evidence": evidence}, ensure_ascii=False)
    by_id = {e["id"]: e for e in evidence}
    located = {h["id"]: h for h in textbook}  # 來源識別與 PDF 頁只給程式顯示用，不送進模型
    licensed = {h["id"] for h in external if str(h.get("provider", "")).startswith("wikipedia")}
    choice_expected = has_options(question)
    completed = []
    generated, repairs = _generate_checked(template, user, by_id, choice_expected, generate, completed)

    output = generated["output"]
    removed_choice = None
    if not choice_expected:
        segments_kept, removed_choice = drop_unasked_choice(output["segments"])
        output = {**output, "segments": segments_kept}
    if not output["segments"]:  # 模型判定依據不足卻未說明時，由程式補一句，不視為格式錯誤
        output = {
            **output,
            "segments": [{"text": "教材與外部資料不足以判定此題，模型未說明缺少的內容。", "citations": []}],
        }

    segments, markers = _mark_segments(output["segments"], by_id, question)
    sources = _build_sources(markers, by_id, located, licensed)
    lines = [s["text"] + (" " + "".join(f"[{m}]" for m in s["markers"]) if s["markers"] else "") for s in segments]
    return {
        "status": output["status"],
        "answer": "\n".join(lines),
        "segments": segments,
        "answer_choice": answer_choice(segments),
        "choice_expected": choice_expected and output["status"] == "supported",
        "citations": list(markers),
        "sources": sources,
        "basis": _basis(sources),
        "flagged_segments": sum(1 for s in segments if s["check"] and s["check"]["flagged"]),
        "model": generated.get("model"),
        "usage": generated.get("usage"),
        "llm_elapsed_ms": generated.get("elapsed_ms"),
        "prompt_sha256": digest(template.encode()),
        "repair_attempts": repairs,
        "removed_choice": removed_choice,
        "completed_citations": completed,
        "low_overlap_threshold": LOW_OVERLAP,
        "validation": "citation_ids_and_lexical_check_not_semantic_verification",
    }


def render_text(result: dict, link_for=None, markdown: bool = False) -> str:
    """給人看的版本：每句後標明教材或外部，可能掛錯的引用加 ⚠。

    教材引用把章節頁碼與 PDF 頁並列。link_for(來源) 回傳可開啟的網址或 None，未提供時只用來源自帶的網址；
    markdown 為真時依據清單寫成 Markdown 連結，且每句、每個 ⚠ 各自成段（聊天介面會把單一換行併成同一段），
    供會渲染 Markdown 的聊天介面使用。
    """
    basis = {
        "textbook_only": "只用教材",
        "external_only": "只用外部資料（教材未涵蓋）",
        "mixed": "教材＋外部資料",
        "none": "無依據",
    }[result["basis"]]
    if any(s["label"].startswith("文件 ") for s in result["sources"]):
        basis = basis.replace("教材", "文件")
    body = []
    for s in result["segments"]:
        body.append(s["text"] + (" " + "".join(f"[{m}]" for m in s["markers"]) if s["markers"] else ""))
        if s["check"] and s["check"]["flagged"]:
            body.append(("" if markdown else "  ") + "⚠ 引用可能不支持此句：" + "；".join(s["check"]["reasons"]))
    if result.get("choice_expected") and not result.get("answer_choice"):
        body.append("⚠ 模型未明寫答案選項，請依上方逐項說明自行判斷。")
    status = f"狀態：{'有依據' if result['status'] == 'supported' else '依據不足'}（{basis}）"
    lines = [status, "", *(["\n\n".join(body)] if markdown else body), "", "依據："]
    for s in result["sources"]:
        label = s["label"] + (f"（PDF 第 {s['pdf_page']} 頁）" if s.get("pdf_page") else "")
        url = (link_for(s) if link_for else None) or s.get("url")
        if url and markdown:
            label = "[" + label.replace("[", "\\[").replace("]", "\\]") + f"]({url})"
        elif url:
            label += f"  {url}"
        lines.append(f"- [{s['marker']}] {label}" + (f"  授權：{s['license']}" if s.get("license") else ""))
    if not result["sources"]:
        lines.append("- （無）")
    if any(s.get("license") == WIKIPEDIA_LICENSE for s in result["sources"]):
        lines += [
            "",
            f"維基百科內容依 {WIKIPEDIA_LICENSE}（{WIKIPEDIA_LICENSE_URL}）授權；"
            "上方句子由模型依條目改寫，非原文，原始版本見各條目連結。",
        ]
    cited = sum(1 for s in result["segments"] if s["citations"])
    lines += [
        "",
        f"核對：{cited} 句有引用，其中 {result['flagged_segments']} 句可能不支持"
        "（字詞比對，非語意驗證；未引用的句子不檢查）。",
        *([""] if markdown else []),
        "提醒：程式只檢查引用存在與字詞重疊，不保證解答正確。",
    ]
    return "\n".join(lines)

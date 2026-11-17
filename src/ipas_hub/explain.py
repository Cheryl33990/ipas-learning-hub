"""逐選項解析：檢查資料檔、產生閱讀用文件與人工複核清單。

用法：uv run python -m ipas_hub.explain
- 讀 docs/project/explanations/115-3-subject1.json
- 檢查：題號齊全、四個選項都有說明、答案與試題答案欄及紀錄表一致、
  「對／錯」的開頭與答案一致、引用的頁碼存在且該頁真的有引用的詞
- 產生 docs/project/explanations/115-3-subject1.md（不含題目原文，進版控）
- 產生 data/review/115-3-subject1-review.md（含題目原文，不進版控，給人複核時對照）
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

from .text import normalize

OPTION_KEYS = ("A", "B", "C", "D")
SAMPLE_SIZE = 5
SAMPLE_SEED = 20261116


def validate(data: dict, official: dict[int, str], pages: dict[str, str] | None,
             additional_pages: dict[str, dict[str, str]] | None = None) -> list[str]:
    """回傳問題清單；空清單表示通過。pages 為 None 時略過頁面內容的比對。"""
    problems = []
    qs = data.get("questions", [])
    numbers = [q.get("n") for q in qs]
    if numbers != list(range(1, len(official) + 1)):
        problems.append(f"題號不是 1–{len(official)} 依序排列")
    for q in qs:
        n = q.get("n")
        if official.get(n) != q.get("answer"):
            problems.append(f"第 {n} 題：答案 {q.get('answer')} 與官方答案 {official.get(n)} 不一致")
        if not q.get("key"):
            problems.append(f"第 {n} 題：缺少重點說明")
        options = q.get("options", {})
        if tuple(options) != OPTION_KEYS:
            problems.append(f"第 {n} 題：選項不是 A、B、C、D 四個")
        for letter, why in options.items():
            expected = "對" if letter == q.get("answer") else "錯"
            if not why.startswith(expected + "。"):
                problems.append(f"第 {n} 題選項 {letter}：說明應以「{expected}。」開頭")
            if letter != q.get("answer") and len(why) <= 2:
                problems.append(f"第 {n} 題選項 {letter}：沒有說明為什麼錯")
        if not q.get("basis") and not q.get("outside"):
            problems.append(f"第 {n} 題：沒有教材依據，也沒有標示教材外")
        for ref in list(q.get("basis", [])) + list(q.get("see_also", [])):
            page, term = ref.get("page"), ref.get("term", "")
            source = ref.get("source", "subject1")
            if source != "subject1" and source not in data.get("additional_guides", {}):
                problems.append(f"第 {n} 題：未知教材來源 {source}")
                continue
            source_pages = pages if source == "subject1" else (additional_pages or {}).get(source)
            if source != "subject1" and source_pages is None:
                problems.append(f"第 {n} 題：教材來源 {source} 未讀取，不能驗證引用")
                continue
            if source_pages is None:
                continue
            if page not in source_pages:
                problems.append(f"第 {n} 題：引用的頁碼 {page} 不存在")
            elif normalize(term).lower() not in source_pages[page].lower():
                problems.append(f"第 {n} 題：{page} 找不到「{term}」")
    return problems


def review_set(data: dict) -> tuple[list[int], list[int]]:
    """回傳（必看題號，抽查題號）。抽查是從非必看的題目用固定種子抽出。"""
    must = [q["n"] for q in data["questions"] if q.get("review") == "必看"]
    rest = [q["n"] for q in data["questions"] if q.get("review") != "必看"]
    sample = sorted(random.Random(SAMPLE_SEED).sample(rest, min(SAMPLE_SIZE, len(rest))))
    return must, sample


def _refs(refs: list[dict]) -> str:
    return "、".join(f"{source_name(r.get('source', 'subject1'))} {r['page']}（{r['term']}" + (f"；{r['note']}" if r.get("note") else "") + "）" for r in refs)


def source_name(source: str) -> str:
    return {"subject1": "科目 1", "subject2": "科目 2"}.get(source, source)


def render_source_overview(data: dict) -> str:
    """依現有引用產生逐題雙科索引；不推論未引用的教材沒有相關內容。"""
    lines = [
        "## 雙科教材對照索引", "",
        "依據：能支持題目核心概念的頁面；相關：僅供延伸閱讀或支持部分說明。兩者都不代表已確認實際命題出處或所有選項理由。",
        "「尚未列入」表示目前沒有該科引用，不能據此判定該科沒有內容。限制與引用詞見下方逐題解析。", "",
        "| 題號 | 科目 1：人工智慧基礎概論 | 科目 2：生成式 AI 應用與規劃 |",
        "|---|---|---|",
    ]
    for q in data["questions"]:
        cells = []
        for source in ("subject1", "subject2"):
            parts = []
            for field, label in (("basis", "依據"), ("see_also", "相關")):
                pages = list(dict.fromkeys(r["page"] for r in q.get(field, [])
                                          if r.get("source", "subject1") == source))
                if pages:
                    parts.append(f"{label}：{'、'.join(pages)}")
            cells.append("；".join(parts) or "尚未列入")
        lines.append(f"| {q['n']} | {cells[0]} | {cells[1]} |")
    return "\n".join(lines) + "\n\n## 逐題解析\n\n"


def render_question(q: dict, question_text: str | None = None) -> str:
    lines = [f"### 第 {q['n']} 題　答案 {q['answer']}", ""]
    if question_text:
        lines += [f"> {question_text}", ""]
    lines += [f"**重點**：{q['key']}", ""]
    lines += [f"- ({letter}) {why}" for letter, why in q["options"].items()]
    lines.append("")
    lines.append("**教材依據**：" + (_refs(q["basis"]) if q["basis"] else "目前未找到足以支持核心概念的頁面"))
    if q.get("see_also"):
        lines.append("")
        lines.append("**教材相關頁**：" + _refs(q["see_also"]))
    if q.get("outside"):
        lines.append("")
        lines.append("**依據限制／補充知識**：" + q["outside"])
    lines.append("")
    return "\n".join(lines)


def render_public(data: dict) -> str:
    head = [
        "---",
        "title: 逐選項解析：115 年第三次初級科目 1",
        "status: draft",
        "updated: 2026-11-16",
        "---",
        "",
        "# 逐選項解析：115 年第三次初級科目 1",
        "",
        f"- 試題：{data['exam']}",
        f"- 教材：{data['guide']}",
        f"- 撰寫：{data['author']}",
        "- 本檔由 `uv run python -m ipas_hub.explain` 從同名的 JSON 產生，請改 JSON，不要直接改本檔。",
        "- 不含題目原文，請對照官方公告試題閱讀。頁碼是教材頁尾印的頁碼。",
        "- 兩科教材相互參照；每筆引用明列科目與頁碼，相關頁或關鍵詞存在，不代表足以驗證整段理由。",
        "- 「依據限制／補充知識」列出未由引用支持的部分；未找到不代表兩科教材都沒有。這是學習對照，不是實際命題出處的認定。新增跨科依據不改寫第一輪探索結果。",
        *[f"- {source_name(key)} 教材：{value['name']}" for key, value in data.get("additional_guides", {}).items()],
        "",
    ]
    return "\n".join(head) + "\n" + render_source_overview(data) + "\n".join(render_question(q) for q in data["questions"])


def render_review(data: dict, texts: dict[int, str]) -> str:
    must, sample = review_set(data)
    by_n = {q["n"]: q for q in data["questions"]}
    out = ["# 複核對照（含題目原文，不進版控）", "", "判定請填在 docs/project/validation/2026-11-16-explanation-review.md。",
           "引用明列科目與教材頁尾頁碼，屬學習依據，未認定實際命題出處。", ""]
    for title, numbers in (("必看", must), ("抽查", sample)):
        out += [f"## {title}", ""]
        for n in numbers:
            q = by_n[n]
            if q.get("review_reason"):
                out += [f"需要看的原因：{q['review_reason']}", ""]
            out.append(render_question(q, texts.get(n)))
    return "\n".join(out)


def write_review(path: Path, content: str) -> Path:
    """既有對照檔可能有人工筆記；不同時另存新版，不覆寫使用者檔案。"""
    if path.exists() and path.read_text(encoding="utf-8") != content:
        path = path.with_name(path.stem + ".generated.md")
    path.write_text(content, encoding="utf-8", newline="\n")
    return path


def main() -> None:
    root = Path.cwd()
    src = root / "docs/project/explanations/115-3-subject1.json"
    data = json.loads(src.read_text(encoding="utf-8"))

    from .exam import read_questions
    from .guide import read_pages
    from .record import parse_record

    from .explore2 import EXAM_PDF, GUIDE_PDF  # 同一份試題與科目 1 教材
    exam_pdf = [root / EXAM_PDF] if (root / EXAM_PDF).is_file() else []
    guide_pdf = [root / GUIDE_PDF] if (root / GUIDE_PDF).is_file() else []
    record = parse_record((root / "docs/project/discovery/exploration-1-record.md").read_text(encoding="utf-8"))
    official = {n: g.answer for n, g in record.items()}
    texts: dict[int, str] = {}
    if exam_pdf:
        questions = read_questions(exam_pdf[0])
        texts = {q.number: q.text for q in questions}
        disagree = [q.number for q in questions if official.get(q.number) != q.answer]
        if disagree:
            sys.exit(f"紀錄表與試題答案欄不一致：{disagree}")
    if len(guide_pdf) != 1:
        sys.exit(f"找不到科目 1 教材 {GUIDE_PDF}，拒絕略過引用檢查")
    pages = {p.label: p.text for p in read_pages(guide_pdf[0])}
    additional_pages = {}
    for source, metadata in data.get("additional_guides", {}).items():
        path = root / metadata["path"]
        if not path.is_file():
            sys.exit(f"缺少教材 {source}：{metadata['path']}")
        additional_pages[source] = {p.label: p.text for p in read_pages(path)}

    problems = validate(data, official, pages, additional_pages)
    for p in problems:
        print("問題：" + p)
    if problems:
        sys.exit(f"共 {len(problems)} 個問題，未產生文件")

    src.with_suffix(".md").write_text(render_public(data), encoding="utf-8", newline="\n")
    must, sample = review_set(data)
    if texts:
        review = root / "data/review/115-3-subject1-review.md"
        review.parent.mkdir(parents=True, exist_ok=True)
        review = write_review(review, render_review(data, texts))
        print(f"複核對照：{review.relative_to(root)}（既有筆記不覆寫）")
    grounded = sum(1 for q in data["questions"] if q["basis"])
    print(f"檢查通過：{len(data['questions'])} 題；有教材依據 {grounded} 題；"
          f"頁面內容比對{'已做' if pages else '未做（沒有教材 PDF）'}")
    print("必看：", must)
    print("抽查：", sample)


if __name__ == "__main__":
    main()

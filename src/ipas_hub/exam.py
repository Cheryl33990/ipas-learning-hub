"""公告試題：把擷取文字切成一題一題（題組情境、題幹加四個選項）。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .text import normalize

_NOISE = re.compile(
    r"^\s*(\d+\s*年第.+?【公告試題】|第.科：.+|考試日期：.+|第\s*\d+\s*頁，共\s*\d+\s*頁|答案\s*題目|題目\s*答案|[一二三四五六七八九十]、\S{1,6}題)\s*$",
    re.M,
)
# 答案欄偶爾是全形字母（Ａ–Ｄ）；漏認會讓整題併入前一題
_QUESTION_START = re.compile(r"^\s*([A-DＡ-Ｄ])\s+(\d{1,2})\.\s", re.M)
# 題組指示句，例如「請依據下方資訊回答第 44~45 題。」「請根據上述情境，回答第 49~50 題。」；可能跨行
_GROUP_HEADER = re.compile(r"請[^。]{0,12}?回答\s*第\s*(\d{1,2})\s*[~～－-]\s*(\d{1,2})\s*題[。．.]?")
# 題組情境從前一題最後一個 (D) 選項之後的第一個縮排行開始（官方試題的情境段落都縮排）
_INDENTED_LINE = re.compile(r"\n[ \t　]{2,}\S")
_LAST_OPTION = re.compile(r"\(D\)")
_FULLWIDTH_OFFSET = ord("Ａ") - ord("A")


@dataclass(frozen=True)
class Question:
    number: int
    answer: str  # 官方答案欄的字母（A–D）
    text: str    # 題組情境（若有）加題幹與四個選項，正規化後


def _split_group_context(segment: str) -> tuple[str, str | None, range]:
    """把接在前一題選項後面的題組情境切出來，回傳（本題文字, 情境, 情境適用的題號）。

    情境可能在指示句之前（「上述情境」）或之後（「下方資訊」）；兩種都從最後一個 (D) 選項之後的
    第一個縮排行開始，找不到縮排行時從指示句那一行開始。指示句本身不保留。
    """
    header = _GROUP_HEADER.search(segment)
    if header is None:
        return segment, None, range(0)
    before = segment[: header.start()]
    options = list(_LAST_OPTION.finditer(before))
    indented = _INDENTED_LINE.search(before, options[-1].end() if options else 0)
    start = indented.start() if indented else before.rfind("\n") + 1
    context = normalize(segment[start : header.start()] + "\n" + segment[header.end() :])
    return segment[:start], context, range(int(header.group(1)), int(header.group(2)) + 1)


def parse_questions(raw: str) -> list[Question]:
    body = _NOISE.sub("", raw)
    starts = list(_QUESTION_START.finditer(body))
    parsed, contexts = [], {}
    for m, nxt in zip(starts, starts[1:] + [None]):
        end = nxt.start() if nxt else len(body)
        text, context, numbers = _split_group_context(body[m.end() : end])
        if context:
            contexts.update(dict.fromkeys(numbers, context))
        letter = m.group(1)
        answer = chr(ord(letter) - _FULLWIDTH_OFFSET) if letter >= "Ａ" else letter
        parsed.append((int(m.group(2)), answer, text))
    return [Question(number, answer, normalize(contexts.get(number, "") + "\n" + text))
            for number, answer, text in parsed]


def read_questions(pdf_path) -> list[Question]:
    from pypdf import PdfReader

    raw = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)
    return parse_questions(raw)

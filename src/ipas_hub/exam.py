"""公告試題：把擷取文字切成一題一題（題幹加四個選項）。"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .text import normalize

_NOISE = re.compile(
    r"^\s*(\d+\s*年第.+?【公告試題】|第.科：.+|考試日期：.+|第\s*\d+\s*頁，共\s*\d+\s*頁|答案\s*題目|一、選擇題)\s*$",
    re.M,
)
_QUESTION_START = re.compile(r"^\s*([A-D])\s+(\d{1,2})\.\s", re.M)


@dataclass(frozen=True)
class Question:
    number: int
    answer: str  # 官方答案欄的字母
    text: str    # 題幹加四個選項，正規化後


def parse_questions(raw: str) -> list[Question]:
    body = _NOISE.sub("", raw)
    starts = list(_QUESTION_START.finditer(body))
    questions = []
    for m, nxt in zip(starts, starts[1:] + [None]):
        end = nxt.start() if nxt else len(body)
        questions.append(Question(int(m.group(2)), m.group(1), normalize(body[m.end() : end])))
    return questions


def read_questions(pdf_path) -> list[Question]:
    from pypdf import PdfReader

    raw = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf_path)).pages)
    return parse_questions(raw)

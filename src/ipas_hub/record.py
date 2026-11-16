"""讀探索一紀錄表（Markdown 表格），取得每題的類型與依據頁碼。"""
from __future__ import annotations

import re
from dataclasses import dataclass

_ROW = re.compile(r"^\|\s*(\d+)\s*\|\s*([A-D]?)\s*\|\s*([^|]*)\|\s*([ABC]?)\s*\|", re.M)
_LABEL = re.compile(r"[0-9A]-\d{1,2}")


@dataclass(frozen=True)
class Gold:
    number: int
    answer: str
    type: str         # A／B／C；未填為空字串
    pages: frozenset  # 依據頁碼；C 類為空


def parse_record(markdown: str) -> dict[int, Gold]:
    out = {}
    for num, ans, pages, typ in _ROW.findall(markdown):
        out[int(num)] = Gold(int(num), ans, typ, frozenset(_LABEL.findall(pages)))
    return out

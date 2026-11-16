"""命中判定：前 k 筆結果中任一筆的頁碼落在依據頁碼內，就算命中。"""
from __future__ import annotations


def hit_at_k(ranked_labels: list[str], gold_pages, k: int) -> bool:
    return any(label in gold_pages for label in ranked_labels[:k])


def first_hit_rank(ranked_labels: list[str], gold_pages) -> int | None:
    for i, label in enumerate(ranked_labels, start=1):
        if label in gold_pages:
            return i
    return None

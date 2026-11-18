"""學習指引：逐頁擷取文字、辨識頁尾頁碼、套用勘誤、切塊。"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .text import normalize

_LABEL_LINE = re.compile(r"^\s*([0-9A]-\d{1,2})\s*$", re.M)
_RUNNING_HEAD = re.compile(r"^\s*(第.章\s*人工智慧基礎概論|附件)\s*$", re.M)


@dataclass(frozen=True)
class Page:
    label: str  # 頁尾印的頁碼，例如 3-25
    text: str  # 正規化後的內文
    pdf_page: int | None = None  # 在 PDF 檔內的頁序（從 1 起算），用來開到該頁


@dataclass(frozen=True)
class Chunk:
    label: str
    index: int  # 同一頁內的第幾塊
    text: str
    pdf_page: int | None = None


def parse_page(raw: str, pdf_page: int | None = None, running_head: str | None = None) -> Page | None:
    """從一頁的原始擷取文字取出頁碼與內文；沒有頁碼的頁（封面、序、目錄）回傳 None。

    running_head 是該份教材頁首（每頁重複的章名等）的正規表示式，逐行比對後移除；未提供時用初級科目 1 的規則。
    """
    labels = _LABEL_LINE.findall(raw)
    if not labels:
        return None
    head = re.compile(running_head, re.M) if running_head else _RUNNING_HEAD
    body = head.sub("", _LABEL_LINE.sub("", raw))
    return Page(labels[-1], normalize(body), pdf_page)


def read_pages(pdf_path: Path, running_head: str | None = None, parser: str = "ipas") -> list[Page]:
    from pypdf import PdfReader

    if parser not in {"ipas", "pdf"}:
        raise ValueError(f"不支援的 PDF 解析模式：{parser}")
    pages = []
    for number, p in enumerate(PdfReader(str(pdf_path)).pages, 1):
        raw = p.extract_text() or ""
        if parser == "pdf":
            body = re.sub(running_head, "", raw, flags=re.M) if running_head else raw
            text = normalize(body)
            page = Page(str(number), text, number) if text else None
        else:
            page = parse_page(raw, number, running_head)
        if page:
            pages.append(page)
    return pages


def apply_patches(pages: list[Page], patches: list[dict]) -> tuple[list[Page], list[dict]]:
    """套用勘誤。每筆 patch 是 {"id", "old", "new"}，比對前先正規化。

    回傳新頁面與每筆 patch 的結果（套用在哪些頁；沒找到則為空）。
    """
    texts = {p.label: p.text for p in pages}
    report = []
    for patch in patches:
        old, new = normalize(patch["old"]), normalize(patch["new"])
        hit = [label for label, t in texts.items() if old in t]
        for label in hit:
            texts[label] = texts[label].replace(old, new)
        report.append({"id": patch.get("id", ""), "applied_on": hit})
    return [Page(p.label, texts[p.label], p.pdf_page) for p in pages], report


def chunk_pages(pages: list[Page], size: int = 400, stride: int = 300) -> list[Chunk]:
    """每頁各自用固定視窗切塊，不跨頁，所以每塊只對應一個頁碼。"""
    chunks = []
    for page in pages:
        index, start = 0, 0
        while True:
            chunks.append(Chunk(page.label, index, page.text[start : start + size], page.pdf_page))
            if start + size >= len(page.text):
                break
            start += stride
            index += 1
    return chunks

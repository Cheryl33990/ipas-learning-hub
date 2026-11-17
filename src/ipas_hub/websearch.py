"""外部搜尋介面。每個提供者回傳相同欄位，RAG 只依這些欄位運作，日後可換成其他搜尋服務。

回傳欄位：id、source_type="external"、provider、title、url、revision、text、retrieved_at、query。
外部結果是補充資料，不是教材；引用時須標明來源。
搜尋詞可附英文版本，主要來源沒有相關結果時改查備援來源（英文維基百科）。
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "ipas-learning-hub/0.1 (https://github.com/Cheryl33990/ipas-learning-hub; local study prototype)"  # 維基媒體要求自動化程式附聯絡方式


class WebSearch(Protocol):
    name: str

    def search(self, query: str, k: int, context: str | None = None,
               fallback_query: str | None = None, fallback_context: str | None = None) -> list[dict]: ...


class NoSearch:
    name = "none"

    def search(self, query: str, k: int, **_) -> list[dict]:
        return []


CJK = re.compile(r"[\u3400-\u9fff]+")
MAX_FOCUS_FETCHES = 2  # 每次搜尋最多再抓幾頁全文找段落，避免請求過多
MIN_INTERVAL = 0.5  # 同一來源兩次請求的最短間隔（秒），降低 429


def _token_matches(token: str, haystack: str) -> bool:
    """英文詞須以完整的字出現（不分大小寫，LIME 不配 timeline）；
    中文詞至少一半的字元二元組出現（暫定，容許「監督式學習」對「監督學習」）。"""
    if not CJK.search(token):
        return re.search(rf"(?<![A-Za-z0-9]){re.escape(token)}(?![A-Za-z0-9])", haystack, re.IGNORECASE) is not None
    grams = {run[i:i + 2] for run in CJK.findall(token) for i in range(len(run) - 1)} or {token}
    return sum(g in haystack for g in grams) / len(grams) >= 0.5


def relevant(query: str, title: str, text: str) -> bool:
    """概念詞的每個空白分隔詞都要在標題或內文出現，才算相關；用來排除同名但無關的條目。"""
    haystack = f"{title}\n{text}"
    return all(_token_matches(token, haystack) for token in query.split())


def _focus(query: str, full_text: str, chars: int) -> str:
    """從全文挑含最多搜尋詞的段落；同分取較前面的。"""
    paragraphs = [p.strip() for p in full_text.split("\n") if p.strip()]
    tokens = query.split()
    scored = [(sum(_token_matches(t, p) for t in tokens), -i, p) for i, p in enumerate(paragraphs)]
    best = max(scored, default=(0, 0, ""))
    return best[2][:chars] if best[0] else ""


class WikipediaSearch:
    """維基百科：中文以 zh-TW 取得繁體標題與摘要；網址固定到當次頁面版本。

    排除消歧義頁；導言不含搜尋詞時，抓全文改取含搜尋詞的段落，仍找不到就捨棄該頁。
    有領域詞時，導言或所取段落也須出現領域詞，排除同名但不同領域的頁面（如 Chromium OS Lime）。
    """

    def __init__(self, host: str = "zh.wikipedia.org", provider: str = "wikipedia", id_prefix: str = "wiki",
                 language: str = "zh-TW", chars: int = 600, timeout: float = 15, opener=urlopen, sleep=time.sleep):
        self.host, self.name, self.id_prefix, self.language = host, provider, id_prefix, language
        self.chars, self.timeout, self.opener, self.sleep = chars, timeout, opener, sleep
        self._last = None

    def _get(self, params: dict) -> dict:
        if self._last is not None:
            wait = MIN_INTERVAL - (time.monotonic() - self._last)
            if wait > 0:
                self.sleep(wait)
        self._last = time.monotonic()
        req = Request(f"https://{self.host}/w/api.php?{urlencode(params)}",
                      headers={"User-Agent": USER_AGENT, "Accept-Language": self.language})
        for attempt in (1, 2):
            try:
                with self.opener(req, timeout=self.timeout) as response:
                    return json.load(response)
            except HTTPError as exc:
                if exc.code != 429 or attempt == 2:
                    raise ValueError(f"維基百科搜尋失敗：HTTP {exc.code}") from exc
                # 請求過於頻繁：依伺服器建議等待後只重試一次
                try:
                    wait = float((exc.headers or {}).get("Retry-After") or 2)
                except ValueError:
                    wait = 2
                self.sleep(min(max(wait, 1), 5))
            except URLError as exc:
                raise ValueError(f"維基百科搜尋失敗：{exc.reason}") from exc
        raise AssertionError("unreachable")

    def search(self, query: str, k: int, context: str | None = None) -> list[dict]:
        """query 是概念詞，context 是領域詞；兩者一起搜尋，但相關性與段落只依概念詞判斷。"""
        if not query.strip() or not (1 <= k <= 10):
            raise ValueError("搜尋詞不可空白，k 須介於 1 至 10")
        full_query = f"{query} {context}".strip() if context else query
        data = self._get({"action": "query", "generator": "search", "gsrsearch": full_query, "gsrlimit": k,
                          "prop": "extracts|info|pageprops", "ppprop": "disambiguation",
                          "inprop": "url|varianttitles", "exintro": 1, "explaintext": 1, "exchars": self.chars,
                          "format": "json", "formatversion": 2})
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
        hits, fetches = [], 0
        for page in pages:
            if "pageid" not in page or "disambiguation" in (page.get("pageprops") or {}):
                continue
            title = (page.get("varianttitles") or {}).get("zh-tw") or page["title"]
            text = intro = (page.get("extract") or "").strip()
            if text and not relevant(query, title, text):
                if fetches >= MAX_FOCUS_FETCHES:
                    continue
                fetches += 1
                full = self._get({"action": "query", "prop": "extracts", "pageids": page["pageid"],
                                  "explaintext": 1, "format": "json", "formatversion": 2})
                full_pages = full.get("query", {}).get("pages", [])
                text = _focus(query, (full_pages[0].get("extract") or "") if full_pages else "", self.chars)
                if not text or not relevant(query, title, text):
                    continue
            if not text or (context and not relevant(context, title, f"{intro}\n{text}")):
                continue
            revision = page.get("lastrevid")
            url = (f"https://{self.host}/w/index.php?curid={page['pageid']}&oldid={revision}"
                   if revision else page.get("fullurl"))
            hits.append({"id": f"{self.id_prefix}:{page['pageid']}", "source_type": "external",
                         "provider": self.name, "title": title, "url": url, "revision": revision,
                         "text": text, "retrieved_at": now, "query": full_query})
        return hits


class WikipediaWithFallback:
    """先查中文維基；沒有相關結果（或中文維基出錯）且有英文詞時，改查英文維基。

    英文維基加領域詞查不到時，再只用概念詞查一次（領域詞可能不在正確頁面中）。
    中文維基不重試無領域詞的查詢，因為同名無關條目多半出在那裡。
    """
    name = "wikipedia"

    def __init__(self, primary=None, fallback=None):
        self.primary = primary or WikipediaSearch()
        self.fallback = fallback or WikipediaSearch(host="en.wikipedia.org", provider="wikipedia-en",
                                                    id_prefix="wiki-en", language="en")

    def search(self, query: str, k: int, context: str | None = None,
               fallback_query: str | None = None, fallback_context: str | None = None) -> list[dict]:
        try:
            hits = self.primary.search(query, k, context)
        except ValueError:
            if not (fallback_query and fallback_query.strip()):
                raise
            hits = []
        if not hits and fallback_query and fallback_query.strip():
            hits = self.fallback.search(fallback_query, k, fallback_context)
            if not hits and fallback_context:
                hits = self.fallback.search(fallback_query, k)
        return hits


PROVIDERS = {"wikipedia": WikipediaWithFallback, "none": NoSearch}


def make_search(name: str) -> WebSearch:
    if name not in PROVIDERS:
        raise ValueError(f"不支援的搜尋提供者：{name}")
    return PROVIDERS[name]()

"""外部搜尋介面。每個提供者回傳相同欄位，RAG 只依這些欄位運作，日後可換成其他搜尋服務。

回傳欄位：id、source_type="external"、provider、title、url、revision、text、retrieved_at、query。
外部結果是補充資料，不是教材；引用時須標明來源。
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

USER_AGENT = "ipas-learning-hub/0.1 (local study prototype)"


class WebSearch(Protocol):
    name: str

    def search(self, query: str, k: int) -> list[dict]: ...


class NoSearch:
    name = "none"

    def search(self, query: str, k: int) -> list[dict]:
        return []


class WikipediaSearch:
    """中文維基百科：以 zh-TW 取得繁體標題與摘要，網址固定到當次頁面版本。"""
    name = "wikipedia"

    def __init__(self, host: str = "zh.wikipedia.org", chars: int = 600, timeout: float = 15,
                 opener=urlopen, sleep=time.sleep):
        self.host, self.chars, self.timeout = host, chars, timeout
        self.opener, self.sleep = opener, sleep

    def search(self, query: str, k: int) -> list[dict]:
        if not query.strip() or not (1 <= k <= 10):
            raise ValueError("搜尋詞不可空白，k 須介於 1 至 10")
        params = {"action": "query", "generator": "search", "gsrsearch": query, "gsrlimit": k,
                  "prop": "extracts|info", "inprop": "url|varianttitles", "exintro": 1,
                  "explaintext": 1, "exchars": self.chars, "format": "json", "formatversion": 2}
        req = Request(f"https://{self.host}/w/api.php?{urlencode(params)}",
                      headers={"User-Agent": USER_AGENT, "Accept-Language": "zh-TW"})
        for attempt in (1, 2):
            try:
                with self.opener(req, timeout=self.timeout) as response:
                    data = json.load(response)
                break
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
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        pages = sorted(data.get("query", {}).get("pages", []), key=lambda p: p.get("index", 0))
        hits = []
        for page in pages:
            text = (page.get("extract") or "").strip()
            if not text or "pageid" not in page:
                continue
            title = (page.get("varianttitles") or {}).get("zh-tw") or page["title"]
            revision = page.get("lastrevid")
            url = (f"https://{self.host}/w/index.php?curid={page['pageid']}&oldid={revision}"
                   if revision else page.get("fullurl"))
            hits.append({"id": f"wiki:{page['pageid']}", "source_type": "external",
                         "provider": self.name, "title": title, "url": url, "revision": revision,
                         "text": text, "retrieved_at": now, "query": query})
        return hits


PROVIDERS = {"wikipedia": WikipediaSearch, "none": NoSearch}


def make_search(name: str) -> WebSearch:
    if name not in PROVIDERS:
        raise ValueError(f"不支援的搜尋提供者：{name}")
    return PROVIDERS[name]()

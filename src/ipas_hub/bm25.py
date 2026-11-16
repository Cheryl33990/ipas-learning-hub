"""BM25（Okapi）排序，輸入是已斷好詞的文件。"""
from __future__ import annotations

import math
from collections import Counter


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.length = [len(d) for d in docs]
        self.avg_len = sum(self.length) / len(docs) if docs else 0.0
        df: Counter[str] = Counter()
        for tf in self.tf:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tf, self.length):
            norm = self.k1 * (1 - self.b + self.b * length / self.avg_len) if self.avg_len else 0.0
            s = 0.0
            for term in query:
                f = tf.get(term, 0)
                if f:
                    s += self.idf[term] * f * (self.k1 + 1) / (f + norm)
            out.append(s)
        return out

    def top(self, query: list[str], k: int) -> list[int]:
        s = self.scores(query)
        return sorted(range(len(s)), key=lambda i: (-s[i], i))[:k]

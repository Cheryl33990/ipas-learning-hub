"""文字正規化與斷詞。中文不斷詞，用字元二元組；英數用整個單字。"""
from __future__ import annotations

import re

_CJK = r"[　-〿㐀-鿿＀-￯]"
_SPACE_NEXT_TO_CJK = re.compile(f"(?<={_CJK}) | (?={_CJK})")
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*|[㐀-鿿]+")


def normalize(text: str) -> str:
    """把所有空白收成一個空格，並拿掉緊鄰中文字的空格（PDF 換行造成的）。"""
    text = re.sub(r"\s+", " ", text).strip()
    return _SPACE_NEXT_TO_CJK.sub("", text)


def tokenize(text: str) -> list[str]:
    """英數單字小寫後整個當一個詞；連續中文字切成重疊的二元組，單一個字自成一詞。"""
    tokens: list[str] = []
    for run in _TOKEN.findall(text.lower()):
        if run[0].isascii() or len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens

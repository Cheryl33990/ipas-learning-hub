"""OpenAI 相容的聊天介面：本機 vLLM 與日後的 OpenAI API 共用同一段程式，只換設定。

預設只允許本機端點；遠端端點須明確開啟且使用 https，避免誤呼叫付費服務。
API 金鑰只從環境變數讀取，不寫入執行紀錄。
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

LOCAL_HOSTS = {"localhost", "127.0.0.1", "vllm"}


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    model: str
    api_key: str | None = None
    allow_remote: bool = False
    timeout: float = 300
    max_tokens: int = 1500

    @classmethod
    def from_env(cls, base_url: str | None = None, model: str | None = None, allow_remote: bool = False) -> "LLMConfig":
        return cls(
            base_url=base_url or os.getenv("LLM_BASE_URL", "http://127.0.0.1:8000/v1"),
            model=model or os.getenv("LLM_MODEL", ""),
            api_key=os.getenv("LLM_API_KEY") or None,
            allow_remote=allow_remote or os.getenv("LLM_ALLOW_REMOTE") == "1",
        )

    def describe(self) -> dict:
        """可寫入執行紀錄的設定，不含金鑰。"""
        return {"base_url": self.base_url, "model": self.model, "remote": not self.is_local()}

    def is_local(self) -> bool:
        return urlparse(self.base_url).hostname in LOCAL_HOSTS


def check_config(cfg: LLMConfig) -> None:
    url = urlparse(cfg.base_url)
    if url.username or url.password or url.query or url.fragment:
        raise ValueError("LLM 端點網址不可含帳密、查詢字串或片段")
    if not cfg.model.strip():
        raise ValueError("須指定模型名稱（--model 或 LLM_MODEL）")
    if cfg.is_local():
        if url.scheme not in {"http", "https"}:
            raise ValueError("LLM 端點須為 http 或 https")
        return
    if not cfg.allow_remote:
        raise ValueError(
            "遠端 LLM 端點預設停用：本機以外的服務可能收費，須以 --allow-remote 或 LLM_ALLOW_REMOTE=1 明確開啟"
        )
    if url.scheme != "https":
        raise ValueError("遠端 LLM 端點必須使用 https")


def parse_json_content(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text[text.find("{") :] if "{" in text else text
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("模型回覆不是有效 JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("模型回覆須為 JSON 物件")
    return value


def chat_json(cfg: LLMConfig, system: str, user: str, opener=urlopen) -> dict:
    """送出一次聊天請求並解析 JSON 回覆；失敗一律拋錯，不回傳替代答案。"""
    check_config(cfg)
    body = {
        "model": cfg.model,
        "temperature": 0,
        "max_tokens": cfg.max_tokens,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    req = Request(
        cfg.base_url.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    started = time.perf_counter()
    try:
        with opener(req, timeout=cfg.timeout) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise ValueError(f"LLM 服務回應錯誤 HTTP {exc.code}") from exc
    except URLError as exc:
        raise ValueError(f"無法連線 LLM 服務：{exc.reason}") from exc
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0].get("message", {}).get("content"), str):
        raise ValueError("LLM 服務沒有回傳內容")
    if choices[0].get("finish_reason") == "length":
        raise ValueError("模型回覆超過長度上限而被截斷")
    return {
        "output": parse_json_content(choices[0]["message"]["content"]),
        "model": data.get("model", cfg.model),
        "usage": data.get("usage"),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
    }

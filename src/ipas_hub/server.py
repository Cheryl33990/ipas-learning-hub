"""把問答流程包成 OpenAI 相容的 /v1/chat/completions，供現成聊天介面當作模型使用。

只綁本機迴路位址；不含任何領域邏輯，回答文字由呼叫端提供的 answer_fn 產生。
另可唯讀提供呼叫端明列的檔案（/files/<名稱>），讓回答中的引用連結能在瀏覽器開啟原始文件。
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"  # 不提供改綁其他位址的選項
MAX_BODY = 1_000_000
FAILURES = (ValueError, OSError, KeyError, TypeError, ImportError)


def last_user_message(payload: dict) -> str:
    """取最後一則使用者訊息當題目；平台附帶的系統提示與歷史對話不使用。"""
    messages = payload.get("messages") if isinstance(payload, dict) else None
    for message in reversed(messages if isinstance(messages, list) else []):
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content")
            if isinstance(content, list):  # OpenAI 的分段格式，只取文字段
                content = "\n".join(
                    p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"
                )
            if isinstance(content, str) and content.strip():
                return content.strip()
            break
    raise ValueError("請求中沒有使用者訊息")


def failure_text(exc: Exception) -> str:
    return (
        "⚠ 無法產生有依據的解答\n\n"
        f"原因：{exc}\n\n"
        "以上不是解答，請勿當作有依據的內容。若原因是無法連線 LLM 服務，請先啟動本機模型再重試。"
    )


ABOUT_PAGE = """<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>API 端點</title>
<body style="font-family:sans-serif;max-width:40em;margin:3em auto;line-height:1.6">
<h1>這是 OpenAI 相容的 API 端點，不是網頁</h1>
<p>請在聊天介面（例如 AnythingLLM）中把這個位址當成模型使用，從聊天介面提問。</p>
<p>可用路徑：<code>GET /v1/models</code>、<code>POST /v1/chat/completions</code>。</p>
</body></html>"""


def _base(kind: str, model: str) -> dict:
    return {"id": f"chatcmpl-{uuid.uuid4().hex}", "object": kind, "created": int(time.time()), "model": model}


def answer_or_failure(question: str, answer_fn) -> str:
    try:
        return answer_fn(question)
    except FAILURES as exc:  # 以清楚的警示文字回覆，讓聊天畫面顯示原因
        return failure_text(exc)


def chat_response(payload: dict, answer_fn, model: str) -> tuple[int, dict]:
    try:
        question = last_user_message(payload)
    except ValueError as exc:
        return 400, {"error": {"message": str(exc), "type": "invalid_request_error"}}
    text = answer_or_failure(question, answer_fn)
    return 200, {
        **_base("chat.completion", model),
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


def sse_chunks(text: str, model: str):
    """回答是一次產生的；串流只為相容要求串流的介面，整段文字放在一個 chunk。"""
    base = _base("chat.completion.chunk", model)
    for delta, finish in (({"role": "assistant", "content": text}, None), ({}, "stop")):
        chunk = {**base, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


def make_server(
    answer_fn, port: int, model: str, files: dict | None = None, models: dict | None = None
) -> ThreadingHTTPServer:
    """files 是「名稱 → 檔案路徑」的允許清單；只比對完整名稱，不把請求路徑接到檔案系統上。"""
    files = dict(files or {})
    routes = dict(models) if models is not None else None

    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, payload: dict) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _file(self, path) -> None:
            try:
                size = path.stat().st_size
                handle = open(path, "rb")
            except OSError:
                return self._json(404, {"error": {"message": "檔案無法讀取", "type": "invalid_request_error"}})
            with handle:
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/pdf" if path.suffix.lower() == ".pdf" else "application/octet-stream"
                )
                self.send_header("Content-Disposition", "inline")
                self.send_header("Content-Length", str(size))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                shutil.copyfileobj(handle, self.wfile)

        def do_GET(self):
            path = self.path.split("?", 1)[0].split("#", 1)[0]
            if path.startswith("/files/") and path[len("/files/") :] in files:
                self._file(files[path[len("/files/") :]])
            elif path.rstrip("/") in ("", "/v1"):  # 用瀏覽器直接開時給說明，避免誤以為服務壞了
                data = ABOUT_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif path.rstrip("/") == "/v1/models":
                self._json(
                    200,
                    {
                        "object": "list",
                        "data": [
                            {"id": name, "object": "model", "owned_by": "local"}
                            for name in (routes if routes is not None else [model])
                        ],
                    },
                )
            else:
                self._json(404, {"error": {"message": "找不到此路徑", "type": "invalid_request_error"}})

        def do_POST(self):
            if self.path.rstrip("/") != "/v1/chat/completions":
                return self._json(404, {"error": {"message": "找不到此路徑", "type": "invalid_request_error"}})
            try:
                length = int(self.headers.get("Content-Length", 0))
                if not 0 < length <= MAX_BODY:
                    raise ValueError("請求內容為空或過大")
                payload = json.loads(self.rfile.read(length))
                question = last_user_message(payload)
            except (ValueError, UnicodeDecodeError) as exc:
                return self._json(400, {"error": {"message": f"請求格式錯誤：{exc}", "type": "invalid_request_error"}})
            selected_model, selected_answer = model, answer_fn
            if routes is not None:
                selected_model = payload.get("model")
                if not isinstance(selected_model, str) or selected_model not in routes:
                    return self._json(
                        400, {"error": {"message": "請指定已設定的模型／知識庫名稱", "type": "invalid_request_error"}}
                    )
                selected_answer = routes[selected_model]
            if not payload.get("stream"):
                return self._json(*chat_response(payload, selected_answer, selected_model))
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            for line in sse_chunks(answer_or_failure(question, selected_answer), selected_model):
                self.wfile.write(line.encode("utf-8"))
            self.wfile.flush()
            self.close_connection = True

        def log_message(self, fmt, *args):  # 不把請求內容印到終端機
            pass

    return ThreadingHTTPServer((HOST, port), Handler)

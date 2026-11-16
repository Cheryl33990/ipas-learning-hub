"""本機生成介面與引用檢查；不將形式檢查當作內容正確性保證。"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .knowledge import digest

PROMPT_PATH = Path(__file__).with_name("prompts") / "answer.txt"


def ollama_generate(prompt: str, model: str, base_url: str, timeout: float = 180) -> dict:
    url = urlparse(base_url)
    if (url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "ollama"}
            or url.username or url.password or url.query or url.fragment
            or url.path not in {"", "/"}):
        raise ValueError("原型只允許本機或 Compose ollama HTTP 端點")
    if not model.strip():
        raise ValueError("須明確指定本機模型，不自動下載")
    payload = {"model": model, "prompt": prompt, "stream": False, "format": "json",
               "options": {"temperature": 0, "num_predict": 2048}}
    req = Request(base_url.rstrip("/") + "/api/generate", data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout) as response:
        data = json.load(response)
    if not data.get("done") or not data.get("response"):
        raise ValueError("模型沒有完整回覆")
    return {"output": json.loads(data["response"]), "model": data.get("model", model),
            "model_duration_ns": data.get("total_duration")}


def answer(question: str, hits: list[dict], generate) -> dict:
    if not hits:
        return {"status": "insufficient", "answer": "目前未檢索到教材依據，無法據此解題。",
                "citations": [], "validation": "no_evidence", "prompt_sha256": None}
    template = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template + "\n" + json.dumps({"question": question, "evidence": hits}, ensure_ascii=False)
    generated = generate(prompt)
    output = generated["output"]
    if not isinstance(output, dict) or output.get("status") not in {"supported", "insufficient"}:
        raise ValueError("模型回覆不符合輸出契約")
    citations = output.get("citations")
    valid_ids = {h["id"] for h in hits}
    if (not isinstance(output.get("answer"), str) or not output["answer"].strip()
            or not isinstance(citations, list)
            or any(not isinstance(c, str) or c not in valid_ids for c in citations)
            or (output["status"] == "supported" and not citations)):
        raise ValueError("模型引用不存在或回答缺少引用，拒絕顯示為有依據回答")
    return {**output, "model": generated.get("model"),
            "model_duration_ns": generated.get("model_duration_ns"),
            "prompt_sha256": digest(template.encode()),
            "validation": "citation_ids_only_not_semantic_verification"}

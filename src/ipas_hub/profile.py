"""領域設定（profile）：把角色描述與領域專屬規則從通用的證據契約中分離。

prompts/answer.txt 是所有領域共用的規則（只用 evidence、逐句引用、不得捏造 id）；
profile 只填入「你是誰、文件叫什麼、還有哪些領域規則」。換資料時改 profile，不改程式。
"""
from __future__ import annotations

import json
from pathlib import Path

ANSWER_TEMPLATE = Path(__file__).with_name("prompts") / "answer.txt"
FIELDS = ("intro", "document_description", "document_term", "extra_rules")
FIRST_EXTRA_RULE = 7  # 範本內建規則為 1–6

DEFAULT_PROFILE = {
    "intro": "你是文件問答助理，依 evidence 回答 question。",
    "document_description": "使用者提供的文件",
    "document_term": "文件",
    "extra_rules": [],
}


def validate(profile: object) -> dict:
    if not isinstance(profile, dict) or set(profile) != set(FIELDS):
        raise ValueError("profile 須剛好包含 " + "、".join(FIELDS))
    for key in FIELDS[:-1]:
        if not isinstance(profile[key], str) or not profile[key].strip():
            raise ValueError(f"profile 的 {key} 須為非空字串")
    rules = profile["extra_rules"]
    if not isinstance(rules, list) or not all(isinstance(r, str) and r.strip() for r in rules):
        raise ValueError("profile 的 extra_rules 須為非空字串清單")
    return profile


def load_profile(root: Path, path: Path | None) -> dict:
    """path 相對於 root，且不能指到 root 以外；未指定時使用通用設定。"""
    if path is None:
        return dict(DEFAULT_PROFILE)
    base = root.resolve()
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("profile 路徑必須位於專案目錄內")
    return validate(json.loads(target.read_text(encoding="utf-8")))


def answer_prompt(profile: dict) -> str:
    validate(profile)
    extra = "".join(f"{n}. {rule}\n" for n, rule in enumerate(profile["extra_rules"], FIRST_EXTRA_RULE))
    text = ANSWER_TEMPLATE.read_text(encoding="utf-8")
    for key in FIELDS[:-1]:
        text = text.replace("{{" + key + "}}", profile[key])
    return text.replace("{{extra_rules}}", extra)

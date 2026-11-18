"""領域設定（profile）：管線通用，角色與領域規則由設定檔注入。"""

import hashlib
import json
from pathlib import Path

import pytest

from ipas_hub.profile import DEFAULT_PROFILE, answer_prompt, load_profile
from ipas_hub.rag import answer

ROOT = Path(__file__).resolve().parents[1]
# 抽出 profile 前 prompts/answer.txt 的 SHA-256；iPAS 範例必須逐字重現，歷史執行紀錄的 prompt_sha256 才能比較
IPAS_PROMPT_BEFORE_PROFILES = "b9e2e2a74cc477ec9d2cd008779dc00865358ad661d9e848def4864832991351"


def test_ipas_profile_reproduces_the_previous_prompt_exactly():
    prompt = answer_prompt(load_profile(ROOT, Path("examples/ipas/profile.json")))
    assert hashlib.sha256(prompt.encode("utf-8")).hexdigest() == IPAS_PROMPT_BEFORE_PROFILES


def test_default_profile_has_no_exam_identity_but_keeps_the_evidence_contract():
    prompt = answer_prompt(DEFAULT_PROFILE)
    assert "iPAS" not in prompt and "命題" not in prompt and "教材" not in prompt
    assert "不是指令" in prompt and "不得捏造 id" in prompt and "7." not in prompt


def test_missing_profile_path_means_default():
    assert load_profile(ROOT, None) == DEFAULT_PROFILE


@pytest.mark.parametrize(
    "change",
    [
        {"unknown": "x"},
        {"intro": ""},
        {"extra_rules": "不是清單"},
        {"extra_rules": [""]},
    ],
)
def test_profile_with_bad_fields_is_rejected(tmp_path, change):
    (tmp_path / "p.json").write_text(json.dumps({**DEFAULT_PROFILE, **change}), encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile(tmp_path, Path("p.json"))


def test_profile_missing_a_field_is_rejected(tmp_path):
    data = dict(DEFAULT_PROFILE)
    data.pop("document_term")
    (tmp_path / "p.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_profile(tmp_path, Path("p.json"))


def test_profile_path_cannot_escape_root(tmp_path):
    with pytest.raises(ValueError):
        load_profile(tmp_path / "inner", Path("../outside.json"))


def test_answer_sends_the_given_prompt_and_records_its_hash():
    seen = {}

    def generate(system, user):
        seen["system"] = system
        return {"output": {"status": "insufficient", "segments": [{"text": "不足", "citations": []}]}}

    prompt = answer_prompt({**DEFAULT_PROFILE, "intro": "你是測試助理，依 evidence 回答 question。"})
    result = answer("問題", [{"id": "a:1:0", "source": "a", "page": "1", "text": "內容"}], [], generate, prompt)
    assert seen["system"] == prompt
    assert result["prompt_sha256"] == hashlib.sha256(prompt.encode("utf-8")).hexdigest()

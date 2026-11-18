"""fetch：依設定檔的官方網址下載文件，SHA-256 不符就不留下檔案。"""

import hashlib
import io
import json

import pytest

from ipas_hub.fetch import fetch_sources

CONTENT = b"%PDF-1.4 synthetic"
SHA = hashlib.sha256(CONTENT).hexdigest()


def config(tmp_path, **source):
    spec = {"id": "s1", "pdf": "data/raw/guide 1.pdf", "sha256": SHA, **source}
    path = tmp_path / "kb.json"
    path.write_text(json.dumps({"download_base": "https://example.org/files/", "sources": [spec]}), encoding="utf-8")
    return path


def opener(body=CONTENT, seen=None):
    def open_url(request, timeout):
        if seen is not None:
            seen.append(request.full_url)
        return io.BytesIO(body)

    return open_url


def test_downloads_from_base_with_encoded_file_name_and_verifies_hash(tmp_path):
    seen = []
    result = fetch_sources(tmp_path, config(tmp_path), opener(seen=seen))
    assert seen == ["https://example.org/files/guide%201.pdf"]
    assert result == [{"id": "s1", "status": "downloaded"}]
    assert (tmp_path / "data/raw/guide 1.pdf").read_bytes() == CONTENT


def test_source_download_url_takes_priority(tmp_path):
    seen = []
    fetch_sources(tmp_path, config(tmp_path, download_url="https://other.org/x.pdf"), opener(seen=seen))
    assert seen == ["https://other.org/x.pdf"]


def test_file_already_present_with_matching_hash_is_not_downloaded(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/guide 1.pdf").write_bytes(CONTENT)

    def unexpected(request, timeout):
        raise AssertionError("不應下載")

    assert fetch_sources(tmp_path, config(tmp_path), unexpected) == [{"id": "s1", "status": "present"}]


def test_hash_mismatch_leaves_no_file(tmp_path):
    with pytest.raises(ValueError, match="SHA-256"):
        fetch_sources(tmp_path, config(tmp_path), opener(b"changed by publisher"))
    assert list((tmp_path / "data/raw").iterdir()) == []


def test_existing_file_with_other_content_is_never_overwritten(tmp_path):
    (tmp_path / "data/raw").mkdir(parents=True)
    (tmp_path / "data/raw/guide 1.pdf").write_bytes(b"user's own copy")
    with pytest.raises(ValueError, match="未覆寫"):
        fetch_sources(tmp_path, config(tmp_path), opener())
    assert (tmp_path / "data/raw/guide 1.pdf").read_bytes() == b"user's own copy"


def test_plain_http_and_missing_url_are_rejected(tmp_path):
    with pytest.raises(ValueError, match="https"):
        fetch_sources(tmp_path, config(tmp_path, download_url="http://example.org/x.pdf"), opener())
    path = tmp_path / "plain.json"
    path.write_text(json.dumps({"sources": [{"id": "s1", "pdf": "data/raw/a.pdf", "sha256": SHA}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="自行放入"):
        fetch_sources(tmp_path, path, opener())


def test_target_outside_data_is_rejected(tmp_path):
    path = tmp_path / "kb.json"
    path.write_text(
        json.dumps(
            {"download_base": "https://example.org/", "sources": [{"id": "s1", "pdf": "../evil.pdf", "sha256": SHA}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="data/"):
        fetch_sources(tmp_path, path, opener())

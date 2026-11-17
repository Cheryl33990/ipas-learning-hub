"""一般 PDF、文件來源標示與知識庫核對；內容皆為合成資料。"""
import json
from types import SimpleNamespace

import pytest

from ipas_hub.cli import main
from ipas_hub.guide import Page, read_pages
from ipas_hub.knowledge import build_index, knowledge_base_id
from ipas_hub.rag import answer, render_text, textbook_label


def test_generic_pdf_keeps_numbered_pages_without_ipas_footer(monkeypatch, tmp_path):
    pages = [SimpleNamespace(extract_text=lambda: "合成：一般公司文件"),
             SimpleNamespace(extract_text=lambda: "  "),
             SimpleNamespace(extract_text=lambda: "第 1 條\n合成規範")]
    monkeypatch.setattr("pypdf.PdfReader", lambda _: SimpleNamespace(pages=pages))
    assert read_pages(tmp_path / "fake.pdf", parser="pdf") == [
        Page("1", "合成：一般公司文件", 1), Page("3", "第1條合成規範", 3)]
    assert read_pages(tmp_path / "fake.pdf") == []
    with pytest.raises(ValueError, match="解析模式"):
        read_pages(tmp_path / "fake.pdf", parser="missing")


def test_generic_pdf_index_metadata_and_wrong_file_knowledge_base(tmp_path, monkeypatch, capsys):
    from ipas_hub.knowledge import digest
    (tmp_path / "data").mkdir()
    (tmp_path / "data/doc.pdf").write_bytes(b"synthetic")
    (tmp_path / "uv.lock").write_text("test")
    config = {"schema_version": 1, "knowledge_base": "company", "chunk_size": 40, "chunk_stride": 30,
              "sources": [{"id": "doc", "name": "合成規範", "version": "v1", "parser": "pdf",
                           "url": "https://example.com", "pdf": "data/doc.pdf", "sha256": digest(b"synthetic")}]}
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(config), encoding="utf-8")
    seen = []
    monkeypatch.setattr("ipas_hub.knowledge.read_pages",
                        lambda _, **kw: seen.append(kw) or [Page("1", "合成規範", 1)])
    path = build_index(tmp_path, cfg, tmp_path / "data/index")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["knowledge_base"] == "company" and seen == [{"running_head": None, "parser": "pdf"}]
    assert data["sources"][0]["url"] == "https://example.com"
    assert main(["--root", str(tmp_path), "search", "--index", str(path), "--kb", "wrong",
                 "--method", "bm25", "--query", "合成"]) == 1
    assert "不屬於" in capsys.readouterr().err
    monkeypatch.setattr("ipas_hub.knowledge.read_pages", lambda *a, **kw: [])
    with pytest.raises(ValueError, match="頁面"):
        build_index(tmp_path, cfg, tmp_path / "data/index")


def test_knowledge_base_name_and_document_source_label():
    assert knowledge_base_id({}) == "ipas"
    for name in ("", "../wrong", "Has Spaces", None):
        with pytest.raises(ValueError, match="知識庫名稱"):
            knowledge_base_id({"knowledge_base": name})
    assert textbook_label({"source": "doc", "page": "1", "name": "合成", "version": "v1",
                           "document_type": "document"}) == "文件 合成，版本：v1"


def test_document_answer_uses_document_markers_version_and_pdf_page():
    hits = [{"id": "doc:2:0", "source": "doc", "name": "合成規範", "version": "v1",
             "page": "2", "pdf_page": 2, "text": "合成規範：資料保存五年", "document_type": "document"}]
    generate = lambda *a: {"output": {"status": "supported", "segments": [
        {"text": "資料保存五年", "citations": ["doc:2:0"]}]}}
    result = answer("資料保存多久", hits, [], generate)
    text = render_text(result)
    assert "只用文件" in text and "[文件1]" in text and "版本：v1（PDF 第 2 頁）" in text

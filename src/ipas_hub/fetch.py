"""依來源設定下載文件：只用 https，SHA-256 與設定不符就丟棄，既有的不同檔案不覆寫。

文件不進版控，也不由本 repo 再散布；設定只記錄官方網址與預期雜湊，使用者自行從發布者取得。
網址取 source.download_url；沒有時用設定頂層的 download_base 接上 pdf 檔名。
download_base 放在頂層而非各來源，是因為來源欄位會寫入索引內容，放進去會改變既有 index_id。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from .knowledge import data_path

CHUNK = 1 << 16


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def source_url(spec: dict, base: str | None) -> str:
    url = spec.get("download_url") or (base + quote(Path(spec["pdf"]).name) if base else None)
    if not url:
        raise ValueError(f"{spec['id']} 沒有 download_url，設定也沒有 download_base；請自行放入 {spec['pdf']}")
    if not url.startswith("https://"):
        raise ValueError(f"{spec['id']} 的下載網址必須使用 https")
    return url


def fetch_sources(root: Path, config_path: Path, opener=urlopen, timeout: float = 60) -> list[dict]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    results = []
    for spec in config["sources"]:
        target = data_path(root, spec["pdf"])
        if target.is_file():
            if _sha256(target) != spec["sha256"]:
                raise ValueError(f"{spec['id']} 既有檔案與設定的 SHA-256 不符，未覆寫：{spec['pdf']}")
            results.append({"id": spec["id"], "status": "present"})
            continue
        url = source_url(spec, config.get("download_base"))
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".part")
        try:
            with (
                opener(Request(url, headers={"User-Agent": "ipas-hub-fetch"}), timeout=timeout) as response,
                partial.open("wb") as out,
            ):
                for block in iter(lambda: response.read(CHUNK), b""):
                    out.write(block)
            if _sha256(partial) != spec["sha256"]:
                raise ValueError(
                    f"{spec['id']} 下載內容與設定的 SHA-256 不符；發布者可能已更新檔案，"
                    "請確認新版本後再更新設定，不要只改雜湊"
                )
            partial.replace(target)
        finally:
            partial.unlink(missing_ok=True)
        results.append({"id": spec["id"], "status": "downloaded"})
    return results

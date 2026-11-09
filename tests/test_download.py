from __future__ import annotations

import hashlib
import json
from pathlib import Path

import httpx
import pytest

from medsql.data import download
from medsql.data.download import MANIFEST, download_all
from medsql.data.schema import SOURCE_FILES


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download.time, "sleep", lambda _s: None)


def _name(request: httpx.Request) -> str:
    return request.url.params.get("fichier") or request.url.path.rsplit("/", 1)[-1]


def test_download_writes_files_and_manifest(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=f"données de {_name(request)}\n".encode())

    files = download_all(tmp_path, transport=httpx.MockTransport(handler))
    assert [f.name for f in files] == list(SOURCE_FILES)
    first = tmp_path / SOURCE_FILES[0]
    assert first.read_bytes() == f"données de {SOURCE_FILES[0]}\n".encode()
    manifest = json.loads((tmp_path / MANIFEST).read_text("utf-8"))
    entry = manifest["files"][0]
    assert entry["sha256"] == hashlib.sha256(first.read_bytes()).hexdigest()
    assert entry["url"].endswith(f"/download/file/{SOURCE_FILES[0]}")


def test_html_error_page_falls_back_to_the_legacy_url(tmp_path: Path) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.startswith("/download/"):
            return httpx.Response(200, content=b"<!DOCTYPE html><p>Maintenance</p>")
        return httpx.Response(200, content=b"ok\n")

    files = download_all(tmp_path, retries=1, transport=httpx.MockTransport(handler))
    assert all("telechargement.php?fichier=" in f.url for f in files)


def test_download_gives_up_after_all_attempts(tmp_path: Path) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(503)

    with pytest.raises(RuntimeError, match=SOURCE_FILES[0]):
        download_all(tmp_path, retries=2, transport=httpx.MockTransport(handler))
    assert len(calls) == 4  # deux adresses, deux tentatives chacune
    assert not (tmp_path / MANIFEST).exists()

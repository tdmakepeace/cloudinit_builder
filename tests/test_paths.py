"""Tests for project paths and output writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudinit_builder import paths


def test_write_output_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    out = tmp_path / "out"
    monkeypatch.setenv("CLOUDINIT_OUTPUT_DIR", str(out))
    d = paths.write_output_files("ud\n", "md\n")
    assert d == out
    assert (out / "user-data").read_text(encoding="utf-8") == "ud\n"
    assert (out / "meta-data").read_text(encoding="utf-8") == "md\n"


def test_read_output_files_if_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLOUDINIT_OUTPUT_DIR", str(tmp_path))
    assert paths.read_output_files_if_present() == (None, None)
    (tmp_path / "user-data").write_text("u", encoding="utf-8")
    assert paths.read_output_files_if_present() == (None, None)
    (tmp_path / "meta-data").write_text("m", encoding="utf-8")
    assert paths.read_output_files_if_present() == ("u", "m")

"""Tests for NoCloud ISO builder."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cloudinit_builder import iso


def test_genisoimageAvailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(iso.shutil, "which", lambda _name: "/usr/bin/genisoimage")
    assert iso.genisoimageAvailable() is True
    monkeypatch.setattr(iso.shutil, "which", lambda _name: None)
    assert iso.genisoimageAvailable() is False


def test_buildCidataIso_missing_seed(tmp_path: Path):
    with pytest.raises(ValueError, match="Missing seed file"):
        iso.buildCidataIso(tmp_path, tmp_path / "out.iso")


def test_buildCidataIso_invokes_genisoimage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "user-data").write_text("#cloud-config\n", encoding="utf-8")
    (tmp_path / "meta-data").write_text("instance-id: i\n", encoding="utf-8")
    iso_out = tmp_path / "cidata.iso"

    mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    monkeypatch.setattr(iso.subprocess, "run", mock_run)

    iso.buildCidataIso(tmp_path, iso_out)

    mock_run.assert_called_once()
    argv = mock_run.call_args[0][0]
    assert argv[0] == "genisoimage"
    assert "-output" in argv
    assert str(iso_out) in argv
    assert "-volid" in argv
    assert "cidata" in argv
    assert "-joliet" in argv
    assert "-r" in argv
    assert str(tmp_path.resolve()) in argv


def test_buildCidataIso_surfaces_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "user-data").write_text("u\n", encoding="utf-8")
    (tmp_path / "meta-data").write_text("m\n", encoding="utf-8")
    mock_run = MagicMock(
        return_value=MagicMock(returncode=1, stdout="", stderr="disk full"),
    )
    monkeypatch.setattr(iso.subprocess, "run", mock_run)

    with pytest.raises(RuntimeError, match="genisoimage failed"):
        iso.buildCidataIso(tmp_path, tmp_path / "out.iso")

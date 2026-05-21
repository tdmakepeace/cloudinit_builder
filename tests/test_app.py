"""Tests for Flask app routes."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def app_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLOUDINIT_OUTPUT_DIR", str(tmp_path))
    from app import app as flask_app

    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


def test_serve_output_artifact_missing(app_client):
    response = app_client.get("/artifact/user-data")
    assert response.status_code == 404


def test_serve_output_artifact_invalid_name(app_client):
    assert app_client.get("/artifact/foo").status_code == 404


def test_serve_output_artifact_ok(app_client, tmp_path: Path):
    (tmp_path / "user-data").write_text("#cloud-config\n", encoding="utf-8")
    response = app_client.get("/artifact/user-data")
    assert response.status_code == 200
    assert b"#cloud-config" in response.data
    assert "no-store" in response.headers.get("Cache-Control", "")


def test_serve_cidata_iso_missing_seed(app_client):
    response = app_client.get("/artifact/cidata.iso")
    assert response.status_code == 404


def test_serve_cidata_iso_no_genisoimage(app_client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "user-data").write_text("u\n", encoding="utf-8")
    (tmp_path / "meta-data").write_text("m\n", encoding="utf-8")
    monkeypatch.setattr("app.iso.genisoimageAvailable", lambda: False)
    response = app_client.get("/artifact/cidata.iso")
    assert response.status_code == 503
    assert b"genisoimage" in response.data


def test_serve_cidata_iso_ok(app_client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "user-data").write_text("#cloud-config\n", encoding="utf-8")
    (tmp_path / "meta-data").write_text("instance-id: i\n", encoding="utf-8")

    def fake_build(seed_dir: Path, iso_path: Path) -> None:
        iso_path.write_bytes(b"FAKEISO")

    monkeypatch.setattr("app.iso.genisoimageAvailable", lambda: True)
    monkeypatch.setattr("app.iso.buildCidataIso", fake_build)

    response = app_client.get("/artifact/cidata.iso")
    assert response.status_code == 200
    assert response.data == b"FAKEISO"
    assert "application/octet-stream" in response.headers.get("Content-Type", "")
    assert "attachment" in response.headers.get("Content-Disposition", "")
    assert "no-store" in response.headers.get("Cache-Control", "")

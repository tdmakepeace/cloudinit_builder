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

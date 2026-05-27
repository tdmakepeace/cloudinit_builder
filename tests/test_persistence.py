"""Tests for preferences JSON persistence."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudinit_builder import persistence


@pytest.fixture
def prefs_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "prefs.json"
    monkeypatch.setenv("CLOUDINIT_PREFS_FILE", str(path))
    return path


def test_save_and_load_roundtrip(prefs_file: Path):
    form = {
        "hostname": "vm1",
        "username": "u",
        "password_plain": "secret",
        "password_hash": "$6$abc",
        "hosts_entries_text": "10.0.0.10 host-a",
        "enable_hosts_file_update": True,
        "late_users": [
            {
                "name": "kevwal",
                "keys": [],
                "shell": "/bin/bash",
                "sudo_nopasswd": False,
                "ssh_config_text": "\n".join(
                    [
                        "host farm",
                        "       hostname 192.168.1.222",
                        "       user kevwal",
                        "       IdentityFile ~/.ssh/287-2023",
                    ]
                ),
                "private_keys": [{"filename": "id_demo", "content": "PRIVATE"}],
            }
        ],
        "enable_network": True,
    }
    persistence.save_preferences(form)
    loaded = persistence.load_preferences()
    assert loaded is not None
    assert loaded["hostname"] == "vm1"
    assert "password_plain" not in loaded
    assert loaded["password_hash"] == "$6$abc"
    assert len(loaded["late_users"]) == 1
    assert loaded["hosts_entries_text"] == "10.0.0.10 host-a"
    assert loaded["enable_hosts_file_update"] is True
    assert len(loaded["late_users"]) == 1
    assert loaded["late_users"][0]["name"] == "kevwal"
    assert "host farm" in loaded["late_users"][0]["ssh_config_text"]
    assert "private_keys" not in loaded["late_users"][0]


def test_merge_saved_over_base():
    base = {"hostname": "seed", "iface": "ens160", "late_users": []}
    saved = {"hostname": "saved", "iface": "ens192"}
    out = persistence.merge_saved_over_base(base, saved)
    assert out["hostname"] == "saved"
    assert out["iface"] == "ens192"


def test_clear_preferences(prefs_file: Path):
    persistence.save_preferences({"hostname": "x"})
    assert persistence.clear_preferences() is True
    assert persistence.load_preferences() is None
    assert persistence.clear_preferences() is False


def test_clear_preferences_removes_prefs_file_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    backup = tmp_path / "backup"
    monkeypatch.setenv("CLOUDINIT_BACKUP_DIR", str(backup))
    persistence.save_preferences({"hostname": "z"})
    assert backup.is_dir()
    assert (backup / persistence.PREFS_FILENAME).is_file()
    assert persistence.clear_preferences() is True
    assert not (backup / persistence.PREFS_FILENAME).exists()
    assert backup.is_dir()
    assert persistence.load_preferences() is None

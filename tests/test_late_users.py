"""Tests for late user form parsing."""

from __future__ import annotations

from werkzeug.datastructures import ImmutableMultiDict

from cloudinit_builder import late_users


def test_late_users_from_form_skips_empty_rows():
    form = ImmutableMultiDict(
        [
            ("late_u_enabled_0", "on"),
            ("late_u_name_0", "alice"),
            ("late_u_keys_0", "ssh-ed25519 AAA alice"),
            ("late_u_shell_0", "/bin/bash"),
            ("late_u_sudo_0", "on"),
            ("late_u_enabled_1", ""),
            ("late_u_name_1", ""),
            ("late_u_keys_1", ""),
        ]
    )
    out = late_users.late_users_from_form(form)
    assert len(out) == 1
    assert out[0]["name"] == "alice"
    assert out[0]["keys"] == ["ssh-ed25519 AAA alice"]
    assert out[0]["sudo_nopasswd"] is True


def test_late_users_from_form_skips_disabled_rows():
    form = ImmutableMultiDict(
        [
            ("late_u_enabled_0", ""),
            ("late_u_name_0", "disabled-user"),
            ("late_u_keys_0", "ssh-ed25519 AAA disabled-user"),
            ("late_u_enabled_1", "on"),
            ("late_u_name_1", "bob"),
            ("late_u_keys_1", "ssh-ed25519 AAA bob"),
        ]
    )
    out = late_users.late_users_from_form(form)
    assert len(out) == 1
    assert out[0]["name"] == "bob"


def test_late_users_for_template_exposes_private_keys():
    rows = late_users.late_users_for_template(
        [
            {
                "name": "alice",
                "keys": [],
                "shell": "/bin/bash",
                "sudo_nopasswd": False,
                "private_keys": [{"filename": "id_alice", "content": "PRIVATE"}],
            }
        ]
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "alice"
    assert rows[0]["private_keys"][0]["filename"] == "id_alice"

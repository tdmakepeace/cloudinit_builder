"""Tests for late user form parsing."""

from __future__ import annotations

from werkzeug.datastructures import ImmutableMultiDict

from cloudinit_builder import late_users


def test_late_users_from_form_skips_empty_rows():
    form = ImmutableMultiDict(
        [
            ("late_u_name_0", "alice"),
            ("late_u_keys_0", "ssh-ed25519 AAA alice"),
            ("late_u_shell_0", "/bin/bash"),
            ("late_u_sudo_0", "on"),
            ("late_u_name_1", ""),
            ("late_u_keys_1", ""),
        ]
    )
    out = late_users.late_users_from_form(form)
    assert len(out) == 1
    assert out[0]["name"] == "alice"
    assert out[0]["keys"] == ["ssh-ed25519 AAA alice"]
    assert out[0]["sudo_nopasswd"] is True

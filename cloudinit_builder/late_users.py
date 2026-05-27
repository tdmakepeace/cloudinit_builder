"""Parse and normalize late cloud-init user entries (SSH keys, sudo, shell)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def late_users_from_form(form: Mapping[str, Any], max_rows: int = 32) -> list[dict[str, Any]]:
    """Build late user dicts from indexed form fields (``late_u_name_0``, etc.)."""
    out: list[dict[str, Any]] = []
    for i in range(max_rows):
        enabled = form.get(f"late_u_enabled_{i}") == "on"
        if not enabled:
            continue
        name = (form.get(f"late_u_name_{i}") or "").strip()
        keys_text = form.get(f"late_u_keys_{i}") or ""
        keys = [k.strip() for k in str(keys_text).splitlines() if k.strip()]
        shell = (form.get(f"late_u_shell_{i}") or "").strip() or "/bin/bash"
        sudo = form.get(f"late_u_sudo_{i}") == "on"
        if not name and not keys:
            continue
        out.append(
            {
                "row_index": i,
                "name": name,
                "keys": keys,
                "shell": shell,
                "sudo_nopasswd": sudo,
                "ssh_config_text": str(form.get(f"late_u_ssh_config_{i}") or "").strip(),
            }
        )
    return out


def late_users_for_template(users: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure each user has ``keys_text`` for textarea binding."""
    rows: list[dict[str, Any]] = []
    for u in users:
        keys = u.get("keys") or u.get("ssh_authorized_keys") or []
        if isinstance(keys, str):
            keys = [keys]
        keys_text = "\n".join(str(k) for k in keys)
        rows.append(
            {
                "enabled": True,
                "name": u.get("name", ""),
                "keys_text": keys_text,
                "shell": u.get("shell", "/bin/bash"),
                "sudo_nopasswd": bool(u.get("sudo_nopasswd", False)),
                "ssh_config_text": u.get("ssh_config_text", ""),
                "private_keys": u.get("private_keys") or [],
            }
        )
    if not rows:
        rows.append(
            {
                "enabled": False,
                "name": "",
                "keys_text": "",
                "shell": "/bin/bash",
                "sudo_nopasswd": True,
                "ssh_config_text": "",
                "private_keys": [],
            }
        )
    return rows

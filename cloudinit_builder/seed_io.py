"""Load defaults from seed user-data and meta-data files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def strip_cloud_config_header(raw: str) -> str:
    lines = raw.splitlines()
    if lines and lines[0].strip().startswith("#"):
        return "\n".join(lines[1:]).lstrip("\n")
    return raw


def load_yaml_user_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(strip_cloud_config_header(text)) or {}


def load_meta_data(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            out[key.strip()] = val.strip()
    return out


def list_ethernets_ordered(network_block: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Preserve YAML order of netplan ``ethernets`` entries."""
    ethernets = (network_block or {}).get("ethernets") or {}
    return [(str(k), dict(v)) for k, v in ethernets.items()]


def format_nameservers(addrs: list[str]) -> str:
    return ", ".join(addrs)


def parse_nameservers(text: str) -> list[str]:
    parts = re.split(r"[\s,]+", text.strip())
    return [p for p in parts if p]


def parse_package_lines(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.replace(",", "\n").splitlines()]
    return [ln for ln in lines if ln and not ln.startswith("#")]


def defaults_from_seed(seed_dir: Path) -> dict[str, Any]:
    """Flatten seed files into form-friendly defaults."""
    user_path = seed_dir / "user-data"
    meta_path = seed_dir / "meta-data"
    data = load_yaml_user_data(user_path) if user_path.is_file() else {}
    meta = load_meta_data(meta_path) if meta_path.is_file() else {}

    ai = data.get("autoinstall") or {}
    identity = ai.get("identity") or {}
    locale_val = ai.get("locale") or "en_US.UTF-8"
    keyboard = ai.get("keyboard") or {}
    net = ai.get("network") or {}
    pairs = list_ethernets_ordered(net)
    if_name, eth = pairs[0] if pairs else ("", {})
    addrs = eth.get("addresses") or []
    addr_cidr = addrs[0] if addrs else ""
    ns = (eth.get("nameservers") or {}).get("addresses") or []

    if_name2, eth2 = pairs[1] if len(pairs) > 1 else ("ens192", {})
    addrs2 = eth2.get("addresses") or []
    addr_cidr2 = addrs2[0] if addrs2 else ""
    ns2 = (eth2.get("nameservers") or {}).get("addresses") or []
    enable_network2 = len(pairs) > 1
    ssh = ai.get("ssh") or {}
    pkgs_early = ai.get("packages") or []
    storage = ai.get("storage") or {}
    layout = (storage.get("layout") or {}).get("name") or "direct"
    updates = ai.get("updates")
    late = ai.get("user-data") or {}

    users_late = late.get("users") or []
    late_users: list[dict[str, Any]] = []
    for u in users_late:
        if not isinstance(u, dict):
            continue
        keys = u.get("ssh_authorized_keys") or []
        if isinstance(keys, str):
            keys = [keys]
        late_users.append(
            {
                "name": u.get("name", ""),
                "keys": [str(k) for k in keys],
                "shell": u.get("shell", "/bin/bash"),
                "sudo_nopasswd": "NOPASSWD" in str(u.get("sudo", "")),
            }
        )
    late_pkgs = late.get("packages") or []
    runcmd = late.get("runcmd") or []

    return {
        "enable_identity": True,
        "enable_locale": True,
        "enable_network": True,
        "enable_ssh": True,
        "enable_packages_early": True,
        "enable_storage": True,
        "enable_updates": True,
        "enable_late_user_data": True,
        "hostname": identity.get("hostname") or meta.get("local-hostname", ""),
        "username": identity.get("username", ""),
        "password_mode": "hashed",
        "password_plain": "",
        "password_hash": identity.get("password", ""),
        "locale": locale_val,
        "keyboard_layout": keyboard.get("layout", "us"),
        "iface": if_name or "ens160",
        "network_mode": "static" if eth.get("dhcp4") is False else "dhcp",
        "address_cidr": addr_cidr,
        "gateway": str(eth.get("gateway4") or ""),
        "nameservers": format_nameservers(ns) if ns else "1.1.1.1",
        "enable_network2": enable_network2,
        "iface2": if_name2 or "ens192",
        "network_mode2": "static" if eth2.get("dhcp4") is False else "dhcp",
        "address_cidr2": addr_cidr2,
        "gateway2": str(eth2.get("gateway4") or ""),
        "nameservers2": format_nameservers(ns2) if ns2 else "1.1.1.1",
        "ssh_install_server": bool(ssh.get("install-server", True)),
        "ssh_allow_pw": bool(ssh.get("allow-pw", True)),
        "packages_early_text": "\n".join(str(p) for p in pkgs_early),
        "storage_layout": layout,
        "updates_policy": updates if updates in ("all", "security") else "all",
        "late_package_update": bool(late.get("package_update", True)),
        "late_package_upgrade": bool(late.get("package_upgrade", True)),
        "late_users": late_users,
        "packages_late_text": "\n".join(str(p) for p in late_pkgs),
        "late_runcmd_autoremove": any(isinstance(c, str) and "autoremove" in c for c in runcmd),
    }

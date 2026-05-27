"""Build user-data (#cloud-config) and meta-data text from form state."""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Optional

import yaml

from cloudinit_builder import passwords, seed_io


def identity_password_configured(form: dict[str, Any]) -> bool:
    """True if the active password field (plain vs hash mode) is non-empty."""
    mode = (form.get("password_mode") or "hashed").strip().lower()
    if mode == "plain":
        return bool((form.get("password_plain") or "").strip())
    return bool((form.get("password_hash") or "").strip())


def validate_generate(form: dict[str, Any]) -> Optional[str]:
    """Return an error message if generation must be blocked; otherwise ``None``."""
    if form.get("enable_identity") and not identity_password_configured(form):
        return "Identity is enabled: set a password (pre-hashed or plain) before generating."
    return None


def resolve_identity_password(form: dict[str, Any]) -> str:
    """Return the identity password string to embed (hashed). Only one source is used."""
    mode = (form.get("password_mode") or "hashed").strip().lower()
    if mode == "plain":
        plain = (form.get("password_plain") or "").strip()
        if not plain:
            return ""
        return passwords.hash_plain_password_sha512(plain)
    return (form.get("password_hash") or "").strip()


def _net_field_map(suffix: str) -> dict[str, str]:
    if suffix == "2":
        return {
            "iface": "iface2",
            "mode": "network_mode2",
            "cidr": "address_cidr2",
            "gw": "gateway2",
            "ns": "nameservers2",
        }
    return {
        "iface": "iface",
        "mode": "network_mode",
        "cidr": "address_cidr",
        "gw": "gateway",
        "ns": "nameservers",
    }


def build_ethernet_config(form: dict[str, Any], suffix: str) -> tuple[str, dict[str, Any]]:
    """Return (interface_name, netplan ethernet stanza)."""
    m = _net_field_map(suffix)
    iface = (form.get(m["iface"]) or "").strip()
    mode = form.get(m["mode"]) or "dhcp"
    eth: dict[str, Any] = {"dhcp4": mode == "dhcp"}
    if mode == "static":
        cidr = (form.get(m["cidr"]) or "").strip()
        if cidr:
            eth["addresses"] = [cidr]
        gw = (form.get(m["gw"]) or "").strip()
        if gw:
            eth["gateway4"] = gw
        ns = seed_io.parse_nameservers(str(form.get(m["ns"]) or ""))
        if ns:
            eth["nameservers"] = {"addresses": ns}
    return iface, eth


def build_autoinstall(form: dict[str, Any]) -> dict[str, Any]:
    """Assemble the autoinstall mapping (without the #cloud-config wrapper)."""
    ai: dict[str, Any] = {"version": 1}

    if form.get("enable_identity"):
        ai["identity"] = {
            "hostname": form["hostname"].strip(),
            "username": form["username"].strip(),
            "password": resolve_identity_password(form),
        }

    if form.get("enable_locale"):
        ai["locale"] = form["locale"].strip()
        ai["keyboard"] = {"layout": form["keyboard_layout"].strip()}

    if form.get("enable_network"):
        ethernets: dict[str, Any] = {}
        if1, e1 = build_ethernet_config(form, "")
        if if1:
            ethernets[if1] = e1
        if form.get("enable_network2"):
            if2, e2 = build_ethernet_config(form, "2")
            if if2:
                ethernets[if2] = e2
        if ethernets:
            ai["network"] = {"version": 2, "ethernets": ethernets}

    if form.get("enable_ssh"):
        ai["ssh"] = {
            "install-server": bool(form.get("ssh_install_server")),
            "allow-pw": bool(form.get("ssh_allow_pw")),
        }

    if form.get("enable_packages_early"):
        pkgs = seed_io.parse_package_lines(form.get("packages_early_text", ""))
        if pkgs:
            ai["packages"] = pkgs

    if form.get("enable_storage"):
        layout = form.get("storage_layout") or "direct"
        ai["storage"] = {"layout": {"name": layout}}

    if form.get("enable_updates"):
        pol = form.get("updates_policy") or "all"
        if pol in ("all", "security"):
            ai["updates"] = pol

    if form.get("enable_late_user_data"):
        late: dict[str, Any] = {}
        write_files: list[dict[str, Any]] = []
        user_ssh_install_commands: list[str] = []
        if form.get("late_package_update"):
            late["package_update"] = True
        if form.get("late_package_upgrade"):
            late["package_upgrade"] = True

        user_entries: list[dict[str, Any]] = []
        fallback_name = (form.get("username") or "").strip()
        for u in form.get("late_users") or []:
            if not isinstance(u, dict):
                continue
            nm = (u.get("name") or "").strip() or fallback_name
            keys = u.get("keys") or []
            if isinstance(keys, str):
                keys = [keys]
            keys = [str(k).strip() for k in keys if str(k).strip()]
            if not nm and not keys:
                continue
            if not nm:
                continue
            user_entry: dict[str, Any] = {"name": nm}
            if keys:
                user_entry["ssh_authorized_keys"] = keys
            if u.get("sudo_nopasswd"):
                user_entry["sudo"] = "ALL=(ALL) NOPASSWD:ALL"
            shell = (u.get("shell") or "").strip() or "/bin/bash"
            if shell:
                user_entry["shell"] = shell
            user_entries.append(user_entry)

        if user_entries:
            late["users"] = user_entries

        late_pkgs = seed_io.parse_package_lines(form.get("packages_late_text", ""))
        if late_pkgs:
            late["packages"] = late_pkgs

        if form.get("enable_hosts_file_update"):
            hosts_entries = seed_io.parse_hosts_entries(str(form.get("hosts_entries_text") or ""))
            if hosts_entries:
                host_lines = [
                    "127.0.0.1 localhost",
                    "::1 localhost ip6-localhost ip6-loopback",
                ]
                host_lines.extend(f"{ip} {host}" for ip, host in hosts_entries)
                hosts_content = "\n".join(host_lines) + "\n"
                write_files.append(
                    {
                        "path": "/etc/hosts",
                        "owner": "root:root",
                        "permissions": "0644",
                        "content": hosts_content,
                    }
                )

        for user in form.get("late_users") or []:
            if not isinstance(user, dict):
                continue
            user_name = str(user.get("name") or "").strip()
            if not user_name:
                continue
            user_quoted = shlex.quote(user_name)
            user_home_ssh = f"/home/{user_quoted}/.ssh"

            ssh_entries = seed_io.parse_ssh_config_entries(str(user.get("ssh_config_text") or ""))
            if ssh_entries:
                ssh_lines = []
                for entry in ssh_entries:
                    ssh_lines.extend(
                        [
                            f"Host {entry['host']}",
                            f"  HostName {entry['hostname']}",
                            f"  User {entry['user']}",
                            f"  IdentityFile {entry['identity_file']}",
                            "",
                        ]
                    )
                ssh_content = "\n".join(ssh_lines).strip() + "\n"
                tmp_config_name = _tmp_ssh_filename(user_name, "config")
                tmp_config_path = f"/var/tmp/{tmp_config_name}"
                write_files.append(
                    {
                        "path": tmp_config_path,
                        "owner": "root:root",
                        "permissions": "0600",
                        "content": ssh_content,
                    }
                )
                user_ssh_install_commands.extend(
                    [
                        f"install -d -m 700 -o {user_quoted} -g {user_quoted} {user_home_ssh}",
                        f"install -m 600 -o {user_quoted} -g {user_quoted} "
                        f"{shlex.quote(tmp_config_path)} {user_home_ssh}/config",
                    ]
                )

            private_keys = user.get("private_keys") or []
            if not isinstance(private_keys, list):
                continue
            for key_entry in private_keys:
                if not isinstance(key_entry, dict):
                    continue
                filename = Path(str(key_entry.get("filename") or "")).name.strip()
                content = str(key_entry.get("content") or "")
                if not filename or not content.strip():
                    continue
                if "/" in filename or "\\" in filename:
                    continue
                tmp_key_name = _tmp_ssh_filename(user_name, filename)
                tmp_key_path = f"/var/tmp/{tmp_key_name}"
                write_files.append(
                    {
                        "path": tmp_key_path,
                        "owner": "root:root",
                        "permissions": "0600",
                        "content": content if content.endswith("\n") else f"{content}\n",
                    }
                )
                user_ssh_install_commands.extend(
                    [
                        f"install -d -m 700 -o {user_quoted} -g {user_quoted} {user_home_ssh}",
                        f"install -m 600 -o {user_quoted} -g {user_quoted} "
                        f"{shlex.quote(tmp_key_path)} {user_home_ssh}/{shlex.quote(filename)}",
                    ]
                )

        if write_files:
            late["write_files"] = write_files

        runcmd: list[str] = []
        if form.get("late_runcmd_autoremove"):
            runcmd.append("apt-get autoremove -y")
        if user_ssh_install_commands:
            runcmd.extend(user_ssh_install_commands)
        if runcmd:
            late["runcmd"] = runcmd

        if late:
            ai["user-data"] = late

    return ai


def _tmp_ssh_filename(user_name: str, source_name: str) -> str:
    joined = f"cloudinit_builder_ssh_{user_name}_{source_name}"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", joined)


def build_user_data_yaml(form: dict[str, Any]) -> str:
    root = {"autoinstall": build_autoinstall(form)}
    body = yaml.dump(
        root,
        default_flow_style=False,
        sort_keys=False,
        allow_unicode=True,
    )
    return f"#cloud-config\n{body}"


def build_meta_data_text(form: dict[str, Any]) -> str:
    """NoCloud meta-data: ``instance-id`` is required; set both from hostname.

    Cloud-init treats ``instance-id`` as the stable instance key (first boot / cache).
    ``local-hostname`` may differ on real clouds; for this builder we mirror the hostname
    field so operators do not maintain separate meta fields (common lab / NoCloud pattern).
    """
    host = (form.get("hostname") or "").strip()
    if not host:
        return ""
    return f"instance-id: {host}\nlocal-hostname: {host}\n"

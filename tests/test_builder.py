"""Tests for YAML builder."""

from __future__ import annotations

from pathlib import Path

import yaml

from cloudinit_builder import builder, seed_io


def _base_form(**overrides):
    form = {
        "enable_identity": False,
        "enable_locale": False,
        "enable_network": True,
        "enable_ssh": False,
        "enable_packages_early": False,
        "enable_storage": False,
        "enable_updates": False,
        "enable_late_user_data": False,
        "hostname": "h1",
        "username": "u1",
        "password_mode": "hashed",
        "password_plain": "",
        "password_hash": "",
        "locale": "en_US.UTF-8",
        "keyboard_layout": "us",
        "iface": "ens192",
        "network_mode": "dhcp",
        "address_cidr": "",
        "gateway": "",
        "nameservers": "",
        "enable_network2": False,
        "iface2": "ens224",
        "network_mode2": "dhcp",
        "address_cidr2": "",
        "gateway2": "",
        "nameservers2": "",
        "ssh_install_server": True,
        "ssh_allow_pw": True,
        "packages_early_text": "",
        "storage_layout": "direct",
        "updates_policy": "all",
        "late_package_update": False,
        "late_package_upgrade": False,
        "late_users": [],
        "packages_late_text": "",
        "late_runcmd_autoremove": False,
    }
    form.update(overrides)
    return form


def test_build_omits_disabled_sections():
    form = _base_form()
    ai = builder.build_autoinstall(form)
    assert "identity" not in ai
    assert "network" in ai
    assert ai["network"]["ethernets"]["ens192"]["dhcp4"] is True


def test_network_two_interfaces_when_enabled():
    form = _base_form(
        enable_network2=True,
        iface2="ens224",
        network_mode2="static",
        address_cidr2="10.1.0.2/24",
        gateway2="10.1.0.1",
        nameservers2="8.8.8.8",
    )
    ai = builder.build_autoinstall(form)
    assert "ens192" in ai["network"]["ethernets"]
    assert "ens224" in ai["network"]["ethernets"]
    assert ai["network"]["ethernets"]["ens224"]["addresses"] == ["10.1.0.2/24"]


def test_identity_password_plain_hashes():
    form = {
        "enable_identity": True,
        "hostname": "h",
        "username": "u",
        "password_mode": "plain",
        "password_plain": "secret",
        "password_hash": "WRONG",
    }
    pw = builder.resolve_identity_password(form)
    assert pw.startswith("$6$")
    assert "WRONG" not in pw


def test_identity_password_hashed_ignores_plain():
    form = {
        "enable_identity": True,
        "hostname": "h",
        "username": "u",
        "password_mode": "hashed",
        "password_plain": "ignored",
        "password_hash": "hashhere",
    }
    assert builder.resolve_identity_password(form) == "hashhere"


def test_meta_data_from_hostname_only():
    form = {"hostname": "vm1"}
    text = builder.build_meta_data_text(form)
    assert text == "instance-id: vm1\nlocal-hostname: vm1\n"


def test_late_multiple_users():
    form = _base_form(
        enable_late_user_data=True,
        late_users=[
            {"name": "a", "keys": ["ssh-rsa AAA a"], "shell": "/bin/bash", "sudo_nopasswd": True},
            {"name": "b", "keys": ["ssh-ed25519 AAA b"], "shell": "/bin/sh", "sudo_nopasswd": False},
        ],
    )
    ai = builder.build_autoinstall(form)
    users = ai["user-data"]["users"]
    assert len(users) == 2
    assert users[0]["name"] == "a"
    assert users[1]["name"] == "b"
    assert "NOPASSWD" in users[0]["sudo"]
    assert "sudo" not in users[1]


def test_defaults_from_seed_roundtrip(tmp_path: Path):
    seed = tmp_path / "seed"
    seed.mkdir()
    (seed / "user-data").write_text(
        "\n".join(
            [
                "#cloud-config",
                "autoinstall:",
                "  version: 1",
                "  identity:",
                "    hostname: testhost",
                "    username: demouser",
                "    password: hashhere",
                "  locale: en_GB",
                "  keyboard:",
                "    layout: gb",
                "  network:",
                "    version: 2",
                "    ethernets:",
                "      ens99:",
                "        dhcp4: false",
                "        addresses:",
                "          - 10.0.0.5/24",
                "        gateway4: 10.0.0.1",
                "        nameservers:",
                "          addresses: [10.0.0.1]",
                "  ssh:",
                "    install-server: true",
                "    allow-pw: false",
                "  packages: [curl]",
                "  storage:",
                "    layout:",
                "      name: direct",
                "  updates: security",
                "  user-data:",
                "    package_update: true",
                "    users:",
                "      - name: demouser",
                "        ssh_authorized_keys: [ssh-ed25519 AAA test]",
                "        sudo: ALL=(ALL) NOPASSWD:ALL",
                "        shell: /bin/bash",
                "    packages: [jq]",
                "    runcmd: [apt-get autoremove -y]",
            ]
        ),
        encoding="utf-8",
    )
    (seed / "meta-data").write_text(
        "instance-id: testhost\nlocal-hostname: testhost\n",
        encoding="utf-8",
    )
    d = seed_io.defaults_from_seed(seed)
    assert d["password_mode"] == "hashed"
    assert d["hostname"] == "testhost"
    assert d["iface"] == "ens99"
    assert d["address_cidr"] == "10.0.0.5/24"
    assert d["updates_policy"] == "security"
    assert d["ssh_allow_pw"] is False
    assert d["late_runcmd_autoremove"] is True
    assert "curl" in d["packages_early_text"]
    assert len(d["late_users"]) == 1
    assert d["late_users"][0]["name"] == "demouser"
    out = builder.build_user_data_yaml({**d, "enable_identity": True})
    parsed = yaml.safe_load(seed_io.strip_cloud_config_header(out))
    assert parsed["autoinstall"]["identity"]["hostname"] == "testhost"


def test_validate_generate_blocks_identity_without_password():
    form = _base_form(enable_identity=True, password_hash="", password_plain="")
    err = builder.validate_generate(form)
    assert err is not None
    assert "password" in err.lower()


def test_validate_generate_allows_identity_with_hash():
    form = _base_form(enable_identity=True, password_hash="$6$rounds=5000$x")
    assert builder.validate_generate(form) is None


def test_validate_generate_allows_identity_with_plain():
    form = _base_form(enable_identity=True, password_mode="plain", password_plain="secret")
    assert builder.validate_generate(form) is None


def test_validate_generate_allows_no_identity_without_password():
    form = _base_form(enable_identity=False, password_hash="")
    assert builder.validate_generate(form) is None

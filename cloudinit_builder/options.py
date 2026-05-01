"""Curated UI choices for locale, XKB keyboard layouts, and VM Ethernet names.

Locale strings follow Ubuntu/glibc ``/usr/share/i18n/SUPPORTED`` style (``lang_COUNTRY.UTF-8``).
Keyboard layout codes are XKB names (``layout`` in cloud-init / subiquity), see
https://wiki.debian.org/Keyboard
Interface names use systemd predictable names (``ens*`` / ``enp*``); common KVM/libvirt
and VMware guests often see ``ens33`` / ``enp0s3`` vs ``ens160`` / ``ens192`` depending on
PCI slot enumeration — see PredictableNetworkInterfaceNames and vendor docs.
"""

from __future__ import annotations

# Common UTF-8 locales (subset of typical Ubuntu installer / cloud images).
LOCALE_CHOICES: list[tuple[str, str]] = [
    ("C.UTF-8", "C.UTF-8 (POSIX minimal)"),
    ("en_US.UTF-8", "English (United States)"),
    ("en_GB.UTF-8", "English (United Kingdom)"),
    ("en_AU.UTF-8", "English (Australia)"),
    ("en_CA.UTF-8", "English (Canada)"),
    ("en_IN.UTF-8", "English (India)"),
    ("en_NZ.UTF-8", "English (New Zealand)"),
    ("en_IE.UTF-8", "English (Ireland)"),
    ("en_ZA.UTF-8", "English (South Africa)"),
    ("de_DE.UTF-8", "German (Germany)"),
    ("de_AT.UTF-8", "German (Austria)"),
    ("de_CH.UTF-8", "German (Switzerland)"),
    ("fr_FR.UTF-8", "French (France)"),
    ("fr_CA.UTF-8", "French (Canada)"),
    ("fr_CH.UTF-8", "French (Switzerland)"),
    ("es_ES.UTF-8", "Spanish (Spain)"),
    ("es_MX.UTF-8", "Spanish (Mexico)"),
    ("es_AR.UTF-8", "Spanish (Argentina)"),
    ("it_IT.UTF-8", "Italian (Italy)"),
    ("pt_BR.UTF-8", "Portuguese (Brazil)"),
    ("pt_PT.UTF-8", "Portuguese (Portugal)"),
    ("nl_NL.UTF-8", "Dutch (Netherlands)"),
    ("nl_BE.UTF-8", "Dutch (Belgium)"),
    ("sv_SE.UTF-8", "Swedish (Sweden)"),
    ("no_NO.UTF-8", "Norwegian (Norway)"),
    ("da_DK.UTF-8", "Danish (Denmark)"),
    ("fi_FI.UTF-8", "Finnish (Finland)"),
    ("pl_PL.UTF-8", "Polish (Poland)"),
    ("cs_CZ.UTF-8", "Czech (Czechia)"),
    ("sk_SK.UTF-8", "Slovak (Slovakia)"),
    ("hu_HU.UTF-8", "Hungarian (Hungary)"),
    ("ro_RO.UTF-8", "Romanian (Romania)"),
    ("bg_BG.UTF-8", "Bulgarian (Bulgaria)"),
    ("el_GR.UTF-8", "Greek (Greece)"),
    ("tr_TR.UTF-8", "Turkish (Türkiye)"),
    ("ru_RU.UTF-8", "Russian (Russia)"),
    ("uk_UA.UTF-8", "Ukrainian (Ukraine)"),
    ("ja_JP.UTF-8", "Japanese (Japan)"),
    ("ko_KR.UTF-8", "Korean (Korea)"),
    ("zh_CN.UTF-8", "Chinese (China, simplified)"),
    ("zh_TW.UTF-8", "Chinese (Taiwan, traditional)"),
    ("hi_IN.UTF-8", "Hindi (India)"),
    ("id_ID.UTF-8", "Indonesian (Indonesia)"),
    ("th_TH.UTF-8", "Thai (Thailand)"),
    ("vi_VN.UTF-8", "Vietnamese (Vietnam)"),
    ("he_IL.UTF-8", "Hebrew (Israel)"),
    ("ar_EG.UTF-8", "Arabic (Egypt)"),
    ("ar_SA.UTF-8", "Arabic (Saudi Arabia)"),
]

# XKB layout codes (``keyboard layout``); see /usr/share/X11/xkb/rules/base.lst ``! layout``.
KEYBOARD_CHOICES: list[tuple[str, str]] = [
    ("us", "us — English (US)"),
    ("gb", "gb — English (UK)"),
    ("ca", "ca — English (Canada)"),
    ("au", "au — English (Australia)"),
    ("de", "de — German"),
    ("de(nodeadkeys)", "de (nodeadkeys)"),
    ("fr", "fr — French"),
    ("fr(latin9)", "fr (latin9)"),
    ("es", "es — Spanish"),
    ("latam", "latam — Latin American Spanish"),
    ("it", "it — Italian"),
    ("pt", "pt — Portuguese"),
    ("br", "br — Portuguese (Brazil)"),
    ("nl", "nl — Dutch"),
    ("se", "se — Swedish"),
    ("no", "no — Norwegian"),
    ("dk", "dk — Danish"),
    ("fi", "fi — Finnish"),
    ("pl", "pl — Polish"),
    ("cz", "cz — Czech"),
    ("sk", "sk — Slovak"),
    ("hu", "hu — Hungarian"),
    ("ro", "ro — Romanian"),
    ("bg", "bg — Bulgarian"),
    ("gr", "gr — Greek"),
    ("tr", "tr — Turkish"),
    ("ru", "ru — Russian"),
    ("ua", "ua — Ukrainian"),
    ("jp", "jp — Japanese"),
    ("kr", "kr — Korean"),
    ("cn", "cn — Chinese"),
    ("tw", "tw — Chinese (Taiwan)"),
    ("in(eng)", "in (eng) — India English"),
    ("il", "il — Hebrew"),
    ("ara", "ara — Arabic"),
    ("dvorak", "dvorak"),
]

# Typical guest NIC names: numbers come from PCI “slot” / topology (systemd v197+), not the
# hypervisor alone — these are the names most often seen in docs/community for virtio vs vmxnet3.
ETHERNET_INTERFACE_GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    (
        "KVM / QEMU / virtio (common examples)",
        [
            ("ens3", "ens3 — common single virtio NIC"),
            ("ens18", "ens18 — virtio (many Proxmox / QEMU setups)"),
            ("ens33", "ens33 — often seen on VMware & older lab docs; also some KVM imports"),
            ("enp0s3", "enp0s3 — libvirt “default” NIC topology"),
            ("enp1s0", "enp1s0 — PCI path style (enp bus)"),
            ("enp3s0", "enp3s0 — PCI path style"),
            ("eth0", "eth0 — legacy / if predictable names disabled"),
        ],
    ),
    (
        "VMware (vmxnet3 — common examples)",
        [
            ("ens160", "ens160 — very common VMware guest NIC"),
            ("ens192", "ens192 — common VMware guest NIC"),
            ("ens224", "ens224 — additional VMware NIC slot"),
            ("ens256", "ens256 — additional slot (example)"),
        ],
    ),
    (
        "Hyper-V / other",
        [
            ("eth0", "eth0 — synthetic / legacy"),
        ],
    ),
]


def all_ethernet_interface_choices() -> list[tuple[str, str]]:
    """Flatten grouped interface choices for HTML ``<select>``."""
    out: list[tuple[str, str]] = []
    for _title, items in ETHERNET_INTERFACE_GROUPS:
        out.extend(items)
    return out


def iface_select_choices(current: str) -> list[tuple[str, str]]:
    """Interface dropdown options, preserving an unknown ``current`` value (e.g. from seed)."""
    choices = list(all_ethernet_interface_choices())
    seen = {v for v, _ in choices}
    cur = (current or "").strip()
    if cur and cur not in seen:
        choices.insert(0, (cur, f"{cur} (from seed / custom)"))
    return choices


def locale_select_choices(current: str) -> list[tuple[str, str]]:
    choices = list(LOCALE_CHOICES)
    seen = {v for v, _ in choices}
    cur = (current or "").strip()
    if cur and cur not in seen:
        choices.insert(0, (cur, f"{cur} (custom / seed)"))
    return choices


def keyboard_select_choices(current: str) -> list[tuple[str, str]]:
    choices = list(KEYBOARD_CHOICES)
    seen = {v for v, _ in choices}
    cur = (current or "").strip()
    if cur and cur not in seen:
        choices.insert(0, (cur, f"{cur} (custom / seed)"))
    return choices

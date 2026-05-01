"""Flask UI for composing autoinstall user-data and meta-data (browser or desktop shell)."""

from __future__ import annotations

import threading
import time
import urllib.request
from pathlib import Path
from typing import Optional

from flask import Flask, abort, make_response, redirect, render_template, request, send_from_directory, url_for

from cloudinit_builder import builder, late_users, options, paths, persistence, seed_io

paths.ensure_backup_env()

app = Flask(__name__)

_OUTPUT_NAMES = frozenset({"user-data", "meta-data"})


def fallback_defaults() -> dict:
    return {
        "enable_identity": True,
        "enable_locale": True,
        "enable_network": True,
        "enable_ssh": True,
        "enable_packages_early": True,
        "enable_storage": True,
        "enable_updates": True,
        "enable_late_user_data": True,
        "hostname": "ubuntu-server",
        "username": "ubuntu",
        "password_mode": "hashed",
        "password_plain": "",
        "password_hash": "",
        "locale": "en_US.UTF-8",
        "keyboard_layout": "us",
        "iface": "ens160",
        "network_mode": "dhcp",
        "address_cidr": "",
        "gateway": "",
        "nameservers": "1.1.1.1",
        "enable_network2": False,
        "iface2": "ens192",
        "network_mode2": "dhcp",
        "address_cidr2": "",
        "gateway2": "",
        "nameservers2": "1.1.1.1",
        "ssh_install_server": True,
        "ssh_allow_pw": True,
        "packages_early_text": "curl\nnet-tools",
        "storage_layout": "direct",
        "updates_policy": "all",
        "late_package_update": True,
        "late_package_upgrade": True,
        "late_users": [],
        "packages_late_text": "",
        "late_runcmd_autoremove": False,
    }


def load_initial_defaults(initial_dir: Path) -> tuple[dict, Optional[str]]:
    """Load ``initial/`` templates, then overlay ``backup/preferences.json`` if present."""
    err: Optional[str] = None
    try:
        if initial_dir.is_dir() and (initial_dir / "user-data").is_file():
            base = seed_io.defaults_from_seed(initial_dir)
        else:
            base = fallback_defaults()
    except Exception as exc:  # noqa: BLE001
        err = f"Could not load initial seed from {initial_dir}: {exc}"
        base = fallback_defaults()
    saved = persistence.load_preferences()
    if saved:
        base = persistence.merge_saved_over_base(base, saved)
    return base, err


def form_from_request() -> dict:
    """Parse POST into a flat dict matching builder/seed defaults keys."""

    def bool_field(name: str) -> bool:
        return request.form.get(name) == "on"

    return {
        "enable_identity": bool_field("enable_identity"),
        "enable_locale": bool_field("enable_locale"),
        "enable_network": bool_field("enable_network"),
        "enable_ssh": bool_field("enable_ssh"),
        "enable_packages_early": bool_field("enable_packages_early"),
        "enable_storage": bool_field("enable_storage"),
        "enable_updates": bool_field("enable_updates"),
        "enable_late_user_data": bool_field("enable_late_user_data"),
        "hostname": request.form.get("hostname", ""),
        "username": request.form.get("username", ""),
        "password_mode": request.form.get("password_mode", "hashed"),
        "password_plain": request.form.get("password_plain", ""),
        "password_hash": request.form.get("password_hash", ""),
        "locale": request.form.get("locale", ""),
        "keyboard_layout": request.form.get("keyboard_layout", ""),
        "iface": request.form.get("iface", ""),
        "network_mode": request.form.get("network_mode", "dhcp"),
        "address_cidr": request.form.get("address_cidr", ""),
        "gateway": request.form.get("gateway", ""),
        "nameservers": request.form.get("nameservers", ""),
        "enable_network2": bool_field("enable_network2"),
        "iface2": request.form.get("iface2", ""),
        "network_mode2": request.form.get("network_mode2", "dhcp"),
        "address_cidr2": request.form.get("address_cidr2", ""),
        "gateway2": request.form.get("gateway2", ""),
        "nameservers2": request.form.get("nameservers2", ""),
        "ssh_install_server": bool_field("ssh_install_server"),
        "ssh_allow_pw": bool_field("ssh_allow_pw"),
        "packages_early_text": request.form.get("packages_early_text", ""),
        "storage_layout": request.form.get("storage_layout", "direct"),
        "updates_policy": request.form.get("updates_policy", "all"),
        "late_package_update": bool_field("late_package_update"),
        "late_package_upgrade": bool_field("late_package_upgrade"),
        "late_users": late_users.late_users_from_form(request.form),
        "packages_late_text": request.form.get("packages_late_text", ""),
        "late_runcmd_autoremove": bool_field("late_runcmd_autoremove"),
    }


@app.get("/artifact/<name>")
def serve_output_artifact(name: str):
    """Serve generated NoCloud files (plain HTTP GET so browsers can export without JavaScript)."""
    if name not in _OUTPUT_NAMES:
        abort(404)
    directory = paths.output_dir()
    path = directory / name
    if not path.is_file():
        abort(404)
    response = send_from_directory(
        directory,
        name,
        mimetype="text/plain; charset=utf-8",
        as_attachment=True,
        download_name=name,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/", methods=["GET", "POST"])
def index():
    initial_dir = paths.initial_dir()
    error: Optional[str] = None
    user_data_out: Optional[str] = None
    meta_data_out: Optional[str] = None
    output_from_disk = False

    if request.method == "POST":
        action = request.form.get("action") or "generate"
        form = form_from_request()

        if action == "save_prefs":
            persistence.save_preferences(form)
            return redirect(url_for("index", prefs_saved="1"))

        if action == "clear_prefs":
            persistence.clear_preferences()
            return redirect(url_for("index", prefs_cleared="1"))

        if action == "generate":
            gen_err = builder.validate_generate(form)
            if gen_err:
                error = gen_err
            else:
                try:
                    user_data_out = builder.build_user_data_yaml(form)
                    meta_data_out = builder.build_meta_data_text(form)
                    paths.write_output_files(user_data_out, meta_data_out)
                except Exception as exc:  # noqa: BLE001
                    error = str(exc)

        defaults = dict(form)
        if error is None and action == "generate":
            defaults["password_plain"] = ""
    else:
        defaults, load_err = load_initial_defaults(initial_dir)
        error = load_err
        ud_disk, md_disk = paths.read_output_files_if_present()
        if ud_disk is not None and md_disk is not None:
            user_data_out = ud_disk
            meta_data_out = md_disk
            output_from_disk = True
    late_users_rows = late_users.late_users_for_template(defaults.get("late_users") or [])
    late_user_slots = list(range(max(6, len(late_users_rows) + 2)))
    locale_choices = options.locale_select_choices(str(defaults.get("locale") or ""))
    keyboard_choices = options.keyboard_select_choices(str(defaults.get("keyboard_layout") or ""))
    iface_choices = options.iface_select_choices(str(defaults.get("iface") or ""))
    iface2_choices = options.iface_select_choices(str(defaults.get("iface2") or ""))

    prefs_saved_flag = request.args.get("prefs_saved") if request.method == "GET" else None
    prefs_cleared_flag = request.args.get("prefs_cleared") if request.method == "GET" else None

    html = render_template(
        "index.html",
        defaults=defaults,
        late_users_rows=late_users_rows,
        late_user_slots=late_user_slots,
        locale_choices=locale_choices,
        keyboard_choices=keyboard_choices,
        iface_choices=iface_choices,
        iface2_choices=iface2_choices,
        error=error,
        user_data_out=user_data_out,
        meta_data_out=meta_data_out,
        output_from_disk=output_from_disk,
        prefs_saved=prefs_saved_flag == "1",
        prefs_cleared=prefs_cleared_flag == "1",
    )
    response = make_response(html)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


def run_flask(host: str, port: int, debug: bool) -> None:
    app.run(host=host, port=port, debug=debug, use_reloader=False, threaded=True)


if __name__ == "__main__":
    port = 5000
    debug = "false"  # true / false option
    browser_only = True  # True

    _tpl_dir = Path(app.root_path) / "templates"
    _index = _tpl_dir / "index.html"
    print(f"[cloudinit-builder] Flask root_path: {app.root_path}", flush=True)
    print(f"[cloudinit-builder] Templates dir: {_tpl_dir.resolve()}", flush=True)
    print(f"[cloudinit-builder] index.html: {_index.resolve()} exists={_index.is_file()}", flush=True)
    if _index.is_file():
        print(f"[cloudinit-builder] index.html bytes: {_index.stat().st_size}", flush=True)

    def _main_flag(label: str, raw: str) -> bool:
        v = raw.strip().lower()
        if v == "true":
            return True
        if v == "false":
            return False
        raise ValueError(f'{label} must be "true" or "false", got {raw!r}')

    listen_host = "0.0.0.0"

    if browser_only is True:
        app.run(host=listen_host, port=port, debug=debug, use_reloader=False)
    else:
        threading.Thread(
            target=run_flask,
            kwargs={"host": listen_host, "port": port, "debug": debug},
            daemon=True,
        ).start()
        deadline = time.monotonic() + 15.0
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=0.25)
                break
            except OSError:
                time.sleep(0.05)
        try:
            import webview
        except ImportError:
            print("pywebview not installed; open http://127.0.0.1:5000 a browser.")
            print("Install desktop shell: uv pip install 'cloudinit-builder[desktop]'")
            threading.Event().wait()
        else:
            # Cache-bust WebView2 disk cache so template/CSS edits show up without stale pages.
            webview.create_window(
                "Cloud-init builder",
                f"http://127.0.0.1:{port}/?v={int(time.time())}",
            )
            webview.start()

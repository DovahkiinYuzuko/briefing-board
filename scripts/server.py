#!/usr/bin/env python3
"""
Briefing Board Lightweight Local Server
- Serves static dashboard files (HTML, CSS, JS)
- Handles GET/POST /api/settings (hybrid: global user_settings.json + project portal_settings.json)
- Handles GET /api/decision & POST /api/save to read/write decision.toml and i18n summary.md
- Handles POST /api/shutdown and manages .server.pid lifecycle
- Enables multi-device access (desktop, mobile/smartphone on local network)
"""

import argparse
import json
import os
import socket
import sys
import threading
import tomllib
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from briefing_common import (
    get_default_port,
    get_skill_root,
    load_locales,
    load_user_settings,
    save_user_settings,
    translate,
)

USER_SETTING_KEYS = {"language", "view_mode"}
PORTAL_SETTING_KEYS = {"sort_key", "sort_order", "search_query"}


def generate_summary_markdown(toml_text: str, target_dir: Path) -> Path:
    """Generate a localized human-readable summary.md from decision TOML content."""
    try:
        data = tomllib.loads(toml_text)
    except Exception:
        data = None

    skill_root = get_skill_root()
    user_settings = load_user_settings(skill_root)
    lang = str(user_settings.get("language") or "en")
    locales = load_locales(skill_root / "locales")
    t = lambda key, **kw: translate(locales, lang, key, **kw)

    lines = [t("summary_title") + "\n"]

    if isinstance(data, dict):
        date_str = data.get("updated_at") or data.get("date") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        status = str(data.get("decision_status", "DRAFT")).upper()
        overall = str(data.get("overall_action", "pending")).upper()
        notes = str(data.get("global_notes") or data.get("user_notes") or data.get("overall_comment") or "").strip()

        lines.append(f"- **{t('summary_updated_at')}**: {date_str}")
        lines.append(f"- **{t('summary_status')}**: `{status}`")
        lines.append(f"- **{t('summary_overall')}**: `{overall}`")
        if notes:
            lines.append(f"- **{t('summary_global_notes')}**:")
            for note_line in notes.splitlines():
                lines.append(f"  > {note_line}")
        lines.append("\n---\n")

        lines.append(t("summary_agenda_heading") + "\n")
        decisions = data.get("decisions", [])
        if isinstance(decisions, list) and decisions:
            for item in decisions:
                item_id = item.get("id", "unknown")
                action = str(item.get("action", "pending")).upper()
                opts = item.get("selected_options", [])
                opt_str = ", ".join(opts) if opts else t("summary_no_options")
                cmt = str(item.get("comment", "")).strip()

                lines.append(f"### `{item_id}`: **{action}**")
                lines.append(f"- **{t('summary_selected_options')}**: {opt_str}")
                if cmt:
                    lines.append(f"- **{t('summary_comment')}**: {cmt}")
                lines.append("")

        proposed = data.get("proposed_agendas", [])
        if isinstance(proposed, list) and proposed:
            lines.append("---\n")
            lines.append(t("summary_proposed_heading") + "\n")
            for p_item in proposed:
                if isinstance(p_item, dict):
                    p_title = str(p_item.get("title", "")).strip()
                    p_detail = str(p_item.get("detail", "")).strip()
                    if p_title:
                        lines.append(f"- **{p_title}**" + (f": {p_detail}" if p_detail else ""))
                elif str(p_item).strip():
                    lines.append(f"- {str(p_item).strip()}")
            lines.append("")
    else:
        lines.append("```toml")
        lines.append(toml_text.strip())
        lines.append("```")

    summary_content = "\n".join(lines)
    summary_file = Path(target_dir).resolve() / "summary.md"
    summary_file.write_text(summary_content, encoding="utf-8")
    return summary_file


def get_local_ip() -> str:
    """Get the local network IP address for smartphone/tablet access."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip


def resolve_serve_directory(raw_dir=None) -> Path:
    """
    Strictly determine the briefing directory to serve under the current project.
    Never falls back to skill installation directories or arbitrary parent roots.
    """
    if raw_dir:
        candidate = Path(raw_dir).resolve()
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"Specified serve directory does not exist: {candidate}")

    cwd = Path.cwd().resolve()
    if (cwd / "briefing-board").is_dir():
        return (cwd / "briefing-board").resolve()
    if cwd.name == "briefing-board" and (cwd / "wip").is_dir():
        return cwd

    raise FileNotFoundError(
        f"No 'briefing-board' directory found in {cwd}. "
        "Run new_briefing.py first or specify --dir."
    )


def _load_portal_settings(root_resolved: Path) -> dict:
    defaults = {
        "sort_key": "number",
        "sort_order": "desc",
        "search_query": "",
    }
    settings_file = root_resolved / "portal_settings.json"
    if settings_file.exists():
        try:
            loaded = json.loads(settings_file.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                defaults.update(loaded)
        except (json.JSONDecodeError, OSError):
            pass
    return defaults


def _save_portal_settings(root_resolved: Path, updates: dict) -> dict:
    current = _load_portal_settings(root_resolved)
    for k, v in updates.items():
        if v is not None:
            current[k] = v
    settings_file = root_resolved / "portal_settings.json"
    settings_file.write_text(json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return current


class BriefingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, shutdown_callback=None, **kwargs):
        self.shutdown_callback = shutdown_callback
        serve_dir = directory or str(resolve_serve_directory())
        super().__init__(*args, directory=str(Path(serve_dir).resolve()), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def _resolve_safe_target(self, raw_target: str) -> Path:
        """Resolve relative target path within serve directory and guard against traversal."""
        root_resolved = Path(self.directory).resolve()
        normalized = raw_target.replace("\\", "/").lstrip("/")
        for prefix in (f"{root_resolved.name}/", "briefing-board/", "docs/briefing/"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix):]
                break

        target_file = (root_resolved / normalized).resolve()
        try:
            target_file.relative_to(root_resolved)
        except ValueError:
            raise PermissionError(f"Directory traversal prohibited: {raw_target}")
        return target_file

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/decision":
            try:
                qs = parse_qs(parsed.query)
                raw_target = (qs.get("target_path") or ["decision.toml"])[0]
                target_file = self._resolve_safe_target(raw_target)
                if not target_file.exists():
                    self._send_json(200, {"status": "ok", "exists": False, "data": None})
                    return

                content = target_file.read_text(encoding="utf-8")
                try:
                    if target_file.suffix.lower() == ".json":
                        parsed_data = json.loads(content)
                    else:
                        parsed_data = tomllib.loads(content)
                except Exception as e:
                    self._send_json(500, {"status": "error", "message": f"Parse failed: {e}"})
                    return

                self._send_json(200, {"status": "ok", "exists": True, "data": parsed_data})
            except PermissionError as e:
                self._send_json(403, {"status": "error", "message": str(e)})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        if parsed.path == "/api/settings":
            try:
                root_resolved = Path(self.directory).resolve()
                user_cfg = load_user_settings(get_skill_root())
                portal_cfg = _load_portal_settings(root_resolved)
                merged = {**portal_cfg, **user_cfg}
                self._send_json(200, {"status": "ok", "settings": merged})
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/save":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")

                try:
                    payload = json.loads(body)
                    decision_content = payload.get("toml") or payload.get("yaml") or payload.get("content") or body
                    raw_target = payload.get("target_path") or payload.get("filename", "decision.toml")
                except json.JSONDecodeError:
                    decision_content = body
                    raw_target = "decision.toml"

                target_file = self._resolve_safe_target(raw_target)
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(decision_content, encoding="utf-8")
                print(f"[SUCCESS] Saved decision to: {target_file}", flush=True)

                summary_file = generate_summary_markdown(decision_content, target_file.parent)
                print(f"[SUCCESS] Generated summary report to: {summary_file}", flush=True)

                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "message": "Saved successfully",
                        "path": str(target_file),
                        "summary_path": str(summary_file),
                    },
                )
            except Exception as e:
                print(f"[ERROR] Failed to save decision payload: {e}", file=sys.stderr, flush=True)
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        if parsed.path == "/api/settings":
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_length).decode("utf-8")
                incoming = json.loads(body)
                if not isinstance(incoming, dict):
                    self._send_json(400, {"status": "error", "message": "Settings payload must be a JSON object"})
                    return

                root_resolved = Path(self.directory).resolve()
                user_updates = {k: v for k, v in incoming.items() if k in USER_SETTING_KEYS}
                portal_updates = {k: v for k, v in incoming.items() if k in PORTAL_SETTING_KEYS}

                user_cfg = (
                    save_user_settings(user_updates, get_skill_root())
                    if user_updates
                    else load_user_settings(get_skill_root())
                )
                portal_cfg = (
                    _save_portal_settings(root_resolved, portal_updates)
                    if portal_updates
                    else _load_portal_settings(root_resolved)
                )
                merged = {**portal_cfg, **user_cfg}
                print(f"[SUCCESS] Updated settings (user={list(user_updates.keys())}, portal={list(portal_updates.keys())})", flush=True)
                self._send_json(200, {"status": "ok", "settings": merged})
            except Exception as e:
                print(f"[ERROR] Failed to save settings: {e}", file=sys.stderr, flush=True)
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        if parsed.path == "/api/shutdown":
            self._send_json(200, {"status": "ok", "message": "Server shutting down"})
            print("[INFO] Shutdown requested via POST /api/shutdown", flush=True)
            if self.shutdown_callback:
                threading.Thread(target=self.shutdown_callback, daemon=True).start()
            return

        self.send_error(404, "Endpoint not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class ExclusiveHTTPServer(HTTPServer):
    """HTTPServer with robust port exclusivity across Windows and Unix."""

    def server_bind(self):
        if sys.platform == "win32":
            self.allow_reuse_address = False
            if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
                try:
                    self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
                except OSError as e:
                    print(f"[WARNING] Could not set SO_EXCLUSIVEADDRUSE: {e}", file=sys.stderr, flush=True)
        else:
            self.allow_reuse_address = True
        super().server_bind()


def run_server(serve_dir=None, port=None):
    host = "0.0.0.0"
    local_ip = get_local_ip()
    target_dir = resolve_serve_directory(serve_dir)
    base_port = port if port is not None else get_default_port(target_dir)

    httpd_holder = {"server": None}

    def request_shutdown():
        srv = httpd_holder["server"]
        if srv is not None:
            srv.shutdown()

    def handler(*args, **kwargs):
        BriefingHandler(*args, directory=str(target_dir), shutdown_callback=request_shutdown, **kwargs)

    current_port = base_port
    httpd = None
    while current_port < base_port + 20:
        try:
            httpd = ExclusiveHTTPServer((host, current_port), handler)
            break
        except OSError:
            print(f"[INFO] Port {current_port} is busy or in use, trying {current_port + 1}...", flush=True)
            current_port += 1

    if not httpd:
        print(f"[ERROR] Could not bind to any port from {base_port} to {base_port + 20}", file=sys.stderr, flush=True)
        sys.exit(1)

    httpd_holder["server"] = httpd

    pid_file = target_dir / ".server.pid"
    try:
        pid_file.write_text(
            json.dumps({"pid": os.getpid(), "port": current_port, "dir": str(target_dir)}, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass

    local_url = f"http://localhost:{current_port}/"
    mobile_url = f"http://{local_ip}:{current_port}/"

    print("=" * 60, flush=True)
    print("  Briefing Board Server is running!", flush=True)
    print(f"  - Local (PC):    {local_url}", flush=True)
    print(f"  - Mobile/LAN:    {mobile_url}", flush=True)
    print(f"  - Session Dir:   {target_dir}", flush=True)
    print("  - Auto-Save API: POST /api/save -> decision.toml", flush=True)
    print("  - Shutdown API:  POST /api/shutdown", flush=True)
    print("=" * 60, flush=True)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.", flush=True)
    finally:
        httpd.server_close()
        try:
            if pid_file.exists():
                pid_file.unlink()
        except OSError:
            pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Briefing Board Server")
    parser.add_argument("--dir", "-d", default=None, help="Directory to serve (defaults to ./briefing-board)")
    parser.add_argument("--port", "-p", type=int, default=None, help="Port to listen on (default: deterministic per project)")
    args = parser.parse_args()

    try:
        run_server(serve_dir=args.dir, port=args.port)
    except FileNotFoundError as e:
        print(f"[ERROR] {e}", file=sys.stderr, flush=True)
        sys.exit(1)

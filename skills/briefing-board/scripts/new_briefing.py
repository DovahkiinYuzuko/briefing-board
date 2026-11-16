#!/usr/bin/env python3
"""
new_briefing.py - Briefing Board Session Generator & Schema Validator
- Validates input briefing TOML/JSON schema using Python standard library (tomllib / json)
- Creates briefing-board/wip/NNN-YYYY-MM-DD-[topic-name]/ session directory
- Generates briefing-board/.gitignore to avoid polluting project git tracking
- Copies pre-built DADS assets (resources/) and bundles locales_data.js
- Builds briefing_data.js and updates the Kanban portal
- Automatically launches local server (unless --no-serve)
"""

import argparse
import html
import json
import re
import shutil
import sys
import tomllib
from datetime import datetime
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from briefing_common import (
    build_locales_js,
    get_default_port,
    get_skill_root,
    load_locales,
    load_user_settings,
    parse_structured_file,
    translate,
)


def validate_schema(data):
    """Validate schema adherence according to references/schema_specification.md."""
    errors = []
    if not isinstance(data, dict):
        return ["Root element must be a table/dictionary."]

    if "title" not in data or not str(data["title"]).strip():
        errors.append("Missing required top-level field: 'title'")

    if "agenda" not in data or not isinstance(data["agenda"], list) or len(data["agenda"]) == 0:
        errors.append("Missing or empty required top-level list: 'agenda'")
        return errors

    seen_ids = set()
    allowed_actions = {"pending", "approve", "revise", "investigate", "cancel"}

    for idx, item in enumerate(data["agenda"]):
        prefix = f"agenda[{idx}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix} must be a table/dictionary.")
            continue

        item_id = item.get("id")
        if not item_id or not str(item_id).strip():
            errors.append(f"{prefix} is missing required field: 'id'")
        elif item_id in seen_ids:
            errors.append(f"{prefix} has duplicate id: '{item_id}'")
        else:
            seen_ids.add(item_id)

        for req_field in ("domain", "title", "summary"):
            if not item.get(req_field):
                errors.append(f"{prefix} is missing required field: '{req_field}'")

        if "defaultAction" in item and item["defaultAction"] not in allowed_actions:
            errors.append(
                f"{prefix}.defaultAction '{item['defaultAction']}' is invalid. "
                f"Allowed values: {sorted(allowed_actions)}"
            )

        if "history" in item and not isinstance(item["history"], list):
            errors.append(f"{prefix}.history must be a list.")

        if "options" in item:
            if not isinstance(item["options"], list):
                errors.append(f"{prefix}.options must be a list.")
            else:
                for opt_idx, opt in enumerate(item["options"]):
                    if not isinstance(opt, dict) or not opt.get("id") or not opt.get("label"):
                        errors.append(f"{prefix}.options[{opt_idx}] must have 'id' and 'label'.")

    return errors


def ensure_output_gitignore(output_root: Path):
    """Ensure briefing-board/.gitignore ignores generated session artifacts."""
    output_root.mkdir(parents=True, exist_ok=True)
    gitignore_path = output_root / ".gitignore"
    if not gitignore_path.exists():
        gitignore_path.write_text("*\n!.gitignore\n", encoding="utf-8")


def get_next_session_number(output_root: Path) -> int:
    """Find the next session number (e.g. 001, 002) by scanning wip/, done/, and root."""
    max_num = 0
    pattern = re.compile(r"^(\d{3})-")
    if output_root.exists():
        for subdir in ["wip", "done"]:
            d = output_root / subdir
            if d.exists():
                for p in d.iterdir():
                    if p.is_dir():
                        m = pattern.match(p.name)
                        if m:
                            max_num = max(max_num, int(m.group(1)))
        for p in output_root.iterdir():
            if p.is_dir() and p.name not in ["wip", "done"]:
                m = pattern.match(p.name)
                if m:
                    max_num = max(max_num, int(m.group(1)))
    return max_num + 1


def sanitize_topic_name(topic: str) -> str:
    """Sanitize topic string for safe folder naming."""
    topic = topic.strip().lower()
    topic = re.sub(r"[\s_]+", "-", topic)
    topic = re.sub(r"[^\w\-]", "", topic)
    return topic or "session"


def _extract_legacy_yaml_fields(text: str, keys: tuple[str, ...]) -> dict:
    """Minimal regex fallback for legacy archived YAML sessions (no PyYAML dependency)."""
    extracted = {}
    for key in keys:
        m = re.search(rf'^{re.escape(key)}:\s*"([^"\n]*)"', text, flags=re.MULTILINE)
        if not m:
            m = re.search(rf"^{re.escape(key)}:\s*'([^'\n]*)'", text, flags=re.MULTILINE)
        if not m:
            m = re.search(rf"^{re.escape(key)}:\s*([^\n#]+)", text, flags=re.MULTILINE)
        if m:
            extracted[key] = m.group(1).strip()
    return extracted


def get_session_metadata(session_dir: Path) -> dict:
    """Extract metadata (title, subtitle, status) from TOML or legacy YAML session folders."""
    data = {}
    briefing_toml = session_dir / "briefing.toml"
    briefing_yaml = session_dir / "briefing.yaml"

    if briefing_toml.exists():
        try:
            data = tomllib.loads(briefing_toml.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    elif briefing_yaml.exists():
        try:
            data = _extract_legacy_yaml_fields(
                briefing_yaml.read_text(encoding="utf-8"),
                ("title", "subtitle"),
            )
        except Exception:
            data = {}

    status = "WIP"
    decision_toml = session_dir / "decision.toml"
    decision_yaml = session_dir / "decision.yaml"
    dec_data = {}

    if decision_toml.exists():
        try:
            dec_data = tomllib.loads(decision_toml.read_text(encoding="utf-8"))
        except Exception:
            dec_data = {}
    elif decision_yaml.exists():
        try:
            dec_data = _extract_legacy_yaml_fields(
                decision_yaml.read_text(encoding="utf-8"),
                ("decision_status", "overall_action"),
            )
        except Exception:
            dec_data = {}

    if isinstance(dec_data, dict) and dec_data:
        dec_status = str(dec_data.get("decision_status", "")).upper()
        overall_action = str(dec_data.get("overall_action", "")).upper()
        if dec_status == "DRAFT":
            status = "DRAFT"
        elif overall_action:
            status = overall_action

    return {
        "folder": session_dir.name,
        "title": data.get("title", session_dir.name),
        "subtitle": data.get("subtitle", ""),
        "status": status,
        "has_summary": (session_dir / "summary.md").exists(),
    }


def write_locales_bundle(target_dir: Path, locales_dir: Path, skill_root: Path):
    """Write locales_data.js with localization dictionaries and initial user settings."""
    user_settings = load_user_settings(skill_root)
    bundle = build_locales_js(locales_dir)
    bundle += (
        f"window.BRIEFING_INITIAL_SETTINGS = "
        f"{json.dumps(user_settings, indent=2, ensure_ascii=False)};\n"
    )
    (target_dir / "locales_data.js").write_text(bundle, encoding="utf-8")


def build_kanban_portal(output_root: Path, resources_dir: Path, locales_dir: Path, skill_root: Path):
    """Generate DADS-compliant kanban portal index.html in output_root."""
    ensure_output_gitignore(output_root)

    wip_sessions = []
    done_sessions = []
    wip_dir = output_root / "wip"
    done_dir = output_root / "done"

    if wip_dir.exists():
        for p in sorted(wip_dir.iterdir(), reverse=True):
            if p.is_dir() and not p.name.startswith("."):
                wip_sessions.append(get_session_metadata(p))

    if done_dir.exists():
        for p in sorted(done_dir.iterdir(), reverse=True):
            if p.is_dir() and not p.name.startswith("."):
                done_sessions.append(get_session_metadata(p))

    style_src = resources_dir / "style.css"
    if style_src.exists():
        shutil.copy2(style_src, output_root / "style.css")

    write_locales_bundle(output_root, locales_dir, skill_root)

    settings_file = output_root / "portal_settings.json"
    if not settings_file.exists():
        default_settings = {
            "sort_key": "number",
            "sort_order": "desc",
            "search_query": "",
        }
        settings_file.write_text(json.dumps(default_settings, indent=2, ensure_ascii=False), encoding="utf-8")

    locales = load_locales(locales_dir)
    en_t = lambda key: html.escape(translate(locales, "en", key))

    status_map = {
        "APPROVE": ("status-badge-approve", "portal_badge_approve"),
        "PARTIAL": ("status-badge-partial", "portal_badge_partial"),
        "REVISE_NEEDED": ("status-badge-revise", "portal_badge_revise"),
        "REVISE": ("status-badge-revise", "portal_badge_revise"),
        "INVESTIGATE": ("status-badge-revise", "portal_badge_revise"),
        "DRAFT": ("status-badge-draft", "portal_badge_draft"),
        "CANCEL": ("status-badge-cancel", "portal_badge_cancel"),
    }

    def render_cards(sessions, subpath):
        if not sessions:
            return f'<div class="kanban-empty-notice" data-i18n="portal_empty_notice">{en_t("portal_empty_notice")}</div>'
        html_cards = []
        for s in sessions:
            st = s["status"]
            cls, i18n_key = status_map.get(st, ("status-badge-wip", "portal_badge_wip"))
            badge = f'<span class="domain-tag {cls}" data-i18n="{i18n_key}">{en_t(i18n_key)}</span>'

            safe_folder = html.escape(s["folder"])
            safe_title = html.escape(str(s["title"]))
            safe_subtitle = html.escape(str(s["subtitle"]))
            summary_link = (
                f' · <a href="{subpath}/{safe_folder}/summary.md" class="kanban-card-summary-link" '
                f'data-i18n="portal_open_summary">{en_t("portal_open_summary")}</a>'
                if s["has_summary"]
                else ""
            )
            search_corpus = html.escape(f"{s['folder']} {s['title']} {s['subtitle']} {st}".lower())

            card = f'''
            <article class="kanban-session-card" data-folder="{safe_folder}" data-title="{safe_title}" data-status="{html.escape(st)}" data-search="{search_corpus}">
              <div class="kanban-card-header">
                <span class="kanban-card-date">{safe_folder}</span>
                {badge}
              </div>
              <h3 class="kanban-card-title">
                <a href="{subpath}/{safe_folder}/index.html">{safe_title}</a>
              </h3>
              {f'<p class="kanban-card-desc">{safe_subtitle}</p>' if safe_subtitle else ''}
              <div class="kanban-card-footer">
                <span><a href="{subpath}/{safe_folder}/index.html" class="kanban-card-action-link" data-i18n="portal_open_dashboard">{en_t("portal_open_dashboard")}</a>{summary_link}</span>
              </div>
            </article>'''
            html_cards.append(card)
        return "\n".join(html_cards)

    wip_cards_html = render_cards(wip_sessions, "wip")
    done_cards_html = render_cards(done_sessions, "done")

    template_path = resources_dir / "portal.html"
    if not template_path.exists():
        print("[WARNING] portal.html template not found in resources/", file=sys.stderr)
        return

    template_content = template_path.read_text(encoding="utf-8")
    portal_html = template_content.replace("{{WIP_COUNT}}", str(len(wip_sessions)))
    portal_html = portal_html.replace("{{DONE_COUNT}}", str(len(done_sessions)))
    portal_html = portal_html.replace("{{WIP_CARDS}}", wip_cards_html)
    portal_html = portal_html.replace("{{DONE_CARDS}}", done_cards_html)

    portal_file = output_root / "index.html"
    portal_file.write_text(portal_html, encoding="utf-8")
    print(f"  [SUCCESS] Updated DADS Kanban Portal at: {portal_file}", flush=True)


def archive_session(session_arg: str, output_root: Path, resources_dir: Path, locales_dir: Path, skill_root: Path):
    """Validate completion of a WIP session, move it to done/, and rebuild the Kanban portal."""
    wip_root = (output_root / "wip").resolve()
    done_root = (output_root / "done").resolve()

    candidate = Path(session_arg)
    session_dir = candidate.resolve() if candidate.is_dir() else (wip_root / session_arg).resolve()

    if not session_dir.is_dir() or session_dir.parent != wip_root:
        print(f"[ERROR] Session not found under wip/: {session_dir}", file=sys.stderr, flush=True)
        sys.exit(1)

    decision_path = session_dir / "decision.toml"
    if not decision_path.is_file():
        print(f"[ERROR] Cannot archive session without decision.toml: {decision_path}", file=sys.stderr, flush=True)
        sys.exit(1)

    try:
        decision_data = tomllib.loads(decision_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[ERROR] Failed to parse decision.toml: {e}", file=sys.stderr, flush=True)
        sys.exit(1)

    decision_status = str(decision_data.get("decision_status", "")).upper()
    overall_action = str(decision_data.get("overall_action", "")).lower()
    allowed_actions = {"approve", "partial", "cancel"}

    if decision_status != "COMPLETED" or overall_action not in allowed_actions:
        print(
            f"[ERROR] Cannot archive incomplete session '{session_dir.name}': "
            f"decision_status='{decision_status}', overall_action='{overall_action}'. "
            "Requires decision_status='COMPLETED' and overall_action in {approve, partial, cancel}.",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)

    done_root.mkdir(parents=True, exist_ok=True)
    dest_dir = done_root / session_dir.name
    if dest_dir.exists():
        print(f"[ERROR] Destination already exists in done/: {dest_dir}", file=sys.stderr, flush=True)
        sys.exit(1)

    print(f"[1/2] Archiving completed session to done/: {dest_dir}", flush=True)
    shutil.move(str(session_dir), str(dest_dir))

    print("[2/2] Rebuilding DADS Kanban Portal...", flush=True)
    build_kanban_portal(output_root, resources_dir, locales_dir, skill_root)
    print(f"[SUCCESS] Archived '{session_dir.name}' and updated Kanban Portal.", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Generate Briefing Board Session Dashboard or Rebuild Kanban Portal")
    parser.add_argument("--rebuild-portal", action="store_true", help="Only rebuild Kanban portal (index.html) from existing sessions")
    parser.add_argument("--archive", default=None, help="Archive a COMPLETED session from wip/ to done/ and rebuild Kanban portal")
    parser.add_argument("--input", "-i", default=None, help="Path to input briefing TOML/JSON file")
    parser.add_argument("--topic", "-t", default=None, help="Topic slug for session folder (e.g. loop-safety)")
    parser.add_argument("--title", default=None, help="Override title of the briefing")
    parser.add_argument("--output", "-o", default=None, help="Root directory for briefing outputs (default: briefing-board)")
    parser.add_argument("--update-session", default=None, help="Existing session folder name or path to update in-place (preserves previous decision)")
    parser.add_argument("--port", "-p", type=int, default=None, help="Server port (default: deterministic per project in 8899..8998)")
    parser.add_argument("--no-serve", action="store_true", help="Only build session files without starting local server")

    args = parser.parse_args()

    skill_root = get_skill_root()
    resources_dir = skill_root / "resources"
    locales_dir = skill_root / "locales"

    if not resources_dir.exists():
        print(f"[ERROR] Resources directory not found at: {resources_dir}", file=sys.stderr)
        sys.exit(1)

    output_root = Path(args.output).resolve() if args.output else (Path.cwd() / "briefing-board").resolve()
    ensure_output_gitignore(output_root)

    if args.archive:
        archive_session(args.archive, output_root, resources_dir, locales_dir, skill_root)
        return

    if args.rebuild_portal:
        print("[1/1] Rebuilding DADS Kanban Portal...", flush=True)
        try:
            build_kanban_portal(output_root, resources_dir, locales_dir, skill_root)
            print("[SUCCESS] Kanban Portal rebuild complete.", flush=True)
        except Exception as e:
            print(f"[ERROR] Failed to rebuild Kanban portal: {e}", file=sys.stderr, flush=True)
            sys.exit(1)
        return

    if not args.input:
        parser.error("Either --input, --archive, or --rebuild-portal must be specified.")

    print(f"[1/4] Loading and validating: {args.input}")
    try:
        data = parse_structured_file(Path(args.input))
    except Exception as e:
        print(f"[ERROR] Failed to load input: {e}", file=sys.stderr)
        sys.exit(1)

    errors = validate_schema(data)
    if errors:
        print("[ERROR] Schema validation failed with the following issues:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    print("  Schema validation PASSED.")

    if args.title:
        data["title"] = args.title

    if args.update_session:
        candidate = Path(args.update_session)
        if candidate.is_dir():
            session_dir = candidate.resolve()
        else:
            session_dir = (output_root / "wip" / args.update_session).resolve()
        session_folder_name = session_dir.name
        session_dir.mkdir(parents=True, exist_ok=True)
        print(f"[2/4] Updating existing session directory: {session_dir}")
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        topic_slug = sanitize_topic_name(args.topic or Path(args.input).stem)
        session_num = get_next_session_number(output_root)
        session_folder_name = f"{session_num:03d}-{today_str}-{topic_slug}"
        session_dir = output_root / "wip" / session_folder_name
        session_dir.mkdir(parents=True, exist_ok=True)
        print(f"[2/4] Target session directory: {session_dir}")

    print("[3/4] Deploying static DADS template assets and localization bundle...")
    for asset_name in ["index.html", "style.css", "app.js"]:
        src = resources_dir / asset_name
        dst = session_dir / asset_name
        if src.exists():
            shutil.copy2(src, dst)
        else:
            print(f"[WARNING] Resource missing: {src}", file=sys.stderr)

    write_locales_bundle(session_dir, locales_dir, skill_root)

    # Save raw input file as briefing.toml (or briefing.json if json input)
    src_input = Path(args.input)
    target_input_name = "briefing.json" if src_input.suffix.lower() == ".json" else "briefing.toml"
    shutil.copy2(src_input, session_dir / target_input_name)

    rel_path_str = f"{output_root.name}/wip/{session_folder_name}/decision.toml"
    data["saveNoticeFilePath"] = rel_path_str

    existing_decision_toml = session_dir / "decision.toml"
    if existing_decision_toml.exists():
        try:
            prev_dec = tomllib.loads(existing_decision_toml.read_text(encoding="utf-8"))
            if isinstance(prev_dec, dict):
                data["previousDecision"] = prev_dec
        except Exception as e:
            print(f"[WARNING] Could not parse existing decision.toml for embedding: {e}", file=sys.stderr)

    js_content = (
        f"/**\n * Auto-generated Briefing Board Data\n * Generated: {datetime.now().isoformat()}\n */\n"
        f"window.BRIEFING_DATA = {json.dumps(data, indent=2, ensure_ascii=False)};\n"
    )
    (session_dir / "briefing_data.js").write_text(js_content, encoding="utf-8")
    print("  Built briefing_data.js successfully.", flush=True)

    index_html_path = session_dir / "index.html"
    print(f"\n[SUCCESS] Briefing Board generated at:\n  {index_html_path}", flush=True)

    print("\n[4/5] Updating DADS Kanban Portal...", flush=True)
    try:
        build_kanban_portal(output_root, resources_dir, locales_dir, skill_root)
    except Exception as e:
        print(f"[WARNING] Failed to update Kanban portal: {e}", file=sys.stderr, flush=True)

    target_port = args.port if args.port is not None else get_default_port(output_root)

    if not args.no_serve:
        print("\n[5/5] Starting Briefing Board Server automatically...", flush=True)
        session_url = f"http://localhost:{target_port}/wip/{session_folder_name}/"
        portal_url = f"http://localhost:{target_port}/"
        print(f"  - Direct Session URL: {session_url}", flush=True)
        print(f"  - Kanban Portal URL:  {portal_url}\n", flush=True)

        try:
            import server
            server.run_server(serve_dir=str(output_root), port=target_port)
        except Exception as e:
            print(f"[ERROR] Failed to start server: {e}", file=sys.stderr, flush=True)
            print(f"You can open the dashboard manually:\n  file:///{index_html_path}", flush=True)
    else:
        print(f"Server omitted (--no-serve). Recommended port for this project: {target_port}", flush=True)
        print(f"Open manually:\n  file:///{index_html_path}", flush=True)


if __name__ == "__main__":
    main()

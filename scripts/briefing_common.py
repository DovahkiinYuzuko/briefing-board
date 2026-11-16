#!/usr/bin/env python3
"""
briefing_common.py - Shared utilities for Briefing Board scripts.
Provides dynamic skill root resolution, TOML/JSON parsing, user settings persistence,
localization dictionary loading, and deterministic port calculation.
"""

import json
import tomllib
import zlib
from pathlib import Path
from typing import Any, Dict, Optional

BASE_PORT = 8899
PORT_RANGE = 100

DEFAULT_USER_SETTINGS: Dict[str, Any] = {
    "language": "en",
    "view_mode": "auto",
}


def get_skill_root() -> Path:
    """Resolve the briefing-board skill root dynamically without hardcoded paths."""
    return Path(__file__).resolve().parent.parent


def get_default_port(output_root: Path) -> int:
    """Compute a deterministic port offset (8899..8998) from the project briefing directory."""
    resolved = str(output_root.resolve()).encode("utf-8")
    offset = zlib.crc32(resolved) % PORT_RANGE
    return BASE_PORT + offset


def parse_structured_file(filepath: Path) -> Dict[str, Any]:
    """Parse a TOML or JSON file using Python standard library (tomllib / json)."""
    if not filepath.exists():
        raise FileNotFoundError(f"Input file not found: {filepath}")

    content = filepath.read_text(encoding="utf-8")
    suffix = filepath.suffix.lower()

    if suffix == ".json":
        data = json.loads(content)
    elif suffix == ".toml":
        data = tomllib.loads(content)
    else:
        # Try TOML first, then JSON as fallback
        try:
            data = tomllib.loads(content)
        except tomllib.TOMLDecodeError:
            data = json.loads(content)

    if not isinstance(data, dict):
        raise ValueError("Root element must be a table/dictionary.")
    return data


def load_locales(locales_dir: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load all localization JSON dictionaries under locales/."""
    target_dir = locales_dir or (get_skill_root() / "locales")
    locales: Dict[str, Dict[str, Any]] = {}
    if not target_dir.exists():
        return locales

    for json_file in sorted(target_dir.glob("*.json")):
        try:
            content = json.loads(json_file.read_text(encoding="utf-8"))
            if isinstance(content, dict):
                code = str(content.get("_meta", {}).get("code") or json_file.stem)
                locales[code] = content
        except (json.JSONDecodeError, OSError):
            continue
    return locales


def build_locales_js(locales_dir: Optional[Path] = None) -> str:
    """Generate locales_data.js content bundling all locale JSON dictionaries."""
    locales = load_locales(locales_dir)
    payload = json.dumps(locales, indent=2, ensure_ascii=False)
    return (
        "/**\n"
        " * Auto-generated Briefing Board Localization Bundle\n"
        " */\n"
        f"window.BRIEFING_LOCALES = {payload};\n"
    )


def translate(locales: Dict[str, Dict[str, Any]], lang: str, key: str, **kwargs: Any) -> str:
    """Translate key using target_lang -> en -> key fallback cascade."""
    target_dict = locales.get(lang) or {}
    en_dict = locales.get("en") or {}
    raw = target_dict.get(key)
    if raw is None:
        raw = en_dict.get(key, key)
    text = str(raw)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def load_user_settings(skill_root: Optional[Path] = None) -> Dict[str, Any]:
    """Load global user settings from <skill_root>/user_settings.json, creating defaults if missing."""
    root = skill_root or get_skill_root()
    settings_path = root / "user_settings.json"
    settings = dict(DEFAULT_USER_SETTINGS)

    if not settings_path.exists():
        try:
            settings_path.write_text(
                json.dumps(settings, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass
        return settings

    try:
        loaded = json.loads(settings_path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            settings.update(loaded)
    except (json.JSONDecodeError, OSError):
        pass
    return settings


def save_user_settings(updates: Dict[str, Any], skill_root: Optional[Path] = None) -> Dict[str, Any]:
    """Merge and persist global user settings to <skill_root>/user_settings.json."""
    root = skill_root or get_skill_root()
    settings_path = root / "user_settings.json"
    current = load_user_settings(root)
    for k, v in updates.items():
        if v is not None:
            current[k] = v
    settings_path.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return current

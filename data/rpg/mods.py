"""Runtime mod discovery for Weapon Blacksmith.

Mods are deliberately data-only.  They are discovered from ``data/mods`` on
startup, copied into a small ``mods.json`` registry for the launcher/UI, and
can contribute translations or additive content without importing Python.
"""
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - requirements installs PyYAML
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
MODS_DIR = ROOT / "data" / "mods"
REGISTRY_PATH = MODS_DIR / "mods.json"


def _read(path: Path) -> dict[str, Any]:
    if path.suffix.lower() == ".yaml":
        if yaml is None:
            return {}
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return json.loads(path.read_text(encoding="utf-8"))


def discover_mods() -> list[dict[str, Any]]:
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    registry: list[dict[str, Any]] = []
    for path in sorted(MODS_DIR.glob("mod-*") ):
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        try:
            payload = _read(path)
            if not isinstance(payload, dict):
                raise ValueError("root must be an object")
            registry.append({
                "id": str(payload.get("id", path.stem)),
                "name": str(payload.get("name", path.stem)),
                "version": str(payload.get("version", "0.1")),
                "file": path.name,
                "description": str(payload.get("description", "")),
                "enabled": bool(payload.get("enabled_by_default", False)),
                "capabilities": list(payload.get("capabilities", [])),
                "status": "loaded",
            })
        except Exception as exc:
            registry.append({"id": path.stem, "name": path.stem, "version": "?", "file": path.name,
                             "description": f"Could not load: {exc}", "enabled": False,
                             "capabilities": [], "status": "error"})
    if REGISTRY_PATH.exists():
        try:
            old = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
            old_by_file = {item.get("file"): item for item in old.get("mods", [])}
            for item in registry:
                if item["file"] in old_by_file:
                    item["enabled"] = bool(old_by_file[item["file"]].get("enabled", item["enabled"]))
        except Exception:
            pass
    REGISTRY_PATH.write_text(json.dumps({"version": 1, "mods": registry}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return registry


def set_enabled(mod_file: str, enabled: bool) -> None:
    mods = discover_mods()
    for mod in mods:
        if mod["file"] == mod_file:
            mod["enabled"] = bool(enabled)
    REGISTRY_PATH.write_text(json.dumps({"version": 1, "mods": mods}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mods_snapshot() -> list[dict[str, Any]]:
    return discover_mods()


def _enabled_payloads() -> list[dict[str, Any]]:
    enabled = {m["file"] for m in discover_mods() if m["enabled"]}
    result = []
    for path in sorted(MODS_DIR.glob("mod-*")):
        if path.name in enabled and path.suffix.lower() in {".json", ".yaml", ".yml"}:
            try:
                result.append(_read(path))
            except Exception:
                pass
    return result


def translation_table() -> dict[str, str]:
    table: dict[str, str] = {}
    for payload in _enabled_payloads():
        table.update({str(k): str(v) for k, v in payload.get("translations", {}).items()})
    return table


def enabled_content(section: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for payload in _enabled_payloads():
        values = payload.get("content", {}).get(section, {})
        if isinstance(values, dict):
            merged.update(deepcopy(values))
    return merged


def translate(value: Any) -> str:
    text = str(value)
    return translation_table().get(text, text)


def merge_enabled_content(cities: dict, activities: dict, recipes: dict, skills: dict, npcs: dict) -> None:
    """Merge additive catalog sections from enabled mods in-place."""
    for payload in _enabled_payloads():
        content = payload.get("content", {})
        for target, destination in (("cities", cities), ("activities", activities), ("recipes", recipes), ("skills", skills)):
            additions = content.get(target, {})
            if isinstance(additions, dict):
                destination.update(deepcopy(additions))
        npc_additions = content.get("npcs", {})
        if isinstance(npc_additions, dict):
            npcs.setdefault("characters", {}).update(deepcopy(npc_additions))


# Always discover at import time so opening the game creates/refreshes mods.json.
MOD_REGISTRY = discover_mods()

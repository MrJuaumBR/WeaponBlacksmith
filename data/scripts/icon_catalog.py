"""Lazy loading for the generated transparent pixel-art UI icons."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import pygame

ICON_ROOT = Path(__file__).resolve().parents[1] / "assets" / "icons"

BUTTON_ICON_KEYS = {
    "CRAFT": "craft",
    "FORGE": "forge",
    "BACK": "back",
    "RETURN": "back",
    "INVENTORY": "inventory",
    "SELL": "sell",
    "IDLE": "work",
    "WORK": "work",
    "LUMBER": "lumber",
    "ADVENTURER": "adventurer",
    "GUILD": "guild",
    "MISSION": "mission",
    "BATTLE": "battle",
    "FIGHT": "battle",
    "ATTACK": "battle",
    "CLAIM": "claim",
    "MATERIAL": "materials",
    "PATTERN": "patterns",
    "MOD": "mods",
    "CITY": "city",
    "EXPLORE": "city",
    "CHARACTER": "adventurer",
    "CREATE": "adventurer",
    "JOIN": "guild",
    "ENABLE": "mods",
    "DISABLE": "mods",
}

@lru_cache(maxsize=128)
def icon(name: str):
    path = ICON_ROOT / f"{name}.png"
    if not path.exists():
        return None
    try:
        return pygame.image.load(str(path)).convert_alpha()
    except pygame.error:
        return None


def icon_for_text(text: str):
    upper = str(text).upper()
    for needle, name in BUTTON_ICON_KEYS.items():
        if needle in upper:
            return icon(name)
    return None

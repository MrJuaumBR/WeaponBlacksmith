# Weapon Blacksmith modding

Weapon Blacksmith mods are data-only JSON or YAML files stored in `data/mods/`.
The game discovers files named `mod-{name}-v{version}.json` or
`mod-{name}-v{version}.yaml` at startup and writes a generated registry to
`data/mods/mods.json`. The in-game **Mods** screen can enable or disable packs;
restart the game after changing a pack so its catalogs are rebuilt safely.

## Mod shape

```yaml
id: example
name: Example Expansion
version: '0.1'
enabled_by_default: false
description: Adds safe, additive content.
capabilities: [cities, npcs, materials, craftings, translations, battle]
translations:
  Inventory: Inventário
content:
  cities: {}
  activities: {}
  recipes: {}
  skills: {}
  npcs: {}
```

All `content` sections are additive dictionaries. RPG recipes use the same
fields as the built-in recipes (`name`, `materials`, `skill`, `level`, `city`,
`station`, `xp`, `description`, and optional `weapon_damage`). City activities
can add drops, gold, XP, and a city restriction. NPCs follow the response-bank
format in `data/rpg/content/npcs.json`.

Translations are exact string replacements used by UI/content helpers. They
should provide a Brazilian Portuguese value for every user-facing string the
mod owns. A translation pack can be enabled independently of content packs.

The registry is generated metadata, not a hand-edited mod. Do not put Python
code, executable files, credentials, or absolute paths in `data/mods/`.

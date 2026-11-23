"""Content catalog for the standalone Weapon Blacksmith RPG example."""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .mods import merge_enabled_content

SKILLS = {
    "blacksmithing": "Blacksmithing",
    "mining": "Mining",
    "woodcutting": "Woodcutting",
    "archery": "Archery",
    "swordmastery": "Swordmastery",
    "fishing": "Fishing",
    "cooking": "Cooking",
    "combat": "Combat",
    "exploration": "Exploration",
}

CITIES = {
    "hearthglade": {
        "name": "Hearthglade",
        "description": "A warm market town of timber roofs, a busy forge, and familiar faces.",
        "unlock_skill": None,
        "unlock_level": 1,
        "npcs": ["Orlen", "Arthur", "Marta", "Elias", "Beth"],
    },
    "coppervein": {
        "name": "Coppervein",
        "description": "A red-rock mining town where old tunnels still glitter with ore.",
        "unlock_skill": "mining",
        "unlock_level": 2,
        "npcs": ["Orlen", "Arthur"],
    },
    "briarwatch": {
        "name": "Briarwatch",
        "description": "A woodland settlement built around living groves and a ranger's trail.",
        "unlock_skill": "woodcutting",
        "unlock_level": 2,
        "npcs": ["Beth", "Elias"],
    },
    "emberfall": {
        "name": "Emberfall",
        "description": "A high-walled foundry city whose furnaces burn through the night.",
        "unlock_skill": "blacksmithing",
        "unlock_level": 2,
        "npcs": ["Orlen", "Marta"],
    },
    "highridge": {
        "name": "Highridge",
        "description": "A cliffside outpost with a clear view of the wild northern pass.",
        "unlock_skill": "archery",
        "unlock_level": 2,
        "npcs": ["Arthur", "Beth"],
    },
}

ACTIVITIES = {
    "mine_copper": {
        "name": "Mine copper ore",
        "skill": "mining",
        "city": "hearthglade",
        "seconds_per_cycle": 30,
        "xp": 12,
        "drops": {"copper": 1},
        "gold": 1,
        "description": "Chip copper from the old surface seam.",
    },
    "gather_oak": {
        "name": "Gather oak timber",
        "skill": "woodcutting",
        "city": "hearthglade",
        "seconds_per_cycle": 30,
        "xp": 12,
        "drops": {"wood": 1},
        "gold": 1,
        "description": "Collect fallen oak and prepare usable lengths.",
    },
    "forge_practice": {
        "name": "Work the forge",
        "skill": "blacksmithing",
        "city": "hearthglade",
        "seconds_per_cycle": 30,
        "xp": 12,
        "drops": {"coal": 1},
        "gold": 0,
        "description": "Tend the coals and practice safe hammer work.",
    },
    "sword_drills": {
        "name": "Practice sword forms",
        "skill": "swordmastery",
        "city": "hearthglade",
        "seconds_per_cycle": 30,
        "xp": 12,
        "drops": {},
        "gold": 0,
        "description": "Repeat measured footwork and clean cuts.",
    },
    "archery_practice": {
        "name": "Practice archery",
        "skill": "archery",
        "city": "hearthglade",
        "seconds_per_cycle": 30,
        "xp": 12,
        "drops": {"stick": 1},
        "gold": 0,
        "description": "Tune your aim at the village targets.",
    },
    "goblin_bounty": {
        "name": "Guard the east road",
        "skill": "combat",
        "city": "hearthglade",
        "seconds_per_cycle": 45,
        "xp": 16,
        "drops": {"string": 1},
        "gold": 3,
        "description": "Keep watch and drive off small goblin raiding parties.",
    },
    "river_fishing": {
        "name": "Fish the mill stream",
        "skill": "fishing",
        "city": "hearthglade",
        "seconds_per_cycle": 40,
        "xp": 12,
        "drops": {"river_trout": 1},
        "gold": 0,
        "description": "Cast beside the old mill and bring home a catch.",
    },
    "cook_stew": {
        "name": "Prepare a hearty stew",
        "skill": "cooking",
        "city": "hearthglade",
        "seconds_per_cycle": 45,
        "xp": 12,
        "drops": {"trail_ration": 1},
        "gold": 0,
        "description": "Turn gathered food into a simple travel ration.",
    },
    "mine_iron": {
        "name": "Mine iron ore",
        "skill": "mining",
        "city": "coppervein",
        "seconds_per_cycle": 35,
        "xp": 16,
        "drops": {"iron": 1},
        "gold": 2,
        "description": "Follow the deep seam beneath Coppervein.",
    },
    "fell_pine": {
        "name": "Cut pine timber",
        "skill": "woodcutting",
        "city": "briarwatch",
        "seconds_per_cycle": 35,
        "xp": 16,
        "drops": {"wood": 1},
        "gold": 2,
        "description": "Harvest straight-grained timber with a forest steward.",
    },
    "forge_iron": {
        "name": "Temper an iron billet",
        "skill": "blacksmithing",
        "city": "emberfall",
        "seconds_per_cycle": 40,
        "xp": 18,
        "drops": {"steel": 1},
        "gold": 2,
        "description": "Learn the heat-and-quench rhythm of the city foundry.",
    },
    "highridge_hunt": {
        "name": "Patrol the high pass",
        "skill": "archery",
        "city": "highridge",
        "seconds_per_cycle": 40,
        "xp": 18,
        "drops": {"leather": 1},
        "gold": 3,
        "description": "Track game and protect the road with a bow.",
    },
}

GUILDS = {
    "ember_order": {
        "name": "The Ember Order",
        "description": "Craftsfolk and guards who keep the roads and forges ready.",
        "contract_activity": "forge_practice",
        "contract_cycles": 4,
        "reward_gold": 35,
        "reward_reputation": 20,
    },
    "delvers_union": {
        "name": "The Delvers' Union",
        "description": "Miners, scouts, and patient collectors of what lies below.",
        "contract_activity": "mine_copper",
        "contract_cycles": 4,
        "reward_gold": 30,
        "reward_reputation": 20,
    },
    "wayfarers_league": {
        "name": "The Wayfarers' League",
        "description": "A loose fellowship for explorers, rangers, and trail makers.",
        "contract_activity": "gather_oak",
        "contract_cycles": 4,
        "reward_gold": 30,
        "reward_reputation": 20,
    },
}

GUILD_MISSIONS = {
    "goblin_cleanup": {
        "name": "Goblin Cleanup", "enemy_id": "goblin", "target_count": 3,
        "reward_gold": 24, "reward_reputation": 12,
    },
    "skeleton_watch": {
        "name": "Skeleton Watch", "enemy_id": "skeleton", "target_count": 3,
        "reward_gold": 32, "reward_reputation": 16,
    },
    "orc_roadblock": {
        "name": "Orc Roadblock", "enemy_id": "orc", "target_count": 2,
        "reward_gold": 45, "reward_reputation": 22,
    },
}

RECIPES = {
    "copper_shortsword": {
        "name": "Hearthglade Shortsword",
        "materials": {"copper": 2, "wood": 2},
        "skill": "blacksmithing",
        "level": 1,
        "city": "hearthglade",
        "xp": 28,
        "description": "A dependable first blade, balanced for a new swordmaster.",
        "weapon_damage": [3, 6],
    },
    "oak_scout_bow": {
        "name": "Oak Scout Bow",
        "materials": {"wood": 3, "string": 1},
        "skill": "blacksmithing",
        "level": 1,
        "city": "hearthglade",
        "xp": 30,
        "description": "A simple bow strung with sinew from the east-road goblins.",
        "weapon_damage": [2, 5],
    },
    "emberfall_ironblade": {
        "name": "Emberfall Ironblade",
        "materials": {"iron": 3, "wood": 2, "coal": 1},
        "skill": "blacksmithing",
        "level": 2,
        "city": "emberfall",
        "xp": 55,
        "description": "A heavier blade made from tempered iron and forest timber.",
        "weapon_damage": [6, 10],
    },
}

NPC_FILE = Path(__file__).with_name("content") / "npcs.json"
NPCS = json.loads(NPC_FILE.read_text(encoding="utf-8"))
ENEMY_FILE = Path(__file__).with_name("enemies.yaml")
ENEMIES = yaml.safe_load(ENEMY_FILE.read_text(encoding="utf-8")).get("enemies", {})

# Mods are additive and data-only.  The registry is refreshed as the game
# starts, then enabled packs extend the normal RPG catalogs in-place.
merge_enabled_content(CITIES, ACTIVITIES, RECIPES, SKILLS, NPCS)

ACTIVITIES_BY_CITY = {
    city_id: [activity_id for activity_id, activity in ACTIVITIES.items() if activity["city"] == city_id]
    for city_id in CITIES
}

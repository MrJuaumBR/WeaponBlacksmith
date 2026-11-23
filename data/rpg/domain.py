"""Deterministic domain rules for the Weapon Blacksmith idle-RPG example.

This module is independent of Pygame so progression, offline rewards, crafting,
city unlocks, guild contracts, and dialogue can be checked without a display.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Any

if __package__:
    from .game_data import ACTIVITIES, CITIES, ENEMIES, GUILDS, GUILD_MISSIONS, NPCS, RECIPES, SKILLS
else:  # Support ``python examples/weapon_blacksmith/app.py`` from the repo root.
    from game_data import ACTIVITIES, CITIES, ENEMIES, GUILDS, GUILD_MISSIONS, NPCS, RECIPES, SKILLS

MAX_CHARACTERS = 3
MAX_SKILL_LEVEL = 99
MAX_OFFLINE_SECONDS = 8 * 60 * 60
STARTING_CITY = "hearthglade"
STARTING_ITEMS = {"wood": 3, "copper": 2, "coal": 1}


class GameError(ValueError):
    """A player action could not be completed under the current game rules."""


@dataclass
class Character:
    id: str
    name: str
    created_at: float
    level: int = 1
    experience: int = 0
    skills: dict[str, dict[str, int]] = field(default_factory=dict)
    inventory: dict[str, int] = field(default_factory=lambda: dict(STARTING_ITEMS))
    current_city: str = STARTING_CITY
    unlocked_cities: list[str] = field(default_factory=lambda: [STARTING_CITY])
    visited_cities: list[str] = field(default_factory=lambda: [STARTING_CITY])
    active_activity: dict[str, Any] | None = None
    guild: dict[str, Any] | None = None
    equipped_weapon: str | None = None
    met_npcs: list[str] = field(default_factory=list)
    dialogue_cursor: dict[str, int] = field(default_factory=dict)

    @classmethod
    def new(cls, name: str, now: float | None = None) -> "Character":
        now = time.time() if now is None else float(now)
        return cls(
            id=uuid.uuid4().hex[:12],
            name=name,
            created_at=now,
            skills={skill: {"level": 1, "xp": 0} for skill in SKILLS},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "level": self.level,
            "experience": self.experience,
            "skills": self.skills,
            "inventory": self.inventory,
            "current_city": self.current_city,
            "unlocked_cities": self.unlocked_cities,
            "visited_cities": self.visited_cities,
            "active_activity": self.active_activity,
            "guild": self.guild,
            "equipped_weapon": self.equipped_weapon,
            "met_npcs": self.met_npcs,
            "dialogue_cursor": self.dialogue_cursor,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Character":
        if not isinstance(data, dict):
            raise GameError("Character save must be an object")
        name = _validate_name(data.get("name", ""))
        character_id = data.get("id")
        if not isinstance(character_id, str) or not character_id:
            raise GameError("Character save has no valid id")
        skills = {skill: {"level": 1, "xp": 0} for skill in SKILLS}
        for key, value in data.get("skills", {}).items():
            if key in skills and isinstance(value, dict):
                level = max(1, min(MAX_SKILL_LEVEL, int(value.get("level", 1))))
                xp = max(0, int(value.get("xp", 0)))
                skills[key] = {"level": level, "xp": xp}
        inventory = {
            str(item): max(0, int(amount))
            for item, amount in data.get("inventory", {}).items()
            if isinstance(amount, (int, float)) and amount >= 0
        }
        current_city = data.get("current_city", STARTING_CITY)
        if current_city not in CITIES:
            current_city = STARTING_CITY
        unlocked = [city for city in data.get("unlocked_cities", [STARTING_CITY]) if city in CITIES]
        if STARTING_CITY not in unlocked:
            unlocked.insert(0, STARTING_CITY)
        if current_city not in unlocked:
            current_city = STARTING_CITY
        activity = data.get("active_activity")
        if not isinstance(activity, dict) or activity.get("id") not in ACTIVITIES:
            activity = None
        guild = data.get("guild")
        if not isinstance(guild, dict) or guild.get("id") not in GUILDS:
            guild = None
        npc_catalog = NPCS.get("characters", NPCS)
        return cls(
            id=character_id,
            name=name,
            created_at=float(data.get("created_at", 0)),
            level=max(1, int(data.get("level", 1))),
            experience=max(0, int(data.get("experience", 0))),
            skills=skills,
            inventory=inventory,
            current_city=current_city,
            unlocked_cities=list(dict.fromkeys(unlocked)),
            visited_cities=[city for city in data.get("visited_cities", [STARTING_CITY]) if city in CITIES],
            active_activity=activity,
            guild=guild,
            equipped_weapon=data.get("equipped_weapon") if isinstance(data.get("equipped_weapon"), str) else None,
            met_npcs=[name for name in data.get("met_npcs", []) if name in npc_catalog],
            dialogue_cursor={str(key): max(0, int(value)) for key, value in data.get("dialogue_cursor", {}).items()},
        )


@dataclass
class GameState:
    characters: list[Character] = field(default_factory=list)
    active_character_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": 1,
            "active_character_id": self.active_character_id,
            "characters": [character.to_dict() for character in self.characters],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameState":
        if not isinstance(data, dict) or data.get("version") != 1:
            raise GameError("Unsupported or invalid save version")
        raw_characters = data.get("characters")
        if not isinstance(raw_characters, list) or len(raw_characters) > MAX_CHARACTERS:
            raise GameError(f"Save must contain no more than {MAX_CHARACTERS} characters")
        characters = [Character.from_dict(item) for item in raw_characters]
        ids = [character.id for character in characters]
        if len(set(ids)) != len(ids):
            raise GameError("Save contains duplicate character ids")
        active_id = data.get("active_character_id")
        if active_id not in ids:
            active_id = ids[0] if ids else None
        return cls(characters=characters, active_character_id=active_id)


def _validate_name(value: Any) -> str:
    if not isinstance(value, str):
        raise GameError("Choose a character name")
    name = " ".join(value.strip().split())
    if not 1 <= len(name) <= 18:
        raise GameError("Character names must be 1–18 characters")
    if not all(character.isalpha() or character in " -'" for character in name):
        raise GameError("Use letters, spaces, hyphens, or apostrophes in a character name")
    return name


@dataclass
class ActivityResult:
    activity_id: str
    cycles: int = 0
    experience: int = 0
    gold: int = 0
    drops: dict[str, int] = field(default_factory=dict)
    level_ups: list[str] = field(default_factory=list)
    message: str = "No completed work yet."


class RPGGame:
    """Mutating game rules over a serializable :class:`GameState`."""

    def __init__(self, state: GameState | None = None):
        self.state = state or GameState()
        self.active_battle: dict[str, Any] | None = None

    @property
    def active_character(self) -> Character | None:
        for character in self.state.characters:
            if character.id == self.state.active_character_id:
                return character
        return None

    def create_character(self, name: str, now: float | None = None) -> Character:
        name = _validate_name(name)
        if len(self.state.characters) >= MAX_CHARACTERS:
            raise GameError(f"You can create up to {MAX_CHARACTERS} characters.")
        if any(character.name.casefold() == name.casefold() for character in self.state.characters):
            raise GameError("Each character needs a distinct name.")
        character = Character.new(name, now)
        self.state.characters.append(character)
        self.state.active_character_id = character.id
        return character

    def select_character(self, character_id: str) -> Character:
        if not any(character.id == character_id for character in self.state.characters):
            raise GameError("That character slot is empty.")
        self.state.active_character_id = character_id
        return self.active_character  # type: ignore[return-value]

    def _require_character(self) -> Character:
        character = self.active_character
        if character is None:
            raise GameError("Create or select a character first.")
        return character

    def _award_xp(self, character: Character, skill_id: str, amount: int) -> list[str]:
        if skill_id not in SKILLS or amount <= 0:
            return []
        skill = character.skills.setdefault(skill_id, {"level": 1, "xp": 0})
        skill["xp"] += amount
        global_xp = max(1, amount // 2)
        character.experience += global_xp
        level_ups: list[str] = []
        while character.level < 99 and character.experience >= character.level * 100:
            character.experience -= character.level * 100
            character.level += 1
            level_ups.append(f"Character level {character.level}")
        while skill["level"] < MAX_SKILL_LEVEL and skill["xp"] >= skill["level"] * 100:
            skill["xp"] -= skill["level"] * 100
            skill["level"] += 1
            level_ups.append(f"{SKILLS[skill_id]} level {skill['level']}")
        self._unlock_eligible_cities(character)
        return level_ups

    def _unlock_eligible_cities(self, character: Character) -> list[str]:
        newly_unlocked: list[str] = []
        for city_id, city in CITIES.items():
            required_skill = city["unlock_skill"]
            if required_skill is None or city_id in character.unlocked_cities:
                continue
            if character.skills[required_skill]["level"] >= city["unlock_level"]:
                character.unlocked_cities.append(city_id)
                newly_unlocked.append(city_id)
        return newly_unlocked

    def start_activity(self, activity_id: str, now: float | None = None) -> ActivityResult | None:
        now = time.time() if now is None else float(now)
        character = self._require_character()
        if activity_id not in ACTIVITIES:
            raise GameError("Unknown activity.")
        activity = ACTIVITIES[activity_id]
        if activity["city"] != character.current_city:
            raise GameError(f"Travel to {CITIES[activity['city']]['name']} to start that activity.")
        previous_result = None
        if character.active_activity:
            if character.active_activity["id"] == activity_id:
                return self.claim_activity(now)
            previous_result = self.claim_activity(now)
        character.active_activity = {"id": activity_id, "started_at": now}
        return previous_result

    def claim_activity(self, now: float | None = None) -> ActivityResult:
        now = time.time() if now is None else float(now)
        character = self._require_character()
        active = character.active_activity
        if not active:
            return ActivityResult("", message="No activity is running.")
        activity_id = active["id"]
        activity = ACTIVITIES[activity_id]
        started_at = float(active.get("started_at", now))
        elapsed = max(0.0, now - started_at)
        credited_elapsed = min(elapsed, MAX_OFFLINE_SECONDS)
        cycles = int(credited_elapsed // activity["seconds_per_cycle"])
        if cycles <= 0:
            return ActivityResult(activity_id, message="No completed work yet.")

        remainder = credited_elapsed - cycles * activity["seconds_per_cycle"]
        # If a save sat idle for longer than the cap, discard excess time rather
        # than allowing repeated claims to harvest an unbounded backlog.
        active["started_at"] = now - remainder
        drops = {item: amount * cycles for item, amount in activity["drops"].items()}
        for item, amount in drops.items():
            character.inventory[item] = character.inventory.get(item, 0) + amount
        gold = activity["gold"] * cycles
        character.inventory["gold"] = character.inventory.get("gold", 0) + gold
        xp = activity["xp"] * cycles
        level_ups = self._award_xp(character, activity["skill"], xp)
        if character.guild and character.guild["id"] in GUILDS:
            guild_def = GUILDS[character.guild["id"]]
            if activity_id == guild_def["contract_activity"]:
                character.guild["contract_progress"] = min(
                    guild_def["contract_cycles"],
                    character.guild.get("contract_progress", 0) + cycles,
                )
        return ActivityResult(
            activity_id=activity_id,
            cycles=cycles,
            experience=xp,
            gold=gold,
            drops=drops,
            level_ups=level_ups,
            message=f"Completed {cycles} work cycle{'s' if cycles != 1 else ''}.",
        )

    def activity_status(self, now: float | None = None) -> str:
        now = time.time() if now is None else float(now)
        character = self._require_character()
        if not character.active_activity:
            return "No idle task is assigned. Choose an activity to begin earning progress."
        active = character.active_activity
        activity = ACTIVITIES[active["id"]]
        elapsed = max(0.0, now - float(active.get("started_at", now)))
        credited = min(elapsed, MAX_OFFLINE_SECONDS)
        cycles = int(credited // activity["seconds_per_cycle"])
        seconds_to_next = max(0, int(activity["seconds_per_cycle"] - credited % activity["seconds_per_cycle"]))
        return (
            f"Working: {activity['name']}  |  {cycles} cycle(s) ready  |  "
            f"next cycle in {seconds_to_next}s  |  offline cap: 8h"
        )

    def visit_city(self, city_id: str) -> str:
        character = self._require_character()
        if city_id not in CITIES:
            raise GameError("That city is not on the map.")
        if city_id not in character.unlocked_cities:
            city = CITIES[city_id]
            skill_id = city["unlock_skill"]
            skill_name = SKILLS[skill_id]
            skill_level = character.skills[skill_id]["level"]
            raise GameError(f"Reach {skill_name} level {city['unlock_level']} to unlock {city['name']} (you are level {skill_level}).")
        character.current_city = city_id
        if city_id not in character.visited_cities:
            character.visited_cities.append(city_id)
            self._award_xp(character, "exploration", 20)
            return f"You arrived in {CITIES[city_id]['name']} and gained 20 Exploration XP."
        return f"You arrived in {CITIES[city_id]['name']}."

    def max_craftable(self, recipe_id: str) -> int:
        character = self._require_character()
        if recipe_id not in RECIPES:
            raise GameError("Unknown blueprint.")
        recipe = RECIPES[recipe_id]
        if character.current_city != recipe["city"]:
            return 0
        if character.skills[recipe["skill"]]["level"] < recipe["level"]:
            return 0
        amounts = [character.inventory.get(item, 0) // amount for item, amount in recipe["materials"].items()]
        return min(amounts, default=0)

    def craft(self, recipe_id: str, quantity: int = 1) -> str:
        character = self._require_character()
        quantity = int(quantity)
        if quantity < 1:
            raise GameError("Craft quantity must be at least one.")
        if recipe_id not in RECIPES:
            raise GameError("Unknown blueprint.")
        recipe = RECIPES[recipe_id]
        if character.current_city != recipe["city"]:
            raise GameError(f"Travel to {CITIES[recipe['city']]['name']} to use this blueprint.")
        if character.skills[recipe["skill"]]["level"] < recipe["level"]:
            raise GameError(f"Requires {SKILLS[recipe['skill']]} level {recipe['level']}.")
        missing = [
            f"{amount} {item.replace('_', ' ')}"
            for item, amount in recipe["materials"].items()
            if character.inventory.get(item, 0) < amount * quantity
        ]
        if missing:
            raise GameError("Missing materials: " + ", ".join(missing) + ".")
        for item, amount in recipe["materials"].items():
            character.inventory[item] -= amount * quantity
        character.inventory[recipe_id] = character.inventory.get(recipe_id, 0) + quantity
        if character.equipped_weapon is None:
            character.equipped_weapon = recipe_id
        level_ups = self._award_xp(character, recipe["skill"], recipe["xp"] * quantity)
        return f"Forged {quantity} × {recipe['name']} (+{recipe['xp'] * quantity} Blacksmithing XP)." + (
            " Level up: " + ", ".join(level_ups) + "." if level_ups else ""
        )

    def sell_price(self, item_id: str) -> int:
        if item_id in RECIPES:
            recipe = RECIPES[item_id]
            return max(2, sum(recipe["materials"].values()) * 3 + recipe["xp"] // 10)
        return max(1, 1 + (len(item_id) % 4))

    def max_sellable(self, item_id: str) -> int:
        character = self._require_character()
        return max(0, int(character.inventory.get(item_id, 0)))

    def sell(self, item_id: str, quantity: int = 1) -> str:
        character = self._require_character()
        quantity = int(quantity)
        if quantity < 1 or character.inventory.get(item_id, 0) < quantity:
            raise GameError("You do not have enough of that item to sell.")
        if item_id == "gold":
            raise GameError("Gold cannot be sold.")
        total = self.sell_price(item_id) * quantity
        character.inventory[item_id] -= quantity
        character.inventory["gold"] = character.inventory.get("gold", 0) + total
        return f"Sold {quantity} × {item_id.replace('_', ' ')} for {total} gold."

    def inventory_items(self, search: str = "", sort: str = "name") -> list[tuple[str, int]]:
        """Return non-zero inventory entries in a UI-friendly order."""
        character = self._require_character()
        query = search.casefold().strip()
        items = [(item, amount) for item, amount in character.inventory.items()
                 if amount > 0 and item != "gold" and (not query or query in item.casefold())]
        if sort == "quantity":
            return sorted(items, key=lambda pair: (-pair[1], pair[0]))
        if sort == "category":
            def category(pair):
                item = pair[0]
                if item.endswith("_ore") or item in {"copper", "iron", "coal", "steel"}:
                    return (0, item)
                if item.endswith(("_sword", "_blade", "_bow", "_edge")):
                    return (2, item)
                return (1, item)
            return sorted(items, key=category)
        return sorted(items, key=lambda pair: pair[0].casefold())

    def start_battle(self, enemy_id: str = "corrupted_citizen") -> str:
        character = self._require_character()
        if character.current_city != "broken_reality":
            raise GameError("Battle encounters are currently available only in Broken Reality.")
        if enemy_id not in ENEMIES:
            raise GameError("Unknown enemy encounter.")
        enemy = ENEMIES[enemy_id]
        self.active_battle = {"enemy_id": enemy_id, **enemy, "max_hp": enemy["hp"]}
        return f"A {self.active_battle['name']} blocks the road."

    def battle_attack(self) -> str:
        character = self._require_character()
        if not self.active_battle:
            raise GameError("Start an encounter before attacking.")
        weapon = RECIPES.get(character.equipped_weapon, {})
        damage_range = weapon.get("weapon_damage", [2, 4])
        attack = max(1, (int(damage_range[0]) + int(damage_range[1])) // 2 + character.skills["combat"]["level"] - 1)
        self.active_battle["hp"] -= attack
        if self.active_battle["hp"] <= 0:
            reward = self.active_battle["reward"]
            name = self.active_battle["name"]
            character.inventory["gold"] = character.inventory.get("gold", 0) + reward
            self._award_xp(character, "combat", 24)
            mission_id = character.guild.get("mission_id") if character.guild else None
            mission = GUILD_MISSIONS.get(mission_id) if mission_id else None
            if mission and mission.get("enemy_id") == self.active_battle.get("enemy_id"):
                character.guild["mission_progress"] = min(
                    mission["target_count"],
                    character.guild.get("mission_progress", 0) + 1,
                )
            self.active_battle = None
            return f"You defeated {name} and found {reward} gold."
        retaliation = self.active_battle["damage"]
        self._award_xp(character, "combat", 6)
        return f"You deal {attack} damage. The enemy has {self.active_battle['hp']} HP and hits back for {retaliation}."

    def battle_status(self) -> str:
        if not self.active_battle:
            return "No active encounter."
        return f"{self.active_battle['name']} · {self.active_battle['hp']}/{self.active_battle['max_hp']} HP"

    def join_guild(self, guild_id: str) -> str:
        character = self._require_character()
        if guild_id not in GUILDS:
            raise GameError("That guild is not recruiting.")
        if character.guild:
            current_name = GUILDS[character.guild["id"]]["name"]
            raise GameError(f"You already belong to {current_name}.")
        character.guild = {
            "id": guild_id,
            "reputation": 0,
            "contract_progress": 0,
            "contracts_completed": 0,
        }
        return f"You joined {GUILDS[guild_id]['name']}. Your first contract is ready."

    def take_guild_mission(self, mission_id: str) -> str:
        character = self._require_character()
        if not character.guild:
            raise GameError("Join a guild before taking a mission.")
        if mission_id not in GUILD_MISSIONS:
            raise GameError("That mission is not available.")
        mission = GUILD_MISSIONS[mission_id]
        character.guild["mission_id"] = mission_id
        character.guild["mission_progress"] = 0
        return f"Mission accepted: {mission['name']}. Defeat {mission['target_count']} {ENEMIES[mission['enemy_id']]['name']}."

    def claim_guild_mission(self) -> str:
        character = self._require_character()
        mission_id = character.guild.get("mission_id") if character.guild else None
        if not mission_id or mission_id not in GUILD_MISSIONS:
            raise GameError("Accept a guild mission first.")
        mission = GUILD_MISSIONS[mission_id]
        progress = character.guild.get("mission_progress", 0)
        if progress < mission["target_count"]:
            raise GameError(f"Mission progress: {progress}/{mission['target_count']}.")
        character.guild["reputation"] += mission["reward_reputation"]
        character.inventory["gold"] = character.inventory.get("gold", 0) + mission["reward_gold"]
        character.guild["mission_id"] = None
        character.guild["mission_progress"] = 0
        return f"Mission complete: +{mission['reward_gold']} gold and +{mission['reward_reputation']} reputation."

    def claim_guild_contract(self) -> str:
        character = self._require_character()
        if not character.guild:
            raise GameError("Join a guild before taking a contract.")
        guild = GUILDS[character.guild["id"]]
        if character.guild.get("contract_progress", 0) < guild["contract_cycles"]:
            remaining = guild["contract_cycles"] - character.guild.get("contract_progress", 0)
            raise GameError(f"Contract in progress: {remaining} more work cycle(s) needed.")
        character.guild["reputation"] += guild["reward_reputation"]
        character.guild["contracts_completed"] += 1
        character.guild["contract_progress"] = 0
        character.inventory["gold"] = character.inventory.get("gold", 0) + guild["reward_gold"]
        rank = self.guild_rank(character.guild["reputation"])
        return f"Contract complete: +{guild['reward_gold']} gold, +{guild['reward_reputation']} guild reputation. Rank: {rank}."

    @staticmethod
    def guild_rank(reputation: int) -> str:
        if reputation >= 200:
            return "Gold Artisan"
        if reputation >= 100:
            return "Silver Artisan"
        if reputation >= 40:
            return "Bronze Artisan"
        return "Guild Initiate"

    def talk(self, npc_id: str, topic: str) -> str:
        character = self._require_character()
        npc_catalog = NPCS.get("characters", NPCS)
        npc = npc_catalog.get(npc_id)
        if npc is None:
            raise GameError("You cannot find that villager here.")
        responses = npc.get("responses", {})
        if topic not in responses:
            raise GameError("That conversation topic is unavailable.")
        selected_topic = "first_meet" if topic == "greeting" and npc_id not in character.met_npcs else topic
        options = responses.get(selected_topic) or responses.get(topic) or []
        if not options:
            raise GameError("This villager has nothing to say about that just yet.")
        cursor_key = f"{npc_id}:{selected_topic}"
        index = character.dialogue_cursor.get(cursor_key, 0) % len(options)
        character.dialogue_cursor[cursor_key] = index + 1
        if npc_id not in character.met_npcs:
            character.met_npcs.append(npc_id)
        guild_name = GUILDS[character.guild["id"]]["name"] if character.guild else "no guild yet"
        text = options[index]
        return text.format_map(_SafeFormat({
            "player": character.name,
            "city": CITIES[character.current_city]["name"],
            "level": character.level,
            "guild": guild_name,
            "weapon": RECIPES.get(character.equipped_weapon, {}).get("name", "no weapon yet"),
        }))

    def skill_summary(self) -> list[str]:
        character = self._require_character()
        return [
            f"{SKILLS[skill]}  Lv {character.skills[skill]['level']}  "
            f"({character.skills[skill]['xp']}/{character.skills[skill]['level'] * 100} XP)"
            for skill in SKILLS
        ]


class _SafeFormat(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""

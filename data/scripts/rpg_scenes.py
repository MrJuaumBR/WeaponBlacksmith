"""Idle-RPG scenes for the original Weapon Blacksmith LunaEngine app."""
from __future__ import annotations

import os
from pathlib import Path

from lunaengine.core import LunaEngine, Scene
from lunaengine.ui import Button, Dropdown, LongTextLabel, ScrollingFrame, TextLabel
from lunaengine.ui.elements.textinputs import TextBox

from data.rpg.domain import (
    ACTIVITIES, CITIES, ENEMIES, GUILDS, GUILD_MISSIONS, MAX_CHARACTERS, NPCS, RECIPES, SKILLS,
    GameError, RPGGame,
)
from data.rpg.savegame import JsonSaveRepository
from data.rpg.mods import mods_snapshot, set_enabled, translate
from data.scripts.icon_catalog import icon, icon_for_text


class GameSession:
    """Shared local game state and save repository for all RPG scenes."""

    def __init__(self, save_path: str | Path | None = None):
        if save_path is None:
            save_path = os.environ.get(
                "WEAPON_BLACKSMITH_SAVE",
                str(Path.home() / ".weapon_blacksmith" / "save.json"),
            )
        self.repository = JsonSaveRepository(save_path)
        self.game = RPGGame(self.repository.load())

    def save(self) -> None:
        self.repository.save(self.game.state)


class RPGScene(Scene):
    def __init__(self, engine: LunaEngine, session: GameSession, title: str):
        super().__init__(engine)
        self.session = session
        self.add_ui_element(TextLabel(44, 28, translate(title), 34))
        self.add_ui_element(TextLabel(46, 74, "FORGE AMBER  /  TEMPERED STEEL  /  YOUR STORY", 14))

    def label(self, x: int, y: int, text: str, size: int = 20) -> TextLabel:
        element = TextLabel(x, y, translate(text), size)
        self.add_ui_element(element)
        return element

    def button(self, x: int, y: int, width: int, height: int, text: str, callback, size: int = 17) -> Button:
        element = Button(x, y, width, height, translate(text), size, icon=icon_for_text(text))
        element.set_on_click(callback)
        self.add_ui_element(element)
        return element

    def notify(self, message: str) -> None:
        self.engine.show_info(message)

    def back_to_town(self) -> None:
        self.engine.set_scene("rpg_town")


class CharacterSelectScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Choose your adventurer")
        self.label(48, 120, f"Create up to {MAX_CHARACTERS} characters. Each keeps their own skills, gear, guild, and idle task.", 18)
        self.name_box = TextBox(
            54, 165, 420, 84,
            placeholder_text="Choose a name (1–18 letters)",
            font_size=18,
            max_length=18,
            label="New character",
            label_position="top",
        )
        self.add_ui_element(self.name_box)
        self.create_button = self.button(500, 184, 220, 52, "CREATE CHARACTER", self._create, 17)
        self.slot_labels = [self.label(72, 290 + index * 100, "", 22) for index in range(MAX_CHARACTERS)]
        self.slot_buttons = [
            self.button(850, 278 + index * 100, 210, 54, "ENTER", lambda slot=index: self._select_slot(slot), 17)
            for index in range(MAX_CHARACTERS)
        ]
        self.error_label = self.label(54, 630, "", 17)
        self.button(870, 630, 230, 52, "RETURN TO TITLE", lambda: self.engine.set_scene("main_menu"), 14)

    def _refresh(self) -> None:
        characters = self.session.game.state.characters
        for index in range(MAX_CHARACTERS):
            if index < len(characters):
                character = characters[index]
                city_name = CITIES[character.current_city]["name"]
                self.slot_labels[index].set_text(
                    f"SLOT {index + 1}  ·  {character.name}  ·  Lv {character.level}  ·  {city_name}"
                )
                self.slot_buttons[index].visible = True
            else:
                self.slot_labels[index].set_text(f"SLOT {index + 1}  ·  Empty")
                self.slot_buttons[index].visible = False
        full = len(characters) >= MAX_CHARACTERS
        self.create_button.enabled = not full
        self.error_label.set_text("All three character slots are occupied." if full else "")

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _create(self) -> None:
        try:
            character = self.session.game.create_character(self.name_box.get_text())
            self.session.save()
            self.engine.set_scene("rpg_town")
            self.notify(f"{character.name} is ready to begin in Hearthglade.")
        except GameError as exc:
            self.error_label.set_text(str(exc))

    def _select_slot(self, slot: int) -> None:
        characters = self.session.game.state.characters
        if slot >= len(characters):
            return
        character = self.session.game.select_character(characters[slot].id)
        self.session.save()
        self.engine.set_scene("rpg_town")
        self.notify(f"Welcome back, {character.name}.")


class TownScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Hearthglade — the starting town")
        self.hero_line = self.label(50, 122, "", 22)
        self.city_line = self.label(50, 160, "", 18)
        self.skill_line = self.label(50, 198, "", 16)
        self.activity_line = self.label(50, 238, "", 16)
        self.inventory_line = self.label(50, 276, "", 16)
        destinations = [
            ("IDLE ACTIVITIES", "rpg_activities"),
            ("EXPLORE CITIES", "rpg_cities"),
            ("INVENTORY", "rpg_inventory"),
            ("CRAFTING HALL", "rpg_crafting_hall"),
            ("BATTLE", "rpg_battle"),
            ("SKILL BOOK", "rpg_skills"),
            ("GUILD HALL", "rpg_guild"),
            ("TALK TO VILLAGERS", "rpg_npcs"),
            ("MODS", "rpg_mods"),
            ("MATERIALS GUIDE", "materials"),
            ("PATTERNS GUIDE", "patterns"),
            ("CHARACTER SLOTS", "rpg_characters"),
            ("RETURN TO TITLE", "main_menu"),
        ]
        for index, (text, scene_name) in enumerate(destinations):
            column, row = index % 4, index // 4
            self.button(30 + column * 310, 344 + row * 78, 290, 54, text,
                        lambda target=scene_name: self.engine.set_scene(target), 15)
        self._refresh()

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        city = CITIES[character.current_city]
        gold = character.inventory.get("gold", 0)
        self.hero_line.set_text(f"{character.name}  ·  Adventurer level {character.level}  ·  {gold} gold")
        self.city_line.set_text(f"{city['name']}  —  {city['description']}")
        self.skill_line.set_text("Skills: " + "  |  ".join(
            f"{SKILLS[key]} {character.skills[key]['level']}"
            for key in ("blacksmithing", "mining", "woodcutting", "archery", "swordmastery")
        ))
        self.activity_line.set_text(self.session.game.activity_status())
        items = [f"{item.replace('_', ' ')} ×{amount}" for item, amount in character.inventory.items() if amount and item != "gold"]
        self.inventory_line.set_text("Pack: " + (",  ".join(items[:6]) if items else "empty"))

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def update(self, dt: float) -> None:
        self._refresh_timer = getattr(self, "_refresh_timer", 0.0) + dt
        if self._refresh_timer >= 2.0:
            self._refresh_timer = 0.0
            self.activity_line.set_text(self.session.game.activity_status())


class InventoryScene(RPGScene):
    """A dedicated pack view instead of compressing the inventory into town."""

    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Inventory · search, sort, and inspect")
        self.search = TextBox(48, 112, 430, 58, placeholder_text="Search items…", font_size=18,
                              label="Search", label_position="top")
        self.add_ui_element(self.search)
        self.sort = Dropdown(520, 112, 300, 58, ["Name", "Quantity", "Category"], font_size=18,
                             label="Sort by", label_position="top")
        self.sort.set_on_selection_changed(lambda *_: self._refresh())
        self.search.set_on_text_changed(lambda *_: self._refresh())
        self.add_ui_element(self.sort)
        self.count = self.label(870, 132, "", 18)
        self.scroll = ScrollingFrame(48, 200, 1140, 390, 1120, 400, scrollbar_size=14, cull_rendering=True)
        self.add_ui_element(self.scroll)
        self.button(48, 630, 220, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        sort_key = ("name", "quantity", "category")[self.sort.selected_index]
        items = self.session.game.inventory_items(self.search.get_text(), sort_key)
        self.scroll.clear_content()
        for index, (item, amount) in enumerate(items):
            y = 12 + index * 66
            self.scroll.add_child(TextLabel(22, y, item.replace("_", " ").title(), 20))
            self.scroll.add_child(TextLabel(610, y, f"× {amount}", 20))
            self.scroll.add_child(TextLabel(700, y, f"{self.session.game.sell_price(item)}g each", 16))
            self.scroll.add_child(Button(820, y - 8, 86, 42, "SELL", 13, icon=icon("sell")))
            self.scroll.children[-1].set_on_click(lambda key=item: self._sell(key, 1))
            self.scroll.add_child(Button(914, y - 8, 70, 42, "x3", 13))
            self.scroll.children[-1].set_on_click(lambda key=item: self._sell(key, 3))
            self.scroll.add_child(Button(992, y - 8, 70, 42, "x5", 13))
            self.scroll.children[-1].set_on_click(lambda key=item: self._sell(key, 5))
            self.scroll.add_child(Button(1070, y - 8, 74, 42, "MAX", 13))
            self.scroll.children[-1].set_on_click(lambda key=item: self._sell(key, self.session.game.max_sellable(key)))
        self.scroll.update_content_area(height=max(390, 24 + len(items) * 66))
        self.count.set_text(f"{len(items)} item type(s) · {character.inventory.get('gold', 0)} gold")

    def _sell(self, item_id: str, quantity: int) -> None:
        try:
            self.session.game.sell(item_id, quantity)
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()


class CraftingHallScene(RPGScene):
    """One place for forge, table, furnace, and expansion stations."""

    STATIONS = {
        "crafting_table": "Crafting Table",
        "forge": "Forge",
        "smeltery": "Smeltery",
        "blast_furnace": "Blast Furnace",
        "antimatter_chamber": "Anti-Matter Chamber",
    }

    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Crafting Hall · every station in one place")
        self.station = Dropdown(48, 112, 420, 58, list(self.STATIONS.values()), font_size=18,
                                label="Station", label_position="top")
        self.station.set_on_selection_changed(lambda *_: self._refresh())
        self.add_ui_element(self.station)
        self.status = self.label(520, 132, "", 17)
        self.recipe_notes: dict[str, TextLabel] = {}
        self.recipe_buttons: dict[str, dict[str, Button]] = {}
        for index, (recipe_id, recipe) in enumerate(RECIPES.items()):
            y = 210 + index * 106
            self.recipe_notes[recipe_id] = self.label(58, y, "", 15)
            self.recipe_buttons[recipe_id] = {}
            for offset, (caption, quantity) in enumerate((("CRAFT", 1), ("x2", 2), ("x3", 3), ("x5", 5), ("x10", 10), ("MAX", 0))):
                self.recipe_buttons[recipe_id][caption] = self.button(
                    740 + offset * 74, y + 30, 68, 42, caption,
                    lambda key=recipe_id, qty=quantity: self._craft(key, qty), 12,
                )
        self.button(48, 630, 220, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        station_id = list(self.STATIONS)[self.station.selected_index]
        self.status.set_text(f"{self.STATIONS[station_id]} · {CITIES[character.current_city]['name']}")
        for recipe_id, recipe in RECIPES.items():
            required_station = recipe.get("station", "forge")
            requirements = ", ".join(
                f"{item.replace('_', ' ')} {character.inventory.get(item, 0)}/{amount}"
                for item, amount in recipe["materials"].items()
            )
            owned = character.inventory.get(recipe_id, 0)
            self.recipe_notes[recipe_id].set_text(f"{recipe['name']} · owned {owned} · {requirements} · {recipe['description']}")
            can_use = (character.current_city == recipe["city"] and
                       character.skills[recipe["skill"]]["level"] >= recipe["level"])
            available = self.session.game.max_craftable(recipe_id)
            for caption, button in self.recipe_buttons[recipe_id].items():
                button.visible = required_station == station_id
                requested = 1 if caption == "CRAFT" else (0 if caption == "MAX" else int(caption[1:]))
                button.enabled = can_use and available >= (available if requested == 0 else requested)

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _craft(self, recipe_id: str, quantity: int = 1) -> None:
        try:
            if quantity == 0:
                quantity = self.session.game.max_craftable(recipe_id)
            if quantity <= 0:
                raise GameError("You do not have enough materials for another craft.")
            self.notify(self.session.game.craft(recipe_id, quantity))
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()


class BattleScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Battle · defend the city")
        self.city_note = self.label(48, 118, "", 19)
        self.status = self.label(48, 164, "", 19)
        self.log = LongTextLabel(48, 220, "Choose an encounter.", width=1080, height=120, font_size=20, wrap_width=1080)
        self.add_ui_element(self.log)
        self.enemy_buttons: dict[str, Button] = {}
        for index, (enemy_id, enemy) in enumerate(ENEMIES.items()):
            col, row = index % 4, index // 4
            self.enemy_buttons[enemy_id] = Button(
                48 + col * 280, 390 + row * 62, 260, 50,
                f"FIGHT {enemy['name'].upper()}", 12, icon=icon(enemy_id),
            )
            self.enemy_buttons[enemy_id].set_on_click(lambda key=enemy_id: self._start(key))
            self.add_ui_element(self.enemy_buttons[enemy_id])
        self.attack = self.button(48, 530, 320, 56, "ATTACK", self._attack, 16)
        self.button(48, 630, 220, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        self.city_note.set_text(f"Current city: {CITIES[character.current_city]['name']} · Combat XP {character.skills['combat']['level']}")
        self.status.set_text(self.session.game.battle_status())
        self.attack.enabled = bool(self.session.game.active_battle)

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _start(self, enemy_id: str) -> None:
        try:
            self.log.set_text(self.session.game.start_battle(enemy_id))
        except GameError as exc:
            self.log.set_text(str(exc))
        self._refresh()

    def _attack(self) -> None:
        try:
            self.log.set_text(self.session.game.battle_attack())
            self.session.save()
        except GameError as exc:
            self.log.set_text(str(exc))
        self._refresh()


class ModsScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Mods · data/mods")
        self.note = self.label(48, 112, "Toggle packs, then restart the game to reload their catalogs.", 17)
        self.mod_buttons: list[tuple[dict, Button]] = []
        for index, mod in enumerate(mods_snapshot()):
            y = 190 + index * 105
            button = self.button(48, y, 360, 54, "", lambda item=mod: self._toggle(item), 15)
            self.mod_buttons.append((mod, button))
            self.label(440, y + 8, f"{mod['name']} v{mod['version']} · {mod['description']}", 15)
        self.button(48, 630, 220, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        for mod, button in self.mod_buttons:
            button.set_text(("DISABLE  " if mod["enabled"] else "ENABLE  ") + mod["file"])

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _toggle(self, mod: dict) -> None:
        mod["enabled"] = not mod["enabled"]
        set_enabled(mod["file"], mod["enabled"])
        self.notify(f"{mod['file']} {'enabled' if mod['enabled'] else 'disabled'}. Restart to apply content changes.")
        self._refresh()


class ActivityScene(RPGScene):
    WORK_FILTERS = {
        "All works": None,
        "Blacksmith": "blacksmithing",
        "Lumber": "woodcutting",
        "Adventurer": "combat",
        "Gatherer": "mining",
    }

    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Idle work & training")
        self.city_label = self.label(48, 114, "", 20)
        self.status_label = self.label(48, 150, "", 16)
        self.work_filter = Dropdown(740, 108, 430, 58, list(self.WORK_FILTERS), font_size=17,
                                    label="Work", label_position="top")
        self.work_filter.set_on_selection_changed(lambda *_: self._refresh())
        self.add_ui_element(self.work_filter)
        self.activity_buttons: dict[str, Button] = {}
        for index, (activity_id, activity) in enumerate(ACTIVITIES.items()):
            col, row = index % 2, index // 2
            x, y = 48 + col * 590, 202 + row * 64
            skill_name = SKILLS[activity["skill"]]
            rewards = [f"{amount} {item.replace('_', ' ')}" for item, amount in activity["drops"].items()]
            if activity.get("gold"):
                rewards.append(f"{activity['gold']} gold")
            reward_text = ", ".join(rewards) if rewards else "skill XP only"
            self.activity_buttons[activity_id] = self.button(
                x, y, 540, 50, f"{activity['name']}  ·  {skill_name}  ·  {reward_text}/cycle", 
                lambda key=activity_id: self._start(key), 15,
            )
        self.button(48, 630, 225, 52, "CLAIM COMPLETED WORK", self._claim, 14)
        self.button(290, 630, 170, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        self.city_label.set_text(f"Current city: {CITIES[character.current_city]['name']} · choose one repeating task")
        self.status_label.set_text(self.session.game.activity_status())
        selected_skill = self.WORK_FILTERS[list(self.WORK_FILTERS)[self.work_filter.selected_index]]
        for activity_id, button in self.activity_buttons.items():
            activity = ACTIVITIES[activity_id]
            button.visible = (activity["city"] == character.current_city and
                              (selected_skill is None or activity["skill"] == selected_skill))

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def update(self, dt: float) -> None:
        self._refresh_timer = getattr(self, "_refresh_timer", 0.0) + dt
        if self._refresh_timer >= 2.0:
            self._refresh_timer = 0.0
            self.status_label.set_text(self.session.game.activity_status())

    def _start(self, activity_id: str) -> None:
        try:
            prior = self.session.game.start_activity(activity_id)
            self.session.save()
            if prior and prior.cycles:
                self.notify(f"Collected {prior.cycles} completed cycles before changing tasks.")
            else:
                self.notify(f"Now assigned: {ACTIVITIES[activity_id]['name']}.")
            self._refresh()
        except GameError as exc:
            self.notify(str(exc))

    def _claim(self) -> None:
        result = self.session.game.claim_activity()
        self.session.save()
        summary = [result.message]
        if result.experience:
            summary.append(f"+{result.experience} skill XP")
        if result.gold:
            summary.append(f"+{result.gold} gold")
        if result.drops:
            summary.append(", ".join(f"{key.replace('_', ' ')} ×{value}" for key, value in result.drops.items()))
        if result.level_ups:
            summary.append("LEVEL UP: " + ", ".join(result.level_ups))
        self.notify(" · ".join(summary))
        self._refresh()


class CityScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Routes & city discoveries")
        self.label(48, 118, "Train a city's signature skill to open its road.", 18)
        self.city_lines: dict[str, TextLabel] = {}
        self.city_buttons: dict[str, Button] = {}
        for index, (city_id, city) in enumerate(CITIES.items()):
            col, row = index % 2, index // 2
            x, y = 48 + col * 590, 194 + row * 132
            self.city_lines[city_id] = self.label(x, y, "", 16)
            self.city_buttons[city_id] = self.button(
                x, y + 42, 500, 54, f"TRAVEL TO {city['name'].upper()}",
                lambda key=city_id: self._visit(key), 15,
            )
        self.button(48, 630, 200, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        for city_id, city in CITIES.items():
            unlocked = city_id in character.unlocked_cities
            current = city_id == character.current_city
            requirement = f"Requires {SKILLS[city['unlock_skill']]} {city['unlock_level']}" if city["unlock_skill"] else "Starting settlement"
            state = "CURRENT" if current else ("OPEN ROAD" if unlocked else "LOCKED")
            self.city_lines[city_id].set_text(f"{city['name']} · {state} · {requirement} · {city['description']}")
            self.city_buttons[city_id].enabled = unlocked and not current

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _visit(self, city_id: str) -> None:
        try:
            message = self.session.game.visit_city(city_id)
            self.session.save()
            self.engine.set_scene("rpg_activities")
            self.notify(message)
        except GameError as exc:
            self.notify(str(exc))


class SkillScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Skill book")
        self.level_label = self.label(48, 118, "", 19)
        self.skill_lines = [self.label(64, 168 + index * 42, "", 19) for index in range(len(SKILLS))]
        self.button(48, 630, 200, 52, "BACK TO TOWN", self.back_to_town, 14)

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        self.level_label.set_text(f"Adventurer level {character.level} · {character.experience}/{character.level * 100} XP to next level")
        for label, line in zip(self.skill_lines, self.session.game.skill_summary()):
            label.set_text(line)


class ForgeScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "The forge & weapon blueprints")
        self.city_note = self.label(48, 118, "", 18)
        self.inventory_note = self.label(48, 154, "", 16)
        self.recipe_notes: dict[str, TextLabel] = {}
        self.recipe_buttons: dict[str, Button] = {}
        for index, (recipe_id, recipe) in enumerate(RECIPES.items()):
            y = 220 + index * 128
            self.recipe_notes[recipe_id] = self.label(70, y, "", 16)
            self.recipe_buttons[recipe_id] = self.button(
                760, y - 16, 430, 56, f"FORGE {recipe['name'].upper()}",
                lambda key=recipe_id: self._craft(key), 15,
            )
        self.button(48, 630, 200, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        city_name = CITIES[character.current_city]["name"]
        equipped = RECIPES.get(character.equipped_weapon, {}).get("name", "none")
        self.city_note.set_text(f"Workshop: {city_name} · equipped weapon: {equipped}")
        inventory = ", ".join(f"{item.replace('_', ' ')} ×{amount}" for item, amount in character.inventory.items() if amount and item != "gold")
        self.inventory_note.set_text("Materials: " + (inventory or "none"))
        for recipe_id, recipe in RECIPES.items():
            requirements = ", ".join(f"{amount} {item.replace('_', ' ')}" for item, amount in recipe["materials"].items())
            self.recipe_notes[recipe_id].set_text(f"{recipe['description']}  ·  Requires {requirements}  ·  Blacksmithing {recipe['level']}")
            self.recipe_buttons[recipe_id].enabled = character.current_city == recipe["city"] and character.skills[recipe["skill"]]["level"] >= recipe["level"]

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _craft(self, recipe_id: str) -> None:
        try:
            self.notify(self.session.game.craft(recipe_id))
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()


class GuildScene(RPGScene):
    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Guild hall")
        self.status = self.label(48, 122, "", 18)
        self.contract = self.label(48, 166, "", 17)
        self.mission_select = Dropdown(48, 198, 470, 58, [mission["name"] for mission in GUILD_MISSIONS.values()],
                                       font_size=16, label="Guild mission", label_position="top")
        self.add_ui_element(self.mission_select)
        self.take_mission_button = self.button(540, 214, 250, 46, "GET MISSION", self._take_mission, 14)
        self.mission_status = self.label(820, 222, "", 15)
        self.guild_buttons: dict[str, Button] = {}
        for index, (guild_id, guild) in enumerate(GUILDS.items()):
            y = 244 + index * 100
            self.guild_buttons[guild_id] = self.button(
                74, y, 520, 58, f"JOIN {guild['name'].upper()}",
                lambda key=guild_id: self._join(key), 15,
            )
            self.label(620, y + 8, guild["description"], 15)
        self.claim_button = self.button(760, 560, 390, 58, "CLAIM COMPLETED CONTRACT", self._claim, 15)
        self.claim_mission_button = self.button(760, 500, 390, 52, "CLAIM MISSION", self._claim_mission, 15)
        self.button(48, 630, 200, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        if character.guild:
            guild = GUILDS[character.guild["id"]]
            progress = character.guild.get("contract_progress", 0)
            self.status.set_text(f"Member of {guild['name']} · {self.session.game.guild_rank(character.guild['reputation'])} · {character.guild['reputation']} reputation")
            self.contract.set_text(f"Contract: complete {guild['contract_cycles']} cycles of {ACTIVITIES[guild['contract_activity']]['name']} · {progress}/{guild['contract_cycles']}")
        else:
            self.status.set_text("Choose one guild. Membership, reputation, and contracts belong to each character.")
            self.contract.set_text("Guild contracts reward gold and reputation; ranks rise as contracts are claimed.")
        mission_id = character.guild.get("mission_id") if character.guild else None
        if mission_id in GUILD_MISSIONS:
            mission = GUILD_MISSIONS[mission_id]
            self.mission_status.set_text(f"{character.guild.get('mission_progress', 0)}/{mission['target_count']} defeated")
        else:
            self.mission_status.set_text("No mission accepted")
        for button in self.guild_buttons.values():
            button.visible = not bool(character.guild)
        self.claim_button.visible = bool(character.guild)
        self.mission_select.visible = bool(character.guild)
        self.take_mission_button.visible = bool(character.guild) and not mission_id
        self.claim_mission_button.visible = bool(character.guild) and bool(mission_id)

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _join(self, guild_id: str) -> None:
        try:
            self.notify(self.session.game.join_guild(guild_id))
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()

    def _claim(self) -> None:
        try:
            self.notify(self.session.game.claim_guild_contract())
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()

    def _take_mission(self) -> None:
        mission_id = list(GUILD_MISSIONS)[self.mission_select.selected_index]
        try:
            self.notify(self.session.game.take_guild_mission(mission_id))
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()

    def _claim_mission(self) -> None:
        try:
            self.notify(self.session.game.claim_guild_mission())
            self.session.save()
        except GameError as exc:
            self.notify(str(exc))
        self._refresh()


class NPCScene(RPGScene):
    TOPICS = (
        ("greeting", "GREET"),
        ("work", "ASK ABOUT WORK"),
        ("crafting", "ASK ABOUT CRAFTING"),
        ("guild", "ASK ABOUT GUILDS"),
        ("rumor", "ASK FOR A RUMOR"),
        ("farewell", "SAY GOODBYE"),
    )

    def __init__(self, engine: LunaEngine, session: GameSession):
        super().__init__(engine, session, "Hearthglade voices")
        self.npc_id = "Orlen"
        self.current_npc = self.label(48, 118, "", 20)
        self.dialogue = LongTextLabel(
            70, 174, "Choose a topic to begin the conversation.",
            width=1120, height=180, font_size=20, wrap_width=1120,
        )
        self.add_ui_element(self.dialogue)
        self.npc_buttons: dict[str, Button] = {}
        for index, npc_id in enumerate(NPCS["characters"]):
            col, row = index % 3, index // 3
            self.npc_buttons[npc_id] = self.button(
                48 + col * 400, 270 + row * 62, 350, 48, f"TALK TO {npc_id.upper()}",
                lambda key=npc_id: self._select_npc(key), 14,
            )
        for index, (topic, caption) in enumerate(self.TOPICS):
            col, row = index % 3, index // 3
            self.button(
                48 + col * 400, 418 + row * 66, 350, 50, caption,
                lambda key=topic: self._talk(key), 14,
            )
        self.button(48, 630, 200, 52, "BACK TO TOWN", self.back_to_town, 14)

    def _refresh(self) -> None:
        character = self.session.game.active_character
        if character is None:
            return
        local_npcs = CITIES[character.current_city]["npcs"]
        if self.npc_id not in local_npcs:
            self.npc_id = local_npcs[0]
        npc = NPCS["characters"][self.npc_id]
        self.current_npc.set_text(f"{self.npc_id} · {npc['occupation']} · {npc['personality']}")
        for npc_id, button in self.npc_buttons.items():
            button.visible = npc_id in local_npcs

    def on_enter(self, previous_scene: str | None = None, *args, **kwargs) -> None:
        self._refresh()

    def _select_npc(self, npc_id: str) -> None:
        self.npc_id = npc_id
        self._refresh()
        self._talk("greeting")

    def _talk(self, topic: str) -> None:
        try:
            self.dialogue.set_text(self.session.game.talk(self.npc_id, topic))
            self.session.save()
            self._refresh()
        except GameError as exc:
            self.notify(str(exc))

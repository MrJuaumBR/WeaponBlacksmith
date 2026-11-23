from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from data.rpg.domain import (
    MAX_OFFLINE_SECONDS,
    GameError,
    GameState,
    RPGGame,
)
from data.rpg.game_data import ENEMIES
from data.rpg.savegame import JsonSaveRepository, SaveCorruptionError


class RPGDomainTests(unittest.TestCase):
    def setUp(self):
        self.game = RPGGame()
        self.character = self.game.create_character("Aster", now=1_000)

    def test_character_roster_is_limited_to_three_and_names_are_unique(self):
        self.game.create_character("Rowan", now=1_001)
        self.game.create_character("Mira", now=1_002)
        with self.assertRaises(GameError):
            self.game.create_character("Fourth", now=1_003)
        with self.assertRaises(GameError):
            self.game.create_character("aster", now=1_004)

    def test_skill_progress_and_offline_collection_award_items_and_xp(self):
        self.game.start_activity("mine_copper", now=1_000)
        result = self.game.claim_activity(now=1_000 + 4 * 30)
        self.assertEqual(result.cycles, 4)
        self.assertEqual(result.drops["copper"], 4)
        self.assertEqual(self.character.inventory["copper"], 6)
        self.assertEqual(self.character.skills["mining"]["xp"], 48)
        self.assertEqual(self.character.experience, 24)

    def test_offline_rewards_are_capped_and_excess_backlog_is_discarded(self):
        self.game.start_activity("mine_copper", now=0)
        result = self.game.claim_activity(now=MAX_OFFLINE_SECONDS + 3_600)
        self.assertEqual(result.cycles, MAX_OFFLINE_SECONDS // 30)
        self.assertEqual(self.character.inventory["copper"], 2 + result.cycles)
        self.assertEqual(self.game.claim_activity(now=MAX_OFFLINE_SECONDS + 3_600).cycles, 0)

    def test_skill_level_unlocks_new_cities(self):
        self.game.start_activity("gather_oak", now=100)
        self.game.claim_activity(now=100 + 9 * 30)
        self.assertEqual(self.character.skills["woodcutting"]["level"], 2)
        self.assertIn("briarwatch", self.character.unlocked_cities)
        message = self.game.visit_city("briarwatch")
        self.assertIn("Exploration XP", message)
        self.assertEqual(self.character.current_city, "briarwatch")

    def test_forging_consumes_materials_and_equips_first_weapon(self):
        message = self.game.craft("copper_shortsword")
        self.assertIn("Hearthglade Shortsword", message)
        self.assertEqual(self.character.inventory["copper"], 0)
        self.assertEqual(self.character.inventory["wood"], 1)
        self.assertEqual(self.character.equipped_weapon, "copper_shortsword")
        with self.assertRaises(GameError):
            self.game.craft("copper_shortsword")

    def test_batch_crafting_and_max_crafting_consume_exact_materials(self):
        self.character.inventory["wood"] = 12
        self.character.inventory["copper"] = 10
        self.assertEqual(self.game.max_craftable("copper_shortsword"), 5)
        self.game.craft("copper_shortsword", 2)
        self.assertEqual(self.character.inventory["copper_shortsword"], 2)
        self.game.craft("copper_shortsword", self.game.max_craftable("copper_shortsword"))
        self.assertEqual(self.character.inventory["copper_shortsword"], 5)
        self.assertEqual(self.character.inventory["copper"], 0)
        self.assertEqual(self.character.inventory["wood"], 2)

    def test_selling_quantity_buttons_are_supported_by_domain_rules(self):
        self.character.inventory["wood"] = 8
        gold_before = self.character.inventory.get("gold", 0)
        price = self.game.sell_price("wood")
        self.game.sell("wood", 3)
        self.assertEqual(self.character.inventory["wood"], 5)
        self.assertEqual(self.character.inventory["gold"], gold_before + price * 3)
        self.game.sell("wood", self.game.max_sellable("wood"))
        self.assertEqual(self.character.inventory["wood"], 0)

    def test_guild_contract_progress_and_rank_rewards(self):
        self.game.join_guild("delvers_union")
        self.game.start_activity("mine_copper", now=200)
        self.game.claim_activity(now=200 + 4 * 30)
        gold_before = self.character.inventory.get("gold", 0)
        message = self.game.claim_guild_contract()
        self.assertIn("reputation", message)
        self.assertEqual(self.character.guild["reputation"], 20)
        self.assertEqual(self.character.inventory["gold"], gold_before + 30)
        with self.assertRaises(GameError):
            self.game.join_guild("ember_order")

    def test_yaml_enemy_catalog_and_guild_mission_progress(self):
        self.assertTrue({"goblin", "skeleton", "orc", "ogre", "slime", "kobold"}.issubset(ENEMIES))
        self.assertEqual(ENEMIES["goblin"]["name"], "Goblin")
        self.game.join_guild("ember_order")
        self.game.take_guild_mission("goblin_cleanup")
        self.character.current_city = "broken_reality"
        for _ in range(3):
            self.game.start_battle("goblin")
            while self.game.active_battle:
                self.game.battle_attack()
        self.assertEqual(self.character.guild["mission_progress"], 3)
        gold_before = self.character.inventory.get("gold", 0)
        self.game.claim_guild_mission()
        self.assertIsNone(self.character.guild["mission_id"])
        self.assertEqual(self.character.inventory["gold"], gold_before + 24)

    def test_npc_greeting_uses_first_meet_then_rotates_authored_lines(self):
        first = self.game.talk("Orlen", "greeting")
        second = self.game.talk("Orlen", "greeting")
        third = self.game.talk("Orlen", "greeting")
        self.assertIn("Aster", first)
        self.assertNotEqual(first, second)
        self.assertNotEqual(second, third)
        self.assertIn("Hearthglade", self.game.talk("Beth", "first_meet"))

    def test_npc_first_meeting_state_survives_save_roundtrip(self):
        self.game.talk("Orlen", "greeting")
        restored = RPGGame(GameState.from_dict(self.game.state.to_dict()))
        self.assertIn("Orlen", restored.active_character.met_npcs)
        self.assertTrue(restored.talk("Orlen", "greeting").startswith("'Back again"))

    def test_save_roundtrip_and_corruption_are_explicit(self):
        self.game.start_activity("sword_drills", now=300)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "save.json"
            repository = JsonSaveRepository(path)
            repository.save(self.game.state)
            loaded = repository.load()
            restored = RPGGame(loaded)
            self.assertEqual(restored.active_character.name, "Aster")
            self.assertEqual(restored.active_character.active_activity["id"], "sword_drills")
            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(SaveCorruptionError):
                repository.load()

    def test_save_state_rejects_more_than_three_characters(self):
        data = self.game.state.to_dict()
        data["characters"] = [data["characters"][0]] * 4
        with self.assertRaises(GameError):
            GameState.from_dict(data)


if __name__ == "__main__":
    unittest.main()

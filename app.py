from data.config import *
from lunaengine.ui import ThemeManager

from data.scripts.scenes import MainMenu, MaterialsScene, PatternsScene
from data.scripts.rpg_scenes import (
    ActivityScene,
    BattleScene,
    CharacterSelectScene,
    CityScene,
    CraftingHallScene,
    ForgeScene,
    GameSession,
    GuildScene,
    InventoryScene,
    ModsScene,
    NPCScene,
    SkillScene,
    TownScene,
)


def start():
    theme_path = APP_ROOT / "data" / "assets" / "ui" / "weapon_blacksmith_theme.json"
    theme_name = ThemeManager.load_custom_theme(theme_path, "weapon_blacksmith", overwrite=True)
    if not engine.set_global_theme(theme_name, dark=True):
        raise RuntimeError(f"Could not apply the custom theme {theme_name!r}")

    session = GameSession()
    engine.add_scene("main_menu", MainMenu)
    engine.add_scene("materials", MaterialsScene)
    engine.add_scene("patterns", PatternsScene)
    engine.add_scene("rpg_characters", lambda game: CharacterSelectScene(game, session))
    engine.add_scene("rpg_town", lambda game: TownScene(game, session))
    engine.add_scene("rpg_activities", lambda game: ActivityScene(game, session))
    engine.add_scene("rpg_inventory", lambda game: InventoryScene(game, session))
    engine.add_scene("rpg_cities", lambda game: CityScene(game, session))
    engine.add_scene("rpg_skills", lambda game: SkillScene(game, session))
    engine.add_scene("rpg_crafting_hall", lambda game: CraftingHallScene(game, session))
    engine.add_scene("rpg_forge", lambda game: ForgeScene(game, session))
    engine.add_scene("rpg_battle", lambda game: BattleScene(game, session))
    engine.add_scene("rpg_guild", lambda game: GuildScene(game, session))
    engine.add_scene("rpg_npcs", lambda game: NPCScene(game, session))
    engine.add_scene("rpg_mods", lambda game: ModsScene(game, session))
    engine.set_scene("main_menu")
    engine.run()


if __name__ == "__main__":
    start()

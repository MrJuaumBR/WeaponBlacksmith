from data.config import *

from data.scripts.scenes import MainMenu, MaterialsScene, PatternsScene


def start():
    engine.add_scene('main_menu', MainMenu)
    engine.add_scene('materials', MaterialsScene)
    engine.add_scene('patterns', PatternsScene)
    engine.set_scene('main_menu')

    engine.run()


if __name__ == "__main__":
    start()
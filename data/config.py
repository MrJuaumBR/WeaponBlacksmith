import os, sys
from pathlib import Path
from argparse import ArgumentParser

from lunaengine.core import LunaEngine, Scene
from lunaengine.storage import Atlas
from lunaengine.ui import *

from data.scripts.params import ParameterParser

APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent

APP_ATLAS = Atlas(APP_ROOT)
APP_ATLAS.add_alias("assets", APP_ROOT / "data" / "assets")

# Material icon sheet: one 32x32 white ingot at (0, 0).
# Registering it here lets SpriteSheet.from_atlas("textures", APP_ATLAS) work,
# and also lets the atlas bundle it if you ever run create_bundle().
APP_ATLAS.add_texture("textures", APP_ROOT / "data" / "assets" / "textures.png")

APP_ICON = APP_ROOT / "data" / "icon.png"

# -- CLI parameters ---------------------------------------------------------
PARAMS = ParameterParser(ArgumentParser(prog="Weapon Blacksmith"))

engine = LunaEngine(
    "Weapon Blacksmith",
    1280,
    720,
    fullscreen=PARAMS.fullscreen,
    icon=APP_ICON,
    debug=PARAMS.debug,
)

engine.atlas = APP_ATLAS
engine.updateRatio(1024, 720)

from data.scripts.yaml_handler import YAMLHandler

APP_YAML_HANDLER = YAMLHandler(
    APP_ROOT / "data" / "materials.yaml",
    APP_ROOT / "data" / "patterns.yaml",
    APP_ROOT / "data" / "crafts.yaml",
)
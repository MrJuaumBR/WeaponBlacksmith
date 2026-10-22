import os, sys
from pathlib import Path

from lunaengine.core import LunaEngine, Scene
from lunaengine.storage import Atlas
from lunaengine.ui import *

APP_ROOT = Path(os.path.dirname(os.path.abspath(__file__))).parent

APP_ATLAS = Atlas(APP_ROOT)
APP_ATLAS.add_alias("assets", APP_ROOT/'data'/'assets')

APP_ICON = APP_ROOT/'data'/'icon.png'

engine = LunaEngine("Weapon Blacksmith", 1280, 720, icon=APP_ICON, debug=True)
engine.atlas = APP_ATLAS
engine.updateRatio(1024, 720)

from data.scripts.yaml_handler import YAMLHandler
APP_YAML_HANDLER = YAMLHandler(APP_ROOT/'data'/'materials.yaml', APP_ROOT/'data'/'patterns.yaml', APP_ROOT/'data'/'crafts.yaml')
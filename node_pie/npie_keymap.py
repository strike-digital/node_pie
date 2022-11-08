import json
from pathlib import Path
import bpy
from .npie_ui import NPIE_MT_node_pie
"""For some reason, blender doesn't save modified keymaps when the addon is reloaded, so this stores the keymaps in a
config file in the presets directory. There is almost certainly a better way to do this, but I couldn't find it"""

addon_keymaps = []

DEFAULT_CONFIG = [
    {
        "type": "LEFTMOUSE",
        "value": "PRESS",
        "ctrl": True,
    },
    {
        "type": "A",
        "value": "PRESS",
        "ctrl": True,
    },
]

POSSIBLE_VALUES = {"type", "value", "shift", "ctrl", "alt", "oskey", "any", "key_modifier", "direction", "repeat"}


def kmi_from_config(config: dict, km: bpy.types.KeyMap):
    kmi = km.keymap_items.new("wm.call_menu_pie", **config)
    kmi.properties.name = NPIE_MT_node_pie.__name__
    addon_keymaps.append((km, kmi))


def config_from_kmi(kmi):
    config = {}
    for key in POSSIBLE_VALUES:
        config[key] = getattr(kmi, key)
    return config


PRESETS_PATH = Path(bpy.utils.resource_path("USER")) / "scripts" / "presets" / "node_pie"
try:
    PRESETS_PATH.mkdir()
except FileExistsError:
    pass

KEYMAP_FILE = PRESETS_PATH / "keymap.json"


def register():
    # Read saved keymap, or save and load the default one if not present
    if not KEYMAP_FILE.exists():
        with open(KEYMAP_FILE, "w") as f:
            json.dump(DEFAULT_CONFIG, f)

    with open(KEYMAP_FILE, "r") as f:
        try:
            keymap_config = json.load(f)
        except json.JSONDecodeError:
            keymap_config = DEFAULT_CONFIG

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')

        for config in keymap_config:
            kmi_from_config(config, km)


def unregister():
    configs = []
    for km, kmi in addon_keymaps:
        configs.append(config_from_kmi(kmi))
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # Save keymap to presets directory file
    with open(KEYMAP_FILE, "w") as f:
        json.dump(configs, f)

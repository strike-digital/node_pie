from pathlib import Path
import bpy
from bpy.types import Operator
from .npie_helpers import BOperator
"""For some reason, blender doesn't save modified keymaps when the addon is reloaded, so this stores the keymaps in a
config file in the presets directory. There is almost certainly a better way to do this, but I couldn't find it"""

addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []
KEYMAP: bpy.types.KeyMap = None

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

POSSIBLE_VALUES = ["type", "value", "shift", "ctrl", "alt", "oskey", "any", "key_modifier", "direction", "repeat"]


def kmi_from_config(config: dict, km: bpy.types.KeyMap, id: int):
    active = config.pop("active", True)
    kmi = km.keymap_items.new("node_pie.call_node_pie", **config)
    kmi.active = active
    kmi.properties.name = id
    addon_keymaps.append((km, kmi))


def config_from_kmi(kmi):
    config = {}
    for key in POSSIBLE_VALUES:
        config[key] = getattr(kmi, key)
    config["active"] = kmi.active
    return config


def get_user_kmi_from_addon_kmi(km_name, kmi_idname, prop_name):
    '''
    returns hotkey of specific type, with specific properties.name (keymap is not a dict, so referencing by keys is not enough
    if there are multiple hotkeys!),
    That can actually be edited by the user (not possible with)
    '''
    user_keymap = bpy.context.window_manager.keyconfigs.user.keymaps[km_name]
    for i, km_item in enumerate(user_keymap.keymap_items):
        if user_keymap.keymap_items.keys()[i] == kmi_idname:
            if user_keymap.keymap_items[i].properties.name == prop_name:
                return km_item
    return None  # not needed, since no return means None, but keeping for readability


KEYMAP_FILE = Path(__file__).parent / "keymap.json"

# commands = ["command1", "command2", "command3", "command4"]
# map_themes = ["map_theme"]

# for command, map_theme in zip(commands, map_themes):
#     exec()


def register():
    # Read saved keymap, or save and load the default one if not present
    # if not KEYMAP_FILE.exists():
    #     with open(KEYMAP_FILE, "w") as f:
    #         # print("*****Node Pie Debug*****")
    #         # print(f"file {KEYMAP_FILE} doesn't exist, creating default")
    #         json.dump(DEFAULT_CONFIG, f, indent=2)

    # with open(KEYMAP_FILE, "r") as f:
    #     try:
    #         keymap_config = json.load(f)
    #     except json.JSONDecodeError as e:
    #         print("*****Node Pie Debug*****")
    #         print("could not decode json")
    #         print(e)
    #         keymap_config = DEFAULT_CONFIG

    keymap_config = DEFAULT_CONFIG

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='View2D')
        global KEYMAP
        KEYMAP = km

        for i, config in enumerate(keymap_config):
            kmi_from_config(config, km, i)


def unregister():
    configs = []
    for km, kmi in addon_keymaps:
        configs.append(config_from_kmi(kmi))
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

    # # Save keymap to presets directory file
    # with open(KEYMAP_FILE, "w") as f:
    #     json.dump(configs, f, indent=2)


def draw_kmi(kmi: bpy.types.KeyMapItem, layout: bpy.types.UILayout):
    row = layout.row(align=True)
    map_type = kmi.map_type
    row.prop(kmi, "map_type", text="")
    if map_type == 'KEYBOARD':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'MOUSE':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'NDOF':
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == 'TWEAK':
        subrow = row.row()
        subrow.prop(kmi, "type", text="")
        subrow.prop(kmi, "value", text="")
    elif map_type == 'TIMER':
        row.prop(kmi, "type", text="")
    else:
        row.label()

    box = layout

    if map_type not in {'TEXTINPUT', 'TIMER'}:
        sub = box.column()
        subrow = sub.row(align=True)

        if map_type == 'KEYBOARD':
            subrow.prop(kmi, "type", text="", event=True)
            subrow.prop(kmi, "value", text="")
            subrow_repeat = subrow.row(align=True)
            subrow_repeat.active = kmi.value in {'ANY', 'PRESS'}
            subrow_repeat.prop(kmi, "repeat", text="", icon="FILE_REFRESH")
        elif map_type in {'MOUSE', 'NDOF'}:
            subrow.prop(kmi, "type", text="")
            subrow.prop(kmi, "value", text="")

        subrow = sub.row(align=True)
        subrow.scale_x = 0.75
        subrow.prop(kmi, "any", toggle=True)
        subrow.prop(kmi, "shift_ui", toggle=True)
        subrow.prop(kmi, "ctrl_ui", toggle=True)
        subrow.prop(kmi, "alt_ui", toggle=True)
        subrow.prop(kmi, "oskey_ui", text="Cmd", toggle=True)
        subrow.prop(kmi, "key_modifier", text="", event=True)


@BOperator("node_pie")
class NPIE_OT_edit_keymap_item(Operator):

    index: bpy.props.IntProperty()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.scale_y = 1.2
        km, kmi = addon_keymaps[self.index]
        draw_kmi(kmi, layout)

    def execute(self, context):
        return {"FINISHED"}


@BOperator("node_pie")
class NPIE_OT_remove_keymap_item(Operator):

    index: bpy.props.IntProperty()

    def execute(self, context):
        km, kmi = addon_keymaps.pop(self.index)
        km.keymap_items.remove(kmi)
        return {"FINISHED"}


@BOperator("node_pie")
class NPIE_OT_new_keymap_item(Operator):
    """Add a new keymap item for calling the node pie menu"""

    def execute(self, context):
        kmi_from_config(DEFAULT_CONFIG[0], KEYMAP, len(addon_keymaps) - 1)
        return {"FINISHED"}
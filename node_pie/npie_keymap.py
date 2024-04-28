import bpy
from bpy.types import Context, KeyMap

from .npie_btypes import BOperator
from .operators.op_call_link_drag import NPIE_OT_call_link_drag
from .operators.op_insert_node_pie import NPIE_OT_insert_node_pie

addon_keymaps: list[tuple[bpy.types.KeyMap, bpy.types.KeyMapItem]] = []


def get_operator_keymap_items(keymap: KeyMap, operator_idname: str) -> list[KeyMap]:
    return [kmi for kmi in keymap.keymap_items if kmi.idname == operator_idname]


def register():
    addon_keymaps.clear()

    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name="View2D")

        kmi = km.keymap_items.new(
            NPIE_OT_call_link_drag.bl_idname,
            type="LEFTMOUSE",
            value="PRESS",
            ctrl=True,
        )
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(
            NPIE_OT_call_link_drag.bl_idname,
            type="A",
            value="PRESS",
            ctrl=True,
        )
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(
            NPIE_OT_insert_node_pie.bl_idname,
            type="LEFTMOUSE",
            value="CLICK_DRAG",
            ctrl=True,
            alt=True,
        )
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()


def get_keymap() -> KeyMap:
    return bpy.context.window_manager.keyconfigs.user.keymaps["View2D"]


def draw_keymap_item(kmi: bpy.types.KeyMapItem, layout: bpy.types.UILayout):
    """Draw a keymap item in a prettier way than the default"""
    row = layout.row(align=True)
    map_type = kmi.map_type
    row.prop(kmi, "map_type", text="")
    if map_type == "KEYBOARD":
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == "MOUSE":
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == "NDOF":
        row.prop(kmi, "type", text="", full_event=True)
    elif map_type == "TWEAK":
        subrow = row.row()
        subrow.prop(kmi, "type", text="")
        subrow.prop(kmi, "value", text="")
    elif map_type == "TIMER":
        row.prop(kmi, "type", text="")
    else:
        row.label()

    box = layout

    if map_type not in {"TEXTINPUT", "TIMER"}:
        sub = box.column()
        subrow = sub.row(align=True)

        if map_type == "KEYBOARD":
            subrow.prop(kmi, "type", text="", event=True)
            subrow.prop(kmi, "value", text="")
            subrow_repeat = subrow.row(align=True)
            subrow_repeat.active = kmi.value in {"ANY", "PRESS"}
            subrow_repeat.prop(kmi, "repeat", text="", icon="FILE_REFRESH")
        elif map_type in {"MOUSE", "NDOF"}:
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
class NPIE_OT_edit_keymap_item(BOperator.type):

    index: bpy.props.IntProperty()

    operator: bpy.props.StringProperty()

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return self.call_popup(width=400)

    def draw(self, context: Context):
        km = get_keymap()
        kmi = get_operator_keymap_items(km, self.operator)[self.index]
        layout = self.layout
        layout.scale_y = 1.2
        row = layout.row(align=True)
        row.label(text="Edit keybind:")
        draw_keymap_item(kmi, layout)


@BOperator("node_pie")
class NPIE_OT_remove_keymap_item(BOperator.type):

    index: bpy.props.IntProperty()

    operator: bpy.props.StringProperty()

    def execute(self, context):
        km = get_keymap()
        kmi = get_operator_keymap_items(km, self.operator)[self.index]
        km.keymap_items.remove(kmi)


@BOperator("node_pie")
class NPIE_OT_new_keymap_item(BOperator.type):
    """Add a new keymap item for calling the node pie menu"""

    operator: bpy.props.StringProperty()

    type: bpy.props.StringProperty(default="LEFTMOUSE")

    value: bpy.props.StringProperty(default="PRESS")

    ctrl: bpy.props.BoolProperty()
    shift: bpy.props.BoolProperty()
    alt: bpy.props.BoolProperty()

    def execute(self, context):
        km = get_keymap()
        km.keymap_items.new(
            self.operator,
            self.type,
            self.value,
            ctrl=self.ctrl,
            shift=self.shift,
            alt=self.alt,
        )
        return {"FINISHED"}

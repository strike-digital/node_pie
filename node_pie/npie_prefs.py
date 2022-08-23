import bpy
from bpy.types import UILayout
from bpy.props import BoolProperty, FloatProperty
from ..shared.functions import get_prefs
from ..shared.ui import draw_enabled_button, draw_section, draw_inline_prop
from .npie_ui import NPIE_MT_node_pie


class NodePiePrefs():
    """Node pie"""

    layout: UILayout
    node_pie_enabled: BoolProperty(name="Enable node pie", default=True)

    npie_variable_sizes: BoolProperty(name="Use variable size", default=True)
    npie_normal_size: FloatProperty(name="Normal size", default=1)
    npie_max_size: FloatProperty(name="Max size", default=2.5)

    npie_freeze_popularity: BoolProperty(
        name="Freeze popularity",
        default=False,
        description="Prevent new changes the popularity of nodes.",
    )

    def draw(self, context):
        layout = self.layout
        layout = draw_enabled_button(layout, self, "node_pie_enabled")
        prefs = get_prefs(context)
        layout = layout.grid_flow(row_major=True, even_columns=True)

        col = draw_section(layout, "Node Popularity")
        fac = .515
        draw_inline_prop(col, prefs, "npie_variable_sizes", factor=fac)
        draw_inline_prop(col, prefs, "npie_normal_size", factor=fac)
        draw_inline_prop(col, prefs, "npie_max_size", factor=fac)

        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(prefs, "npie_freeze_popularity", text="Freeze popularity", icon="FREEZE", toggle=True)
        row.operator("node_pie.reset_popularity", icon="FILE_REFRESH")

        col = draw_section(layout, "Keymap")
        global addon_keymaps
        for km, kmi in addon_keymaps:
            row = col.row(align=True)
            row.active = kmi.active
            sub = row.row(align=True)
            sub.prop(kmi, "active", text="")
            sub = row.row(align=True)
            sub.scale_x = .5
            sub.prop(kmi, "type", full_event=True, text="")
            sub = row.row(align=True)
            sub.enabled = True
            sub.operator("preferences.keyitem_restore", text="", icon="X").item_id = kmi.id


addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')

        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type='LEFTMOUSE',
            value='PRESS',
            ctrl=True,
        )
        kmi.properties.name = NPIE_MT_node_pie.__name__
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type='A',
            value='PRESS',
            ctrl=True,
        )
        kmi.properties.name = NPIE_MT_node_pie.__name__
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

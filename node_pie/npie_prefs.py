import bpy
from bpy.types import UILayout
from bpy.props import BoolProperty, FloatProperty
from .npie_helpers import get_prefs
from .npie_ui import draw_section, draw_inline_prop
from .npie_keymap import addon_keymaps, get_user_kmi_from_addon_kmi


class NodePiePrefs(bpy.types.AddonPreferences):
    """Node pie"""

    bl_idname: str = __package__.split(".")[0]

    layout: UILayout
    node_pie_enabled: BoolProperty(name="Enable node pie", default=True)

    npie_variable_sizes: BoolProperty(
        name="Use variable size",
        default=True,
        description="Whether to increase the size of node buttons that are used most often",
    )

    npie_normal_size: FloatProperty(
        name="Normal size",
        default=1,
        description="The default size of the nodes buttons",
    )

    npie_max_size: FloatProperty(
        name="Max size",
        default=2.5,
        description="The size of the most popular nodes",
    )

    npie_show_node_groups: BoolProperty(
        name="Show node groups",
        default=True,
        description="Whether to show node groups in the pie menu or not",
    )

    npie_color_size: FloatProperty(
        name="Color bar size",
        default=.02,
        description="Having this value too low can cause the colors to disapear.",
        subtype="FACTOR",
        min=0,
        max=1,
    )

    npie_freeze_popularity: BoolProperty(
        name="Freeze popularity",
        default=False,
        description="Prevent new changes the popularity of nodes.",
    )

    npie_dev_extras: BoolProperty(
        name="Show dev extras",
        default=False,
        description="Show some operators in the right click menu to make creating custom definition files easier.",
    )

    npie_separator_headings: BoolProperty(
        name="Subcategory labels",
        default=True,
        description="Draw the headings of subcategories or just a gap",
    )

    def draw(self, context):
        layout = self.layout
        # layout = draw_enabled_button(layout, self, "node_pie_enabled")
        prefs = get_prefs(context)
        layout = layout.grid_flow(row_major=True, even_columns=True)

        fac = .515
        col = draw_section(layout, "Node Popularity")
        draw_inline_prop(col, prefs, "npie_variable_sizes", factor=fac)
        draw_inline_prop(col, prefs, "npie_normal_size", factor=fac)
        draw_inline_prop(col, prefs, "npie_max_size", factor=fac)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(prefs, "npie_freeze_popularity", text="Freeze popularity", icon="FREEZE", toggle=True)
        row.operator("node_pie.reset_popularity", icon="FILE_REFRESH")

        col = draw_section(layout, "General")
        draw_inline_prop(col, prefs, "npie_show_node_groups", factor=fac)
        draw_inline_prop(col, prefs, "npie_color_size", factor=fac)
        draw_inline_prop(col, prefs, "npie_separator_headings", factor=fac)
        draw_inline_prop(col, prefs, "npie_dev_extras", factor=fac)

        col = draw_section(layout, "Keymap")
        kc = bpy.context.window_manager.keyconfigs.user
        for i, (km, addon_kmi) in enumerate(addon_keymaps):
            kmi = addon_kmi
            try:
                # We need to get the user version of the keymap item so that they can be modified by the user.
                # I spent far too much time pulling my hair out over this. It really needs to be better on Blenders end.
                kmi = get_user_kmi_from_addon_kmi("View2D", addon_kmi.idname, addon_kmi.properties.name)
            except AttributeError:
                # the properties for the user keymap items are not created instantly on load, account for that.
                return

            row = col.row(align=True)
            row.active = kmi.active
            sub = row.row(align=True)
            sub.prop(kmi, "active", text="")
            sub = row.row(align=True)
            sub.scale_x = .5
            sub.prop(kmi, "type", full_event=True, text="")
            sub = row.row(align=True)
            sub.enabled = True
            op = sub.operator("node_pie.edit_keymap_item", text="", icon="GREASEPENCIL")
            op.index = i
            # if kmi.is_user_modified:
            #     op = sub.operator("preferences.keyitem_restore", text="", icon="BACK")
            #     op.item_id = kmi.id
            op = sub.operator("node_pie.remove_keymap_item", text="", icon="X")
            op.index = i
        col.operator("node_pie.new_keymap_item", text="", icon="ADD")

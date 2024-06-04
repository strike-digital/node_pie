import bpy
from bpy.props import BoolProperty, FloatProperty
from bpy.types import KeyMap, KeyMapItem, UILayout

from .npie_helpers import get_prefs
from .npie_keymap import get_keymap, get_operator_keymap_items
from .npie_ui import draw_inline_prop, draw_section
from .operators.op_call_link_drag import (
    NPIE_OT_call_link_drag,
    register_debug_handler,
    unregister_debug_handler,
)
from .operators.op_insert_node_pie import NPIE_OT_insert_node_pie
from .operators.op_show_info import InfoSnippets


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
        default=2,
        description="The size of the most popular nodes",
    )

    npie_show_node_groups: BoolProperty(
        name="Show node groups",
        default=True,
        description="Whether to show node groups in the pie menu or not",
    )

    npie_expand_node_groups: BoolProperty(
        name="Expand node groups",
        default=False,
        description="Whether to draw the node groups as a sub menu or as individual buttons",
    )

    npie_color_size: FloatProperty(
        name="Color bar size",
        default=0.02,
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

    npie_separator_headings: BoolProperty(
        name="Subcategory labels",
        default=True,
        description="Draw the headings of subcategories or just a gap",
    )

    npie_show_variants: BoolProperty(
        name="Show variants",
        default=True,
        description="Draw the variants menus for nodes that support them",
    )

    npie_show_icons: BoolProperty(
        name="Show icons",
        default=True,
        description="Draw icons for categories",
    )

    npie_dev_extras: BoolProperty(
        name="Show dev extras",
        default=False,
        description="Show some operators in the right click menu to make creating custom definition files easier.",
    )

    npie_use_link_dragging: BoolProperty(
        name="Enable link dragging",
        default=True,
        description="Allow automatically connecting the new node to a socket if it is hovered",
    )

    npie_link_drag_disable_invalid: BoolProperty(
        name="Disable invalid nodes",
        default=True,
        description="Grey out nodes that are no able to be connected when using link drag or link insert",
    )

    def draw_debug_update(self, context):
        if self.npie_draw_debug_lines:
            register_debug_handler()
        else:
            unregister_debug_handler()

    npie_draw_debug_lines: BoolProperty(
        name="Draw debug boxes",
        default=False,
        description="Draw some debug lines to show the bounding box for clicking a node socket for drag linking.",
        update=draw_debug_update,
    )

    npie_socket_separation: FloatProperty(
        name="Socket separation",
        default=22,
        description="The vertical distance between node sockets.\
            This should only be changed if you use a high or low UI scale,\
            and drag linking doesn't work as a result.".replace(
            "  ", ""
        ),
        subtype="PIXEL",
    )

    def draw(self, context):
        layout = self.layout
        # layout = draw_enabled_button(layout, self, "node_pie_enabled")
        prefs = get_prefs(context)
        layout = layout.grid_flow(row_major=True, even_columns=True)
        fac = 0.515

        col = draw_section(layout, "General")
        col.scale_y = 0.9
        draw_inline_prop(col, prefs, "npie_show_icons", factor=fac)
        draw_inline_prop(col, prefs, "npie_show_variants", factor=fac)
        draw_inline_prop(col, prefs, "npie_separator_headings", factor=fac)
        draw_inline_prop(col, prefs, "npie_expand_node_groups", factor=fac)
        draw_inline_prop(col, prefs, "npie_dev_extras", factor=fac)
        draw_inline_prop(col, prefs, "npie_color_size", factor=fac)

        col = draw_section(layout, "Node Size")
        draw_inline_prop(col, prefs, "npie_variable_sizes", factor=fac)
        draw_inline_prop(col, prefs, "npie_normal_size", factor=fac)
        draw_inline_prop(col, prefs, "npie_max_size", factor=fac)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.prop(
            prefs,
            "npie_freeze_popularity",
            text="Unfreeze popularity" if prefs.npie_freeze_popularity else "Freeze popularity",
            icon="FREEZE",
            toggle=True,
        )
        row.operator("node_pie.reset_popularity", icon="FILE_REFRESH")

        col = draw_section(layout, "On Link Drag")
        draw_inline_prop(col, prefs, "npie_use_link_dragging", factor=fac)
        if prefs.npie_use_link_dragging:
            draw_inline_prop(col, prefs, "npie_link_drag_disable_invalid", factor=fac)
            draw_inline_prop(col, prefs, "npie_draw_debug_lines", factor=fac)
            if prefs.npie_draw_debug_lines:
                draw_inline_prop(col, prefs, "npie_socket_separation", factor=fac)
        InfoSnippets.link_drag.draw(col)

        def draw_op_kmis(keymap: KeyMap, operator: str, text: str, properties: dict = {}, default_new: dict = {}):
            row = col.row(align=True)
            row.scale_y = 0.8
            row.label(text=text)

            row = row.row(align=True)
            row.alignment = "RIGHT"
            op = row.operator("node_pie.new_keymap_item", text="", icon="ADD", emboss=False)
            op.operator = operator
            for name, arg in default_new.items():
                setattr(op, name, arg)

            kmis = get_operator_keymap_items(keymap, operator)
            for i, kmi in enumerate(kmis):
                kmi: KeyMapItem

                # Check that properties are the same
                matches = True
                for key, value in properties.items():
                    if getattr(kmi.properties, key) != value:
                        matches = False
                        break
                if not matches:
                    continue

                row = col.row(align=True)
                row.active = kmi.active
                sub = row.row(align=True)
                sub.prop(kmi, "active", text="")
                sub = row.row(align=True)
                sub.scale_x = 0.5
                sub.prop(kmi, "type", full_event=True, text="")
                sub = row.row(align=True)
                sub.enabled = True

                # TODO get this working, currently doesn't save with the keymap
                # if hasattr(kmi.properties, "pass_through"):
                #     sub.prop(kmi.properties, "pass_through", text="", icon="IPO_EASE_IN_OUT", invert_checkbox=True)

                op = sub.operator("node_pie.edit_keymap_item", text="", icon="GREASEPENCIL")
                op.index = i
                op.operator = operator
                # if kmi.is_user_modified:
                #     op = sub.operator("preferences.keyitem_restore", text="", icon="BACK")
                #     op.item_id = kmi.id
                op = sub.operator("node_pie.remove_keymap_item", text="", icon="X")
                op.index = i
                op.operator = operator

        col = draw_section(layout, "Keymap")
        km = get_keymap()
        draw_op_kmis(km, NPIE_OT_call_link_drag.bl_idname, "Pie menu:")
        col.separator()
        draw_op_kmis(km, NPIE_OT_insert_node_pie.bl_idname, "Link insert:", default_new={"value": "CLICK_DRAG"})

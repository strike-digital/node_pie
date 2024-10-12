import bpy
from bpy.types import UILayout

from .npie_helpers import get_all_def_files, get_prefs
from .operators.op_generate_socket_types_file import NPIE_OT_generate_socket_types_file


def context_menu_draw(self, context):
    prefs = get_prefs(context)
    if not prefs.npie_dev_extras:
        return
    layout: UILayout = self.layout
    layout.separator()
    layout.label(text="Node Pie Utilities:", icon="NODE")
    op = layout.operator("node_pie.open_definition_file", text="Open example definition file")
    op.example = True

    for file in get_all_def_files():
        if file.name == f"{context.space_data.tree_type}.jsonc":
            word = "Open"
            break
    else:
        word = "Create"
    op = layout.operator("node_pie.open_definition_file", text=f"{word} definition file for this node tree type")
    op.example = False
    layout.operator("node_pie.copy_nodes_as_json")
    NPIE_OT_generate_socket_types_file.draw_button(layout)


def register():
    bpy.types.NODE_MT_context_menu.append(context_menu_draw)


def unregister():
    bpy.types.NODE_MT_context_menu.remove(context_menu_draw)

from bpy.types import UILayout
from .operators.op_copy_type_to_selected_nodes import NPIE_OT_copy_type_to_selected_nodes

from .npie_btypes import BPanel
from .npie_helpers import NpieCache


@BPanel(
    space_type="NODE_EDITOR",
    region_type="UI",
    label="Node Pie",
    parent="NODE_PT_active_node_generic",
    auto_register=False,
)
class NPIE_PT_node_info(BPanel.type):
    def draw(self, context):
        layout: UILayout = self.layout
        node = context.active_node

        if not NpieCache.categories:
            layout.label(text="Definition file not cached yet")
            return

        node_props = node.node_pie
        row = layout.row(align=True)
        row.prop(node_props, "type")
        NPIE_OT_copy_type_to_selected_nodes.draw_button(row, "", icon="COPYDOWN")

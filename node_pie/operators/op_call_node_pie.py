import bpy
from ..npie_btypes import BOperator
from ..npie_custom_pies import NodeItem, load_custom_nodes_info
from ..npie_ui import NPIE_MT_node_pie, get_variants_menu


@BOperator("node_pie")
class NPIE_OT_call_node_pie(BOperator.type):
    """Call the node pie menu"""

    name: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def execute(self, context):
        # The variants menus can't be added in a draw function, so add them here beforehand
        categories, cat_layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
        has_node_file = categories != {}
        if has_node_file:
            for cat_name, category in categories.items():
                for node in category.nodes:
                    if isinstance(node, NodeItem) and node.variants:
                        get_variants_menu(cat_name, node.idname, node.variants)

        area = context.area
        bpy.ops.wm.call_menu_pie("INVOKE_DEFAULT", name=NPIE_MT_node_pie.__name__)
        return {"FINISHED"}
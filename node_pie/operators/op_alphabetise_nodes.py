from bpy.types import Node, NodeTree

from ..npie_btypes import BOperator


@BOperator(label="Alphabetise Nodes", undo=True)
class NPIE_OT_alphabetise_nodes(BOperator.type):
    """Arrange the selected nodes in alphabetical order"""

    def execute(self, context):
        node_tree: NodeTree = context.space_data.edit_tree
        selected_nodes: list[Node] = context.selected_nodes

        pos = [min(n.location.x for n in selected_nodes), min(n.location.y for n in selected_nodes)]
        selected_nodes.sort(key=lambda n: n.bl_label)

        for node in selected_nodes:
            node.location = pos
            pos[0] += node.width + 10

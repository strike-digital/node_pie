

from ..npie_btypes import BOperator


@BOperator(label="Copy Type to Selected", undo=True)
class NPIE_OT_copy_type_to_selected_nodes(BOperator.type):
    """Copy the node type from the active node to all other selected nodes"""

    def execute(self, context):
        active_node = context.active_node
        selected_nodes = context.selected_nodes

        for node in selected_nodes:
            if node != active_node:
                node.node_pie.type = active_node.node_pie.type

        return self.FINISHED
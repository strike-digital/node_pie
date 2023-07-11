import bpy
from bpy.types import Context, Event, NodeTree
from ..npie_ui import NPIE_MT_node_pie
from ..npie_btypes import BOperator


@BOperator("node_pie", undo=True)
class NPIE_OT_insert_node_pie(BOperator.type):
    """Allow user to draw over a node link, call the node pie and insert the chosen node into the link"""

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def invoke(self, context, event):
        self.quit = False
        self.start_names = {n.name for n in context.space_data.node_tree.nodes}

        # Call the reroute operator as a quick way to get which links have been dragged over
        bpy.ops.node.add_reroute("INVOKE_DEFAULT")
        self.cursor.set_icon(self.cursor.PICK_AREA)
        return self.start_modal()

    def modal(self, context: Context, event: Event):
        node_tree: NodeTree = context.space_data.node_tree
        self.cursor.set_icon(self.cursor.DOT)

        if event.type in {"RIGHTMOUSE", "ESC"} or self.quit:
            nodes = node_tree.nodes
            end_names = {n.name for n in nodes}
            new_nodes = list(end_names - self.start_names)
            if new_nodes:
                # Remove the newly created reroutes
                for new_node in new_nodes[::-1]:
                    new_node = nodes[new_node]
                    from_socket = new_node.inputs[0].links[0].from_socket
                    to_sockets = [l.to_socket for l in new_node.outputs[0].links]

                    for s in to_sockets:
                        node_tree.links.new(from_socket, s)
                    nodes.remove(new_node)

                # Call the node pie
                NPIE_MT_node_pie.from_socket = from_socket
                NPIE_MT_node_pie.to_sockets = to_sockets
                bpy.ops.node_pie.call_node_pie("INVOKE_DEFAULT", reset_args=False)

            self.cursor.reset_icon()
            return self.FINISHED

        elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
            self.quit = True
            return self.PASS_THROUGH

        return self.PASS_THROUGH
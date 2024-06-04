import json
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from bpy.types import Context, NodeTree

from ..npie_btypes import BOperator
from ..npie_constants import NODE_DEF_SOCKETS
from ..npie_custom_pies import NodeItem, load_custom_nodes_info
from . import op_add_node
from .op_call_link_drag import NPIE_OT_call_link_drag


@dataclass
class DummySocket:
    bl_idname: str
    is_output: bool


def generate_node_socket_info(context: Context, path: Path):
    categories, layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
    all_nodes: list[NodeItem] = []
    for cat in categories.values():
        for node_type in cat.nodes:
            if isinstance(node_type, NodeItem):
                all_nodes.append(node_type)

    data = {}
    node_tree: NodeTree = context.space_data.edit_tree
    for node_type in all_nodes:
        node = node_tree.nodes.new(node_type.idname)
        node_data = {}
        node_data["inputs"] = set()
        node_data["outputs"] = set()
        for socket_type in op_add_node.all_types:
            op_add_node.set_node_settings(DummySocket(socket_type, True), node)
            for socket in node.inputs:
                node_data["inputs"].add(socket.bl_idname)
            for socket in node.outputs:
                node_data["outputs"].add(socket.bl_idname)

        node_data["inputs"] = list(node_data["inputs"])
        node_data["outputs"] = list(node_data["outputs"])
        data[node_type.idname] = node_data
        node_tree.nodes.remove(node)
    data_str = json.dumps(data, indent=2)
    data_str = (
        "// This is a list of the socket types of all nodes"
        + "\n// used for telling whether a node is valid during link drag."
        + "\n// It can be auto generated using the 'generate socket types file' operator\n"
        + data_str
    )
    with open(path, "w") as f:
        f.write(data_str)
    return data


@BOperator("node_pie")
class NPIE_OT_generate_socket_types_file(BOperator.type):
    """Generate a socket types file for this node tree type.
    This is used to disable node items that are not compatible during link dragging or inserting."""

    poll = NPIE_OT_call_link_drag.poll

    def invoke(self, context, event):
        node_tree: NodeTree = context.space_data.edit_tree
        self.tree_type = node_tree.bl_rna.identifier
        self.to_path = NODE_DEF_SOCKETS / f"{self.tree_type}_sockets.jsonc"
        generate_node_socket_info(context, self.to_path)
        return self.call_popup_confirm(width=500)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Successfully generated socket types for node tree {self.tree_type}")
        layout.label(text="Open file?")

    def execute(self, context):
        webbrowser.open(self.to_path)

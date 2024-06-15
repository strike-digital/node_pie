import json
import webbrowser
from dataclasses import dataclass
from pathlib import Path

import bpy
from bpy.types import Context, NodeTree

from ..npie_btypes import BOperator
from ..npie_constants import NODE_DEF_SOCKETS
from ..npie_node_def_file import NodeItem, load_custom_nodes_info
from ..npie_node_info import ALL_TYPES, get_node_socket_info
from . import op_add_node
from .op_call_link_drag import NPIE_OT_call_link_drag


@dataclass
class DummySocket:
    bl_idname: str
    is_output: bool


def generate_node_socket_info(context: Context, tree_type: str, directory: Path):
    categories, layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
    all_nodes: list[NodeItem] = []
    for cat in categories.values():
        for node_type in cat.nodes:
            if isinstance(node_type, NodeItem):
                all_nodes.append(node_type)

    data = {}
    data["bl_version"] = bpy.app.version[:2]
    all_node_data = {}
    node_tree: NodeTree = context.space_data.edit_tree
    for node_type in all_nodes:
        node = node_tree.nodes.new(node_type.idname)
        node_data = {}
        inputs = set()
        outputs = set()
        for socket_type in ALL_TYPES:
            op_add_node.set_node_settings(DummySocket(socket_type, True), node, ui=False)
            for socket in node.inputs:
                inputs.add(socket.bl_idname)
            for socket in node.outputs:
                outputs.add(socket.bl_idname)

        node_data["inputs"] = list(inputs)
        node_data["outputs"] = list(outputs)
        all_node_data[node_type.idname] = node_data
        node_tree.nodes.remove(node)

    # Remove nodes that have already been defined in a previous socket file
    version = list(bpy.app.version)
    version[1] -= 1
    prev_data = get_node_socket_info(tree_type, max_bl_version=version)
    if prev_data:
        for name, sockets in prev_data.items():
            if name not in all_node_data.keys():
                continue
            node_data = all_node_data[name]
            if set(sockets["inputs"]) != set(node_data["inputs"]):
                continue
            if set(sockets["outputs"]) != set(node_data["outputs"]):
                continue

            del all_node_data[name]

    if not all_node_data:
        return None

    data["nodes"] = all_node_data
    data_str = json.dumps(data, indent=2)
    data_str = (
        "// This is a list of the socket types of all nodes"
        + "\n// used for telling whether a node is valid during link drag."
        + "\n// It contains all of the new and updated nodes in this blender version."
        + "\n// It can be auto generated using the 'generate socket types file' operator\n"
        + data_str
    )

    version_str = "_".join(str(i) for i in bpy.app.version[:2])
    path = directory / f"{tree_type}_sockets_{version_str}.jsonc"
    with open(path, "w") as f:
        f.write(data_str)
    return path


@BOperator("node_pie")
class NPIE_OT_generate_socket_types_file(BOperator.type):
    """Generate a socket types file for this node tree type.
    This is used to disable node items that are not compatible during link dragging or inserting."""

    poll = NPIE_OT_call_link_drag.poll

    def invoke(self, context, event):
        node_tree: NodeTree = context.space_data.edit_tree
        self.tree_type = node_tree.bl_rna.identifier
        self.to_path = generate_node_socket_info(context, self.tree_type, NODE_DEF_SOCKETS)
        if not self.to_path:
            self.report({"INFO"}, "No new socket information in this blender version")
            return self.FINISHED
        return self.call_popup_confirm(width=500)

    def draw(self, context):
        layout = self.layout
        layout.label(text=f"Successfully generated socket types for node tree {self.tree_type}")
        layout.label(text="Open file?")

    def execute(self, context):
        webbrowser.open(self.to_path)

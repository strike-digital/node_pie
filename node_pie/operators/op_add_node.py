import json
from typing import OrderedDict

import bpy
from bpy.types import Node, NodeSocket, NodeTree

from ..npie_btypes import BOperator
from ..npie_constants import POPULARITY_FILE, POPULARITY_FILE_VERSION
from ..npie_node_info import ALL_TYPES, COMPARE_TYPES, EXCLUSIVE_SOCKETS, SWITCH_TYPES
from ..npie_ui import NPIE_MT_node_pie, get_popularity_id


def set_node_settings(socket: NodeSocket, node: Node, ui: bool = True):
    """Set a nodes settings so that the correct type of socket is visible.
    If ui is false don't make any changes that might be better for the user."""
    # Make sure that the node has the correct data type
    # exclude bool if ui so that bool inputs are put into switch rather than true or false socket
    if node.bl_idname == "GeometryNodeSwitch" and not (
        socket.bl_idname.startswith("NodeSocketBool") and ui and socket.is_output
    ):
        try:
            name = next(s for s in SWITCH_TYPES if socket.bl_idname.startswith(s))
        except StopIteration:
            return
        node.input_type = SWITCH_TYPES[name]

    elif node.bl_idname == "FunctionNodeCompare" and socket.is_output:
        try:
            name = next(s for s in COMPARE_TYPES if socket.bl_idname.startswith(s))
        except StopIteration:
            return
        node.data_type = COMPARE_TYPES[name]

    elif hasattr(node, "data_type"):
        name = next(s for s in ALL_TYPES if socket.bl_idname.startswith(s))
        for data_type in ALL_TYPES[name]:
            try:
                node.data_type = data_type
            except TypeError:
                pass


def get_socket(from_socket, to_sockets):
    """
    Try to find the best match of from socket in to_sockets based on socket types.
    Is agnostic to whether sockets are inputs or outputs.
    """
    if not to_sockets:
        return

    socket = None
    for s in to_sockets:
        if s.bl_idname != from_socket.bl_idname:
            if s.bl_idname in EXCLUSIVE_SOCKETS or from_socket.bl_idname in EXCLUSIVE_SOCKETS:
                continue
        socket = s
        break
    if not socket:
        socket = to_sockets[0]
    return socket


def handle_node_linking(socket: NodeSocket, node: Node):
    """Make the optimal link between a node and a socket, taking into account socket types"""

    if socket.is_output:
        inputs = [s for s in node.inputs if s.enabled and not s.hide]
        to_socket = get_socket(socket, inputs)
        from_socket = socket
    else:
        outputs = [s for s in node.outputs if s.enabled and not s.hide]
        from_socket = get_socket(socket, outputs)
        to_socket = socket

    if from_socket and to_socket:
        node.id_data.links.new(from_socket, to_socket)


@BOperator("node_pie", idname="add_node", undo=True)
class NPIE_OT_add_node(BOperator.type):
    """Add a node to the node tree, and increase its popularity by 1"""

    type: bpy.props.StringProperty(name="Type", description="Node type to add", default="FunctionNodeInputVector")
    group_name: bpy.props.StringProperty(name="Group name", description="The name of the node group to add")
    use_transform: bpy.props.BoolProperty(default=True)

    settings: bpy.props.StringProperty(
        name="Settings",
        description="Settings to be applied on the newly created node",
        default="{}",
        options={"SKIP_SAVE"},
    )

    def execute(self, context):
        try:
            bpy.ops.node.add_node(
                "INVOKE_DEFAULT",
                False,
                type=self.type,
                use_transform=self.use_transform,
            )
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {"CANCELLED"}

        node_tree: NodeTree = context.area.spaces.active.path[-1].node_tree
        node = node_tree.nodes.active
        if self.group_name:
            node.node_tree = bpy.data.node_groups[self.group_name]

        # If being added by dragging from a socket
        if socket := NPIE_MT_node_pie.from_socket:
            set_node_settings(socket, node)

        # Set the settings for the node
        settings = eval(self.settings)
        for name, value in settings.items():
            name = "node." + name
            attr = ".".join(name.split(".")[:-1])
            name = name.split(".")[-1]
            setattr(eval(attr), name, value)

        # If being added by dragging from a socket
        if socket := NPIE_MT_node_pie.from_socket:
            handle_node_linking(socket, node)

        # If being added by dragging from a socket
        if sockets := NPIE_MT_node_pie.to_sockets:
            for socket in sockets:
                handle_node_linking(socket, node)

        with open(POPULARITY_FILE, "r") as f:
            if text := f.read():
                try:
                    data = json.loads(text)
                except json.decoder.JSONDecodeError:
                    data = {}
            else:
                data = {}

        version = data.get("version", POPULARITY_FILE_VERSION)

        if version[0] > POPULARITY_FILE_VERSION[0]:
            self.report({"ERROR"}, "Saved nodes file is from a newer version of the addon")
            return {"CANCELLED"}

        trees = data.get("node_trees", {})
        nodes = OrderedDict(trees.get(node_tree.bl_rna.identifier, {}))
        key = get_popularity_id(self.type, self.settings)
        node = nodes.get(key, {})
        count = node.get("count", 0)
        count += 1

        data["version"] = POPULARITY_FILE_VERSION
        node["count"] = count
        nodes[key] = node
        # Sort the nodes in descending order
        nodes = OrderedDict(sorted(nodes.items(), key=lambda item: item[1].get("count", 0), reverse=True))
        trees[node_tree.bl_rna.identifier] = nodes
        data["node_trees"] = trees

        with open(POPULARITY_FILE, "w") as f:
            json.dump(data, f, indent=4)

        return {"PASS_THROUGH"}

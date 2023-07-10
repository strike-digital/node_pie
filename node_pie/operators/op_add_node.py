import bpy
from bpy.types import NodeTree
from ..npie_btypes import BOperator
from ..npie_constants import POPULARITY_FILE, POPULARITY_FILE_VERSION
from ..npie_ui import NPIE_MT_node_pie, get_popularity_id

import json
from typing import OrderedDict


@BOperator("node_pie", idname="add_node", undo=True)
class NPIE_OT_add_node(BOperator.type):
    """Add a node to the node tree, and increase its poularity by 1"""

    type: bpy.props.StringProperty(name="Type", description="Node type to add", default="FunctionNodeInputVector")
    group_name: bpy.props.StringProperty(name="Group name", description="The name of the node group to add")
    use_transform: bpy.props.BoolProperty(default=True)

    settings: bpy.props.StringProperty(
        name="Settings",
        description="Settings to be applied on the newly created node",
        default="{}",
        options={'SKIP_SAVE'},
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
            return {'CANCELLED'}

        node_tree: NodeTree = context.area.spaces.active.path[-1].node_tree
        node = node_tree.nodes.active
        if self.group_name:
            node.node_tree = bpy.data.node_groups[self.group_name]

        # If being added by dragging from a socket
        if socket := NPIE_MT_node_pie.from_socket:
            exclusive_sockets = {"Material", "Object", "Collection", "Geometry", "Shader", "String", "Image"}
            exclusive_sockets = {"NodeSocket" + s for s in exclusive_sockets}

            # Try to find the best link based on the socket types
            def get_socket(from_socket, sockets):
                socket = None
                for s in sockets:
                    if s.bl_idname != from_socket.bl_idname:
                        if s.bl_idname in exclusive_sockets or from_socket.bl_idname in exclusive_sockets:
                            continue
                    socket = s
                    break
                if not socket:
                    socket = sockets[0]
                return socket

            if socket.is_output:
                inputs = [s for s in node.inputs if s.enabled and not s.hide]
                to_socket = get_socket(socket, inputs)
                from_socket = socket
            else:
                outputs = [s for s in node.outputs if s.enabled and not s.hide]
                from_socket = get_socket(socket, outputs)
                to_socket = socket
            node_tree.links.new(from_socket, to_socket)

        # Set the settings for the node
        settings = eval(self.settings)
        for name, value in settings.items():
            name = "node." + name
            attr = ".".join(name.split(".")[:-1])
            name = name.split(".")[-1]
            setattr(eval(attr), name, value)

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
            return {'CANCELLED'}

        trees = data.get("node_trees", {})
        nodes = OrderedDict(trees.get(node_tree.bl_rna.identifier, {}))
        key = get_popularity_id(self.type, self.settings)
        node = nodes.get(key, {})
        count = node.get("count", 0)
        count += 1

        data["version"] = POPULARITY_FILE_VERSION
        node["count"] = count
        nodes[key] = node
        # Sort the nodes in decending order
        nodes = OrderedDict(sorted(nodes.items(), key=lambda item: item[1].get("count", 0), reverse=True))
        trees[node_tree.bl_rna.identifier] = nodes
        data["node_trees"] = trees

        with open(POPULARITY_FILE, "w") as f:
            json.dump(data, f, indent=4)

        # from pprint import pprint
        # pprint(list(bpy.utils.manual_map()))
        # url = get_docs_url(self.type)
        # print(get_docs_url(self.type))
        # webbrowser.open(url)
        return {'PASS_THROUGH'}
import bpy
from ..npie_btypes import BOperator
from ..npie_constants import POPULARITY_FILE, POPULARITY_FILE_VERSION
from ..npie_ui import get_popularity_id


import json
from typing import OrderedDict


@BOperator("node_pie", idname="add_node", undo=True)
class NPIE_OT_node_pie_add_node(BOperator.type):
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

        node_tree = context.area.spaces.active.path[-1].node_tree
        node = node_tree.nodes.active
        if self.group_name:
            node.node_tree = bpy.data.node_groups[self.group_name]

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
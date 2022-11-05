import bpy
import json
from bpy.types import Operator, UILayout
from collections import OrderedDict
from .npie_helpers import Op
from .npie_constants import POPULARITY_FILE, POPULARITY_FILE_VERSION


@Op("node_pie", idname="add_node", undo=True)
class NPIE_OT_node_pie_add_node(Operator):
    """Add a node to the node tree, and increase its polularity by 1"""

    type: bpy.props.StringProperty(name="Type", description="Node type to add", default="FunctionNodeInputVector")
    group_name: bpy.props.StringProperty(name="Group name", description="The name of the node group to add")
    use_transform: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        try:
            bpy.ops.node.add_node("INVOKE_DEFAULT", False, type=self.type, use_transform=self.use_transform)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {'CANCELLED'}

        node_tree = context.area.spaces.active.path[-1].node_tree
        if self.group_name:
            print(node_tree)
            node = node_tree.nodes.active
            node.node_tree = bpy.data.node_groups[self.group_name]
        # node_tree = context.space_data.node_tree
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
        node = nodes.get(self.type, {})
        count = node.get("count", 0)
        count += 1

        data["version"] = POPULARITY_FILE_VERSION
        node["count"] = count
        nodes[self.type] = node
        # Sort the nodes in decending order
        nodes = OrderedDict(sorted(nodes.items(), key=lambda item: item[1].get("count", 0), reverse=True))
        trees[node_tree.bl_rna.identifier] = nodes
        data["node_trees"] = trees

        with open(POPULARITY_FILE, "w") as f:
            json.dump(data, f, indent=4)
        return {'PASS_THROUGH'}


@Op("node_pie")
class NPIE_OT_reset_popularity(Operator):
    """Reset the popularity of all nodes back to zero"""

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout: UILayout = self.layout
        box = layout.box()
        box.alert = True
        col = box.column(align=True)
        col.scale_y = .8
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Warning!")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="This will reset the popularity of all nodes back to zero.")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="This cannot be undone.")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Continue anyway?")

    def execute(self, context):
        with open(POPULARITY_FILE, "w"):
            pass
        self.report({"INFO"}, "Node popularity successfully reset")
        return {"FINISHED"}


@Op("node_pie")
class NPIE_OT_new_keymap_item(Operator):
    """Reset the popularity of all nodes back to zero"""
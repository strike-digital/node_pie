import bpy
import json
from pathlib import Path
from bpy.types import Operator
from . import FILE_VERSION


class STRIKE_OT_node_pie_add(Operator):
    """Add a node to the node tree"""
    bl_idname = "node_pie.add_node"
    bl_label = "Add node"
    bl_options = {'REGISTER', 'UNDO'}

    type: bpy.props.StringProperty(name="Type", description="Node type to add", default="FunctionNodeInputVector")
    use_transform: bpy.props.BoolProperty(default=True)

    def execute(self, context):
        try:
            bpy.ops.node.add_node("INVOKE_DEFAULT", False, type=self.type, use_transform=self.use_transform)
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {'CANCELLED'}

        node_tree = context.space_data.node_tree
        with open(Path(__file__).parent / "nodes.json", "r") as f:
            if text := f.read():
                try:
                    data = json.loads(text)
                except json.decoder.JSONDecodeError:
                    data = {}
            else:
                data = {}

        with open(Path(__file__).parent / "nodes.json", "w") as f:
            version = data.get("version", FILE_VERSION)

            if version[0] > FILE_VERSION[0]:
                self.report({"ERROR"}, "Saved nodes file is from a newer version of the addon")
                return {'CANCELLED'}

            trees = data.get("node_trees", {})
            nodes = trees.get(node_tree.bl_rna.identifier, {})
            node = nodes.get(self.type, {})
            count = node.get("count", 0)
            count += 1

            data["version"] = FILE_VERSION
            data["node_trees"] = trees
            trees[node_tree.bl_rna.identifier] = nodes
            nodes[self.type] = node
            node["count"] = count
            data["node_trees"] = trees

            json.dump(data, f, indent=4)

        return {'PASS_THROUGH'}
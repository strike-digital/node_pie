import json
from collections import OrderedDict
import shutil
import webbrowser

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator, UILayout

from .npie_ui import NPIE_MT_node_pie
from .npie_helpers import Op
from .npie_constants import NODE_DEF_BASE_FILE, NODE_DEF_DIR, NODE_DEF_EXAMPLE_FILE, POPULARITY_FILE, POPULARITY_FILE_VERSION


class NodeSetting(bpy.types.PropertyGroup):
    value: bpy.props.StringProperty(
        name="Value",
        description="Python expression to be evaluated "
        "as the initial node setting",
        default="",
    )


@Op("node_pie", idname="add_node", undo=True)
class NPIE_OT_node_pie_add_node(Operator):
    """Add a node to the node tree, and increase its polularity by 1"""

    type: bpy.props.StringProperty(name="Type", description="Node type to add", default="FunctionNodeInputVector")
    group_name: bpy.props.StringProperty(name="Group name", description="The name of the node group to add")
    use_transform: bpy.props.BoolProperty(default=True)

    settings: bpy.props.StringProperty(
        name="Settings",
        description="Settings to be applied on the newly created node",
        default="[]",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        settings = eval(self.settings)
        try:
            bpy.ops.node.add_node(
                "INVOKE_DEFAULT",
                False,
                type=self.type,
                use_transform=self.use_transform,
                settings=settings,
            )
        except RuntimeError as e:
            self.report({"ERROR"}, str(e))
            return {'CANCELLED'}

        node_tree = context.area.spaces.active.path[-1].node_tree
        if self.group_name:
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

        # from pprint import pprint
        # pprint(list(bpy.utils.manual_map()))
        # url = get_docs_url(self.type)
        # print(get_docs_url(self.type))
        # webbrowser.open(url)
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
class NPIE_OT_call_node_pie(Operator):
    """Call the node pie menu"""

    name: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def execute(self, context):
        bpy.ops.wm.call_menu_pie("INVOKE_DEFAULT", name=NPIE_MT_node_pie.__name__)
        return {"FINISHED"}


@Op("node_pie")
class NPIE_OT_open_definition_file(Operator):
    """Open the node pie definition file for this node tree"""

    example: BoolProperty()

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def execute(self, context):
        if self.example:
            file = NODE_DEF_EXAMPLE_FILE
        else:
            file = NODE_DEF_DIR / f"{context.space_data.tree_type}.jsonc"
            if not file.exists():
                shutil.copyfile(NODE_DEF_BASE_FILE, file)

        webbrowser.open(file)
        return {"FINISHED"}


@Op("node_pie")
class NPIE_OT_copy_nodes_as_json(Operator):
    """Copy the selected nodes in the correct format to be pasted into the node pie definition file."""

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        if not context.selected_nodes:
            return False
        return True

    def execute(self, context):
        items = []
        for node in context.selected_nodes:
            data_item = {"identifier": node.bl_idname}
            items.append(str(data_item).replace("'", '"'))
            # items.append(json.dumps(data_item, indent=2))
        items = ",\n".join(items)
        context.window_manager.clipboard = items
        print()
        print("Nodes to copy:")
        print(items)
        print()
        num = len(context.selected_nodes)
        self.report({"INFO"}, message=f"Copied {num} node{'' if num == 1 else 's'}")
        return {"FINISHED"}

import json
from collections import OrderedDict
import shutil
import webbrowser

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator, UILayout
from .npie_custom_pies import NodeItem, load_custom_nodes_info

from .npie_ui import NPIE_MT_node_pie, get_popularity_id, get_variants_menu
from .npie_helpers import BOperator, get_all_def_files
from .npie_constants import NODE_DEF_BASE_FILE, NODE_DEF_DIR, NODE_DEF_EXAMPLE_FILE, POPULARITY_FILE, POPULARITY_FILE_VERSION


class NodeSetting(bpy.types.PropertyGroup):
    value: bpy.props.StringProperty(
        name="Value",
        description="Python expression to be evaluated "
        "as the initial node setting",
        default="",
    )


@BOperator("node_pie", idname="add_node", undo=True)
class NPIE_OT_node_pie_add_node(Operator):
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


@BOperator("node_pie")
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


@BOperator("node_pie")
class NPIE_OT_call_node_pie(Operator):
    """Call the node pie menu"""

    name: bpy.props.IntProperty()

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def execute(self, context):
        # The variants menus can't be added in a draw function, so add them here beforehand
        categories, cat_layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
        has_node_file = categories != {}
        if has_node_file:
            for cat_name, category in categories.items():
                for node in category.nodes:
                    if isinstance(node, NodeItem) and node.variants:
                        get_variants_menu(cat_name, node.idname, node.variants)

        area = context.area
        bpy.ops.wm.call_menu_pie("INVOKE_DEFAULT", name=NPIE_MT_node_pie.__name__)
        return {"FINISHED"}


@BOperator("node_pie")
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
            files = get_all_def_files()
            for file in files:
                if file.name == f"{context.space_data.tree_type}.jsonc":
                    break
            else:
                file = NODE_DEF_DIR / "user" / f"{context.space_data.tree_type}.jsonc"
            if not file.exists():
                shutil.copyfile(NODE_DEF_BASE_FILE, file)

        webbrowser.open(file)
        return {"FINISHED"}


@BOperator("node_pie")
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

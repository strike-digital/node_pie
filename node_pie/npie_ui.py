from collections import OrderedDict
from statistics import mean
import bpy
import json
import nodeitems_utils
from ..shared.functions import get_prefs
from ..shared.helpers import lerp, inv_lerp
from pathlib import Path
from bpy.types import UILayout, Menu


def get_all_node_data():
    with open(Path(__file__).parent / "nodes.json", "r") as f:
        try:
            data = json.load(f)
        except json.decoder.JSONDecodeError:
            data = {"node_trees": {}}
    return data


class NPIE_MT_node_pie(Menu):
    """The node pie menu"""
    bl_label = "Node pie"

    @classmethod
    def poll(cls, context):
        prefs = get_prefs(context)
        return context.space_data.node_tree and prefs.node_pie_enabled

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        prefs = get_prefs(context)

        tree_type = context.space_data.node_tree.bl_rna.identifier
        if tree_type == "ShaderNodeTree":
            menu_prefix = "NODE_MT_category_SH_NEW_"
            icons = {
                "CONVERTOR": "converter",
                "INPUT": "input",
                "OP_COLOR": "color",
                "OP_VECTOR": "vector",
                "OUTPUT": "output",
                "SHADER": "shader",
                "TEXTURE": "texture",
                "GROUP": "group",
            }
            overrides = {"ShaderNodeVectorMath": "OP_VECTOR"}
            icon_overrides = {}
            exclude = {"ShaderNodeSubsurfaceScattering"}

        elif tree_type == "GeometryNodeTree":
            menu_prefix = "NODE_MT_category_GEO_"
            icons = {
                "ATTRIBUTE": "attribute",
                "COLOR": "color",
                "CURVE": "geometry",
                "GEOMETRY": "geometry",
                "INPUT": "input",
                "INSTANCE": "geometry",
                "MATERIAL": "geometry",
                "MESH": "geometry",
                "POINT": "geometry",
                "PRIMITIVES_CURVE": "geometry",
                "PRIMITIVES_MESH": "geometry",
                "TEXT": "geometry",
                "TEXTURE": "texture",
                "UTILITIES": "converter",
                "VECTOR": "vector",
                "VOLUME": "geometry",
            }
            overrides = {}
            icon_overrides = {
                "Input": "input",
                "FunctionNode": "converter",
            }
            exclude = set()

        elif tree_type == "CompositorNodeTree":
            menu_prefix = "NODE_MT_category_CMP_"
            icons = {
                "CONVERTOR": "converter",
                "DISTORT": "distor",
                "INPUT": "input",
                "MATTE": "matte",
                "OP_COLOR": "color",
                "OP_FILTER": "filter",
                "OP_VECTOR": "vector",
                "OUTPUT": "output",
            }
            overrides = {}
            icon_overrides = {}
            exclude = set()

        else:
            menu_prefix = ""
            icons = {}
            overrides = {}
            icon_overrides = {}
            exclude = set()

        try:
            menu_prefix
        except NameError as e:
            print(e)
            return
        submenus = {d: getattr(bpy.types, d) for d in dir(bpy.types) if d.startswith(menu_prefix)}
        all_nodes = {n.nodetype: n for n in nodeitems_utils.node_items_iter(context) if hasattr(n, "label")}
        node_count_data = get_all_node_data()["node_trees"].get(tree_type, {})
        all_node_counts = {n: node_count_data.get(n, {}).get("count", 0) for n in all_nodes}
        all_node_counts = OrderedDict(sorted(all_node_counts.items(), key=lambda item: item[1]))
        average_count = mean(all_node_counts.values())

        def get_node_count(identifier):
            data = get_all_node_data()
            trees = data["node_trees"]
            nodes = trees.get(tree_type, {})
            node = nodes.get(identifier, {})
            count = node.get("count", 0)
            return count

        def draw_op(layout: UILayout, text: str, category_name: str, identifier: str, average: float = .0):
            """Draw the add node operator"""
            count = all_node_counts[identifier]

            row = layout.row(align=True)
            # draw the operator larger if the node is used more often
            if prefs.npie_variable_sizes:
                # lerp between the min and max sizes based on how used each node is compared to the most used one.
                # counts = sorted(all_node_counts.items(), key=lambda item: item[1])
                counts = list(dict.fromkeys(all_node_counts.values()))
                fac = inv_lerp(counts.index(count), 0, max(len(counts) - 1, 1))
                row.scale_y = lerp(fac, prefs.npie_normal_size, prefs.npie_max_size)
                # max_count = max(*all_node_counts.values(), 1)
                # row.scale_y = lerp(inv_lerp(count, 0, max_count), prefs.npie_normal_size, prefs.npie_max_size)

            # Draw the colour bar to the side
            split = row.split(factor=.02, align=True)

            sub = split.row(align=True)
            sub.prop(context.preferences.themes[0].node_editor, category_name + "_node", text="")
            sub.scale_x = .01

            # draw the button
            op = split.operator("node_pie.add_node", text=text)
            op.type = identifier
            op.use_transform = True

        def get_icon(identifier: str, node_category: str):
            """Get the icon name for this node"""
            for override in icon_overrides:
                if override in identifier:
                    return icon_overrides[override]
            return icons[node_category]

        def sort_item(identifier: str, node_category: str):
            """Returns whether the node should be overriden"""
            for override in icon_overrides:
                if override in identifier and override.lower() not in node_category.lower():
                    return len(icon_overrides[override])
            return 0

        def draw_header(layout: UILayout, text: str):
            """Draw the header of a node category"""
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=text.capitalize().replace("_", " "))

        def draw_category(layout: UILayout, cat: str, remove: str = ""):
            """Draw all node items in this category"""
            col = layout.column(align=True)
            label = getattr(bpy.types, menu_prefix + cat).bl_label
            draw_header(col, label)

            if cat == "GROUP":
                node_groups = [ng for ng in bpy.data.node_groups if ng.bl_rna.identifier == tree_type]
                for ng in node_groups:
                    op = layout.operator("node.add_group", text=ng.name, icon=icon)
                    op.name = ng.name
                return

            # Split the node items into sub categories depending on the location of blank node items.
            # This is then used to sort the node items inside each of the sub categories.
            nodeitems = submenus[menu_prefix + cat].category.items(bpy.context)
            subgroups = []
            temp = []
            for node in nodeitems:
                if not hasattr(node, "nodetype"):
                    subgroups.append(temp)
                    temp = []
                    continue
                temp.append(node)
            subgroups.append(temp)

            # Draw each of the subgroups with a separator in between each one.
            for i, subgroup in enumerate(subgroups):
                # Sort each item in the subgroup based on whether its icon has been overriden or not.
                # This is used to group nodes with the same icon together inside the subgroups.
                subgroup = sorted(subgroup, key=lambda node: sort_item(node.nodetype, cat))
                if i != 0:
                    col.separator()

                if not subgroup:
                    continue
                average_count = mean([all_node_counts[n.nodetype] for n in subgroup])
                for node in subgroup:
                    # Don't draw these nodes
                    if node.nodetype in exclude:
                        continue

                    # Check that the node category has not been overriden to something different
                    if not (overriden := overrides.get(node.nodetype)) or overriden == cat:
                        icon = get_icon(node.nodetype, cat)
                        draw_op(col, node.label.replace(remove, ""), icon, node.nodetype, average_count)

                # Draw nodes whose category has been overriden.
                for node_id, node_cat in overrides.items():
                    if node_cat == cat:
                        icon = get_icon(node_id, node_cat)
                        draw_op(col, all_nodes[node_id].label.replace(remove, ""), icon, node_id, average_count)

        def draw_search(layout: UILayout):
            layout.operator("node.add_search", text="Search", icon="VIEWZOOM").use_transform = True

        if tree_type == "ShaderNodeTree":
            # left
            row = pie.row(align=False)
            draw_category(row.box(), "TEXTURE", remove=" Texture")
            draw_category(row.box(), "CONVERTOR")

            # right
            row = pie.row(align=False)
            draw_category(row.box(), "INPUT")
            draw_category(row.box(), "SHADER", remove=" BSDF")

            # bottom
            col = pie.column()
            draw_search(col.box())
            col.separator(factor=.4)
            box = col.box().row()
            draw_category(box, "OP_COLOR")

            # top
            box = pie.column(align=True).box()
            draw_category(box, "OP_VECTOR")

        elif tree_type == "GeometryNodeTree":
            # left
            row = pie.row(align=False)
            draw_category(row.box(), "INPUT")
            col = row.column(align=False)
            draw_category(col.box(), "ATTRIBUTE")
            col.separator(factor=.4)
            draw_category(col.box(), "TEXTURE")
            col.separator(factor=.4)
            draw_category(col.box(), "COLOR")
            col.separator(factor=.4)
            col = row.column(align=False)
            draw_category(col.box(), "VECTOR")
            col.separator(factor=.4)
            draw_category(col.box(), "UTILITIES")

            # right
            row = pie.row(align=False)
            col = row.column(align=False)
            draw_category(col.box(), "CURVE")
            col.separator(factor=.4)
            draw_category(col.box(), "POINT")
            col = row.column(align=False)
            draw_category(col.box(), "MESH")
            col.separator(factor=.4)
            draw_category(col.box(), "MATERIAL")

            col = row.column(align=False)
            draw_category(col.box(), "PRIMITIVES_MESH")
            col.separator(factor=.4)
            draw_category(col.box(), "PRIMITIVES_CURVE")
            col.separator(factor=.4)
            draw_category(col.box(), "TEXT")

            # bottom
            row = pie.row()
            col = row.column(align=False)
            draw_search(col.box())
            col.separator(factor=.4)
            draw_category(col.box(), "INSTANCE")
            col.separator(factor=.4)
            draw_category(col.box(), "VOLUME")

            # top
            col = pie.column(align=True)
            draw_category(col.box(), "GEOMETRY")

        elif tree_type == "CompositorNodeTree":
            # left
            row = pie.row(align=False)
            draw_category(row.box(), "CONVERTOR")
            col = row.column(align=True)
            draw_category(col.box(), "DISTORT", remove=" Texture")
            col.separator(factor=.4)
            draw_category(col.box(), "OP_VECTOR")

            # right
            row = pie.row(align=False)
            col = row.column(align=True)
            draw_category(col.box(), "INPUT")
            col.separator(factor=.4)
            draw_category(col.box(), "OUTPUT")
            draw_category(row.box(), "OP_FILTER")

            # bottom
            col = pie.column()
            draw_search(col.box())
            col.separator(factor=.4)
            row = col.row()
            draw_category(row.box(), "MATTE", remove=" BSDF")

            # top
            box = pie.column(align=True).box()
            draw_category(box, "OP_COLOR")

        else:
            # Automatically draw all node items as space efficiently as possible.

            # Get all categories for the current context, and sort them based on the number of nodes they contain.
            categories = list(nodeitems_utils.node_categories_iter(context))
            categories.sort(key=lambda cat: len(list(cat.items(context))))

            # Remove the layout category, all of it's entries can be accessed with shortcuts
            for i, cat in enumerate(categories[:]):
                if cat.name == "Layout":
                    categories.pop(i)

            # Pick two categories from the middle of the list, and draw them in the top and bottom of the pie.
            # From the middle so that they aren't too big and aren't too small.
            areas = [[], [], [], []]
            areas[2] = [categories.pop(len(categories) // 2)]
            areas[3] = [categories.pop(len(categories) // 2 - 1)]

            # The structure of areas is:
            # [left, right, top, bottom]
            # where each item can be:
            # [[small_category, small_category], big_category]
            # and each sublist is equivalent to a column in the pie.

            def add_categories(orig_cats: list, i: int, max_height: int):
                """
                Add the given categories to the given area.
                The categories are packed according to their height relative to the provided max size.
                """

                for j, cat in enumerate(orig_cats):
                    idx = categories.index(cat)

                    # If first category, add it and continue
                    if j == 0:
                        areas[i].append(categories.pop(idx))
                        continue

                    size = len(list(cat.items(context)))
                    columns = areas[i]

                    # Loop over all columns and if current category fits in one, add it, else create a new column
                    for column in columns:
                        # Get the length of all items in the column
                        prev_items = column
                        if not isinstance(prev_items, list):
                            prev_items = [column]
                        prev_item_size = sum(len(list(c.items(context))) for c in prev_items)

                        # Add an extra item to account for the heading of each category
                        prev_item_size += len(prev_items)

                        # Decide whether to add the category to the current column or a new one
                        if prev_item_size + size < max_height:
                            areas[i][areas[i].index(column)] = prev_items + [categories.pop(idx)]
                            break
                    else:
                        areas[i].append(categories.pop(idx))

                if i:
                    areas[i] = areas[i][::-1]

            # Add half the categories
            big_on_inside = True
            biggest = len(list(categories[-1].items(context)))
            orig_cats = categories.copy()
            add_categories(orig_cats[::2 * -1 if big_on_inside else 1], 0, biggest)

            # Add the other half, which is now just the rest of them
            # biggest = len(list(categories[-1].items(context)))
            orig_cats = categories.copy()
            add_categories(orig_cats[::1 * -1 if big_on_inside else 1], 1, biggest)

            # Draw all of the areas
            for i, area in enumerate(areas):
                row = pie.row()
                # Use this to control whether the big nodes are at the center or at the edges
                area = area[::-1]
                # Draw the columns inside the area
                for node_cats in area:
                    # Add the parent column
                    bigcol = row.column(align=False)

                    # Draw search button at top of the bottom column
                    if i == 2:
                        draw_search(bigcol.box())
                        bigcol.separator(factor=.4)

                    if not isinstance(node_cats, list):
                        node_cats = [node_cats]

                    # Draw all of the categories in this column
                    for node_cat in node_cats:
                        col = bigcol.box().column(align=True)
                        draw_header(col, node_cat.name)

                        average_count = mean([all_node_counts[n.nodetype] for n in node_cat.items(context)])

                        for nodeitem in node_cat.items(context):
                            if not hasattr(nodeitem, "label"):
                                col.separator(factor=.4)
                                continue
                            draw_op(col, nodeitem.label, "input", nodeitem.nodetype, average_count)

                        bigcol.separator(factor=.4)

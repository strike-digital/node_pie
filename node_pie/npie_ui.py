import json
from pathlib import Path
from statistics import mean
from collections import OrderedDict

import bpy
from .npie_custom_pies import load_custom_nodes_info
import nodeitems_utils
from bpy.types import Menu, UILayout

from .npie_helpers import lerp, inv_lerp, get_prefs
from .geo_nodes_categories import (NodeItem, NodeCategory, all_geo_nodes, geo_nodes_categories)


class DummyUI():
    """Class that immitates UILayout, but doesn't draw anything"""

    def row(*args, **kwargs):
        return DummyUI()

    def column(*args, **kwargs):
        return DummyUI()

    def split(*args, **kwargs):
        return DummyUI()

    def label(*args, **kwargs):
        return DummyUI()

    def operator(*args, **kwargs):
        return DummyUI()

    def prop(*args, **kwargs):
        return DummyUI()


def draw_section(layout: UILayout, title: str, show_data=None, show_prop: str = "", index_prop: str = "") -> UILayout:
    """Draw a box with a title, and return it"""
    main_col = layout.column(align=True)

    box = main_col.box()
    col = box.column(align=True)
    col.scale_y = 0.85
    row = col.row(align=True)

    is_showing = True
    if show_data:
        index = getattr(show_data, index_prop)
        is_showing = getattr(show_data, show_prop)[index]
        sub = row.row(align=True)
        sub.prop(
            show_data,
            show_prop,
            index=index,
            text="",
            icon="TRIA_DOWN" if is_showing else "TRIA_RIGHT",
            emboss=False,
        )
        sub.scale_x = 1.2
        setattr(show_data, index_prop, index + 1)

    sub = row.row(align=True)
    sub.active = is_showing
    sub.label(text=title)
    sub.alignment = "CENTER"

    if show_data:
        # Use two separators to avoid making the box taller
        sub.separator(factor=3)
        sub.separator(factor=2)

    if not is_showing:
        return DummyUI()

    box = main_col.box()
    col = box.column()
    return col


def draw_inline_prop(
    layout: UILayout,
    data,
    data_name,
    text="",
    prop_text="",
    invert=False,
    factor=0.48,
    alignment="RIGHT",
    full_event=False,
) -> UILayout:
    """Draw a property with the label to the left of the value"""
    row = layout.row()
    split = row.split(factor=factor, align=True)
    split.use_property_split = False
    left = split.row(align=True)
    left.alignment = alignment
    if not text:
        text = data.bl_rna.properties[data_name].name
    left.label(text=text)
    col = split.column(align=True)
    col.prop(data, data_name, text=prop_text, invert_checkbox=invert, full_event=full_event)
    return row


def draw_enabled_button(layout: UILayout, data, prop: str) -> UILayout:
    """Draw the 'section enabled' button, and return the following layout"""
    col = layout.column(align=True)
    row = col.row(align=True)
    enabled = getattr(data, prop)
    icon = get_tick_icon(enabled, show_box=True)
    text = "Enabled     " if enabled else "Disabled     "
    row.prop(data, prop, text=text, toggle=True, icon=icon)
    row.scale_y = 1
    layout = layout.column(align=True)
    layout = col.box()

    if not enabled:
        layout.active = False

    return layout


def get_tick_icon(enabled, show_box=False) -> str:
    """Returns the name of the tick icon, enabled or disabled."""
    if show_box:
        return "CHECKBOX_HLT" if enabled else "CHECKBOX_DEHLT"
    return "CHECKMARK" if enabled else "BLANK1"


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
        need_new_categories = True

        if tree_type == "ShaderNodeTree":
            menu_prefix = "NODE_MT_category_SH_NEW_"
            colours = {
                "Converter": "converter",
                "Input": "input",
                "Color": "color",
                "Vector": "vector",
                "Output": "output",
                "Shader": "shader",
                "Texture": "texture",
                "NodeGroups": "group",
                "Layout": "layout",
            }
            overrides = {"ShaderNodeVectorMath": "Vector"}
            icon_overrides = {}
            exclude = set()

        elif tree_type == "GeometryNodeTree":
            menu_prefix = "NODE_MT_category_GEO_"
            colours = {
                "Attribute": "attribute",
                "Color": "color",
                "Curve": "geometry",
                "Geometry": "geometry",
                "Input": "input",
                "Instances": "geometry",
                "Material": "geometry",
                "Mesh": "geometry",
                "Point": "geometry",
                "Curve Primitives": "geometry",
                "Mesh Primitives": "geometry",
                "Text": "geometry",
                "Texture": "texture",
                "Utilities": "converter",
                "Vector": "vector",
                "Volume": "geometry",
                "Layout": "layout",
                # 3.4+
                "Mesh Topology": "input",
                "Curve Topology": "input",
                "UV": "converter",
                "Simulation": "layout"
            }
            overrides = {}
            icon_overrides = {
                "FunctionNodeInputBool": "input",
                "FunctionNodeInputImage": "input",
                "FunctionNodeInputInt": "input",
                "FunctionNodeInputColor": "input",
                "FunctionNodeInputVector": "input",
                "FunctionNodeInputString": "input",
                "GeometryNodeEdgesToFaceGroups": "input",
                "GeometryNodeMeshFaceSetBoundaries": "input",
                "GeometryNodeSimulationInput": "layout",
                "GeometryNodeStringJoin": "converter",
                "GeometryNodeSampleVolume": "converter",
                "ShaderNodeValToRGB": "converter",
                "ShaderNodeCombineXYZ": "converter",
                "ShaderNodeSeparateXYZ": "converter",
                "GeometryNodeSplineParameter": "input",
                "GeometryNodeSplineLength": "input",
                "GeometryNodeCurveHandleTypeSelection": "input",
                "GeometryNodeCurveEndpointSelection": "input",
                "FunctionNode": "converter",
                "Input": "input",
            }
            exclude = set()

        elif tree_type == "CompositorNodeTree":
            menu_prefix = "NODE_MT_category_CMP_"
            colours = {
                "Converter": "converter",
                "Distort": "distor",  # Blender has a typo in the preferences name lol
                "Input": "input",
                "Matte": "matte",
                "Color": "color",
                "Filter": "filter",
                "Vector": "vector",
                "Output": "output",
                "Layout": "layout",
            }
            overrides = {}
            icon_overrides = {}
            exclude = set()

        else:
            need_new_categories = False
            categories, layout = load_custom_nodes_info(context.area.spaces.active.tree_type)
            all_nodes = {n.nodetype: n for c in categories.values() for n in c.nodeitems if isinstance(n, NodeItem)}
            is_node_file = False
            if categories:
                is_node_file = True

            colours = {c.idname: c.color if c.color else "input" for c in categories.values()}
            menu_prefix = "  "
            overrides = {}
            icon_overrides = {}
            exclude = set()

        categories: dict[str, NodeCategory]

        if tree_type == "GeometryNodeTree" and bpy.app.version >= (3, 4, 0):
            categories = geo_nodes_categories
            if bpy.app.version >= (3, 5, 0):
                all_nodes = all_geo_nodes

            elif bpy.app.version >= (3, 4, 0):
                all_nodes = {n.nodetype: n for c in geo_nodes_categories.values() for n in c.nodeitems}
                all_nodes["GeometryNodeGroup"] = NodeItem("NodeGroups", "GeometryNodeGroup")

        elif need_new_categories:
            categories = {
                getattr(bpy.types, d).bl_label: getattr(bpy.types, d).category
                for d in dir(bpy.types)
                if d.startswith(menu_prefix) and hasattr(getattr(bpy.types, d), "category")
            }
            all_nodes = {n.nodetype: n for n in nodeitems_utils.node_items_iter(context) if hasattr(n, "label")}

        # print(list(nodeitems_utils.node_items_iter(context)))
        node_count_data = get_all_node_data()["node_trees"].get(tree_type, {})
        all_node_counts = {n: node_count_data.get(n, {}).get("count", 0) for n in all_nodes}
        all_node_counts = OrderedDict(sorted(all_node_counts.items(), key=lambda item: item[1]))

        def draw_op(
            layout: UILayout,
            text: str,
            category_name: str,
            identifier: str = "",
            group_name="",
            max_len=200,
            op="",
            params={},
        ):
            """Draw the add node operator"""
            count = all_node_counts.get(identifier, 1)

            row = layout.row(align=True)
            # draw the operator larger if the node is used more often
            if prefs.npie_variable_sizes and not group_name:
                # lerp between the min and max sizes based on how used each node is compared to the most used one.
                # counts = sorted(all_node_counts.items(), key=lambda item: item[1])
                counts = list(dict.fromkeys(all_node_counts.values()))
                fac = inv_lerp(counts.index(count), 0, max(len(counts) - 1, 1))
                row.scale_y = lerp(fac, prefs.npie_normal_size, prefs.npie_max_size)
                # max_count = max(*all_node_counts.values(), 1)
                # row.scale_y = lerp(inv_lerp(count, 0, max_count), prefs.npie_normal_size, prefs.npie_max_size)

            # Draw the colour bar to the side
            split = row.split(factor=prefs.npie_color_size, align=True)

            sub = split.row(align=True)
            sub.prop(context.preferences.themes[0].node_editor, category_name + "_node", text="")
            sub.scale_x = .03

            # draw the button
            row = split.row(align=True)
            text = bpy.app.translations.pgettext(text)
            # import blf
            # length = blf.dimensions(0, text)[0]
            # max_length = blf.dimensions(0, "a" * 12)[0]
            # # print(max_length, length)
            # if length > max_length:
            #     text = text[:int(length / max_length * len(text))]
            #     print(int(length / max_length * len(text)), int(length), int(max_length), len(text), text)
            # print(text)
            if len(text) > max_len:
                text = text[:max_len] + "..."

            if op:
                op = row.operator(op, text=text)
            else:
                op = row.operator("node_pie.add_node", text=text)
                op.group_name = group_name
                op.type = identifier
                op.use_transform = True
            for name, value in params.items():
                setattr(op, name, value)
            # op: NPIE_OT_show_node_docs = row.operator("node_pie.show_node_docs", text="", icon="HELP")
            # op.type = identifier
            # op.link = ""
            # op.prev_pages = ""

        def get_icon(identifier: str, node_category: str):
            """Get the icon name for this node"""
            # print(icon_overrides)
            for override in icon_overrides:
                if override in identifier:
                    return icon_overrides[override]
            try:
                return colours[node_category]
            except KeyError:
                return "geometry"

        def sort_item(identifier: str, node_category: str):
            """Returns whether the node should be overriden"""
            for override in icon_overrides:
                if override in identifier and override.lower() not in node_category.lower():
                    return len(icon_overrides[override])
            return 0

        def draw_header(layout: UILayout, text: str, keep_text=False):
            """Draw the header of a node category"""
            row = layout.row(align=True)
            row.alignment = "CENTER"
            text = text if keep_text else text.capitalize().replace("_", " ")
            row.label(text=text)

        def draw_node_groups(layout: UILayout):
            node_groups = [ng for ng in bpy.data.node_groups if ng.bl_idname == tree_type]
            if not node_groups or not prefs.npie_show_node_groups:
                return
            col = layout.box().column(align=True)
            draw_header(col, "Groups")
            for ng in node_groups:
                if ng.bl_idname == tree_type and not ng.name.startswith("."):
                    draw_op(
                        col,
                        ng.name,
                        category_name="group",
                        identifier=tree_type.replace("Tree", "Group"),
                        group_name=ng.name,
                        max_len=18,
                    )

        def draw_category(layout: UILayout, cat: str, header="", remove: str = ""):
            """Draw all node items in this category"""

            # Draw the special category for node groups Groups
            if cat == "NodeGroups":
                node_groups = [ng for ng in bpy.data.node_groups if ng.bl_rna.identifier == tree_type]
                for ng in node_groups:
                    text = bpy.app.translations.pgettext(ng.name)
                    op = layout.operator("node.add_group", text=text, icon=icon)
                    op.name = ng.name
                return

            category = categories[cat]
            label = category.name
            nodeitems = list(category.items(context))

            col = layout.box().column(align=True)
            draw_header(col, header or label, keep_text=header)

            if hasattr(category, "children") and category.children:

                for child in category.children:
                    draw_category(col, child.name, f"{child.name}")

            if len(nodeitems) == 0:
                return

            # Split the node items into sub categories depending on the location of blank node items.
            # This is then used to sort the node items inside each of the sub categories.
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
                # subgroup = sorted(subgroup, key=lambda node: sort_item(node.nodetype, cat))
                if i != 0:
                    col.separator(factor=.5)

                if not subgroup:
                    continue
                # average_count = mean([all_node_counts[n.nodetype] for n in subgroup])
                for node in subgroup:
                    # Don't draw these nodes
                    if node.nodetype in exclude:
                        continue

                    # Check that the node category has not been overriden to something different
                    if not (overriden := overrides.get(node.nodetype)) or overriden == cat:
                        icon = get_icon(node.nodetype, cat)
                        settings = getattr(node, "settings", [])
                        settings = settings or []

                        # Non geo nodes settings have a different format
                        if isinstance(settings, dict):
                            formatted_settings = []
                            for name, setting in settings.items():
                                formatted_settings.append({"name": name, "value": setting})
                            settings = formatted_settings

                        params = {"settings": str(settings)}
                        draw_op(col, node.label.replace(remove, ""), icon, node.nodetype, params=params)

                # Draw nodes whose category has been overriden.
                for node_id, node_cat in overrides.items():
                    if node_cat == cat:
                        icon = get_icon(node_id, node_cat)
                        draw_op(col, all_nodes[node_id].label.replace(remove, ""), icon, node_id)

        def draw_search(layout: UILayout):
            layout.operator("node.add_search", text="Search", icon="VIEWZOOM").use_transform = True

        if tree_type == "ShaderNodeTree":
            # LEFT
            row = pie.row(align=False)
            draw_category(row, "Texture", remove=" Texture")
            draw_category(row, "Converter")

            # RIGHT
            row = pie.row(align=False)
            draw_category(row, "Input")
            draw_category(row, "Shader", remove=" BSDF")

            # BOTTOM
            col = pie.column()
            draw_category(col, "Color")
            col.separator(factor=.4)
            draw_node_groups(col)

            # TOP
            col = pie.column()
            draw_category(col, "Vector")
            col.separator(factor=.4)
            draw_search(col.box())

        elif tree_type == "GeometryNodeTree":
            # LEFT
            # left
            row = pie.row(align=False)
            col = row.column(align=False)
            draw_category(col, "Input")
            col.separator(factor=.4)
            draw_category(col, "Layout")
            if bpy.app.version >= (4, 0, 0):
                col.separator(factor=.4)
                col = col.box().column(align=True)
                draw_header(col, "Simulation")
                draw_op(col, "Simulation Zone", colours["Layout"], op="node.add_simulation_zone")

            # middle
            col = row.column(align=False)
            draw_category(col, "Attribute")
            col.separator(factor=.4)
            draw_category(col, "Texture")
            col.separator(factor=.4)
            draw_category(col, "Color")
            col.separator(factor=.4)
            if bpy.app.version >= (3, 4, 0):
                draw_category(col, "UV", header="UV")

            # right
            col = row.column(align=False)
            draw_category(col, "Vector")
            col.separator(factor=.4)
            draw_category(col, "Utilities")

            # RIGHT
            # left
            row = pie.row(align=False)
            col = row.column(align=False)
            draw_category(col, "Curve")
            col.separator(factor=.4)
            draw_category(col, "Point")

            # middle
            col = row.column(align=False)
            draw_category(col, "Mesh")
            col.separator(factor=.4)
            draw_category(col, "Material")

            # right
            col = row.column(align=False)
            draw_category(col, "Mesh Primitives")
            col.separator(factor=.4)
            draw_category(col, "Curve Primitives")
            col.separator(factor=.4)
            if bpy.app.version >= (3, 4, 0):
                draw_category(col, "Mesh Topology")
                col.separator(factor=.4)
                draw_category(col, "Curve Topology")
            col.separator(factor=.4)
            draw_category(col, "Text")

            # BOTTOM
            row = pie.row()
            col = row.column(align=False)
            draw_category(col, "Instances")
            col.separator(factor=.4)
            draw_category(col, "Volume")
            col.separator(factor=.4)
            draw_node_groups(col)

            # TOP
            col = pie.column()
            draw_category(col, "Geometry")
            col.separator(factor=.4)
            draw_search(col.box())

        elif tree_type == "CompositorNodeTree":
            # LEFT
            row = pie.row(align=False)
            draw_category(row, "Converter")
            col = row.column(align=True)
            draw_category(col, "Distort", remove=" Texture")
            col.separator(factor=.4)
            draw_category(col, "Vector")

            # RIGHT
            row = pie.row(align=False)
            col = row.column(align=True)
            draw_category(col, "Input")
            col.separator(factor=.4)
            draw_category(col, "Output")
            draw_category(row, "Filter")

            # BOTTOM
            col = pie.column()
            row = col.row()
            draw_category(row, "Matte", remove=" BSDF")
            col.separator(factor=.4)
            draw_node_groups(col)

            # TOP
            col = pie.column(align=True)
            draw_category(col, "Color")
            col.separator(factor=.4)
            draw_search(col.box())

        else:
            if is_node_file:

                def draw_area(area: list):
                    row = pie.row()
                    if not area:
                        return row.column()
                    for col in area:
                        column = row.column()
                        for cat in col:
                            draw_category(column, cat)
                    return column

                draw_area(layout["left"])
                draw_area(layout["right"])
                draw_area(layout["bottom"])
                col = draw_area(layout["top"])
                draw_search(col.box())
                pass
            else:
                # Automatically draw all node items as space efficiently as possible.

                # Get all categories for the current context, and sort them based on the number of nodes they contain.
                categories = list(nodeitems_utils.node_categories_iter(context))
                categories.sort(key=lambda cat: len(list(cat.items(context))))

                if not categories:
                    pie.separator()
                    pie.separator()
                    box = pie.box().column(align=True)
                    box.label(
                        text="Unfortunately, this node tree is not supported, as it doesn't use the standard node api.")
                    return

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
                                draw_op(col, nodeitem.label, "input", nodeitem.nodetype)

                            bigcol.separator(factor=.4)

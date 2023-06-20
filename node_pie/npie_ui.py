import json
from pathlib import Path
from collections import OrderedDict

import bpy
from .npie_custom_pies import NodeCategory, NodeItem, Separator
from .npie_custom_pies import load_custom_nodes_info
import nodeitems_utils
from bpy.types import Menu, UILayout

from .npie_helpers import lerp, inv_lerp, get_prefs


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

        categories, cat_layout = load_custom_nodes_info(context.area.spaces.active.tree_type)
        has_node_file = categories != {}

        if not has_node_file:
            all_nodes = {n.nodetype: n for n in nodeitems_utils.node_items_iter(context) if hasattr(n, "label")}
        else:
            all_nodes = {n.idname: n for c in categories.values() for n in c.nodes if isinstance(n, NodeItem)}

        # Get the count of times each node has been used
        node_count_data = get_all_node_data()["node_trees"].get(tree_type, {})
        all_node_counts = {}
        for node_name in all_nodes:
            all_node_counts[node_name] = node_count_data.get(node_name, {}).get("count", 0)
        all_node_counts = OrderedDict(sorted(all_node_counts.items(), key=lambda item: item[1]))

        def draw_add_operator(
            layout: UILayout,
            text: str,
            color_name: str,
            identifier: str = "",
            group_name="",
            max_len=200,
            op="",
            params={},
        ):
            """Draw the add node operator"""
            index = all_node_counts.get(identifier, 1)

            row = layout.row(align=True)
            # draw the operator larger if the node is used more often
            if prefs.npie_variable_sizes and not group_name:
                # lerp between the min and max sizes based on how used each node is compared to the most used one.
                # counts = sorted(all_node_counts.items(), key=lambda item: item[1])
                counts = list(dict.fromkeys(all_node_counts.values()))
                fac = inv_lerp(counts.index(index), 0, max(len(counts) - 1, 1))
                row.scale_y = lerp(fac, prefs.npie_normal_size, prefs.npie_max_size)

            # Draw the colour bar to the side
            split = row.split(factor=prefs.npie_color_size, align=True)

            sub = split.row(align=True)
            sub.prop(context.preferences.themes[0].node_editor, color_name + "_node", text="")
            sub.scale_x = .03

            # draw the button
            row = split.row(align=True)
            text = bpy.app.translations.pgettext(text)
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

        def get_color_name(category: NodeCategory, nodeitem: NodeItem) -> str:
            """Get the icon name for this node"""

            if nodeitem.color:
                return nodeitem.color
            return category.color

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
                    draw_add_operator(
                        col,
                        ng.name,
                        color_name="group",
                        identifier=tree_type.replace("Tree", "Group"),
                        group_name=ng.name,
                        max_len=18,
                    )

        def draw_category(layout: UILayout, category: NodeCategory, header="", remove: str = ""):
            """Draw all node items in this category"""
            nodeitems = category.nodes
            col = layout.box().column(align=True)
            draw_header(col, header or category.label, keep_text=header)

            if hasattr(category, "children") and category.children:
                for child in category.children:
                    draw_category(col, child, child.label)

            if len(nodeitems) == 0:
                return

            # Split the node items into sub categories depending on the location of blank node items.
            # This is then used to sort the node items inside each of the sub categories.
            subgroups = []
            temp = []
            for node in nodeitems:
                if isinstance(node, Separator):
                    subgroups.append(temp)
                    temp = []
                    continue
                temp.append(node)
            subgroups.append(temp)

            # Draw each of the subgroups with a separator in between each one.
            for i, subgroup in enumerate(subgroups):
                if i != 0:
                    col.separator(factor=.5)

                if not subgroup:
                    continue

                for node in subgroup:
                    icon = get_color_name(category, node)
                    settings = getattr(node, "settings", [])
                    params = {"settings": str(settings)}
                    draw_add_operator(col, node.label.replace(remove, ""), icon, node.idname, params=params)

        def draw_search(layout: UILayout):
            layout.operator("node.add_search", text="Search", icon="VIEWZOOM").use_transform = True

        if has_node_file:

            def draw_area(area: list):
                row = pie.row()
                if not area:
                    return row.column()
                for col in area:
                    column = row.column()
                    for cat in col:
                        draw_category(column, categories[cat])
                return column

            draw_area(cat_layout["left"])
            draw_area(cat_layout["right"])
            col = draw_area(cat_layout["bottom"])
            if tree_type in {"GeometryNodeTree", "ShaderNodeTree", "CompositorNodeTree"}:
                draw_node_groups(col)
            col = draw_area(cat_layout["top"])
            draw_search(col.box())

        else:
            # Automatically draw all node items as space efficiently as possible.

            # Get all categories for the current context, and sort them based on the number of nodes they contain.
            categories = list(nodeitems_utils.node_categories_iter(context))
            categories.sort(key=lambda cat: len(list(cat.items(context))))

            if not categories:
                pie.separator()
                pie.separator()
                box = pie.box().column(align=True)
                box.alignment = "CENTER"
                box.label(
                    text="Unfortunately, this node tree is not supported, as it doesn't use the standard node api.")
                box.label(text="You can define the pie menu for this node tree manually by enabling developer extras")
                box.label(text="in the preferences, and choosing 'Create definition file for this node tree type'")
                box.label(text="from the right click menu in this node editor")
                box.label(
                    text="Be aware that this could require a lot of work, depending on the number of nodes required")
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

                        for nodeitem in node_cat.items(context):
                            if not hasattr(nodeitem, "label"):
                                col.separator(factor=.4)
                                continue
                            draw_add_operator(col, nodeitem.label, "input", nodeitem.nodetype)

                        bigcol.separator(factor=.4)

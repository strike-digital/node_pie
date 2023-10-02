import json
import random
import traceback
from pathlib import Path
from collections import OrderedDict

import bpy
import nodeitems_utils
from bpy.types import Menu, Context, UILayout, NodeSocket

from .npie_constants import IS_4_0
from .npie_helpers import lerp, inv_lerp, get_prefs
from .npie_custom_pies import NodeItem, Separator, NodeCategory, NodeOperator, load_custom_nodes_info


class DummyUI:
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


def get_popularity_id(node_idname, settings={}):
    if not isinstance(settings, str):
        settings = str(settings)
    return node_idname + ("" if settings == "{}" else settings)


def get_variants_menu(node_item: NodeItem, scale=1):
    hash_val = node_item.category.idname + node_item.idname + node_item.label
    hash_val += str(node_item.settings) + str(node_item.variants)
    cls_idname = f"NPIE_MT_{abs(hash(hash_val))}"

    class NPIE_MT_node_sub_menu(Menu):
        """A sub menu that can be added to certain nodes with different parameters."""

        bl_label = "Node options"
        bl_idname = cls_idname

        def draw(self, context):
            layout = self.layout
            col = layout.column(align=True)
            col.scale_y = self._scale
            for name, variant in node_item.variants.items():
                if name == "separator":
                    col.separator()
                    continue
                op = col.operator("node_pie.add_node", text=name)
                op.type = node_item.idname
                op.settings = str(variant)

    try:
        bpy.utils.register_class(NPIE_MT_node_sub_menu)
    except RuntimeError:
        pass

    if cls := getattr(bpy.types, cls_idname):
        cls._scale = scale
    return cls_idname


def get_node_groups(context):
    """Get a list of node groups that can be added to the current node tree"""

    # A set of the node trees that are currently being edited in this area.
    # These can't be added as that would cause recursion.
    editing_groups = {p.node_tree for p in context.space_data.path}

    tree_type = context.space_data.tree_type
    node_groups = []
    for ng in bpy.data.node_groups:
        if ng.bl_idname == tree_type and ng not in editing_groups and not ng.name.startswith("."):
            node_groups.append(ng)
    return node_groups


class NPIE_MT_node_groups(Menu):
    """Show a list of node groups that you can add"""

    bl_label = "Node Groups"

    def draw(self, context):
        tree_type = context.space_data.tree_type
        node_groups = get_node_groups(context)
        if not node_groups:
            return

        layout = self.layout
        col = layout.column(align=True)
        for ng in node_groups:
            op = col.operator("node_pie.add_node", text=ng.name)
            op.type = tree_type.replace("Tree", "Group")
            op.group_name = ng.name


class NPIE_MT_node_pie(Menu):
    """The node pie menu"""

    bl_label = "Node Pie"

    from_socket: NodeSocket = None
    to_sockets: list[NodeSocket] = []

    @classmethod
    def poll(cls, context):
        prefs = get_prefs(context)
        return context.space_data.edit_tree and prefs.node_pie_enabled

    def draw(self, context):
        try:
            self.draw_menu(context)
        except Exception as e:
            pie = self.layout.menu_pie()
            pie.row()
            pie.row()
            box = pie.box()
            col = box.column(align=True)
            col.label(text="An error occurred while trying to draw the pie menu:")
            col.separator()
            e = traceback.format_exception(e)
            lines = []
            for line in e:
                lines += line.split("\n")
            for line in lines:
                if line:
                    col.label(text=line.replace("\n", ""))
                    print(line)

    def draw_menu(self, context: Context):
        layout = self.layout

        pie = layout.menu_pie()
        prefs = get_prefs(context)
        tree_type = context.space_data.edit_tree.bl_rna.identifier

        categories, cat_layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
        has_node_file = categories != {}

        if not has_node_file:
            all_nodes = {n.nodetype: n for n in nodeitems_utils.node_items_iter(context) if hasattr(n, "nodetype")}
        else:
            all_nodes = {}
            for cat in categories.values():
                for node in cat.nodes:
                    if isinstance(node, NodeItem):
                        name = node.idname + (str(node.settings) if node.settings else "")
                        all_nodes[name] = node

        # Get the count of times each node has been used
        node_count_data = get_all_node_data()["node_trees"].get(tree_type, {})
        all_node_counts = {}
        for node_name in all_nodes:
            all_node_counts[node_name] = node_count_data.get(node_name, {}).get("count", 0)
        all_node_counts[""] = 1
        all_node_counts = OrderedDict(sorted(all_node_counts.items(), key=lambda item: item[1]))

        def get_node_size(node_item: NodeItem):
            # lerp between the min and max sizes based on how used each node is compared to the most used one.
            identifier = get_popularity_id(node_item.idname, node_item.settings)
            index = all_node_counts.get(identifier, 0)
            counts = list(dict.fromkeys(all_node_counts.values()))
            fac = inv_lerp(counts.index(index), 0, max(len(counts) - 1, 1))
            return lerp(fac, prefs.npie_normal_size, prefs.npie_normal_size * prefs.npie_max_size)

        def draw_add_operator(
            layout: UILayout,
            text: str,
            color_name: str,
            node_item: NodeItem = None,
            group_name="",
            max_len=200,
            op="",
            params={},
        ):
            """Draw the add node operator"""
            if node_item:
                identifier = node_item.idname
            elif group_name:
                identifier = tree_type.replace("Tree", "Group")

            row = layout.row(align=True)

            active = True
            if "" not in text.lower():
                active = False
                row.active = False
            scale = 1
            # draw the operator larger if the node is used more often
            if prefs.npie_variable_sizes and not group_name and not op:
                scale = get_node_size(node_item)
            row.scale_y = scale

            # Draw the colour bar to the side
            split = row.split(factor=prefs.npie_color_size, align=True)

            sub = split.row(align=True)
            sub.prop(context.preferences.themes[0].node_editor, color_name + "_node", text="")
            sub.scale_x = 0.03

            # draw the button
            row = split.row(align=True)
            text = bpy.app.translations.pgettext(text)
            if len(text) > max_len:
                text = text[:max_len] + "..."
            row.scale_x = 0.9

            if op:
                op = row.operator(op, text=text)
            else:
                op = row.operator("node_pie.add_node", text=text)
                op.group_name = group_name
                op.type = identifier
                op.use_transform = True
                op.settings = str(node_item.settings)
                if nodeitem := all_nodes.get(identifier):
                    if hasattr(nodeitem, "description") and nodeitem.description:
                        op.bl_description = nodeitem.description

                # Dark magic to draw the variants menu on top of the add node button
                # Works similarly to this: https://blender.stackexchange.com/a/277673/57981
                if node_item.variants and prefs.npie_show_variants:
                    col = layout.column(align=True)
                    col.active = active

                    # Draw a property with negative scale. This essentially gives it a negative bounding box,
                    # Pushing everything drawn below it upwards on top of whatever is already there.
                    subcol = col.column(align=True)
                    subcol.prop(context.scene, "frame_end", text="")
                    subcol.scale_y = -scale

                    # Draw the menu, which will now be pushed on top of the add node button
                    subrow = col.row(align=False)
                    subrow.scale_x = 1.1
                    subrow.scale_y = scale
                    subrow.alignment = "RIGHT"
                    subrow.menu(
                        get_variants_menu(node_item, scale=1.1),
                        text="",
                        icon="TRIA_RIGHT",
                    )

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
            node_groups = get_node_groups(context)
            if not node_groups or not prefs.npie_show_node_groups:
                return
            col = layout.box().column(align=True)
            if prefs.npie_expand_node_groups:
                draw_header(col, "Node Groups")
                for ng in node_groups:
                    draw_add_operator(
                        col,
                        ng.name,
                        color_name="group",
                        group_name=ng.name,
                        max_len=18,
                    )
            else:
                col.scale_y = prefs.npie_normal_size
                col.operator("wm.call_menu", text="Node Groups", icon="NODE")
                scale = -1

                # Uncomment to add an arrow to the right hand side
                # subcol = col.column(align=True)
                # subcol.prop(context.scene, "frame_end", text="")
                # subcol.scale_y = scale
                # row = col.row(align=True)
                # row.alignment = "RIGHT"
                # row.menu(NPIE_MT_node_groups.__name__, text="", icon="TRIA_RIGHT")

                subcol = col.column(align=True)
                subcol.prop(context.scene, "frame_end", text="")
                subcol.scale_y = scale
                subcol.scale_x = 1.6
                col.menu(NPIE_MT_node_groups.__name__, text=" ")

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

            for i, node in enumerate(nodeitems):
                # Draw separators
                if isinstance(node, Separator):
                    if node.label and prefs.npie_separator_headings:
                        if i:
                            col.separator(factor=0.5)
                        row = col.row(align=True)
                        row.scale_y = 0.8
                        draw_header(row, node.label)
                    elif i:
                        col.separator(factor=0.5)
                    continue
                elif isinstance(node, NodeOperator):
                    color = get_color_name(category, node)
                    draw_add_operator(col, node.label, color, op=node.idname, params=node.settings)
                    continue

                # Draw node items
                color = get_color_name(category, node)
                # settings = node.settings
                # variants = node.variants
                # params = {"settings": str(settings)}
                draw_add_operator(
                    col,
                    node.label.replace(remove, ""),
                    color,
                    node_item=node,
                )

        def draw_search(layout: UILayout):
            layout.scale_y = prefs.npie_normal_size
            if IS_4_0:
                layout.operator("wm.search_single_menu", text="Search", icon="VIEWZOOM").menu_idname = "NODE_MT_add"
            else:
                layout.operator("node.add_search", text="Search", icon="VIEWZOOM").use_transform = True

        if has_node_file:

            def draw_area(area: list, layout=None):
                if layout:
                    row = layout.row()
                else:
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
            col = pie.column()
            if tree_type in {"GeometryNodeTree", "ShaderNodeTree", "CompositorNodeTree"}:
                draw_node_groups(col)
            col = draw_area(cat_layout["bottom"], col)
            col = draw_area(cat_layout["top"])
            draw_search(col.box())

        else:
            # Automatically draw all node items as space efficiently as possible.

            # Get all categories for the current context, and sort them based on the number of nodes they contain.
            categories = list(nodeitems_utils.node_categories_iter(context))
            categories.sort(key=lambda cat: len(list(cat.items(context))))
            # categories.sort(key=lambda cat: sum(get_node_size(n.nodetype) for n in cat.items(context) if hasattr(n, "nodetype")))

            if not categories:
                pie.separator()
                pie.separator()
                box = pie.box().column(align=True)
                box.alignment = "CENTER"
                box.label(
                    text="Unfortunately, this node tree is not supported, as it doesn't use the standard node api."
                )
                box.label(text="You can define the pie menu for this node tree manually by enabling developer extras")
                box.label(text="in the preferences, and choosing 'Create definition file for this node tree type'")
                box.label(text="from the right click menu in this node editor")
                box.label(
                    text="Be aware that this could require a lot of work, depending on the number of nodes required"
                )
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
            add_categories(orig_cats[:: 2 * -1 if big_on_inside else 1], 0, biggest)

            # Add the other half, which is now just the rest of them
            # biggest = len(list(categories[-1].items(context)))
            orig_cats = categories.copy()
            add_categories(orig_cats[:: 1 * -1 if big_on_inside else 1], 1, biggest)
            orig_colors = [
                "converter",
                "color",
                # "distor",
                "input",
                "output",
                "filter",
                "vector",
                "texture",
                "shader",
                # "script",
                "geometry",
                "attribute",
            ]
            new_colors = orig_colors.copy()
            random.seed(tree_type)

            # Draw all of the areas
            for i, area in enumerate(areas):
                row = pie.row()
                # Use this to control whether the big nodes are at the center or at the edges
                area = area[::-1]
                # Draw the columns inside the area
                for node_cats in area:
                    # Add the parent column
                    bigcol = row.column(align=False)

                    if not isinstance(node_cats, list):
                        node_cats = [node_cats]

                    # Draw all of the categories in this column
                    for node_cat in node_cats:
                        col = bigcol.box().column(align=True)
                        # color = random.choice(colors)
                        if not new_colors:
                            new_colors = orig_colors.copy()
                        color = new_colors.pop(random.randint(0, len(new_colors) - 1))
                        draw_header(col, node_cat.name)

                        for nodeitem in node_cat.items(context):
                            if not hasattr(nodeitem, "nodetype") or not hasattr(nodeitem, "label"):
                                col.separator(factor=0.4)
                                continue

                            # Convert from blender node item to node pie NodeItem
                            nodeitem = NodeItem(nodeitem.label, nodeitem.nodetype, nodeitem.settings, color=color)
                            draw_add_operator(col, nodeitem.label, color, node_item=nodeitem)

                        bigcol.separator(factor=0.4)

                    # Draw search button at bottom of the top column
                    if i == 3:
                        draw_search(bigcol.box())
                        bigcol.separator(factor=0.4)

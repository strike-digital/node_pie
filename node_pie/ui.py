import bpy
import nodeitems_utils
from bpy.types import UILayout, Menu


class STRIKE_MT_node_pie(Menu):
    """The node pie menu"""
    bl_label = "Node pie"

    def draw(self, context):
        layout = self.layout
        pie = layout.menu_pie()
        if not context.space_data.node_tree:
            return
        tree_type = context.space_data.node_tree.bl_rna.identifier
        if tree_type == "ShaderNodeTree":
            menu_prefix = "NODE_MT_category_SH_NEW_"
            icons = {
                "CONVERTOR": "SEQUENCE_COLOR_05",
                "INPUT": "SEQUENCE_COLOR_01",
                "OP_COLOR": "SEQUENCE_COLOR_03",
                "OP_VECTOR": "SEQUENCE_COLOR_06",
                "OUTPUT": "SEQUENCE_COLOR_08",
                "SHADER": "SEQUENCE_COLOR_04",
                "TEXTURE": "SEQUENCE_COLOR_02",
                "GROUP": "SEQUENCE_COLOR_07",
            }
            overrides = {"ShaderNodeVectorMath": "OP_VECTOR"}
            icon_overrides = {}
            exclude = {"ShaderNodeSubsurfaceScattering"}
            parent_type = bpy.types.ShaderNode

        elif tree_type == "GeometryNodeTree":
            menu_prefix = "NODE_MT_category_GEO_"
            icons = {
                "ATTRIBUTE": "SEQUENCE_COLOR_09",
                "COLOR": "SEQUENCE_COLOR_03",
                "CURVE": "SEQUENCE_COLOR_04",
                "GEOMETRY": "SEQUENCE_COLOR_04",
                "INPUT": "SEQUENCE_COLOR_01",
                "INSTANCE": "SEQUENCE_COLOR_04",
                "MATERIAL": "SEQUENCE_COLOR_04",
                "MESH": "SEQUENCE_COLOR_04",
                "POINT": "SEQUENCE_COLOR_04",
                "PRIMITIVES_CURVE": "SEQUENCE_COLOR_04",
                "PRIMITIVES_MESH": "SEQUENCE_COLOR_04",
                "TEXT": "SEQUENCE_COLOR_04",
                "TEXTURE": "SEQUENCE_COLOR_02",
                "UTILITIES": "SEQUENCE_COLOR_05",
                "VECTOR": "SEQUENCE_COLOR_06",
                "VOLUME": "SEQUENCE_COLOR_04",
            }
            overrides = {}
            icon_overrides = {"FunctionNode": "SEQUENCE_COLOR_05", "Input": "SEQUENCE_COLOR_01"}
            exclude = set()
            parent_type = bpy.types.GeometryNode

        else:
            menu_prefix = ""
            icons = {}
            overrides = {}
            icon_overrides = {}
            exclude = set()
            parent_type = bpy.types.Node

        try:
            menu_prefix
        except NameError as e:
            print(e)
            return
        submenus = {d: getattr(bpy.types, d) for d in dir(bpy.types) if d.startswith(menu_prefix)}
        all_nodes = {n.bl_rna.identifier: n for n in parent_type.__subclasses__()}

        def draw_op(layout: UILayout, text: str, icon: str, identifier: str):
            """Draw the add node operator"""
            op = layout.operator("node_pie.add_node", text=text, icon=icon)
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
                    return True
            return False

        def draw_header(layout: UILayout, text: str):
            """Draw the header of a node category"""
            row = layout.row(align=True)
            row.alignment = "CENTER"
            row.label(text=text.capitalize().replace("_", " "))

        def draw_category(layout: UILayout, cat: str, remove: str = ""):
            """Draw all node items in this category"""
            col = layout.column(align=True)
            draw_header(col, cat)

            if cat == "GROUP":
                node_groups = [ng for ng in bpy.data.node_groups if ng.type == tree_type]
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
                for node in subgroup:
                    # Don't draw these nodes
                    if node.nodetype in exclude:
                        continue

                    # Check that the node category has not been overriden to something different
                    if not (overriden := overrides.get(node.nodetype)) or overriden == cat:
                        icon = get_icon(node.nodetype, cat)
                        draw_op(col, node.label.replace(remove, ""), icon, node.nodetype)

                # Draw nodes whose category has been overriden.
                for node_id, node_cat in overrides.items():
                    if node_cat == cat:
                        icon = get_icon(node_id, node_cat)
                        draw_op(col, all_nodes[node_id].bl_rna.name.replace(remove, ""), icon, node_id)

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
            box = pie.box().row()
            draw_category(box, "OP_VECTOR")

            # top
            box = pie.column(align=True).box()
            draw_category(box, "OP_COLOR")

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
            col.separator(factor=.4)
            draw_category(col.box(), "INSTANCE")
            col.separator(factor=.4)
            draw_category(col.box(), "VOLUME")

            # top
            col = pie.column(align=True)
            draw_category(col.box(), "GEOMETRY")

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

            def add_categories(orig_cats: list, i: int):
                """
                Add the given categories to the given area.
                The categories are packed according to their height relative to the tallest category.
                """

                for j, cat in enumerate(orig_cats):
                    idx = categories.index(cat)

                    # If first category, add it and continue
                    if j == 0:
                        areas[i].append(categories.pop(idx))
                        continue

                    # Get the length of all items in the previous column
                    size = len(list(cat.items(context)))
                    prev_items = areas[i][-1]
                    if not isinstance(prev_items, list):
                        prev_items = [areas[i][-1]]
                    prev_item_size = sum(len(list(c.items(context))) for c in prev_items)

                    # Add an extra item to account for the heading of each category
                    prev_item_size += len(prev_items)

                    # Decide whether to add the category to the current column or a new one
                    if prev_item_size + size < biggest:
                        areas[i][-1] = prev_items + [cat]
                    else:
                        areas[i].append(categories.pop(idx))

            # Add half the categories
            biggest = len(list(categories[-1].items(context)))
            orig_cats = categories.copy()
            add_categories(orig_cats[::-2], 0)

            # Add the other half, which is now just the rest of them
            biggest = len(list(categories[-1].items(context)))
            orig_cats = categories.copy()
            add_categories(orig_cats, 1)

            # Draw all of the areas
            for area in areas:
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
                        draw_header(col, node_cat.name)

                        for nodeitem in node_cat.items(context):
                            if not hasattr(nodeitem, "label"):
                                col.separator(factor=.4)
                                continue
                            draw_op(col, nodeitem.label, "SEQUENCE_COLOR_01", nodeitem.nodetype)

                        bigcol.separator(factor=.4)


addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon
    if kc:
        km = kc.keymaps.new(name='Node Editor', space_type='NODE_EDITOR')

        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type='LEFTMOUSE',
            value='PRESS',
            ctrl=True,
        )
        kmi.properties.name = "STRIKE_MT_node_pie"
        addon_keymaps.append((km, kmi))
        kmi = km.keymap_items.new(
            "wm.call_menu_pie",
            type='A',
            value='PRESS',
            ctrl=True,
        )
        kmi.properties.name = "STRIKE_MT_node_pie"
        addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in addon_keymaps:
        km.keymap_items.remove(kmi)
    addon_keymaps.clear()

import bpy

from .npie_btypes import BPropertyGroup
from .npie_helpers import NpieCache


@BPropertyGroup(bpy.types.Node, "node_pie")
class NPIE_NodeProperties(BPropertyGroup.type):

    def get_type_items(self, context):

        if not NpieCache.categories:
            return []
        items = [("", "None", "No category")]
        for cat_name, category in NpieCache.categories.items():
            items.append((cat_name, cat_name, cat_name))
        return items

    type: bpy.props.EnumProperty(items=get_type_items)

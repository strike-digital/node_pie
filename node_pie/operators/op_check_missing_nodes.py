from inspect import isclass

import bpy
from bpy.types import NodeTree

from ..npie_btypes import BOperator
from ..npie_node_def_file import Separator, load_custom_nodes_info
from .op_call_link_drag import region_to_view

EXCLUDED_NODES = {
    "GeometryNodeRepeatInput",
    "GeometryNodeForeachGeometryElementInput",
    "GeometryNodeForeachGeometryElementOutput",
    "GeometryNodeSimulationOutput",
    "GeometryNodeSimulationInput",
    "GeometryNodeRepeatOutput",
    "GeometryNodeViewer",
    "GeometryNodeGroup",
    "NodeGroupInput",
    "NodeGroupOutput",
    "ShaderNodeOutputLineStyle",
    "ShaderNodeOutputWorld",
    "ShaderNodeGroup",
    "CompositorNodeGroup",
}


@BOperator()
class NPIE_OT_check_missing_nodes(BOperator.type):

    def execute(self, context):
        node_tree: NodeTree = context.space_data.edit_tree
        categories, cat_layout = load_custom_nodes_info(context.area.spaces.active.tree_type, context)
        nodes: set[str] = set()
        for cat in categories.values():
            for node in cat.nodes:
                if isinstance(node, Separator):
                    continue
                nodes.add(node.idname)
                # print(node.idname)

        bpy_nodes: set[str] = set()
        for bpy_type in dir(bpy.types):
            bpy_type = getattr(bpy.types, bpy_type)
            if not isclass(bpy_type) or not issubclass(bpy_type, bpy.types.Node):
                continue
            if bpy_type.bl_rna.identifier in EXCLUDED_NODES:
                continue
            try:
                node = node_tree.nodes.new(bpy_type.bl_rna.identifier)
            except RuntimeError:
                continue
            node_tree.nodes.remove(node)
            bpy_nodes.add(bpy_type.bl_rna.identifier)

        print("Missing nodes:")
        unused_nodes = bpy_nodes - nodes
        position = region_to_view(context.area, self.mouse_region)
        for node_type in unused_nodes:
            node = node_tree.nodes.new(node_type)
            node.location = position
            position.x += node.width + 20
            print(node_type)

        print(len(nodes), len(bpy_nodes))

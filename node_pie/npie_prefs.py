import bpy
from mathutils import Color
from bpy.types import UILayout
from bpy.props import BoolProperty, FloatProperty, FloatVectorProperty
from ..shared.functions import get_prefs
from ..shared.ui import draw_enabled_button, draw_section, draw_inline_prop


class NodePiePrefs():
    """Node pie"""

    layout: UILayout
    node_pie_enabled: BoolProperty(name="Enable node pie", default=True)

    npie_variable_sizes: BoolProperty(name="Use variable size", default=True)
    npie_normal_size: FloatProperty(name="Normal size", default=1)
    npie_max_size: FloatProperty(name="Max size", default=2.5)

    # def get_true_colour(name: str):
    #     """For some reason the colours displayed in the headers of nodes are a bit different to the ones that
    #     are displayed in the theme. This converts the raw colour from the theme into the visual colour that you
    #     actually see in the node editor, based on some very crude tests I did."""
    #     col = Color(getattr(bpy.context.preferences.themes[0].node_editor, name)[:3])
    #     # For some reason, the value and saturation are offset by these constants:
    #     col.v -= .486
    #     col.s -= .174
    #     return col

    # converter_node: FloatVectorProperty(default=get_true_colour("converter_node"), subtype="COLOR_GAMMA")
    # color_node: FloatVectorProperty(default=get_true_colour("color_node"), subtype="COLOR_GAMMA")
    # group_node: FloatVectorProperty(default=get_true_colour("group_node"), subtype="COLOR_GAMMA")
    # group_socket_node: FloatVectorProperty(default=get_true_colour("group_socket_node"), subtype="COLOR_GAMMA")
    # frame_node: FloatVectorProperty(default=get_true_colour("frame_node"), subtype="COLOR_GAMMA")
    # matte_node: FloatVectorProperty(default=get_true_colour("matte_node"), subtype="COLOR_GAMMA")
    # distort_node: FloatVectorProperty(default=get_true_colour("distor_node"), subtype="COLOR_GAMMA")
    # input_node: FloatVectorProperty(default=get_true_colour("input_node"), subtype="COLOR_GAMMA")
    # output_node: FloatVectorProperty(default=get_true_colour("output_node"), subtype="COLOR_GAMMA")
    # filter_node: FloatVectorProperty(default=get_true_colour("filter_node"), subtype="COLOR_GAMMA")
    # vector_node: FloatVectorProperty(default=get_true_colour("vector_node"), subtype="COLOR_GAMMA")
    # texture_node: FloatVectorProperty(default=get_true_colour("texture_node"), subtype="COLOR_GAMMA")
    # shader_node: FloatVectorProperty(default=get_true_colour("shader_node"), subtype="COLOR_GAMMA")
    # script_node: FloatVectorProperty(default=get_true_colour("script_node"), subtype="COLOR_GAMMA")
    # pattern_node: FloatVectorProperty(default=get_true_colour("pattern_node"), subtype="COLOR_GAMMA")
    # layout_node: FloatVectorProperty(default=get_true_colour("layout_node"), subtype="COLOR_GAMMA")
    # geometry_node: FloatVectorProperty(default=get_true_colour("geometry_node"), subtype="COLOR_GAMMA")
    # attribute_node: FloatVectorProperty(default=get_true_colour("attribute_node"), subtype="COLOR_GAMMA")

    def draw(self, context):
        layout = self.layout
        layout = draw_enabled_button(layout, self, "node_pie_enabled")
        prefs = get_prefs(context)
        layout = layout.grid_flow(row_major=True, even_columns=True)

        col = draw_section(layout, "Node Popularity")
        fac = .5
        draw_inline_prop(col, prefs, "npie_variable_sizes", factor=fac)
        draw_inline_prop(col, prefs, "npie_normal_size", factor=fac)
        draw_inline_prop(col, prefs, "npie_max_size", factor=fac)
        col.separator(factor=.2)
        row = col.row(align=True)
        row.scale_y = 1.5
        row.operator("node_pie.reset_popularity", icon="FILE_REFRESH")

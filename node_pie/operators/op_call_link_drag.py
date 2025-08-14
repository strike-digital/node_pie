import bpy
import gpu
from bpy.props import BoolProperty, IntProperty
from bpy.types import Area, Context, Event, Node, NodeSocket
from gpu_extras.presets import draw_circle_2d
from mathutils import Vector as V

from ..bl_types import get_socket_location
from ..npie_btypes import BOperator
from ..npie_constants import IS_4_0, IS_4_5
from ..npie_drawing import draw_line
from ..npie_helpers import Rectangle, get_node_location, get_prefs
from ..npie_ui import NPIE_MT_node_pie

location = None
hitbox_size = 10  # The radius in which to register a socket click


def view_to_region(area: Area, coords: V) -> V:
    """Convert 2d editor to screen space coordinates"""
    coords = area.regions[3].view2d.view_to_region(coords[0], coords[1], clip=False)
    return V(coords)


def region_to_view(area: Area, coords: V) -> V:
    """Convert screen space to 2d editor coordinates"""
    coords = area.regions[3].view2d.region_to_view(coords[0], coords[1])
    return V(coords)


def dpifac():
    prefs = bpy.context.preferences.system
    return prefs.dpi / 72
    return prefs.dpi * prefs.pixel_size / 72


def get_socket_bboxes(node: Node) -> tuple[dict[NodeSocket, V], dict[NodeSocket, Rectangle]]:
    """Get the bounding boxes of all inputs and outputs for the given node.
    There is no built in way to do this so it's mostly arbitrary numbers that look about right.
    This doesn't account for nodes with panels, as they are not currently accessible with the api"""
    if not node:
        return

    not_vectors = {"Subsurface Radius"}  # Who decided to make this one socket different smh
    exclude_nodes = {"ShaderNodeBsdfPrincipled", "FunctionNodeCombineMatrix"}

    if node.bl_idname in exclude_nodes:
        return ({}, {})

    location = get_node_location(node)
    positions = {}
    bboxes = {}

    # inputs
    if IS_4_5:
        inputs = [i for i in node.inputs if i.is_icon_visible]
    else:
        inputs = [i for i in node.inputs if not i.hide and i.enabled]
    bottom = V((location.x, location.y - node.dimensions.y / dpifac()))
    min_offset = V((18, 11)) * dpifac()
    max_offset_x = node.width * dpifac()

    if node.type == "REROUTE":
        pos = location * dpifac()
        positions[node.outputs[0]] = pos
        size = V((20, 20))
        bboxes[node.outputs[0]] = Rectangle(pos - size, pos + size)
        return positions, bboxes

    for i, input in enumerate(list(inputs)[::-1]):
        pos = bottom.copy()
        min_offset_y = 0
        if i == 0:
            pos.y -= 5
        if (
            input.type in {"VECTOR", "ROTATION"}
            and not input.hide_value
            and not input.is_linked
            and input.name not in not_vectors
        ):
            pos.y += 82
            min_offset_y = 65
        else:
            pos.y += get_prefs(bpy.context).npie_socket_separation
        bottom = pos
        positions[input] = pos * dpifac()
        pos = pos * dpifac()

        min_co = pos - V((min_offset.x, min_offset.y + min_offset_y))
        max_co = pos + V((max_offset_x, min_offset.y))
        bboxes[input] = Rectangle(min_co, max_co)

    # Outputs
    top = V((location.x + node.width, location.y))
    outputs = [o for o in node.outputs if not o.hide and o.enabled]

    for i, output in enumerate(list(outputs)[::]):
        pos = top.copy()
        if i == 0:
            pos.y -= 35
        else:
            pos.y -= 22
        top = pos
        positions[output] = pos * dpifac()
        pos = pos * dpifac()

        min_co = pos - V((max_offset_x, min_offset.y))
        max_co = pos + V((min_offset.x, min_offset.y))
        bboxes[output] = Rectangle(min_co, max_co)

    return positions, bboxes


def get_socket_locations(node: Node) -> dict[NodeSocket, V]:
    positions = {}
    for socket in node.inputs:
        if not socket.is_icon_visible:
            continue
        positions[socket] = get_socket_location(socket)
    return positions


if IS_4_0:
    shader: gpu.types.GPUShader = gpu.shader.from_builtin("UNIFORM_COLOR")
else:
    shader: gpu.types.GPUShader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")


def draw_debug_lines():
    """Draw a circle around the sockets of the active node, and also the last location that the node pie was activated"""
    node = bpy.context.active_node
    if node:
        positions, bboxes = get_socket_bboxes(node)
        positions = get_socket_locations(node)
        # for socket, bbox in bboxes.items():
        #     batch = batch_for_shader(shader, "LINES", {"pos": bbox.as_lines()})
        #     shader.bind()
        #     line_colour = (1, 0, 1, 0.9)
        #     shader.uniform_float("color", line_colour)
        #     batch.draw(shader)
        for socket, pos in positions.items():
            draw_circle_2d(pos, (1, 0, 1, 1), 5 * dpifac())
    if location:
        draw_circle_2d(location, (0, 1, 1, 1), 5 * dpifac())


handlers = []


def register_debug_handler():
    if get_prefs(bpy.context).npie_draw_debug_lines:
        global handlers
        handlers.append(bpy.types.SpaceNodeEditor.draw_handler_add(draw_debug_lines, (), "WINDOW", "POST_VIEW"))


def unregister_debug_handler():
    unregister()


def register():
    bpy.app.timers.register(register_debug_handler)


def unregister():
    global handlers
    for handler in handlers:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handler, "WINDOW")
    handlers.clear()


@BOperator("node_pie")
class NPIE_OT_call_link_drag(BOperator.type):
    """Call the node pie menu"""

    name: IntProperty()

    pass_through: BoolProperty(
        name="Enable link drag",
        description="Whether to check for link drag, or just pass through to the default pie menu",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR" or not context.space_data.edit_tree:
            return False
        return True

    def invoke(self, context: Context, event: Event):
        self.handler = None
        self.socket = None
        self.from_pos = V((0, 0))
        self.released = False

        mouse_pos = region_to_view(context.area, self.mouse_region)
        global location
        location = mouse_pos
        # Look for a socket near to the mouse position
        for node in context.space_data.edit_tree.nodes:
            if node.hide:
                continue
            positions, bboxes = get_socket_bboxes(node)
            for socket, bbox in bboxes.items():
                if bbox.isinside(mouse_pos) and socket.bl_idname != "NodeSocketVirtual":
                    self.socket = socket
                    self.from_pos = view_to_region(context.area, positions[socket])
                    break

        # if socket clicked
        if not self.pass_through and self.socket and get_prefs(context).npie_use_link_dragging:
            context.area.tag_redraw()
            self.handler = bpy.types.SpaceNodeEditor.draw_handler_add(
                self.draw_handler,
                tuple([context]),
                "WINDOW",
                "POST_PIXEL",
            )
            handlers.append(self.handler)
            return self.start_modal()
        else:
            NPIE_MT_node_pie.from_socket = self.socket
            NPIE_MT_node_pie.to_sockets = []
            bpy.ops.node_pie.call_node_pie("INVOKE_DEFAULT")
        return self.FINISHED

    def finish(self):
        bpy.types.SpaceNodeEditor.draw_handler_remove(self.handler, "WINDOW")
        global handlers
        handlers.remove(self.handler)
        return self.FINISHED

    def modal(self, context: Context, event: Event):
        context.area.tag_redraw()

        if event.type in {"RIGHTMOUSE", "ESC"} and event.value != "RELEASE":
            return self.finish()

        elif event.value == "RELEASE" and event.type not in {"CTRL", "ALT", "OSKEY", "SHIFT"}:
            NPIE_MT_node_pie.from_socket = self.socket
            NPIE_MT_node_pie.to_sockets = []
            bpy.ops.node_pie.call_node_pie("INVOKE_DEFAULT", reset_args=False)
            return self.finish()

        return self.RUNNING_MODAL

    def draw_handler(self, context: Context):
        to_pos = self.mouse_region
        color = self.socket.draw_color(context, self.socket.node)
        draw_line(self.from_pos, to_pos, color)

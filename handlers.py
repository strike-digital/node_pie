# import bpy
# import gpu
# import gpu_extras
# from mathutils import Vector as V

# started = False

# shader = gpu.shader.from_builtin("2D_UNIFORM_COLOR")

# def dpifac():
#     prefs = bpy.context.preferences.system
#     return round(bpy.context.preferences.view.ui_scale, 2)
#     return prefs.dpi * prefs.pixel_size / 72

# def draw_rect(shader, x, y, width, height, color=(1, 1, 1, 1)):
#     points = [(x, y), (x, y + height), (x + width, y + height), (x + width, y)]
#     coords = [points[0], points[1], points[2], points[2], points[3], points[0]]

#     batch = gpu_extras.batch.batch_for_shader(shader, "TRIS", content={"pos": coords})
#     shader.bind()
#     shader.uniform_float("color", color)
#     batch.draw(shader)

# def my_draw():
#     """This is some testing for detecting when the user clicks on a socket.
#     Uncomment the register functions to see it."""
#     context = bpy.context
#     node_tree = context.space_data.edit_tree

#     node = node_tree.nodes.active
#     if not node:
#         return

#     location = node.location.copy()
#     location *= dpifac()
#     bottom = V((location.x, location.y - node.dimensions.y))
#     # socket_positions = [bottom]
#     socket_positions = []
#     inputs = [i for i in node.inputs if not i.hide and i.enabled]
#     # draw_rect(shader, location.x, location.y, node.dimensions.x, -node.dimensions.y)
#     for i, input in enumerate(list(inputs)[::-1]):
#         if not input.enabled:
#             continue

#         pos = bottom.copy()
#         if i == 0:
#             pos.y -= 10 * dpifac()
#             pass
#         if input.type == "VECTOR" and not input.hide_value:
#             pos.y += 82 * dpifac()
#         else:
#             pos.y += 22 * dpifac()
#         bottom = pos
#         socket_positions.append(pos)

#     # socket_positions = [(0, 0), (100, 100), (0, 100)]
#     for pos in socket_positions:
#         width = 10 * dpifac()
#         draw_rect(shader, pos[0] - width / 2, pos[1], width, width, (1, 0, 0, 1))
#     # draw_rect(shader, 0, 0, 100, 100, (1, 0, 0, 1))
#     # draw_rect(shader, 0, 0, 100, 100, (1, 0, 0, 1))
#     verts = [(0, 0), (0, 100), (100, 100), (100, 0)]
#     verts = [verts[0], verts[1], verts[2], verts[2], verts[3], verts[0]]

#     batch = gpu_extras.batch.batch_for_shader(shader, "TRIS", content={"pos": verts})
#     shader.bind()
#     shader.uniform_float("color", (1, 1, 1, 1))
#     batch.draw(shader)

# handler = None

# def register():
#     global handler
#     handler = bpy.types.SpaceNodeEditor.draw_handler_add(my_draw, (), "WINDOW", "POST_VIEW")

# def unregister():
#     global handler
#     bpy.types.SpaceNodeEditor.draw_handler_remove(handler, "WINDOW")
# import bpy
# from ..npie_btypes import BOperator


# @BOperator("node_pie")
# class NPIE_OT_link_drag_listener(BOperator.type):

#     def invoke(self, context, event):
#         self.quit = False
#         self.count = 0
#         print("start")
#         return self.start_modal()

#     # def on_press(self):

#     def modal(self, context, event):
#         if self.quit:
#             if event.type == "MOUSEMOVE":
#                 if self.count > 3:
#                     print("quit")
#                     return self.FINISHED
#                 print("add")
#                 self.count += 1
#                 return self.PASS_THROUGH
#             print("no_quit")
#             return self.PASS_THROUGH

#         if event.type in {"ESC"}:
#             return self.FINISHED

#         print(event.type)
#         if event.type == "LEFTMOUSE" and event.value == "PRESS":
#             self.quit = True
#             bpy.app.timers.register(call, first_interval=.1)
#             # self.on_press()
#             print("ho")
#             return self.PASS_THROUGH
#         elif event.type == "LEFTMOUSE" and event.value == "RELEASE":
#             print("ha")
#             for area in context.screen.areas:
#                 if area.type == "NODE_EDITOR":
#                     break
#             else:
#                 print("fuck")
#             with context.temp_override(area=area):
#                 bpy.ops.node_pie.call_node_pie("INVOKE_DEFAULT")
#             return self.RUNNING_MODAL

#         return self.PASS_THROUGH


# def call():
#     bpy.ops.node_pie.link_drag_listener("INVOKE_DEFAULT")


# def register():
#     bpy.app.timers.register(call)

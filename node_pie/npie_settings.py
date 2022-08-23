# import bpy
# from bpy.props import PointerProperty, BoolProperty
# from bpy.types import PropertyGroup


# class TestSettings(PropertyGroup):

#     show_test: BoolProperty(
#         name="show test operator",
#         description="show test operator",
#         default=False,
#     )


# def register():
#     bpy.types.Scene.test_tool = PointerProperty(type=TestSettings)


# def unregister():
#     del bpy.types.Scene.test_tool
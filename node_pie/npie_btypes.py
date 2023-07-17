from enum import Enum
import inspect
from typing import TYPE_CHECKING, Literal
from dataclasses import dataclass

import blf
import bpy
from bpy.props import BoolProperty, FloatProperty, FloatVectorProperty, IntProperty, PointerProperty, StringProperty
from bpy.types import Context, Event, Material, Menu, Object, Operator, Panel, UILayout
from mathutils import Vector
"""A module containing helpers to make defining blender types easier (panels, operators etc.)"""

to_register = []


def wrap_text(self, context: Context, text: str, layout: UILayout, width: int = 0, centered: bool = False) -> list[str]:
    """Take a string and draw it over multiple lines so that it is never concatenated."""
    return_text = []
    row_text = ''

    width = width or context.region.width
    system = context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11, dpi)

    for word in text.split():
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)

        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word

    if row_text:
        return_text.append(row_text)

    for text in return_text:
        row = layout.row()
        if centered:
            row.alignment = "CENTER"
        row.label(text=text)

    return return_text


@dataclass
class BMenu():
    """A decorator for defining blender menus that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the menu class, with whatever arguments you want.
    all of the arguments are optional, as they can all be inferred from the class name and __doc__.
    This works best for menus that use the naming convension ADDON_NAME_MT_menu_name.

    Args:
        label (str): The name of the menu that is displayed when it is drawn in the UI.
        description (str): The description of the menu that is displayed in the tooltip.
        idname (str): a custom identifier for this menu. By default it is the name of the menu class.
    """

    label: str = ""
    description: str = ""
    idname: str = ""

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("PT_")[-1]
        idname = self.idname if self.idname else cls.__name__
        label = self.label or cls_name_end.replace("_", " ").title()

        if self.description:
            panel_description = self.description
        elif cls.__doc__:
            panel_description = cls.__doc__
        else:
            panel_description = label

        class Wrapped(cls, Menu):
            bl_idname = idname
            bl_label = label
            bl_description = panel_description

            wrap_text = wrap_text
            layout: UILayout

            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.wrap_text(context, "That's a cool menu you've got there", self.layout, centered=True)

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        return Wrapped


@dataclass
class BPanel():
    """A decorator for defining blender Panels that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the panel class, with whatever arguments you want.
    The only required arguments are the space and region types,
    and the rest can be inferred from the class name and __doc__.
    This works best for panels that use the naming convension ADDON_NAME_PT_panel_name.

    Args:
        space_type (str): The type of editor to draw this panel in (e.g. VIEW_3D, NODE_EDITOR, etc.)
        region_type (str): The area of the UI to draw the panel in (almost always UI)
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        label (str): The name of the panel that is displayed in the header (if no header draw function is supplied).
        description (str): The description of the panel that is displayed in the UI.
        idname (str): a custom identifier for this panel. By default it is the name of the panel class.
        parent (str): if provided, this panel will be a subpanel of the given panel bl_idname.
        index (int): if set, this panel will be drawn at that index in the list
            (panels with lower indeces will be drawn higher).
        context (str): The mode to show this panel in. find them here: https://blender.stackexchange.com/a/73154/57981
        popover_width (int): The width of this panel when it is drawn in a popover in UI units (16px x UI scale).
        show_header (bool): Whether to draw the header of this panel.
        default_closed (bool): Whether to draw this panel closed by default before it is opened.
        header_button_expand (bool): Whether to allow buttons drawn in the header to expand to take up the full width,
            or to draw them as squares instead (which is the default).
    """

    space_type: Literal["EMPTY", "VIEW_3D", "NODE_EDITOR", "IMAGE_EDITOR", "SEQUENCE_EDITOR", "CLIP_EDITOR",
                        "DOPESHEET_EDITOR", "GRAPH_EDITOR", "NLA_EDITOR", "TEXT_EDITOR", "CONSOLE", "INFO", "TOPBAR",
                        "STATUSBAR", "OUTLINER", "PROPERTIES", "FILE_BROWSER", "SPREADSHEET", "PREFERENCES",]
    region_type: Literal["UI", "TOOLS", "HEADER", "FOOTER", "TOOL_PROPS", "WINDOW", "CHANNELS", "TEMPORARY", "PREVIEW",
                         "HUD", "NAVIGATION_BAR", "EXECUTE", "TOOL_HEADER", "XR",]
    category: str = ""
    label: str = ""
    description: str = ""
    idname: str = ""
    parent: str = ""
    index: int = -1
    context: str = ""
    popover_width: int = -1
    show_header: bool = True
    default_closed: bool = False
    header_button_expand: bool = False

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("PT_")[-1]
        idname = self.idname if self.idname else cls.__name__
        label = self.label or cls_name_end.replace("_", " ").title()
        label = cls.bl_label if hasattr(cls, "bl_label") else label
        parent_id = self.parent.bl_idname if hasattr(self.parent, "bl_idname") else self.parent

        if self.description:
            panel_description = self.description
        elif cls.__doc__:
            panel_description = cls.__doc__
        else:
            panel_description = label

        options = {
            "DEFAULT_CLOSED": self.default_closed,
            "HIDE_HEADER": not self.show_header,
            "HEADER_BUTTON_EXPAND": self.header_button_expand,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)

        class Wrapped(cls, Panel):
            bl_idname = idname
            bl_label = label
            bl_options = options
            bl_category = self.category
            bl_space_type = self.space_type
            bl_region_type = self.region_type
            bl_description = panel_description

            if self.context:
                bl_context = self.context
            if self.index != -1:
                bl_order = self.index
            if parent_id:
                bl_parent_id = parent_id
            if self.popover_width != -1:
                bl_ui_units_x = self.popover_width

            wrap_text = wrap_text

            # Create a default draw function, useful for quick tests
            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.wrap_text(context, "That's a cool panel you've got there", self.layout, centered=True)

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        return Wrapped


property_groups = []


@dataclass
class BPropertyGroup():

    type: bpy.types.ID
    name: str

    def __call__(self, cls):
        self.cls = cls
        global property_groups
        property_groups.append(self)
        return cls

    def register(self):
        setattr(self.type, self.name, PointerProperty(type=self.cls))

    def unregister(self):
        delattr(self.type, self.name)


class Cursor(Enum):
    """Wraps the poorly documented blender cursor functions to allow for auto-complete"""
    DEFAULT = "DEFAULT"
    NONE = 'NONE'
    WAIT = 'WAIT'
    CROSSHAIR = 'CROSSHAIR'
    MOVE_X = 'MOVE_X'
    MOVE_Y = 'MOVE_Y'
    KNIFE = 'KNIFE'
    TEXT = 'TEXT'
    PAINT_BRUSH = 'PAINT_BRUSH'
    PAINT_CROSS = 'PAINT_CROSS'
    DOT = 'DOT'
    ERASER = 'ERASER'
    HAND = 'HAND'
    SCROLL_X = 'SCROLL_X'
    SCROLL_Y = 'SCROLL_Y'
    SCROLL_XY = 'SCROLL_XY'
    EYEDROPPER = 'EYEDROPPER'
    PICK_AREA = 'PICK_AREA'
    STOP = 'STOP'
    COPY = 'COPY'
    CROSS = 'CROSS'
    MUTE = 'MUTE'
    ZOOM_IN = 'ZOOM_IN'
    ZOOM_OUT = 'ZOOM_OUT'

    @classmethod
    def set_icon(cls, value: str):
        if isinstance(value, Enum):
            value = value.name
        bpy.context.window.cursor_modal_set(str(value))

    @classmethod
    def reset_icon(cls):
        bpy.context.window.cursor_modal_set("DEFAULT")

    @classmethod
    def set_location(cls, location: tuple):
        bpy.context.window.cursor_warp(location[0], location[1])


@dataclass
class BOperator():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    To get type hinting for it's extra functions, the class should inherit from BOperator.type instead of Operator
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        idname (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        label (str): The name of the operator that is displayed in the UI.
        description (str): The description of the operator that is displayed in the UI.
        dynamic_description (bool): Whether to automatically allow bl_description to be altered from the UI.
        register (bool): Whether to display the operator in the info window and support the redo panel.
        undo (bool): Whether to push an undo step after the operator is executed.
        undo_grouped (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        internal (bool): Whether the operator is only used internally and should not be shown in menu search
            (doesn't affect the operator search accessible when developer extras is enabled).
        wrap_cursor (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        wrap_cursor_x (bool): Only wrap the cursor in the horizontal (x) direction.
        wrap_cursor_y (bool): Only wrap the cursor in the horizontal (y) direction.
        preset (bool): Display a preset button with the operators settings.
        blocking (bool): Block anything else from using the cursor.
        macro (bool): Use to check if an operator is a macro.
    """

    category: str
    idname: str = ""
    label: str = ""
    description: str = ""
    dynamic_description: bool = True
    register: bool = True
    undo: bool = False
    undo_grouped: bool = False
    internal: bool = False
    wrap_cursor: bool = False
    wrap_cursor_x: bool = False
    wrap_cursor_y: bool = False
    preset: bool = False
    blocking: bool = False
    macro: bool = False

    # Here we need to do some cursed stuff to get type hinting to work
    if TYPE_CHECKING:

        @property
        @classmethod
        def type(cls):
            """Inherit from this to get proper type hinting for operator classes defined with the BOperator decorator"""
            return BOperatorType

    def __call__(decorator, cls=None):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        inherit_from = [cls, Operator]
        if cls:
            cls_name_end = cls.__name__.split("OT_")[-1]
            idname = f"{decorator.category}." + (decorator.idname or cls_name_end)
            label = decorator.label or cls_name_end.replace("_", " ").title()

            if decorator.description:
                op_description = decorator.description
            elif cls.__doc__:
                op_description = cls.__doc__
            else:
                op_description = label
        else:
            inherit_from = [Operator]
            op_description = idname = label = ""

        options = {
            "REGISTER": decorator.register,
            "UNDO": decorator.undo,
            "UNDO_GROUPED": decorator.undo_grouped,
            "GRAB_CURSOR": decorator.wrap_cursor,
            "GRAB_CURSOR_X": decorator.wrap_cursor_x,
            "GRAB_CURSOR_Y": decorator.wrap_cursor_y,
            "BLOCKING": decorator.blocking,
            "INTERNAL": decorator.internal,
            "PRESET": decorator.preset,
            "MACRO": decorator.macro,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)

        class Wrapped(*inherit_from):
            bl_idname = idname
            bl_label = label
            bl_options = options
            layout: UILayout
            event: Event

            cursor = Cursor

            wrap_text = wrap_text

            # Set up a description that can be set from the UI draw function
            if decorator.dynamic_description:
                bl_description: StringProperty(default=op_description, options={"HIDDEN"})

                @classmethod
                def description(cls, context, props):
                    if props:
                        return props.bl_description
                    else:
                        return op_description
            else:
                bl_description = op_description

            def __init__(self):
                # Allow auto-complete for execute function return values
                self.FINISHED = {"FINISHED"}
                self.CANCELLED = {"CANCELLED"}
                self.PASS_THROUGH = {"PASS_THROUGH"}
                self.RUNNING_MODAL = {"RUNNING_MODAL"}

            def call_popup(self, width=300):
                """Call a popup that shows the parameters of the operator, or a custom draw function.
                Doesn't execute the operator.
                This needs to be returned by the invoke method to work."""
                return bpy.context.window_manager.invoke_popup(self, width=width)

            def call_popup_confirm(self, width=300):
                """Call a popup that shows the parameters of the operator (or a custom draw function),
                and a confirmation button.
                This needs to be returned by the invoke method to work."""
                return bpy.context.window_manager.invoke_props_dialog(self, width=width)

            def call_popup_auto_confirm(self):
                """Call a popup that shows the parameters of the operator, or a custom draw function.
                Every time the parameters of the operator are changed, the operator is executed automatically.
                This needs to be returned by the invoke method to work."""
                return bpy.context.window_manager.invoke_props_popup(self, self.event)

            def start_modal(self):
                """Initialize this as a modal operator.
                Should be called and returned by the invoke function"""
                bpy.context.window_manager.modal_handler_add(self)
                return self.RUNNING_MODAL

            def set_event_attrs(self, event):
                self.event = event
                self.mouse_window = Vector((event.mouse_x, event.mouse_y))
                self.mouse_window_prev = Vector((event.mouse_prev_x, event.mouse_prev_y))
                self.mouse_region = Vector((event.mouse_region_x, event.mouse_region_y))

            def invoke(self, context: Context, event: Event):
                """Wrap the invoke function so we can set some initial attributes"""
                self.set_event_attrs(event)
                if hasattr(super(), "invoke"):
                    return super().invoke(context, event)
                else:
                    return self.execute(context)

            def modal(self, context: Context, event: Event):
                """Wrap the modal function so we can set some initial attributes"""
                self.set_event_attrs(event)
                return super().modal(context, event)

            def execute(self, context: Context):
                """Wrap the execute function to remove the need to return {"FINISHED"}"""
                ret = super().execute(context)
                if ret is None:
                    return self.FINISHED
                return ret

        Wrapped.__doc__ = op_description
        if cls:
            Wrapped.__name__ = cls.__name__
        return Wrapped


class BOperatorType(BOperator("")()):
    """A type to inherit from that gives proper type hinting for classes using the @BOperator decorator"""


BOperator.type = BOperatorType


@dataclass
class FunctionToOperator():
    """A decorator that takes a function and registers an operator that will call it in the execute function.
    It automatically converts the arguments of the function to operator arguments for basic data types,
    and for blender id types (e.g. Objects etc.), the operator takes the name and then automatically gets the data
    block to pass to the wrapped function

    The idname of the operator is just bpy.ops.{category}.{function_name}
    
    Maybe this is going overboard and making the code harder to understand, but it works for me.
    
    Args:
        category (str): The category that the operator will be placed in.
        label (str): The label to display in the UI"""

    category: str
    label: str = ""

    def __call__(self, function):

        parameters = inspect.signature(function).parameters
        supported_id_types = {
            Material,
            Object,
        }

        # Convert between python and blender property types
        # In the future if I need to add more Data blocks, I can, but for now it is just materials and objects.
        prop_types = {
            str: StringProperty,
            bool: BoolProperty,
            float: FloatProperty,
            int: IntProperty,
            Vector: FloatVectorProperty,
        }

        prop_types.update({id_type: StringProperty for id_type in supported_id_types})
        label = self.label if self.label else function.__name__.replace("_", " ").title()

        # Define the new operator
        @BOperator(
            category=self.category,
            idname=function.__name__,
            description=function.__doc__,
            label=label,
        )
        class CustomOperator(BOperator.type):

            def execute(self, context):
                # Get the operator properties and convert them to function key word arguments

                types_to_data = {
                    Material: bpy.data.materials,
                    Object: bpy.data.objects,
                }

                kwargs = {}
                for name, param in parameters.items():
                    # If it is an ID type, convert the name to the actual data block
                    if param.annotation in supported_id_types:
                        kwargs[name] = types_to_data[param.annotation].get(getattr(self, name))
                    # Context is a special case
                    elif param.annotation == Context:
                        kwargs[name] = context
                    # Otherwise just pass the value
                    else:
                        kwargs[name] = getattr(self, name)

                # Call the function
                function(**kwargs)
                return {"FINISHED"}

        # Convert the function arguments into operator properties by adding to the annotations
        for name, param in parameters.items():
            prop_type = prop_types.get(param.annotation)

            # Custom python objects cannot be passed.
            if not prop_type and param.annotation != Context:
                raise ValueError(f"Cannot convert function arguments of type {param.annotation} to operator property")

            # Whether to set a default value or not
            if param.default == inspect._empty:
                prop = prop_types[param.annotation](name=name)
            else:
                prop = prop_types[param.annotation](name=name, default=param.default)

            # Create the property
            CustomOperator.__annotations__[name] = prop

        # CustomOperator.__name__ = function.__name__
        to_register.append(CustomOperator)
        return function


# def increment(cls, value):
#     for name, prop in cls.__annotations__.items():
#         if hasattr(prop, "keywords") and prop.function == PointerProperty:
#             cls = prop.keywords.get("type")
#             if cls:
#                 return increment(cls, value + 1)
#     return value

# def get_depth(pgroup: BPropertyGroup):
#     return increment(pgroup.cls, 0)
#     return 1


def register():
    for op in to_register:
        bpy.utils.register_class(op)

    # property_groups.sort(key=get_depth, reverse=True)
    for pgroup in property_groups:
        pgroup.register()


def unregister():
    for op in to_register:
        bpy.utils.unregister_class(op)
    for pgroup in property_groups:
        pgroup.unregister()
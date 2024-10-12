import copy
import importlib
import inspect
import pkgutil
import typing
from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from pathlib import Path
from types import ModuleType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterator,
    Literal,
    MutableMapping,
    ParamSpec,
    Self,
    TypeVar,
    Union,
)

import bpy
from bpy.props import (
    BoolProperty,
    BoolVectorProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    FloatVectorProperty,
    IntProperty,
    IntVectorProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    ID,
    Area,
    Context,
    Event,
    Material,
    Menu,
    Node,
    NodeTree,
    Object,
    Operator,
    Panel,
    PropertyGroup,
    UILayout,
    bpy_prop_collection,
    bpy_struct,
)
from mathutils import Vector

"""A module containing helpers to make defining blender types easier (panels, operators etc.)
Optionally also allows for automatically registering decorated classes, in the correct order."""

__all__ = [
    "BMenu",
    "BOperator",
    "BPanel",
    "BPoll",
    "BPropertyGroup",
    "FunctionToOperator",
    "CustomProperty",
    "configure",
    "register",
    "unregister",
]
T = TypeVar("T")
KT = TypeVar("KT")
VT = TypeVar("VT")


# CONFIG
class Config:
    addon_string: str = ""
    register: bool = False

    all_modules: list[ModuleType] = []
    register_list: list[bpy_struct] = []


def configure(addon_string: str = "", auto_register: bool = False):
    """Configure btypes settings for this addon, should usually be called in the root init file.
    This must be called in the root init file.
    Make sure it is called before auto_load.init() in order for the configuration to apply before registration.

    addon_string: The name of the addon. Used to set the subpath of operators e.g. `bpy.ops.addon_string.op`
    auto_register: Whether to automatically register classes created using btypes decorators."""
    Config.addon_string = addon_string
    Config.register = auto_register
    if auto_register:
        Config.all_modules = _get_modules()


def _get_modules() -> list[ModuleType]:
    """Get the list of modules in the addon using btypes"""

    def get_module_names(path: Path, root: str = ""):
        """Recursively get a list of all module names in a path"""
        module_names = []
        for _, module_name, is_pkg in pkgutil.iter_modules([path]):
            if is_pkg:
                sub_path = path / module_name
                sub_root = root + module_name + "."
                module_names.extend(get_module_names(sub_path, sub_root))
            else:
                module_names.append(root + module_name)
        return module_names

    # Get the file that configure() was called from
    file = Path(inspect.stack()[2].filename).parent
    module_names = sorted(get_module_names(file))

    # Get the base package. This includes bl_ext.repo in 4.2 and above
    split = 3 if __package__.startswith("bl_ext.") else 1
    base_package = ".".join(__package__.split(".")[:split])

    all_modules = []
    for name in module_names:
        # Ignore self
        if base_package + "." + name == __name__:
            continue
        # Import all files in module to load them.
        all_modules.append(importlib.import_module("." + name, package=base_package))

    # observe custom __reg_order__ parameter
    all_modules.sort(key=lambda m: getattr(m, "__reg_order__", 100))
    return all_modules


# UTILS
def enum_value(enum_or_value: Enum | T):
    """If value is an enum item, return enum value, else return value"""
    if isinstance(enum_or_value, Enum):
        return enum_or_value.value
    return enum_or_value


# ENUMS


class Cursor(Enum):
    """Wraps the poorly documented blender cursor functions to allow for auto-complete"""

    DEFAULT = "DEFAULT"
    NONE = "NONE"
    WAIT = "WAIT"
    CROSSHAIR = "CROSSHAIR"
    MOVE_X = "MOVE_X"
    MOVE_Y = "MOVE_Y"
    KNIFE = "KNIFE"
    TEXT = "TEXT"
    PAINT_BRUSH = "PAINT_BRUSH"
    PAINT_CROSS = "PAINT_CROSS"
    DOT = "DOT"
    ERASER = "ERASER"
    HAND = "HAND"
    SCROLL_X = "SCROLL_X"
    SCROLL_Y = "SCROLL_Y"
    SCROLL_XY = "SCROLL_XY"
    EYEDROPPER = "EYEDROPPER"
    PICK_AREA = "PICK_AREA"
    STOP = "STOP"
    COPY = "COPY"
    CROSS = "CROSS"
    MUTE = "MUTE"
    ZOOM_IN = "ZOOM_IN"
    ZOOM_OUT = "ZOOM_OUT"

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
        bpy.context.window.cursor_warp(int(location[0]), int(location[1]))


class ExecContext:
    """Operator execution contexts"""

    INVOKE = "INVOKE_DEFAULT"
    "Emulate an operator being clicked on by the user (executes the invoke function)."
    EXEC = "EXECUTE_DEFAULT"
    "The default execution context, only runs the execute function."

    "Tbh I have no idea what these ones do."
    INVOKE_SCREEN = "INVOKE_SCREEN"
    INVOKE_AREA = "INVOKE_AREA"
    INVOKE_REGION_PREVIEW = "INVOKE_REGION_PREVIEW"
    INVOKE_REGION_CHANNELS = "INVOKE_REGION_CHANNELS"
    INVOKE_REGION_WIN = "INVOKE_REGION_WIN"
    EXEC_REGION_WIN = "EXEC_REGION_WIN"
    EXEC_REGION_CHANNELS = "EXEC_REGION_CHANNELS"
    EXEC_REGION_PREVIEW = "EXEC_REGION_PREVIEW"
    EXEC_AREA = "EXEC_AREA"
    EXEC_SCREEN = "EXEC_SCREEN"


class BDict(OrderedDict, MutableMapping[str, VT]):
    """Used to mimic the behavior of the built in Collection Properties in Blender, which act as a
    mix of dictionaries and lists."""

    def get(*args, **kwargs) -> VT:
        return super().get(*args, **kwargs)

    def __iter__(self) -> Iterator[VT]:
        return iter(self.values())

    def __getitem__(self, __key: str) -> VT:
        if isinstance(__key, int):
            return list(self.values())[__key]
        return super().__getitem__(__key)


def _unwrap_method(func: classmethod):
    """Convert a classmethod to a plain function"""
    return func.__func__ if hasattr(func, "__func__") else func


class BPoll:
    """Presets for common poll functions
    All functions starting with `poll_` are poll functions.
    Other functions can be used to modify and combine poll functions.
    ```
    class MyOperator:
        poll = BPoll.poll_x
        # or
        poll = BPoll.both(BPoll.poll_x, BPoll.poll_y)
        # or
        poll = BPoll.both(BPoll.inverse(BPoll.poll_x), BPoll.poll_y)
    ```

    Eventually it's probably easier to just write your own poll function,
    but these can still be used as building blocks"""

    def _unwrap_classmethod_args(func):
        """Convert all provided function arguments that are classmethods into normal functions
        This is needed for the operation functions so they can be called from within each other.
        It's a stupid amount of complexity for such a simple feature, but it is nice that it works."""

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            args = list(args)
            for i, arg in enumerate(args):
                args[i] = _unwrap_method(arg)
            for name, kwarg in kwargs:
                kwargs[name] = _unwrap_method(kwarg)
            return func(*args, **kwargs)

        return wrapped_func

    @_unwrap_classmethod_args
    def inverse(f: Callable) -> classmethod:
        """Return the inverse of the provided poll function. Equivalent to the `not` keyword"""
        return classmethod(lambda cls, context: not f(cls, context))

    @_unwrap_classmethod_args
    def both(f1: Callable, f2: Callable) -> classmethod:
        """Combine two poll functions. Equivalent to the `and` keyword"""
        # return classmethod(lambda cls, context: f1(context) and _unwrap_method(f2)(cls, context))
        return classmethod(lambda cls, context: f1(cls, context) and f2(cls, context))

    @_unwrap_classmethod_args
    def neither(f1: Callable, f2: Callable) -> classmethod:
        """Return if both poll functions are False. Equivalent to `not f1 and not f2`"""
        return classmethod(lambda cls, context: not f1(cls, context) and not f2(cls, context))

    @classmethod
    def poll_file_saved(cls, context: Context) -> bool:
        return bpy.data.is_saved

    @classmethod
    def poll_node_editor(cls, context: Context, tree_type=None) -> Area:
        if context.area.type != "NODE_EDITOR":
            return None
        if tree_type:
            return context.area if context.space_data.tree_type == tree_type else None
        return context.area

    @classmethod
    def poll_geometry_node_editor(cls, context: Context) -> Area:
        return BPoll.poll_node_editor(context, tree_type="GeometryNodeTree")

    @classmethod
    def poll_shader_node_editor(cls, context: Context) -> Area:
        return BPoll.poll_node_editor(context, tree_type="ShaderNodeTree")

    @classmethod
    def poll_compositor_node_editor(cls, context: Context) -> Area:
        return BPoll.poll_node_editor(context, tree_type="CompositorNodeTree")

    @classmethod
    def poll_active_node_tree(cls, context: Context) -> NodeTree:
        if BPoll.poll_node_editor(context) and context.space_data.node_tree:
            return context.space_data.node_tree


# TYPES
class BRegister:
    """A decorator used to register a class with `btypes`, without using a specific btypes decorator."""

    def __call__(self, cls: T) -> T:
        Config.register_list.append(cls)
        return cls


@dataclass
class BMenu:
    """
    A decorator for defining blender menus that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the menu class, with whatever arguments you want.
    all of the arguments are optional, as they can all be inferred from the class name and __doc__.
    This works best for menus that use the naming convention ADDON_NAME_MT_menu_name.

    ```
    @BMenu()
    class ADDON_MT_my_menu(BMenu.type):
        pass
    ```

    Args:
        label (str): The name of the menu that is displayed when it is drawn in the UI.
        description (str): The description of the menu that is displayed in the tooltip.
        idname (str): a custom identifier for this menu. By default it is the name of the menu class.
    """

    label: str = ""
    description: str = ""
    idname: str = ""

    type = Menu

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

        @wraps(cls, updated=())
        class Wrapped(cls, Menu):
            bl_idname = idname
            bl_label = label
            bl_description = panel_description

            layout: UILayout

            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.layout.label(text="That's a cool menu you've got there")

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        Config.register_list.append(Wrapped)
        return Wrapped


@dataclass
class BPanel:
    """
    A decorator for defining blender Panels that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the panel class, with whatever arguments you want.
    The only required arguments are the space and region types,
    and the rest can be inferred from the class name and __doc__.
    This works best for panels that use the naming convention ADDON_NAME_PT_panel_name.

    Simplest example:
    ```
    @BPanel("VIEW_3D")
    class ADDON_PT_my_panel(BPanel.type):
        pass
    ```

    Args:
        space_type (str): The type of editor to draw this panel in (e.g. VIEW_3D, NODE_EDITOR, etc.)
        region_type (str): The area of the UI to draw the panel in (almost always UI)
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        label (str): The name of the panel that is displayed in the header (if no header draw function is supplied).
        description (str): The description of the panel that is displayed in the UI.
        idname (str): a custom identifier for this panel. By default it is the name of the panel class.
        parent (str): if provided, this panel will be a sub-panel of the given panel bl_idname.
        index (int): if set, this panel will be drawn at that index in the list
            (panels with lower indices will be drawn higher).
        context (str): The mode to show this panel in. find them here: https://blender.stackexchange.com/a/73154/57981
        popover_width (int): The width of this panel when it is drawn in a popover in UI units (16px x UI scale).
        show_header (bool): Whether to draw the header of this panel.
        default_closed (bool): Whether to draw this panel closed by default before it is opened.
        header_button_expand (bool): Whether to allow buttons drawn in the header to expand to take up the full width,
            or to draw them as squares instead (which is the default).
    """

    space_type: Literal[
        "EMPTY",
        "VIEW_3D",
        "NODE_EDITOR",
        "IMAGE_EDITOR",
        "SEQUENCE_EDITOR",
        "CLIP_EDITOR",
        "DOPESHEET_EDITOR",
        "GRAPH_EDITOR",
        "NLA_EDITOR",
        "TEXT_EDITOR",
        "CONSOLE",
        "INFO",
        "TOPBAR",
        "STATUSBAR",
        "OUTLINER",
        "PROPERTIES",
        "FILE_BROWSER",
        "SPREADSHEET",
        "PREFERENCES",
    ]
    region_type: Literal[
        "UI",
        "TOOLS",
        "HEADER",
        "FOOTER",
        "TOOL_PROPS",
        "WINDOW",
        "CHANNELS",
        "TEMPORARY",
        "PREVIEW",
        "HUD",
        "NAVIGATION_BAR",
        "EXECUTE",
        "TOOL_HEADER",
        "XR",
    ] = "UI"
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

    type = Panel

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
            "HEADER_LAYOUT_EXPAND": self.header_button_expand,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)

        @wraps(cls, updated=())
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

            # Create a default draw function, useful for quick tests
            if not hasattr(cls, "draw"):

                def draw(self, context: Context):
                    self.layout.label(text="That's a cool panel you've got there")

        Wrapped.__doc__ = panel_description
        Wrapped.__name__ = cls.__name__
        Config.register_list.append(Wrapped)
        return Wrapped


@dataclass
class CustomPropertyType:
    """Placeholder used to identify a custom property on an operator."""

    type: Any


def CustomProperty(type: T, description: str) -> T:
    """Define a custom property on an operator, in the same way as bpy.props:
    ```
    my_property: CustomProperty(type=bpy.types.Object, description="My property")
    ```
    You'll only be able to use this property as an argument for the operator when using the
    BOperator.run() function, otherwise you'll get an error."""
    if TYPE_CHECKING:
        return type
    else:
        return CustomPropertyType(type)


# Define a TypeVar to be able to have proper type hinting and auto complete when using the decorator
OperatorClass = TypeVar("OperatorClass", bound=Operator)


class BOperatorBase(Operator, Generic[OperatorClass]):
    """The base operator class used by the @BOperator decorator."""

    bl_idname: str
    bl_label: str
    bl_options: set[str]
    bl_description: str

    layout: UILayout
    event: Event
    poll_message: str = ""

    cursor = Cursor
    __no_reg__ = True

    FINISHED = {"FINISHED"}
    CANCELLED = {"CANCELLED"}
    PASS_THROUGH = {"PASS_THROUGH"}
    RUNNING_MODAL = {"RUNNING_MODAL"}

    custom_args: dict
    _has_set_custom_args: bool = False

    @classmethod
    def register(cls):
        """Wrap the register function"""

        # Find all of the custom properties that are defined as type hints on the class
        custom_args = {k: v for k, v in cls.__bases__[1].__annotations__.items() if isinstance(v, CustomPropertyType)}
        cls.custom_args = custom_args
        for name, prop_type in custom_args.items():
            setattr(cls, name, prop_type.type)

        if hasattr(super(), "register"):
            super().register()

    @classmethod
    def run(cls, exec_context: ExecContext = None, **kwargs) -> set[str]:
        """Run this operator with the given execution context.
        An extra feature is that you can pass arguments of custom types (not just built in blender ones).
        They need to be defined in the same way as normal arguments on the class (e.g. my_prop: BoolProperty()),
        but using the CustomProperty() function instead."""

        # Get operator function
        op = bpy.ops
        for part in cls.bl_idname.split("."):
            op = getattr(op, part)

        for name, value in kwargs.copy().items():
            if name in cls.custom_args:
                setattr(cls, name, value)
                del kwargs[name]

        # Execute
        if exec_context:
            return op(exec_context, **kwargs)
        else:
            return op(**kwargs)

    @classmethod
    def draw_button(
        cls,
        layout: UILayout,
        text=None,
        icon="NONE",
        emboss=True,
        depress=False,
        icon_value=0,
        text_ctxt="",
        translate=True,
        exec_context=ExecContext.INVOKE,
        **kwargs,
    ) -> OperatorClass:
        """Draw this operator as a button in a provided layout.
        All extra keyword arguments are set as arguments for the operator.
        The operator object is also returned, so for type hinting set the attributes on that."""
        layout.operator_context = exec_context
        op = layout.operator(
            cls.bl_idname,
            text=text if isinstance(text, str) else cls.bl_label,
            icon=icon,
            icon_value=icon_value,
            emboss=emboss,
            depress=depress,
            text_ctxt=text_ctxt,
            translate=translate,
        )
        for name, value in kwargs.items():
            setattr(op, name, value)
        return op

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
        """Set the `event, mouse_window, mouse_window_prev` and `mouse_region` attributes on the class"""
        self.event = event
        self.mouse_window = Vector((event.mouse_x, event.mouse_y))
        self.mouse_window_prev = Vector((event.mouse_prev_x, event.mouse_prev_y))
        self.mouse_region = Vector((event.mouse_region_x, event.mouse_region_y))

    def _set_custom_args(self):
        """Set the custom arguments as attributes on the class instance and clear them from the class object."""
        if self._has_set_custom_args:
            return

        for name in self.custom_args:
            setattr(self, name, getattr(self.__class__, name))
            setattr(self.__class__, name, None)

        self._has_set_custom_args = True

    @classmethod
    def poll(cls, context: Context):
        """Wrap the poll function to automate the setting of poll messages."""
        if hasattr(super(), "poll"):
            retval = super().poll(context)
            if not retval and cls.poll_message:
                # This should be a function so as to avoid unnecessary evaluation,
                # But also because it being a string causes the Blender VSCode extension
                # to freeze up, for some extremely clear reason.
                cls.poll_message_set(lambda: cls.poll_message)
            return retval
        return True

    def invoke(self, context: Context, event: Event):
        """Wrap the invoke function so we can set some initial attributes"""
        self._set_custom_args()

        self.set_event_attrs(event)
        if hasattr(super(), "invoke"):
            return super().invoke(context, event)
        else:
            return self.execute(context)

    def draw(self, context: Context):
        """Wrap the draw function to add a default layout"""
        if hasattr(super(), "draw"):
            super().draw(context)
        else:
            self.layout.label(text="This is my awesome operator.")

    def modal(self, context: Context, event: Event):
        """Wrap the modal function so we can set some initial attributes"""
        self.set_event_attrs(event)
        return super().modal(context, event)

    def execute(self, context: Context):
        """Wrap the execute function to remove the need to return {"FINISHED"}"""
        self._set_custom_args()

        if hasattr(super(), "execute"):
            ret = super().execute(context)
            if ret is None:
                return self.FINISHED
            return ret
        return self.FINISHED


@dataclass
class BOperator:
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    To get type hinting for it's extra functions, the class should inherit from BOperator.type instead of Operator
    The category of the operator is required if the addon acronym has not been set.
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convention ADDON_NAME_OT_operator_name.

    ```
    # Minimal example
    @BOperator("addon")
    class ADDON_OT_my_operator(BOperator.type):
        def execute(self, context):
            print("My operator!")
    ```

    Args:
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
            This is optional if the addon_string property has been configured in the init file,
            otherwise this will raise a ValueError if no value is given.
        idname (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        label (str): The name of the operator that is displayed in the UI.
        description (str): The description of the operator that is displayed in the UI.
        dynamic_description (bool): Whether to automatically allow bl_description to be altered from the UI.
        register (bool): Whether to display the operator in the info window and support the redo panel.
        undo (bool): Whether to push an undo step after the operator is executed.
        undo_grouped (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        internal (bool): Whether the operator is only used internally and should not be shown in menu search
        modal_priority (bool): Handle events before other modal operators without this option.
            (doesn't affect the operator search accessible when developer extras is enabled).
        wrap_cursor (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        wrap_cursor_x (bool): Only wrap the cursor in the horizontal (x) direction.
        wrap_cursor_y (bool): Only wrap the cursor in the horizontal (y) direction.
        preset (bool): Display a preset button with the operators settings.
        blocking (bool): Block anything else from using the cursor.
        macro (bool): Use to check if an operator is a macro.
    """

    category: str = ""
    idname: str = ""
    label: str = ""
    description: str = ""
    dynamic_description: bool = True
    register: bool = True
    undo: bool = False
    undo_grouped: bool = False
    internal: bool = False
    modal_priority: bool = False
    wrap_cursor: bool = False
    wrap_cursor_x: bool = False
    wrap_cursor_y: bool = False
    preset: bool = False
    blocking: bool = False
    macro: bool = False

    if TYPE_CHECKING:
        type = BOperatorBase
        "Inherit from this to get proper auto complete for the extra attributes and functions"
    else:
        type = Operator

    # The amount of time put into these type hints is not funny. And it looks so simple smh.
    def __call__(decorator, cls: T) -> Union[T, BOperatorBase[T]]:
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""

        # Get the first part of the idname
        if decorator.category:
            category = decorator.category
        else:
            if not Config.addon_string:
                raise ValueError(
                    f"No category provided for BOperator {cls.__name__}, \
                    and the addon acronym has not been set with the btypes.configure function in the init file".replace(
                        "  ", ""
                    )
                )
            category = Config.addon_string

        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = f"{category}." + (decorator.idname or cls_name_end)
        label = decorator.label or cls_name_end.replace("_", " ").title()

        if decorator.description:
            op_description = decorator.description
        elif cls.__doc__:
            op_description = cls.__doc__
        else:
            op_description = label

        options = {
            "REGISTER": decorator.register,
            "UNDO": decorator.undo,
            "UNDO_GROUPED": decorator.undo_grouped,
            "MODAL_PRIORITY": decorator.modal_priority,
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

        @wraps(cls, updated=(), assigned=("__module__", "__name__", "__qualname__", "__doc__", "__type_params__"))
        class Wrapped(BOperatorBase, cls, Operator):
            bl_idname = idname
            bl_label = label
            bl_options = options

            __no_reg__ = False

            # Set up a description that can be set from the UI draw function
            if decorator.dynamic_description:
                bl_description: StringProperty(default=op_description, options={"HIDDEN"})

                @classmethod
                def description(cls, context, props) -> str:
                    return props.bl_description if props else op_description

            else:
                bl_description = op_description

        Wrapped.__doc__ = op_description
        Wrapped.__name__ = cls.__name__
        Config.register_list.append(Wrapped)
        return Wrapped


@dataclass
class FunctionToOperator:
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
        Config.register_list.append(CustomOperator)
        return function


# ------------------------------------------------------------------
# PROPERTIES
# ------------------------------------------------------------------


"""
This is my attempt at a method of defining Blender properties while maintaining useful type hinting.
I have no idea if it's worth it, or if it's massive overkill, but it does make me feel better.

Some notes:
    - properties need to be defined using the "=" sign rather than the ":" sign
      (this is because type hints aren't propagated through function calls)
"""


BpyParams = ParamSpec("BpyParams")  # The Blender property ParamSpec
BpyReturn = TypeVar("BpyReturn")  # The return type of the Blender property
DecoratedParams = ParamSpec("DecoratedParams")  # The decorated function ParamSpec
DecoratedReturn = TypeVar("DecoratedReturn")  # The return type of the decorated function


def override_prop_return(bpy_property: Callable[BpyParams, BpyReturn]):
    """This is some type magic that lets the decorated function inherit the type signature of another function.
    It's pretty mind bending: https://github.com/python/mypy/issues/10574#issuecomment-1902246197.
    I modified it to allow you to override the return type, allowing creating wrapper functions
    that type hint a different return type to reality."""

    def decorator(wrapper: Callable[DecoratedParams, DecoratedReturn]) -> Callable[BpyParams, DecoratedReturn]:

        def decorated(*args: BpyParams.args, **kwargs: BpyParams.kwargs) -> DecoratedReturn:
            return bpy_property(*args, **kwargs)

        return decorated

    return decorator


class BProperty:
    """
    Used to interact with properties at runtime, for example drawing a property using the syntax:
    ```
    MyClass.my_prop.draw(layout, data, ...)
    ```
    """

    def __init__(self, name: str):
        self._name = name

    def __repr__(self):
        return f"BProperty('{self._name}')"

    def draw(self, layout: UILayout, data, *args, **kwargs):
        layout.prop(data, self._name, *args, **kwargs)


@override_prop_return(StringProperty)
def BStringProperty(*args, **kwargs) -> Union[str, BProperty]:
    return StringProperty(*args, **kwargs)


@override_prop_return(EnumProperty)
def BEnumProperty(*args, **kwargs) -> Union[str, BProperty]:
    return EnumProperty(*args, **kwargs)


@override_prop_return(IntProperty)
def BIntProperty(*args, **kwargs) -> Union[int, BProperty]:
    return IntProperty(*args, **kwargs)


@override_prop_return(IntVectorProperty)
def BIntVectorProperty(*args, **kwargs) -> Union[list[int], BProperty]:
    return IntVectorProperty(*args, **kwargs)


@override_prop_return(BoolProperty)
def BBoolProperty(*args, **kwargs) -> Union[bool, BProperty]:
    return BoolProperty(*args, **kwargs)


@override_prop_return(BoolVectorProperty)
def BBoolVectorProperty(*args, **kwargs) -> Union[list[bool], BProperty]:
    return BoolVectorProperty(*args, **kwargs)


@override_prop_return(FloatProperty)
def BFloatProperty(*args, **kwargs) -> Union[float, BProperty]:
    return FloatProperty(*args, **kwargs)


@override_prop_return(FloatVectorProperty)
def BFloatVectorProperty(*args, **kwargs) -> Union[list[float], BProperty]:
    return FloatVectorProperty(*args, **kwargs)


@override_prop_return(CollectionProperty)
def BCollectionProperty(*args, **kwargs) -> Union[bpy.types.bpy_prop_collection, BProperty]:
    return CollectionProperty(*args, **kwargs)


# @override_prop_return(PointerProperty)
# def BPointerProperty(*args, **kwargs) -> Union[BProperty]:
#     return PointerProperty(*args, **kwargs)
# Since the PointerProperty return type hint is dependent on its input arguments,
# I implemented this one manually without using the decorator
# I can't be bothered to add a docstring for it.
def BPointerProperty(
    type: T,
    name: str = "",
    description: str = "",
    translation_context: str = "*",
    options: set = {"ANIMATABLE"},
    override: set = set(),
    poll: Callable[[Self, Context], bool] = None,
    update: Callable[[Self, Context], None] = None,
) -> Union[T, BProperty]:
    return PointerProperty(
        type=type,
        name=name,
        description=description,
        translation_context=translation_context,
        options=options,
        override=override,
        poll=poll,
        update=update,
    )


PropertyGroupClass = TypeVar("PropertyGroupClass", bound=PropertyGroup)


class BPropertyGroupBase(PropertyGroup):

    @property
    def parent(self):
        """Get the parent instance of this property group"""
        try:
            path = self.path_from_id()
        except ValueError:
            # The object has been removed
            return None
        parts = path.split(".")[:-1]
        parent = self.id_data
        for part in parts:
            # Special case for collections that require indices to access
            if "[" in part:
                subparts = part.split("[")
                index = subparts[1][:-1]
                if index.replace("-", "").isdigit():
                    index = int(index)
                elif index.startswith('"') or index.startswith("'"):
                    index = index[1:-1]
                parent = getattr(parent, subparts[0])[index]
                continue
            parent = getattr(parent, part)
        return parent

    def copy_settings_to(self, other: PropertyGroup, recursive=False):
        """Copy the attributes of this property group to another one."""
        for name in self.keys():
            attr = getattr(self, name)

            # Special case for collection properties
            if recursive and issubclass(type(attr), bpy_prop_collection):
                other_collection = getattr(other, name)
                for item in attr:
                    other_item = other_collection.add()
                    BPropertyGroupBase.copy_settings_to(item, other_item, recursive=recursive)
                continue

            # Copy attribute
            try:
                setattr(other, name, getattr(self, name))
            except AttributeError as e:
                print(e)
                pass


class BPropertyGroup:
    """
    A decorator for extending the PropertyGroup type.

    Args:
        id_type: An ID type to register this group to (equivalent of setting a `PointerProperty` on that type).
        name: The name to set the attribute on the ID type to be.
    """

    type = BPropertyGroupBase

    def __init__(self, id_type: ID = None, name: str = ""):
        self.id_type = id_type
        self.name = name

    @staticmethod
    def resolve_property_group_props(wrapped_cls):
        """Convert the BProperty syntax to Blender annotations.
        This is a separate method so it can be used by all class that can hold properties.

        Returns:
            wrapped_cls: The class that will be registered
            return_cls: The class to be returned by the decorator"""
        # Here we need two versions of the class:
        # One that is registered with all of the properties as annotations
        # One that has actual values for the properties that can be used as an api, e.g. for drawing the property
        # This is necessary because if we just change out the value in the original class, the blender property is
        # overridden by the new value.
        return_cls = copy.copy(wrapped_cls)

        for name, value in inspect.getmembers(wrapped_cls, lambda x: hasattr(x, "keywords") and hasattr(x, "function")):
            # Convert properties created with the = sign to annotations for registration
            wrapped_cls.__annotations__[name] = value
            # Set the value of the returned class to be a custom class so that it can be used to draw the property
            # Using the syntax
            # MyClass.my_prop.draw(...)
            setattr(return_cls, name, BProperty(name))

        Config.register_list.append(wrapped_cls)
        return wrapped_cls, return_cls

    def __call__(self, cls: PropertyGroupClass) -> PropertyGroupClass:
        self.cls = cls
        property_groups.append(self)

        @wraps(cls, updated=())
        class Wrapped(cls, BPropertyGroupBase):
            pass

        self.wrapped_cls, return_cls = self.resolve_property_group_props(Wrapped)

        return return_cls

    def _register(self):
        # Set Blender pointer property
        if self.id_type:
            setattr(self.id_type, self.name, PointerProperty(type=self.wrapped_cls))

    def _unregister(self):
        if self.id_type:
            delattr(self.id_type, self.name)


property_groups: list[BPropertyGroup] = []


# -----------------------------------------------------------------
# NODE TREES
# -----------------------------------------------------------------


class BNodeTreeBase(NodeTree):
    pass


@dataclass
class BNodeTree:
    idname: str = ""
    label: str = ""
    icon: str = ""

    if TYPE_CHECKING:
        type = BNodeTreeBase
        "Inherit from this to get proper auto complete for the extra attributes and functions"
    else:
        type = NodeTree

    def __call__(decorator, cls: T) -> Union[T, BNodeTreeBase]:
        idname = decorator.idname or cls.__name__
        label = decorator.label or idname
        icon = decorator.icon or "X"

        @wraps(cls, updated=())
        class Wrapped(BNodeTreeBase, cls, NodeTree):
            bl_idname = idname
            bl_label = label
            bl_icon = icon

        _, return_cls = BPropertyGroup.resolve_property_group_props(Wrapped)

        # Config.register_list.append(Wrapped)
        return return_cls


class BNodeBase(Node):
    pass


@dataclass
class BNode:
    idname: str = ""
    label: str = ""
    icon: str = ""

    if TYPE_CHECKING:
        type = BNodeBase
        "Inherit from this to get proper auto complete for the extra attributes and functions"
    else:
        type = Node

    def __call__(decorator, cls: T) -> Union[T, BNodeBase]:
        idname = decorator.idname or cls.__name__
        label = decorator.label or idname
        icon = decorator.icon or "X"

        @wraps(cls, updated=())
        class Wrapped(BNodeBase, cls, Node):
            bl_idname = idname
            bl_label = label
            bl_icon = icon

        Config.register_list.append(Wrapped)
        return Wrapped


def _get_dependencies():
    """
    Get a dictionary of each class and the classes that it depends on.
    Currently this takes into account property groups, and their Pointer and Collection properties.
    """

    # Get the direct children of each class
    children = {}
    for cls in Config.register_list:
        if issubclass(cls, PropertyGroup):
            children[cls] = set()
            for name, value in typing.get_type_hints(cls, {}, {}).items():
                if not isinstance(value, bpy.props._PropertyDeferred):
                    continue
                child = value.keywords.get("type")
                if child is None:
                    continue
                children[cls].add(child)

    dependencies = {}

    def get_deps(cls):
        """Recursively get the classes that have the given class as a child"""
        deps = {c for c, child_list in children.items() if cls in child_list}
        for dep in deps:
            deps = deps.union(get_deps(dep))
        return deps

    for cls in Config.register_list:
        dependencies[cls] = get_deps(cls)

    return dependencies


def register():
    if Config.register:
        # Sort classes so that they can register in the correct order without errors
        dependencies = _get_dependencies()
        Config.register_list.sort(key=lambda cls: len(dependencies[cls]), reverse=True)

        for cls in Config.register_list:
            bpy.utils.register_class(cls)

    for pgroup in property_groups:
        pgroup._register()

    if Config.register:
        for module in Config.all_modules:
            if hasattr(module, "register"):
                module.register()


def unregister():
    for pgroup in property_groups:
        pgroup._unregister()

    if Config.register:
        for cls in Config.register_list:
            bpy.utils.unregister_class(cls)

        for module in Config.all_modules:
            if hasattr(module, "unregister"):
                module.unregister()

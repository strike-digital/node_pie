from dataclasses import dataclass
import json
from typing import TYPE_CHECKING, Generic, Type, TypeVar
from bpy.props import StringProperty
from bpy.types import Context, Operator, AddonPreferences, UILayout
from mathutils import Vector as V
from .npie_constants import NODE_DEF_DIR, NODE_DEF_EXAMPLE_PREFIX
if TYPE_CHECKING:
    from .npie_prefs import NodePiePrefs
else:
    NodePiePrefs = AddonPreferences


def get_prefs(context) -> NodePiePrefs:
    """Return the addon preferences"""
    return context.preferences.addons[__package__.split(".")[0]].preferences


def lerp(fac, a, b) -> float:
    """Linear interpolation (mix) between two values"""
    return (fac * b) + ((1 - fac) * a)


def inv_lerp(fac, a, b) -> float:
    """Inverse Linar Interpolation, get the fraction between a and b on which fac resides."""
    return (fac - a) / (b - a)


def vec_divide(a, b) -> V:
    """Elementwise divide for two vectors"""
    return V(e1 / e2 if e2 != 0 else 0 for e1, e2 in zip(a, b))


def vec_min(a, b) -> V:
    """Elementwise minimum for two vectors"""
    return V(min(e) for e in zip(a, b))


def vec_max(a, b) -> V:
    """Elementwise maximum for two vectors"""
    return V(max(e) for e in zip(a, b))


def map_range(val, from_min=0, from_max=1, to_min=0, to_max=2):
    """Map a value from one input range to another. Works in the same way as the map range node in blender.
    succinct formula from: https://stackoverflow.com/a/45389903"""
    return (val - from_min) / (from_max - from_min) * (to_max - to_min) + to_min


class JSONWithCommentsDecoder(json.JSONDecoder):

    def __init__(self, **kw):
        super().__init__(**kw)

    def decode(self, s: str):
        s = '\n'.join(l if not l.lstrip().startswith('//') else '' for l in s.split('\n'))
        return super().decode(s)


def get_all_def_files():
    files = []
    for file in NODE_DEF_DIR.rglob("*"):
        if file.is_file() and file.suffix == ".jsonc" and not file.name.startswith(NODE_DEF_EXAMPLE_PREFIX):
            files.append(file)
    return files


T = TypeVar("T")


@dataclass
class BOperator():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        category (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        idname (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        label (str): The name of the operator that is displayed in the UI.
        description (str): The description of the operator that is displayed in the UI.
        dynamic_description (bool): Whether to automatically allow bl_description to be altered from the UI.
        custom_invoke (bool): Whether to automatically log each time an operator is invoked.
        call_popup (bool): Whether to call a popup after the invoke function is run.
        
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
        logging (int | bool): Whether to log when this operator is called.
            Default is to use the class logging variable which can be set with set_logging() and is global.
    """

    _logging = False

    @classmethod
    def set_logging(cls, enable):
        """Set the global logging state for all operators"""
        cls._logging = enable

    category: str
    idname: str = ""
    label: str = ""
    description: str = ""
    dynamic_description: bool = True
    custom_invoke: bool = True
    call_popup: bool = False

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
    # The default is to use the class logging setting, unless this has a value other than -1.
    # ik this is the same name as the module, but I don't care.
    logging: int = -1

    def __call__(self, cls: Type[T]):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""
        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = f"{self.category}." + (self.idname or cls_name_end)
        label = self.label or cls_name_end.replace("_", " ").title()

        if self.description:
            op_description = self.description
        elif cls.__doc__:
            op_description = cls.__doc__
        else:
            op_description = label

        options = {
            "REGISTER": self.register,
            "UNDO": self.undo,
            "UNDO_GROUPED": self.undo_grouped,
            "GRAB_CURSOR": self.wrap_cursor,
            "GRAB_CURSOR_X": self.wrap_cursor_x,
            "GRAB_CURSOR_Y": self.wrap_cursor_y,
            "BLOCKING": self.blocking,
            "INTERNAL": self.internal,
            "PRESET": self.preset,
            "MACRO": self.macro,
        }

        options = {k for k, v in options.items() if v}
        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)
        log = self._logging if self.logging == -1 else bool(self.logging)

        class Wrapped(cls, Operator, Generic[T]):
            bl_idname = idname
            bl_label = label
            bl_options = options
            __original__ = cls

            if self.dynamic_description:
                bl_description: StringProperty(default=op_description)

                @classmethod
                def description(cls, context, props):
                    if props:
                        return props.bl_description.replace("  ", "")
                    else:
                        return op_description
            else:
                bl_description = op_description

            if not hasattr(cls, "execute"):

                def execute(self, context):
                    return {"FINISHED"}

            if self.custom_invoke or self.call_popup:

                def invoke(_self, context: Context, event):
                    """Here we can log whenever an operator using this decorator is invoked"""
                    if log:
                        print(f"Invoke: {idname}")

                    if hasattr(super(), "invoke"):
                        retval = super().invoke(context, event)

                    if self.call_popup:
                        return context.window_manager.invoke_props_dialog(_self)

                    if not hasattr(super(), "invoke"):
                        retval = _self.execute(context)
                    return retval

            @classmethod
            def draw_button(
                _cls,
                layout: UILayout,
                text: str = "",
                text_ctxt: str = "",
                translate: bool = True,
                icon: str | int = 'NONE',
                emboss: bool = True,
                depress: bool = False,
                icon_value: int = 0,
            ) -> 'Wrapped':
                """Draw this operator as a button.
                I wanted it to be able to provide proper auto complete for the operator properties,
                but I can't figure out how to do that for a decorator... It's really annoying.

                Args:
                    text (str): Override automatic text of the item
                    text_ctxt (str): Override automatic translation context of the given text
                    translate (bool): Translate the given text, when UI translation is enabled
                    icon (str | into): Icon, Override automatic icon of the item
                    emboss (bool): Draw the button itself, not just the icon/text
                    depress (bool): Draw pressed in
                    icon_value (int): Icon Value, Override automatic icon of the item
                
                Returns:
                    OperatorProperties: Operator properties to fill in
                """
                return layout.operator(
                    _cls.bl_idname,
                    text=text,
                    text_ctxt=text_ctxt,
                    translate=translate,
                    icon=icon,
                    emboss=emboss,
                    depress=depress,
                    icon_value=icon_value,
                )

        Wrapped.__doc__ = op_description
        Wrapped.__name__ = cls.__name__
        return Wrapped


class Rectangle():
    """Helper class to represent a rectangle"""

    __slots__ = ["min", "max"]

    def __init__(self, min_co=(0, 0), max_co=(0, 0)):
        min_co = V(min_co)
        max_co = V(max_co)

        self.min = min_co
        self.max = max_co

    # alternate getter syntax
    minx = property(fget=lambda self: self.min.x)
    miny = property(fget=lambda self: self.min.y)
    maxx = property(fget=lambda self: self.max.x)
    maxy = property(fget=lambda self: self.max.y)

    @property
    def coords(self):
        """Return coordinates for drawing"""
        coords = [
            (self.minx, self.miny),
            (self.maxx, self.miny),
            (self.maxx, self.maxy),
            (self.minx, self.maxy),
        ]
        return coords

    @property
    def size(self):
        return self.max - self.min

    # FIXME: This can just be changed to using vec_mean of the min and max
    @property
    def center(self):
        return self.min + vec_divide(self.max - self.min, V((2, 2)))

    # return the actual min/max values. Needed because the class does not check
    # if the min and max values given are actually min and max at init.
    # I could fix it, but a bunch of stuff is built on it already, and I can't really be bothered
    @property
    def true_min(self):
        return vec_min(self.min, self.max)

    @property
    def true_max(self):
        return vec_max(self.min, self.max)

    def __str__(self):
        return f"Rectangle(V({self.minx}, {self.miny}), V({self.maxx}, {self.maxy}))"

    def __repr__(self):
        return self.__str__()

    def __mul__(self, value):
        if not isinstance(value, V):
            value = V((value, value))
        return Rectangle(self.min * value, self.max * value)

    def __add__(self, value):
        if not isinstance(value, V):
            value = V((value, value))
        return Rectangle(self.min + value, self.max + value)

    def isinside(self, point) -> bool:
        """Check if a point is inside this rectangle"""
        point = point
        min = self.true_min
        max = self.true_max
        return min.x <= point[0] <= max.x and min.y <= point[1] <= max.y

    def as_lines(self, individual=False):
        """Return a list of lines that make up this rectangle"""
        lines = []
        add = lines.append if individual else lines.extend
        coords = self.coords
        for i, coord in enumerate(coords):
            add((coord, coords[i - 1]))
        return lines

    def crop(self, rectangle):
        """Crop this rectangle to the inside of another one"""
        self.min = vec_max(self.min, rectangle.min)
        self.max = vec_min(self.max, rectangle.max)
        # prevent min/max overspilling on other side
        self.min = vec_min(self.min, rectangle.max)
        self.max = vec_max(self.max, rectangle.min)
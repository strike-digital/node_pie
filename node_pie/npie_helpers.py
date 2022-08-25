from dataclasses import dataclass
from bpy.types import Operator
import bpy


def get_prefs(context) -> bpy.types.AddonPreferences:
    """Return the addon preferences"""
    return context.preferences.addons[__package__.split(".")[0]].preferences


def lerp(fac, a, b) -> float:
    """Linear interpolation (mix) between two values"""
    return (fac * b) + ((1 - fac) * a)


def inv_lerp(fac, a, b) -> float:
    """Inverse Linar Interpolation, get the fraction between a and b on which fac resides."""
    return (fac - a) / (b - a)


@dataclass
class Op():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        `category` (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        `idname` (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        `label` (str): The name of the operator that is displayed in the UI.
        `description` (str): The description of the operator that is displayed in the UI.
        `register` (bool): Whether to display the operator in the info window and support the redo panel.
        `undo` (bool): Whether to push an undo step after the operator is executed.
        `undo_grouped` (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        `internal` (bool): Whether the operator is only used internally and should not be shown in menu search
            (doesn't affect the operator search accessible when developer extras is enabled).
        `wrap_cursor` (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        `wrap_cursor_x` (bool): Only wrap the cursor in the horizontal (x) direction.
        `wrap_cursor_y` (bool): Only wrap the cursor in the horizontal (y) direction.
        `preset` (bool): Display a preset button with the operators settings.
        `blocking` (bool): Block anything else from using the cursor.
        `macro` (bool): Use to check if an operator is a macro.
        `logging` (int | bool): Whether to log when this operator is called.
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
    invoke: bool = True
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

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""

        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = self.category + "." + (self.idname if self.idname else cls_name_end)

        if self.label:
            label = self.label
        else:
            label = cls_name_end.replace("_", " ").title()

        if self.description:
            description = self.description
        elif cls.__doc__:
            description = cls.__doc__
        else:
            description = label

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

        if self.logging == -1:
            log = self._logging
        else:
            log = bool(self.logging)

        class Wrapped(cls, Operator):
            bl_idname = idname
            bl_label = label
            bl_description = description
            bl_options = options

            if self.invoke:

                def invoke(_self, context, event):
                    """Here we can log whenever an operator using this decorator is invoked"""
                    if log:
                        # I could use the actual logging module here, but I can't be bothered.
                        print(f"Invoke: {idname}")
                    if hasattr(super(), "invoke"):
                        return super().invoke(context, event)
                    else:
                        return _self.execute(context)

        Wrapped.__doc__ = description
        Wrapped.__name__ = cls.__name__
        return Wrapped
import importlib
import inspect
import pkgutil
import traceback
import typing
from pathlib import Path
from time import perf_counter

import bpy

__all__ = (
    "init",
    "register",
    "unregister",
)

blender_version = bpy.app.version

modules = None
ordered_classes = None
exclude_dirs = []
exclude_classes = []


def init():
    global modules
    global ordered_classes

    modules = get_all_submodules(Path(__file__).parent)
    ordered_classes = get_ordered_classes_to_register(modules)


def register():

    for module in modules.copy():
        if module.__name__ == __name__ or hasattr(module, "__no_reg__") and module.__no_reg__:
            modules.remove(module)
            continue

    # Custom attributes to prevent registering, and to enable proper registration order
    for cls in ordered_classes.copy():
        if hasattr(cls, "__no_reg__") and cls.__no_reg__ or cls in exclude_classes:
            ordered_classes.remove(cls)

    for cls in ordered_classes:
        # Unregister if error
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            unregister()
            raise e

    for module in modules.copy():
        if hasattr(module, "register"):
            try:
                module.register()
            except Exception as e:
                unregister()
                raise e


def unregister():
    for cls in reversed(ordered_classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError as e:
            traceback.print_exception(e)
            # print(traceback.format_exc(e))

    for module in modules:
        if hasattr(module, "unregister"):
            module.unregister()


# Import modules
#################################################


def get_all_submodules(directory):
    # changed this from directory.name to __package__ for 4.2 extensions compatibility
    return list(iter_submodules(directory, __package__))


def iter_submodules(path, package_name):
    for name in sorted(iter_submodule_names(path)):
        start = perf_counter()
        yield importlib.import_module("." + name, package_name)
        # print(f"Importing {name} took {perf_counter()-start:.5f}")


def iter_submodule_names(path, root=""):
    if any(d in Path(path).parts for d in exclude_dirs):
        return
    for _, module_name, is_package in pkgutil.iter_modules([str(path)]):
        if is_package:
            sub_path = path / module_name
            sub_root = root + module_name + "."
            yield from iter_submodule_names(sub_path, sub_root)
        else:
            yield root + module_name


# Find classes to register
#################################################


def get_ordered_classes_to_register(modules):
    return toposort(get_register_deps_dict(modules))


def get_register_deps_dict(modules):
    my_classes = set(iter_my_classes(modules))
    my_classes_by_idname = {cls.bl_idname: cls for cls in my_classes if hasattr(cls, "bl_idname")}

    deps_dict = {}
    for cls in my_classes:
        deps_dict[cls] = set(iter_my_register_deps(cls, my_classes, my_classes_by_idname))
    return deps_dict


def iter_my_register_deps(cls, my_classes, my_classes_by_idname):
    yield from iter_my_deps_from_annotations(cls, my_classes)
    yield from iter_my_deps_from_parent_id(cls, my_classes_by_idname)


def iter_my_deps_from_annotations(cls, my_classes):
    for value in typing.get_type_hints(cls, {}, {}).values():
        dependency = get_dependency_from_annotation(value)
        if dependency is not None:
            if dependency in my_classes:
                yield dependency


def get_dependency_from_annotation(value):
    if blender_version >= (2, 93):
        if isinstance(value, bpy.props._PropertyDeferred):
            return value.keywords.get("type")
    else:
        if isinstance(value, tuple) and len(value) == 2:
            if value[0] in (bpy.props.PointerProperty, bpy.props.CollectionProperty):
                return value[1]["type"]
    return None


def iter_my_deps_from_parent_id(cls, my_classes_by_idname):
    if issubclass(cls, bpy.types.Panel):
        parent_idname = getattr(cls, "bl_parent_id", None)
        if parent_idname is not None:
            parent_cls = my_classes_by_idname.get(parent_idname)
            if parent_cls is not None:
                yield parent_cls


def iter_my_classes(modules):
    base_types = get_register_base_types()
    for cls in get_classes_in_modules(modules):
        if any(issubclass(cls, base) for base in base_types):
            if not getattr(cls, "is_registered", False):
                yield cls


def get_classes_in_modules(modules):
    classes = set()
    for module in modules:
        for cls in iter_classes_in_module(module):
            classes.add(cls)
    return classes


def iter_classes_in_module(module):
    for value in module.__dict__.values():
        if inspect.isclass(value):
            yield value


def get_register_base_types():
    return set(
        getattr(bpy.types, name)
        for name in [
            "Panel",
            "Operator",
            "PropertyGroup",
            "AddonPreferences",
            "Header",
            "Menu",
            "Node",
            "NodeSocket",
            "NodeTree",
            "UIList",
            "RenderEngine",
            "Gizmo",
            "GizmoGroup",
        ]
    )


# Find order to register to solve dependencies
#################################################


def toposort(deps_dict):
    sorted_list = []
    sorted_values = set()
    while len(deps_dict) > 0:
        unsorted = []
        for value, deps in deps_dict.items():
            if len(deps) == 0:
                sorted_list.append(value)
                sorted_values.add(value)
            else:
                unsorted.append(value)
        deps_dict = {value: deps_dict[value] - sorted_values for value in unsorted}
    return sorted_list

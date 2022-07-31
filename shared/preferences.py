import bpy
import importlib
import inspect
from pathlib import Path
from bpy.props import EnumProperty
from .icons import icon_collections

PACKAGE = __package__.split(".")[0]

# import individual preferences classes from sub addons
# so that they can be inherited from by the main prefs.
all_prefs = []
addon_dir = Path(__file__).parents[1]
pref_files = addon_dir.glob("*/*_prefs.py")  # preferences files need to end with "_prefs.py"

for file in pref_files:
    # convert file path to import path. There's probably a better way to do this.
    import_path = file.as_posix().split(PACKAGE)[-1].replace("/", ".").replace(".py", "")
    mod = importlib.import_module(import_path, PACKAGE)
    classes = inspect.getmembers(mod, inspect.isclass)  # Get all classes from the imported module.
    for name, cls in classes:
        if "prefs" in name.lower():  # preferences class names must have "prefs" in them
            all_prefs.append(cls)


# Inherit from all preferences defined by sub addons
class NodeExtrasPrefs(bpy.types.AddonPreferences, *all_prefs):
    bl_idname = PACKAGE
    global all_prefs

    def get_pages(self, context):
        items = []
        icons = icon_collections["icons"]
        for i, pref in enumerate(all_prefs):
            icon = pref.icon if hasattr(pref, "icon") else 0
            icon = icons[icon].icon_id if icon else 0
            items.append((str(i), pref.__doc__, pref.__doc__, 0, i))
        return items

    prefs_page: EnumProperty(items=get_pages)
    layout: bpy.types.UILayout
    is_single = len(all_prefs) == 1

    def draw(self, context):
        """Draw the preferences of sub addons as separate pages"""
        layout = self.layout
        if len(self.get_pages(context)) > 1:
            row = layout.row(align=True)
            row.prop(self, "prefs_page", expand=True)

        pref = all_prefs[int(self.prefs_page)]
        pref.draw(self, context)

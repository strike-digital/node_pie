import bpy
from dataclasses import dataclass
from pathlib import Path
import re

geo_nodes_categories = {}


@dataclass
class NodeCategory():
    """An imitator of the built in blender NodeCategory class, that implements the necessary settings"""

    name: str
    nodeitems: list

    def items(self, context):
        return self.nodeitems


@dataclass
class NodeItem():
    """An imitator of the built in blender NodeItem class, that implements the necessary settings"""

    label: str
    nodetype: str


def main():
    """Due to a change in the way geometry nodes generates the add menu in 3.4, the old method of using
    noditems_utils to get the node categories and items will no longer work
    (which I'm not too happy about, as there's no other official way to get the same information).
    I made a devtalk post, but that hasn't really gone anywhere unfortunately:
    https://devtalk.blender.org/t/nodeitems-utils-module-deprecated-in-3-4-with-no-obvious-alternative.
    So as a kinda shitty workaround, this parses the python file that defines the menu,
    and extracts the node items and categories. This isn't ideal, as it's likely to be broken if the file is changed,
    but it's the best solution I have :("""

    scripts_path = bpy.utils.resource_path("LOCAL")
    script_path = Path(scripts_path) / "scripts" / "startup" / "bl_ui" / "node_add_menu_geometry.py"

    with open(script_path, "r") as f:
        text = f.readlines()

    # https://regex101.com/r/cVXk6l/1
    category_label_pattern = re.compile("bl_label\s*=\s*\"([^\"]*)\"")
    node_type_pattern = re.compile("node_add_menu\.add_node_type\(.*, \"([^\"]*)\"")

    category = ""
    for line in text:
        match = re.findall(category_label_pattern, line)
        if match and match[0] != '':
            category = match[0]
            continue
        match = re.findall(node_type_pattern, line)
        if match:
            cat = geo_nodes_categories.get(category, NodeCategory(category, []))
            node_idname = match[0]
            label = getattr(bpy.types, node_idname).bl_rna.name
            cat.nodeitems.append(NodeItem(label, node_idname))
            geo_nodes_categories[category] = cat


if bpy.app.version >= (3, 4, 0):
    main()

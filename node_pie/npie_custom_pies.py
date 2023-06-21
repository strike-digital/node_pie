from collections import OrderedDict
from dataclasses import dataclass, field
import json

import bpy
from .npie_constants import NODE_DEF_DIR
from .npie_helpers import JSONWithCommentsDecoder


@dataclass
class NodeCategory():
    """An imitator of the built in blender NodeCategory class, that implements the necessary settings"""

    label: str
    nodes: list
    color: str
    children: list = None
    idname: str = ""

    def items(self, context):
        return self.nodes


@dataclass
class NodeItem():
    """An imitator of the built in blender NodeItem class, that implements the necessary settings"""

    label: str
    idname: str
    settings: list = field(default_factory=list)
    color: str = ""


class Separator():
    pass


def load_custom_nodes_info(tree_identifier: str) -> tuple[dict[str, NodeCategory], dict]:
    bl_version = bpy.app.version
    categories = {}
    layout = {}

    # Load config file
    files = {}
    for file in (NODE_DEF_DIR).iterdir():
        if file.is_file() and file.suffix == ".jsonc" and file.name.startswith(f"{tree_identifier}"):
            files[file.stem.split("_")[-1]] = file

    for file in files.copy():
        if file != tree_identifier:
            try:
                int(file)
            except ValueError:
                del files[file]
                continue
            if int(file) > int(f"{bl_version[0]}{bl_version[1]}"):
                del files[file]

    if not files:
        return {}, {}

    def sort(f):
        if f[0] != tree_identifier:
            return int(f[0])
        return 0

    files = OrderedDict(sorted(list(files.items()), key=sort))

    with open(list(files.values())[0], "r") as f:
        data = json.load(f, cls=JSONWithCommentsDecoder)

    # Merge in nodes from newer versions
    for file in list(files.values())[1:]:
        with open(file, "r") as f:
            new_data = json.load(f, cls=JSONWithCommentsDecoder)

        # Merge layout
        for orig_area_name, orig_columns in data["layout"].items():
            new_columns = new_data["additions"]["layout"].get(orig_area_name)
            if not new_columns:
                continue
            for i, new_column in enumerate(new_columns):
                for new_row in new_column:
                    orig_columns[i].append(new_row)

        # Merge in the new nodes
        for orig_cat_name, orig_cat in data["categories"].items():
            new_cat = new_data["additions"]["categories"].get(orig_cat_name)
            if new_cat:
                # Insert the node after the specified one.
                names = [n.get("identifier") for n in orig_cat["nodes"]]
                idx = -1
                for new_node in new_cat["nodes"]:
                    if name := new_node.get("after_node"):
                        idx = names.index(name)
                    if idx == -1:
                        orig_cat["nodes"].append(new_node)
                    else:
                        orig_cat["nodes"].insert(idx + 1, new_node)

        # Add new categories
        new_cats = new_data["additions"]["categories"].keys() - data["categories"].keys()
        for new_cat in new_cats:
            data["categories"][new_cat] = new_data["additions"]["categories"][new_cat]
        # data["categories"].update(new_data["additions"]["categories"])

    # Load the latest version
    # def_path = ""
    # version = int(f"{bl_version[0]}{bl_version[1]}")
    # while True:
    #     try:
    #         def_path = files[str(version)]
    #         break
    #     except KeyError:
    #         version -= 1
    #         if version < 0:
    #             break
    #         continue
    # def_path = def_path or list(files.values())[-1]

    layout = data["layout"]

    for idname, cat in data["categories"].items():
        items = []
        for node in cat["nodes"]:
            if node["label"] == "sep":
                items.append(Separator())
                continue
            item = NodeItem(node["label"], node["identifier"], color=node.get("color", ""))
            item.settings = node.get("settings", [])
            items.append(item)

        category = NodeCategory(cat["label"], items, color=cat.get("color", ""), idname=idname)
        categories[idname] = category
    return categories, layout
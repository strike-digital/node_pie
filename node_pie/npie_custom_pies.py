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
    all_nodes = {}
    categories = {}
    layout = {}

    # Load config file
    files = {}
    for file in (NODE_DEF_DIR).iterdir():
        if file.is_file() and file.suffix == ".jsonc" and file.name.startswith(f"{tree_identifier}"):
            files[file.stem.split("_")[-1]] = file

    if not files:
        return {}, {}

    # Load the latest version
    def_path = ""
    version = int(f"{bl_version[0]}{bl_version[1]}")
    while True:
        try:
            def_path = files[str(version)]
            break
        except KeyError:
            version -= 1
            if version < 0:
                break
            continue
    def_path = def_path or list(files.values())[-1]

    with open(def_path, "r") as f:
        data = json.load(f, cls=JSONWithCommentsDecoder)

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
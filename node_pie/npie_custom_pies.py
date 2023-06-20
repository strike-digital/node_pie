import json
from pathlib import Path

import bpy
from .npie_helpers import JSONWithCommentsDecoder

from .geo_nodes_categories import NodeCategory, NodeItem, Separator


def load_custom_nodes_info(tree_identifier: str):
    print(tree_identifier)
    bl_version = bpy.app.version
    all_nodes = {}
    categories = {}
    layout = {}

    # Load config file
    files = {}
    for file in (Path(__file__).parent / "node_def_files").iterdir():
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
        # data = json.load(f)

    layout = data["layout"]

    for idname, cat in data["categories"].items():
        items = []
        for node in cat["nodes"]:
            if node["label"] == "sep":
                items.append(Separator())
                continue
            item = NodeItem(node["label"], node["identifier"])
            item.settings = node.get("settings", [])
            item.color = node.get("color", "")
            items.append(item)

        category = NodeCategory(cat["label"], items, color=cat.get("color", ""), idname=idname)
        categories[idname] = category

    # for cat_idname, cat in data.items():
    #     items = []
    #     for nodeitem in cat["items"]:
    #         if nodeitem["name"] == "sep":
    #             items.append(Separator())
    #             continue
    #         item = NodeItem(nodeitem["name"], nodeitem["identifier"])
    #         if settings := nodeitem.get("settings"):
    #             item.settings = settings
    #         items.append(item)
    #         all_nodes[nodeitem["identifier"]] = item
    #     category = NodeCategory(cat["name"], items)

    #     categories[cat["name"]] = category

    # Check to see if there are any new nodes not in pie menu. NOT FOOLPROOF!
    # excluded = {"GeometryNodeViewer", "GeometryNodeGroup", "GeometryNodeCustomGroup"}

    # available_nodes = {node.bl_rna.identifier for node in bpy.types.GeometryNode.__subclasses__()}
    # available_nodes |= {node.bl_rna.identifier for node in bpy.types.FunctionNode.__subclasses__()}
    # missing_nodes = available_nodes - set(all_nodes.keys()) - excluded

    # if missing_nodes:
    #     print()
    #     print(
    #         f"Node Pie Warning! There are {len(missing_nodes)} new nodes available that are not displayed in the Node Pie Menu:"
    #     )
    #     pprint(missing_nodes)
    #     print()

    return categories, layout
import json
import bpy
from .npie_constants import NODE_DEF_DIR
import nodeitems_utils

# File used to generate the initial node def file, doesn't actually do anything in the addon currently

colours = {
    "Attribute": "attribute",
    "Color": "color",
    "Curve": "geometry",
    "Geometry": "geometry",
    "Input": "input",
    "Instances": "geometry",
    "Material": "geometry",
    "Mesh": "geometry",
    "Point": "geometry",
    "Curve Primitives": "geometry",
    "Mesh Primitives": "geometry",
    "Text": "geometry",
    "Texture": "texture",
    "Utilities": "converter",
    "Vector": "vector",
    "Volume": "geometry",
    "Layout": "layout",
    # 3.4+
    "Mesh Topology": "input",
    "Curve Topology": "input",
    "UV": "converter",
}
overrides = {}
color_overrides = {
    "Input": "input",
    "FunctionNode": "converter",
    "GeometryNodeStringJoin": "converter",
    "ShaderNodeValToRGB": "converter",
    "ShaderNodeCombineXYZ": "converter",
    "ShaderNodeSeparateXYZ": "converter",
    "GeometryNodeSplineParameter": "input",
    "GeometryNodeSplineLength": "input",
    "GeometryNodeCurveHandleTypeSelection": "input",
    "GeometryNodeCurveEndpointSelection": "input",
}

data = {}


def main():

    # for area in bpy.context.window.screen.areas:
    #     if area.type == "NODE_EDITOR":
    #         with bpy.context.temp_override(area=area):
    #             cats = list(nodeitems_utils.node_categories_iter(bpy.context))
    #             for cat in cats:
    #                 # if cat.name not in colours.keys():
    #                 #     continue
    #                 items = []
    #                 for item in cat.items(bpy.context):
    #                     if not isinstance(item, nodeitems_utils.NodeItem):
    #                         continue
    #                     settings = item.settings
    #                     data_item = {"label": item.label, "identifier": item.nodetype}
    #                     if settings:
    #                         data_item["settings"] = settings
    #                     if item.nodetype in color_overrides:
    #                         data_item["color"] = color_overrides[item.nodetype]
    #                     items.append(data_item)
    #                 data[cat.identifier] = {"label": cat.name, "color": "input", "nodes": items}

    #             selected_nodes = bpy.context.selected_nodes
    #             items = []
    #             for node in selected_nodes:
    #                 data_item = {"label": node.bl_label, "identifier": node.bl_idname}
    #                 items.append(data_item)

    # # Uncomment to write out the initial file from an old version that still has a working NodeItems api.
    # # Shouldn't need to be used now.
    # if data:
    #     fpath = NODE_DEF_DIR / "CompositorNodeTree2.jsonc"
    #     with open(fpath, "w") as f:
    #         json.dump(data, f, indent=2)

    #     print("Dumped!")
    # print(data)

    orig_file = NODE_DEF_DIR / "GeometryNodeTree.jsonc"
    new_file = NODE_DEF_DIR / "GeometryNodeTree_40 copy.jsonc"

    with open(orig_file, "r") as f:
        orig_data = json.load(f)
    with open(new_file, "r") as f:
        new_data = json.load(f)

    orig_categories = orig_data["categories"]
    new_categories = new_data["categories"]
    data = {}

    for orig_name, orig_cat in orig_categories.items():
        new_cat = new_categories[orig_name]
        nodes = []
        for node in new_cat["nodes"]:
            if node.get("identifier") not in {n.get("identifier") for n in orig_cat["nodes"]}:
                if node["label"] != "sep":
                    nodes.append(node)
        if nodes:
            data[orig_name] = {"nodes": nodes}

    # print(dict(new_categories.items() - orig_categories.items()))
    data.update({k: v for k, v in new_categories.items() if k not in orig_categories})

    print(json.dumps(data, indent=2) + ",")


# Uncomment to call main function
# bpy.app.timers.register(main)
import json

import bpy

from .npie_constants import NODE_DEF_SOCKETS
from .npie_helpers import JSONWithCommentsDecoder
from .npie_node_def_file import NodeItem

# Convert from node socket types to node enum names
# Switch and compare nodes have special cases that need to be dealt with individually
COMPARE_TYPES = {
    "Float": "FLOAT",
    "Int": "INT",
    "Vector": "VECTOR",
    "String": "STRING",
    "Color": "RGBA",
}

SWITCH_TYPES = {
    "Bool": "BOOLEAN",
    "Object": "OBJECT",
    "Collection": "COLLECTION",
    "Image": "IMAGE",
    "Geometry": "GEOMETRY",
    "Rotation": "ROTATION",
    "Menu": "MENU",
    "Material": "MATERIAL",
}
SWITCH_TYPES.update(COMPARE_TYPES)
if bpy.app.version >= (4, 2):
    SWITCH_TYPES["Matrix"] = "MATRIX"


def add_socket_names(names_dict):
    return {"NodeSocket" + k: v for k, v in names_dict.items()}


# All other nodes then have a list of enum types associated with each socket type
ALL_TYPES = SWITCH_TYPES.copy()
ALL_TYPES.update({"Shader": "SHADER"})
ALL_TYPES.update({"Texture": "TEXTURE"})
ALL_TYPES = {k: [v] for k, v in ALL_TYPES.items()}
ALL_TYPES["Vector"].append("FLOAT_VECTOR")
ALL_TYPES["Color"].append("FLOAT_COLOR")

SWITCH_TYPES = add_socket_names(SWITCH_TYPES)
COMPARE_TYPES = add_socket_names(COMPARE_TYPES)
ALL_TYPES = add_socket_names(ALL_TYPES)

EXCLUSIVE_SOCKETS = {"Material", "Object", "Collection", "Geometry", "Shader", "String", "Image", "Texture"}
EXCLUSIVE_SOCKETS = {"NodeSocket" + s for s in EXCLUSIVE_SOCKETS}


def is_socket_to_node_valid(from_socket_type: str, from_socket_is_output: bool, to_node: NodeItem, socket_data: dict):
    """Check if the given socket type has any valid connections to the given node."""
    in_out = "inputs" if from_socket_is_output else "outputs"
    valid_types = (
        {from_socket_type} if from_socket_type in EXCLUSIVE_SOCKETS else set(ALL_TYPES.keys()) - EXCLUSIVE_SOCKETS
    )
    node_socket_data = socket_data.get(to_node.idname)
    if not node_socket_data:
        print(f"Socket data not defined for node {to_node.idname}")
        return True
    if any(t in socket_data[to_node.idname][in_out] for t in valid_types):
        return True
    return False


def get_node_socket_info(tree_type: str, max_bl_version=bpy.app.version):
    """Return a dictionary of nodes and their socket types"""
    sockets_files = NODE_DEF_SOCKETS.rglob(f"**/{tree_type}*.jsonc")
    sockets_files_data = [json.loads(f.read_text(), cls=JSONWithCommentsDecoder) for f in sockets_files]
    sockets_files_data.sort(key=lambda data: data["bl_version"])

    all_socket_data = {}
    for data in sockets_files_data:
        if tuple(data["bl_version"]) <= tuple(max_bl_version):
            all_socket_data.update(data["nodes"])

    return all_socket_data

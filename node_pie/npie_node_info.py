from .npie_custom_pies import NodeItem

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
    "Menu": "Menu",
    # "Texture": "TEXTURE",
    "Material": "MATERIAL",
}


def add_socket_names(names_dict):
    return {"NodeSocket" + k: v for k, v in names_dict.items()}


SWITCH_TYPES.update(COMPARE_TYPES)

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


def socket_to_node_valid(from_socket_type: str, from_socket_is_output: bool, to_node: NodeItem, socket_data: dict):
    in_out = "inputs" if from_socket_is_output else "outputs"
    valid_types = {from_socket_type} if from_socket_type in EXCLUSIVE_SOCKETS else set(ALL_TYPES.keys()) - EXCLUSIVE_SOCKETS
    if any(t in socket_data[to_node.idname][in_out] for t in valid_types):
        return True
    return False

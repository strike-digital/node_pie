import json
from dataclasses import dataclass, field
from inspect import isclass
from pathlib import Path
from typing import Any

import bpy
from bpy.types import Context

from .npie_constants import NODE_DEF_BUILTIN, NODE_DEF_USER
from .npie_helpers import JSONWithCommentsDecoder, get_all_def_files


class PollCondition:
    """Represents a condition that can be evaluated to determine whether to show a node or not."""

    def __init__(self, context_path: str, operand: str, value: Any = None):
        supported_operands = {"bool", "equals", "in", "not_equals"}
        if operand not in supported_operands:
            raise ValueError(f"Operand for item {self} '{operand}' is not in {supported_operands}")

        self.context_path = context_path
        self.operand = operand
        self.value = value

    def evaluate(self, context: Context):
        attr_path = f"context.{self.context_path}"
        result = eval(attr_path)
        if self.operand == "bool" and bool(result):
            return True
        elif self.operand == "equals" and self.value == result:
            return True
        elif self.operand == "not_equals" and self.value != result:
            return True
        elif self.operand == "in" and self.value in result:
            return True
        return False


@dataclass
class NodeItem:
    """An imitator of the built in blender NodeItem class, that implements the necessary settings"""

    label: str
    idname: str
    settings: dict = field(default_factory=dict)
    variants: dict = field(default_factory=dict)
    poll_conditions: list[PollCondition] = field(default_factory=list)
    color: str = ""
    description: str = ""
    category = None

    def poll(self, context: Context):
        if not self.poll_conditions:
            return True
        for condition in self.poll_conditions:
            if condition.evaluate(context):
                return True
        return False


@dataclass
class NodeCategory:
    """An imitator of the built in blender NodeCategory class, that implements the necessary settings"""

    label: str
    nodes: list[NodeItem]
    color: str
    icon: str = ""
    children: list = None
    idname: str = ""
    poll_conditions: list[PollCondition] = field(default_factory=list)

    poll = NodeItem.poll
    # def poll(self, context: Context):
    #     if not self.poll_conditions:
    #         return True
    #     for condition in self.poll_conditions:
    #         if condition.evaluate(context):
    #             return True
    #     return False

    def items(self, context) -> list[NodeItem]:
        return self.nodes


@dataclass
class Separator:
    label: str = ""
    poll_conditions: list[PollCondition] = field(default_factory=list)

    poll = NodeItem.poll


@dataclass
class NodeOperator:
    idname: str
    label: str = ""
    settings: dict = field(default_factory=dict)
    color: str = ""


def create_defaults(data: dict):
    # Add default values in case they are missing from the file
    default_layout = {"top": [[]], "bottom": [[]], "left": [[]], "right": [[]]}
    data["layout"] = data.get("layout", default_layout)
    default_layout.update(data["layout"])
    data["layout"] = default_layout
    data["poll_types"] = data.get("poll_types", {})
    data["categories"] = data.get("categories", {})
    return data


def merge_configs(base: dict, additions: dict, removals: dict = {}):
    # Add default values in case they are missing from the file
    base = create_defaults(base)
    additions = create_defaults(additions)
    removals = create_defaults(removals)

    # REMOVALS
    # Process layout removals
    orig_layout = base["layout"]
    remove_layout = removals["layout"]
    for area_name, rem_area in remove_layout.items():
        for orig_column, rem_column in zip(orig_layout[area_name], rem_area):
            for cat_id in rem_column:
                orig_column.remove(cat_id)

    # Process category removals
    orig_categories = base["categories"]
    remove_categories = removals["categories"]
    for rem_cat_name, rem_cat in remove_categories.items():
        if nodes := rem_cat.get("nodes", []):
            orig_nodes = orig_categories[rem_cat_name]["nodes"]
            for rem_node in nodes:
                for i, orig_node in enumerate(orig_nodes.copy()):
                    if rem_node.get("separator") or orig_node.get("separator"):
                        continue
                    if rem_node["identifier"] == orig_node["identifier"]:
                        orig_nodes.remove(orig_node)
                        break
            pass
        else:
            del orig_categories[rem_cat_name]

    # Process full node removals
    remove_nodes = removals.get("nodes", [])
    for rem_node in remove_nodes:
        for orig_category in orig_categories.values():
            for orig_node in orig_category["nodes"].copy():
                if rem_node == orig_node.get("identifier"):
                    orig_category["nodes"].remove(orig_node)
                    break

    # ADDITIONS
    # Merge layout
    for orig_area_name, orig_columns in base["layout"].items():
        new_columns = additions["layout"].get(orig_area_name)
        if not new_columns:
            continue
        for i, new_column in enumerate(new_columns):
            new_column = new_column.copy()
            for new_row in new_column:
                orig_columns = base["layout"][orig_area_name]
                if i > len(orig_columns) - 1:
                    orig_columns.append([new_row])
                else:
                    orig_columns[i].append(new_row)

    # Merge poll types
    poll_types: dict = base["poll_types"]
    poll_types.update(additions["poll_types"])

    # Merge in the new nodes
    for orig_cat_name, orig_cat in base["categories"].items():
        new_cat = additions["categories"].get(orig_cat_name)
        if new_cat:
            # Insert the node after the specified one.
            idx = -1
            for new_node in new_cat["nodes"]:
                if name := new_node.get("after_node"):
                    if name == "top":
                        idx = 0
                    elif name == "bottom":
                        idx = -1
                    else:
                        names = [n.get("identifier") for n in orig_cat["nodes"]]
                        idx = names.index(name) + 1
                elif name := new_node.get("before_node"):
                    names = [n.get("identifier") for n in orig_cat["nodes"]]
                    idx = names.index(name)

                if idx == -1:
                    orig_cat["nodes"].append(new_node)
                else:
                    orig_cat["nodes"].insert(idx, new_node)

    # Add new categories
    new_cats = additions["categories"].keys() - base["categories"].keys()
    for new_cat in new_cats:
        base["categories"][new_cat] = additions["categories"][new_cat]
    return base


modified_times = {}


def load_custom_nodes_info(tree_identifier: str, context) -> tuple[dict[str, NodeCategory], dict]:
    categories = {}
    layout = {}

    all_files = get_all_def_files()

    # Different render engines can use different nodes in the default shader editor, account for that.
    if tree_identifier == "ShaderNodeTree":
        for file in all_files:
            with open(file, "r") as f:
                data = json.load(f, cls=JSONWithCommentsDecoder)
            if data.get("render_engine") == context.scene.render.engine:
                tree_identifier = file.name
                break
        else:
            # Auto generate if not blender render engine
            if context.scene.render.engine not in {
                "BLENDER_EEVEE",
                "BLENDER_EEVEE_NEXT",
                "CYCLES",
                "BLENDER_WORKBENCH",
            }:
                return {}, {}

    def get_def_files(dir: Path) -> Path:
        files = []
        for file in dir.rglob("*"):
            if file.is_file() and file.suffix == ".jsonc" and file.name.startswith(f"{tree_identifier}"):
                files.append(file)
        return files

    # Get files
    files = get_def_files(NODE_DEF_USER)
    names = {f.name for f in files}
    files += [f for f in get_def_files(NODE_DEF_BUILTIN) if f.name not in names]

    if not files:
        return {}, {}

    # Sort the files from first version to latest version so that they are applied in the correct order
    def sort(f):
        with open(f, "r") as file:
            fdata = json.load(file, cls=JSONWithCommentsDecoder)

            # TODO: REMOVE
            if fdata.get("apply_after", False):
                return [9, 9, 9]

            return fdata.get("blender_version", [0, 0, 0])

    files.sort(key=sort)

    with open(files[0], "r") as f:
        data = json.load(f, cls=JSONWithCommentsDecoder)

    # Merge in imports
    if imports := data.get("imports"):
        for import_name in imports:
            for file in all_files:
                if file.stem == import_name:
                    with open(file, "r") as f:
                        new_data = json.load(f, cls=JSONWithCommentsDecoder)
                    merge_configs(data, new_data)
                    break
            else:
                raise ValueError(f"file {import_name}.jsonc not found")

    # Merge in nodes from newer versions
    for file in files:
        with open(file, "r") as f:
            new_data = json.load(f, cls=JSONWithCommentsDecoder)

        if tuple(new_data.get("blender_version", [0, 0, 0])) > bpy.app.version or not new_data.get("enable", True):
            continue

        # check for resetting
        # Happens if there is a major change to nodes in an update
        reset_all = new_data.get("reset_all", False)
        if new_data.get("reset_layout", False) or reset_all:
            data["layout"] = {"left": [], "right": [], "top": [], "bottom": []}
        if reset_all:
            data["categories"] = {}

        merge_configs(data, new_data.get("additions", {}), new_data.get("removals", {}))

    layout = data["layout"]
    poll_types = data.get("poll_types", {})

    # Get all node definition classes so that the labels can be auto generated
    bl_node_types = {n.bl_idname: n for n in bpy.types.Node.__subclasses__() if hasattr(n, "bl_idname")}
    types = set()
    for t in dir(bpy.types):
        try:
            t = getattr(bpy.types, t)
        except RuntimeError as e:
            print(f"NodePie: Couldn't get type '{t}', error: '{e}'")
            continue
        types.add(t)
        
    types = {getattr(bpy.types, t) for t in dir(bpy.types)}
    for t in types:
        if isclass(t) and issubclass(t, bpy.types.Node):
            bl_node_types[t.bl_rna.identifier] = t

    not_found = []

    for cat_idname, cat in data["categories"].items():
        items = []
        for node in cat["nodes"]:

            # Create poll conditions
            poll_conditions = []
            if poll_type := node.get("poll_type"):
                conditions = node.get("poll_conditions", [])
                node["poll_conditions"] = poll_types[poll_type] + conditions
            for condition in node.get("poll_conditions", []):
                poll_conditions.append(PollCondition(**condition))

            if node.get("separator"):
                items.append(Separator(label=node.get("label", ""), poll_conditions=poll_conditions))
                continue
            if node.get("operator"):
                items.append(
                    NodeOperator(
                        node["operator"],
                        label=node.get("label", ""),
                        settings=node.get("settings", {}),
                    )
                )
                continue
            idname = node["identifier"]

            # Get an auto generated label, if one is not provided
            bl_node = bl_node_types.get(idname)
            label = node.get("label")
            if not label:
                if bl_node:
                    label = bl_node.bl_rna.name if bl_node.bl_rna.name != "Node" else bl_node.bl_label

            if not label and not bl_node:
                not_found.append(idname)
                continue
            description = bl_node.bl_rna.description if bl_node else ""
            item = NodeItem(label, idname, color=node.get("color", ""), description=description)
            item.settings = node.get("settings", {})
            item.variants: dict[str, dict] = node.get("variants", {})
            item.poll_conditions = poll_conditions

            for name, variant in item.variants.items():
                if name != "separator":
                    all_settings = item.settings.copy()
                    all_settings.update(variant)
                    item.variants[name] = all_settings
            items.append(item)

        if not cat.get("label"):
            raise ValueError(f"No label found for category '{cat_idname}'")
        category = NodeCategory(
            cat["label"],
            items,
            color=cat.get("color", ""),
            idname=cat_idname,
            icon=cat.get("icon", ""),
        )
        for condition in cat.get("poll_conditions", {}):
            category.poll_conditions.append(PollCondition(**condition))
        categories[cat_idname] = category
        for nodeitem in category.nodes:
            nodeitem.category = category

    if not_found:
        raise ValueError(f"No label found for node(s) '{not_found}'")
    return categories, layout

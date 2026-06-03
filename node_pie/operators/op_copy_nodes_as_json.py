from ..npie_btypes import BOperator
from ..npie_helpers import NpieCache
from ..npie_node_def_file import NodeItem


@BOperator("node_pie")
class NPIE_OT_copy_nodes_as_json(BOperator.type):
    """Copy the selected nodes in the correct format to be pasted into the node pie definition file."""

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        if not context.selected_nodes:
            return False
        return True

    def execute(self, context):
        node_items = []
        category = ""
        for node in context.selected_nodes:
            npie_settings = node.node_pie
            if not npie_settings.type or self.event.ctrl:
                data_item = {"identifier": node.bl_idname}
            else:
                categories = NpieCache.categories
                cat = categories[node.node_pie.type]
                category = cat
                nodes = [n for n in cat.nodes if isinstance(n, NodeItem)]
                for n in nodes:
                    if node.name < n.label:
                        # print(n, node.name)
                        break
                data_item = {"identifier": node.bl_idname, "before_node": n.idname}

            node_items.append(str(data_item).replace("'", '"'))

        items = ",\n".join(node_items)
        if self.event.shift and category:
            items = f"""
            "{category.idname}": {{
                "nodes": [
            {items}
            ]
            }},
            """.replace("            ", "")
        print(items)
        context.window_manager.clipboard = items
        print()
        print("Nodes to copy:")
        print(items)
        print()
        num = len(context.selected_nodes)
        self.report({"INFO"}, message=f"Copied {num} node{'' if num == 1 else 's'}")
        return {"FINISHED"}

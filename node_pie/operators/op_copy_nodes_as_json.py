from ..npie_btypes import BOperator


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
        items = []
        for node in context.selected_nodes:
            data_item = {"identifier": node.bl_idname}
            items.append(str(data_item).replace("'", '"'))
            # items.append(json.dumps(data_item, indent=2))
        items = ",\n".join(items)
        context.window_manager.clipboard = items
        print()
        print("Nodes to copy:")
        print(items)
        print()
        num = len(context.selected_nodes)
        self.report({"INFO"}, message=f"Copied {num} node{'' if num == 1 else 's'}")
        return {"FINISHED"}
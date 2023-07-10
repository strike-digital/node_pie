from bpy.types import UILayout
from ..npie_btypes import BOperator
from ..npie_constants import POPULARITY_FILE


@BOperator("node_pie")
class NPIE_OT_reset_popularity(BOperator.type):
    """Reset the popularity of all nodes back to zero"""

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout: UILayout = self.layout
        box = layout.box()
        box.alert = True
        col = box.column(align=True)
        col.scale_y = .8
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Warning!")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="This will reset the popularity of all nodes back to zero.")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="This cannot be undone.")
        row = col.row(align=True)
        row.alignment = "CENTER"
        row.label(text="Continue anyway?")

    def execute(self, context):
        with open(POPULARITY_FILE, "w"):
            pass
        self.report({"INFO"}, "Node popularity successfully reset")
        return {"FINISHED"}
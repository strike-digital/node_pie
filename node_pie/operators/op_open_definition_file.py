from bpy.props import BoolProperty
from ..npie_btypes import BOperator
from ..npie_constants import NODE_DEF_BASE_FILE, NODE_DEF_DIR, NODE_DEF_EXAMPLE_FILE
from ..npie_helpers import get_all_def_files

import shutil
import webbrowser


@BOperator("node_pie")
class NPIE_OT_open_definition_file(BOperator.type):
    """Open the node pie definition file for this node tree"""

    example: BoolProperty()

    @classmethod
    def poll(cls, context):
        if not context.space_data or context.area.type != "NODE_EDITOR":
            return False
        return True

    def execute(self, context):
        if self.example:
            file = NODE_DEF_EXAMPLE_FILE
        else:
            files = get_all_def_files()
            for file in files:
                if file.name == f"{context.space_data.tree_type}.jsonc":
                    break
            else:
                file = NODE_DEF_DIR / "user" / f"{context.space_data.tree_type}.jsonc"
            if not file.exists():
                shutil.copyfile(NODE_DEF_BASE_FILE, file)

        webbrowser.open(file)
        return {"FINISHED"}
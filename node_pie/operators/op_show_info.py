from dataclasses import dataclass

from bpy.props import IntProperty, BoolProperty, StringProperty
from bpy.types import Context, UILayout
from ..npie_btypes import BOperator
import blf


def wrap_text(
    context: Context,
    text: str,
    layout: UILayout,
    centered: bool = False,
    width=0,
    splitter=None,
) -> list[str]:
    """Take a string and draw it over multiple lines so that it is never concatenated."""
    return_text = []
    row_text = ''

    width = width or context.region.width
    system = context.preferences.system
    ui_scale = system.ui_scale
    width = (4 / (5 * ui_scale)) * width

    dpi = 72 if system.ui_scale >= 1 else system.dpi
    blf.size(0, 11, dpi)

    for word in text.split(splitter):
        if word == "":
            return_text.append(row_text)
            row_text = ""
            continue
        word = f' {word}'
        line_len, _ = blf.dimensions(0, row_text + word)

        if line_len <= (width - 16):
            row_text += word
        else:
            return_text.append(row_text)
            row_text = word

    if row_text:
        return_text.append(row_text)

    for text in return_text:
        row = layout.row()
        if centered:
            row.alignment = "CENTER"
        row.label(text=text)

    return return_text


@BOperator("npie")
class NPIE_OT_show_info(BOperator.type):

    title: StringProperty()

    message: StringProperty()

    icon: StringProperty()

    show_content: BoolProperty()

    width: IntProperty(default=300)

    def invoke(self, context, event):
        return self.call_popup(self.width)

    def draw(self, context):
        layout = self.layout
        column = layout.column(align=True)
        box = column.box().row(align=True)
        box.alignment = "CENTER"
        offset = "" if self.icon else "    "
        box.label(text=self.title + offset, icon=self.icon)

        box = column.box().column(align=True)
        message = self.message.replace("  ", "").replace("\n", " ")
        wrap_text(context, message, box, width=self.width * 1.25, splitter=" ")
        # wrap_text(None, context, message, box, width=self.width * 1.25)


@dataclass
class InfoSnippet():

    title: str
    message: str
    icon: str = "NONE"

    def draw(self, layout: UILayout, icon_override=""):
        op = layout.operator(NPIE_OT_show_info.bl_idname, text="", icon=icon_override or "INFO")
        op.title = self.title
        op.message = self.message
        op.icon = self.icon


class InfoSnippets():

    link_drag = InfoSnippet(
        "Link drag",
        """\
        If you press the pie menu keyboard shortcut over a node socket, the node you select will be automatically \
        connected to that socket.\n

        NOTE: The node socket hitboxes can be innacurate at high or low UI scales, so if you use a UI scale that is \
        either especially high or especially low, you may want to turn on "Draw debug lines", and then adjust the \
        "Socket separation" parameter until they line up again.
        The problem will be most obvious with large nodes like the Principled BSDF or the Raycast node.
        """,
        icon="NODE",
    )

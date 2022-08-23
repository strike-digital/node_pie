from bpy.types import UILayout


class DummyUI():
    """Class that immitates UILayout, but doesn't draw anything"""

    def row(*args, **kwargs):
        return DummyUI()

    def column(*args, **kwargs):
        return DummyUI()

    def split(*args, **kwargs):
        return DummyUI()

    def label(*args, **kwargs):
        return DummyUI()

    def operator(*args, **kwargs):
        return DummyUI()

    def prop(*args, **kwargs):
        return DummyUI()


def draw_section(layout: UILayout, title: str, show_data=None, show_prop: str = "", index_prop: str = "") -> UILayout:
    """Draw a box with a title, and return it"""
    main_col = layout.column(align=True)

    box = main_col.box()
    col = box.column(align=True)
    col.scale_y = 0.85
    row = col.row(align=True)

    is_showing = True
    if show_data:
        index = getattr(show_data, index_prop)
        is_showing = getattr(show_data, show_prop)[index]
        sub = row.row(align=True)
        sub.prop(
            show_data,
            show_prop,
            index=index,
            text="",
            icon="TRIA_DOWN" if is_showing else "TRIA_RIGHT",
            emboss=False,
        )
        sub.scale_x = 1.2
        setattr(show_data, index_prop, index + 1)

    sub = row.row(align=True)
    sub.active = is_showing
    sub.label(text=title)
    sub.alignment = "CENTER"

    if show_data:
        # Use two separators to avoid making the box taller
        sub.separator(factor=3)
        sub.separator(factor=2)

    if not is_showing:
        return DummyUI()

    box = main_col.box()
    col = box.column()
    return col


def draw_inline_prop(
    layout: UILayout,
    data,
    data_name,
    text="",
    prop_text="",
    invert=False,
    factor=0.48,
    alignment="RIGHT",
    full_event=False,
) -> UILayout:
    """Draw a property with the label to the left of the value"""
    row = layout.row()
    split = row.split(factor=factor, align=True)
    split.use_property_split = False
    left = split.row(align=True)
    left.alignment = alignment
    if not text:
        text = data.bl_rna.properties[data_name].name
    left.label(text=text)
    col = split.column(align=True)
    col.prop(data, data_name, text=prop_text, invert_checkbox=invert, full_event=full_event)
    return row


def draw_enabled_button(layout: UILayout, data, prop: str) -> UILayout:
    """Draw the 'section enabled' button, and return the following layout"""
    col = layout.column(align=True)
    row = col.row(align=True)
    enabled = getattr(data, prop)
    icon = get_tick_icon(enabled, show_box=True)
    text = "Enabled     " if enabled else "Disabled     "
    row.prop(data, prop, text=text, toggle=True, icon=icon)
    row.scale_y = 1
    layout = layout.column(align=True)
    layout = col.box()

    if not enabled:
        layout.active = False

    return layout


def get_tick_icon(enabled, show_box=False) -> str:
    """Returns the name of the tick icon, enabled or disabled."""
    if show_box:
        return "CHECKBOX_HLT" if enabled else "CHECKBOX_DEHLT"
    return "CHECKMARK" if enabled else "BLANK1"

from pathlib import Path
from random import randint
import bpy
import gpu
import blf
from gpu_extras.batch import batch_for_shader
from mathutils import Vector as V
from ..vendor import requests
from .npie_helpers import Op
from bpy.types import Operator
"""Modified from the blender python source wm.py file
Gets the documentation source .rst file for the selected node"""


def _wm_doc_get_id(doc_id, *, do_url=True, url_prefix="", report=None):

    def operator_exists_pair(a, b):
        # Not fast, this is only for docs.
        return b in dir(getattr(bpy.ops, a))

    def operator_exists_single(a):
        a, b = a.partition("_OT_")[::2]
        return operator_exists_pair(a.lower(), b)

    id_split = doc_id.split(".")
    url = rna = None

    if len(id_split) == 1:  # rna, class
        if do_url:
            url = "%s/bpy.types.%s.html" % (url_prefix, id_split[0])
        else:
            rna = "bpy.types.%s" % id_split[0]

    elif len(id_split) == 2:  # rna, class.prop
        class_name, class_prop = id_split

        # an operator (common case - just button referencing an op)
        if operator_exists_pair(class_name, class_prop):
            if do_url:
                url = ("%s/bpy.ops.%s.html#bpy.ops.%s.%s" % (url_prefix, class_name, class_name, class_prop))
            else:
                rna = "bpy.ops.%s.%s" % (class_name, class_prop)
        elif operator_exists_single(class_name):
            # note: ignore the prop name since we don't have a way to link into it
            class_name, class_prop = class_name.split("_OT_", 1)
            class_name = class_name.lower()
            if do_url:
                url = ("%s/bpy.ops.%s.html#bpy.ops.%s.%s" % (url_prefix, class_name, class_name, class_prop))
            else:
                rna = "bpy.ops.%s.%s" % (class_name, class_prop)
        else:
            # An RNA setting, common case.

            # Check the built-in RNA types.
            rna_class = getattr(bpy.types, class_name, None)
            if rna_class is None:
                # Check class for dynamically registered types.
                rna_class = bpy.types.PropertyGroup.bl_rna_get_subclass_py(class_name)

            if rna_class is None:
                return None

            # Detect if this is a inherited member and use that name instead.
            rna_parent = rna_class.bl_rna
            rna_prop = rna_parent.properties.get(class_prop)
            if rna_prop:
                rna_parent = rna_parent.base
                while rna_parent and rna_prop == rna_parent.properties.get(class_prop):
                    class_name = rna_parent.identifier
                    rna_parent = rna_parent.base

                if do_url:
                    url = ("%s/bpy.types.%s.html#bpy.types.%s.%s" % (url_prefix, class_name, class_name, class_prop))
                else:
                    rna = "bpy.types.%s.%s" % (class_name, class_prop)
            else:
                # We assume this is custom property, only try to generate generic url/rna_id...
                if do_url:
                    url = ("%s/bpy.types.bpy_struct.html#bpy.types.bpy_struct.items" % (url_prefix,))
                else:
                    rna = "bpy.types.bpy_struct"

    return url if do_url else rna


def _find_reference(rna_id, url_mapping):
    # XXX, for some reason all RNA ID's are stored lowercase
    # Adding case into all ID's isn't worth the hassle so force lowercase.
    rna_id = rna_id.lower()
    print(rna_id)

    # This is about 100x faster than the method currently used in Blender
    # I might make a patch to fix it.
    url_mapping = dict(url_mapping)
    url = url_mapping[rna_id + "*"]
    return url


def _lookup_rna_url(rna_id, full_url=False):
    for prefix, url_manual_mapping in bpy.utils.manual_map():
        rna_ref = _find_reference(rna_id, url_manual_mapping)
        if rna_ref is not None:
            url = prefix + rna_ref if full_url else rna_ref
            return url


def get_docs_source_url(doc_id):
    rna_id = _wm_doc_get_id(doc_id, do_url=False)
    if rna_id is None:
        return ""

    url = _lookup_rna_url(rna_id, full_url=False)
    url = "https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/" + url.split(".html")[0] + ".rst"

    if url is None:
        return ""
    else:
        return url


def draw_rst(layout: bpy.types.UILayout, rst: str):
    layout.scale_y = .5
    for line in rst.splitlines():
        layout.label(text=line)


def listget(list, idx, default="last_element"):
    if default == "last_element":
        return list[min(idx, len(list) - 1)]
    else:
        try:
            return list[idx]
        except IndexError:
            return default


handlers = []

# @Op("node_pie")
# class NPIE_OT_show_node_docs(Operator):
#     """Show the documentation for this node"""

#     type: bpy.props.StringProperty()

#     def invoke(self, context, event):
#         url = get_docs_source_url(self.type)
#         self.rst_source = requests.get(url).content.decode("utf-8").replace("\\n", "\n")
#         print(self.rst_source)
#         self._handle = bpy.types.SpaceView3D.draw_handler_add(self.draw_callback_px, args, "WINDOW", "POST_PIXEL")
#         context.window_manager.modal_handler_add(self)
#         return context.window_manager.invoke_popup(self, width=500)

#     def draw(self, context):
#         layout = self.layout
#         draw_rst(layout, self.rst_source)

#     def execute(self, context):
#         return {"FINISHED"}


@Op("node_pie")
class NPIE_OT_show_node_docs(Operator):
    """Show the documentation for this node"""

    type: bpy.props.StringProperty()

    link: bpy.props.StringProperty()

    pos: bpy.props.IntVectorProperty(size=2)

    def invoke(self, context, event):
        args = ()
        self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            self.draw_callback_px,
            args,
            "WINDOW",
            "POST_PIXEL",
        )
        handlers.append(self._handle)
        path = Path(__file__).parent / "fonts"
        # print((path / "DefaVuSansMono.ttf").exists())
        self.fonts = {
            "default": blf.load(str(path / "Lato-Regular.ttf")),
            "header": blf.load(str(path / "RobotoSlab-Bold.ttf")),
            "bold": blf.load(str(path / "Lato-Bold.ttf")),
            "italic": blf.load(str(path / "Italic-Oblique.ttf")),
            "bolditalic": blf.load(str(path / "Lato-BoldItalic.ttf")),
            "code": blf.load(str(path / "DejaVuSanMono.ttf")),
        }

        if self.link:
            url = f"https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/{self.link}.rst"
        else:
            url = get_docs_source_url(self.type)
        self.rst_source: str = requests.get(url).content.decode("utf-8").replace("\\n", "\n")
        if tuple(self.pos) != (0, 0):
            self.view_location = V(self.pos)
        else:
            self.view_location = V((event.mouse_region_x, event.mouse_region_y))

        self.sections: list[dict] = []
        self.doclink = ""
        self.dragging = False
        self.prev_mouse_pos = self.view_location
        self.press_pos = V((0, 0))
        self.bounding_box = V((0, 0), (0, 0))
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type in {"RIGHTMOUSE", "ESC"}:
            return self.finish()

        mouse_pos = V((event.mouse_region_x, event.mouse_region_y))

        if event.type == "LEFTMOUSE":
            if event.value == "PRESS":
                if
                self.dragging = True
                self.press_pos = mouse_pos.copy()

            elif event.value == "RELEASE":
                # if self.doclink and mouse_pos == self.prev_mouse_pos:
                if self.doclink and self.press_pos == mouse_pos:
                    bpy.ops.node_pie.show_node_docs(
                        "INVOKE_DEFAULT",
                        link=self.doclink,
                        pos=tuple(int(i) for i in self.view_location),
                    )
                    print(self.doclink)
                    return self.finish()
                self.dragging = False
            # return self.finish()

        if self.dragging:
            self.view_location += mouse_pos - self.prev_mouse_pos
            context.area.tag_redraw()

        for section in self.sections:
            if section.get("doclink"):
                mouse = V((event.mouse_region_x, event.mouse_region_y))
                min_pos = section["pos"]
                max_pos = min_pos + section["dimensions"]
                if min_pos.y < mouse.y < max_pos.y and min_pos.x < mouse.x < max_pos.x:
                    context.window.cursor_modal_set("HAND")
                    self.doclink = section.get("doclink")
                    break
                context.window.cursor_modal_restore()
        else:
            self.doclink = ""
        self.prev_mouse_pos = mouse_pos

        return {"RUNNING_MODAL"}

    def finish(self):
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, "WINDOW")
        handlers.remove(self._handle)
        bpy.context.window.cursor_modal_restore()
        bpy.context.area.tag_redraw()
        print("finished")
        return {"FINISHED"}

    def draw_callback_px(self):

        self.sections = []
        pos = self.view_location.copy()
        orig_size = 15
        is_chapter = False

        lines = self.rst_source.splitlines()
        for i, line in enumerate(lines):
            font_id = self.fonts["default"]
            padding = 2.5
            size = orig_size
            sections: list[dict]
            sections = [{"text": line.replace(" ", "  "), "size": 1}]

            # Chapters
            if is_chapter:
                sections[0]["size"] = 2
                sections[0]["font_id"] = self.fonts["header"]
                padding = orig_size / 2
            is_chapter_header = set(line) == {"*"}
            is_chapter = is_chapter_header and set(listget(lines, i + 2)) == {"*"}
            if is_chapter_header:
                continue

            # Headers
            if line.startswith("="):
                continue
            if listget(lines, i + 1).startswith("="):
                sections[0]["size"] = 1.5
                sections[0]["font_id"] = self.fonts["header"]
                padding = size / 2

            def highlight_surrounded_section(surrounder: str, attr: str, sections: list[dict]):
                """Split the provided sections into further sections based on the provided surrounder,
                and give them the provided attribute"""
                new_sections = []
                for section in sections:
                    text: str = section["text"]
                    parts = text.split(surrounder)
                    parts = [s for s in parts if s]
                    odd = text.startswith(surrounder)
                    for i, text in enumerate(parts):
                        is_surrounded = not bool(i % 2) if odd else bool(i % 2)
                        new_section = section.copy()
                        new_section["text"] = text
                        new_section[attr] = is_surrounded
                        new_sections.append(new_section)
                return new_sections

            # Bold
            sections = highlight_surrounded_section("**", "bold", sections)
            sections = highlight_surrounded_section("*", "italic", sections)
            sections = highlight_surrounded_section("``", "code", sections)

            def highlight_section(
                sections: list[dict],
                prefix: str,
                attr: str,
                suffix: str = "",
                surrounding_suffix=False,
                set_attr_to_inside_suffix=False,
            ):
                new_sections = []
                for section in sections:
                    text: str = section["text"]
                    parts = text.split(prefix)
                    parts = [s for s in parts if s]
                    odd = text.startswith(prefix)
                    for i, text in enumerate(parts):
                        is_after_prefix = not bool(i % 2) if odd else bool(i % 2)
                        new_section = section.copy()
                        if is_after_prefix:
                            result = text.split(suffix)[1 if surrounding_suffix else 0]
                            if set_attr_to_inside_suffix:
                                new_section[attr] = result
                            else:
                                new_section[attr] = True
                        else:
                            result = text
                        new_section["text"] = result
                        new_sections.append(new_section)
                return new_sections

            sections = highlight_section(
                sections,
                ":doc:",
                "doclink",
                suffix="`",
                surrounding_suffix=True,
                set_attr_to_inside_suffix=True,
            )

            # bold = line.split("**")
            # bold = [s for s in bold if s]
            # odd = line.startswith("**")
            # sections = []
            # for i, section in enumerate(bold):
            #     is_bold = not bool(i % 2) if odd else bool(i % 2)
            #     sections.append({"text": section, "bold": is_bold})

            # Italics
            # new_sections = []
            # for section in sections:
            #     text: str = section["text"]
            #     italic = text.split("*")
            #     italic = [s for s in italic if s]
            #     odd = text.startswith("*")
            #     for i, text in enumerate(italic):
            #         is_italic = not bool(i % 2) if odd else bool(i % 2)
            #         new_sections.append({"text": text, "bold": section["bold"], "italic": is_italic})
            # sections = new_sections
            # if "*" in line:
            #     font_id = self.fonts["italic"]
            #     pass

            # Draw
            pos.y -= padding
            for font_id in self.fonts.values():
                blf.size(font_id, size, 72)
            x = pos.x
            val = .8
            for section in sections:
                font_id = self.fonts["default"]
                color = (val, val, val, .8)

                if section.get("bold") and section.get("italic"):
                    font_id = self.fonts["bolditalic"]
                elif section.get("bold"):
                    font_id = self.fonts["bold"]
                elif section.get("italic"):
                    font_id = self.fonts["italic"]
                elif section.get("code"):
                    font_id = self.fonts["code"]

                if section.get("doclink"):
                    color = (.0, .4, 1, 1)
                    try:
                        section["text"] = section["text"].split(" ")[1]
                        section["doclink"] = section["doclink"].split(" ")[1]
                    except IndexError:
                        section["text"] = section["text"].split("/")[-1]

                dims = blf.dimensions(font_id, section["text"])
                if not section.get("font_id"):
                    section["font_id"] = font_id
                section["color"] = color
                section["pos"] = V((x, pos.y))
                section["size"]
                section["dimensions"] = V(dims)

                x += dims[0]
            pos.y -= blf.dimensions(font_id, "".join([s["text"] for s in sections]))[1] + padding

            self.sections += sections

        # Draw background
        indices = ((0, 1, 2), (2, 1, 3))
        padding = 15

        min_pos = self.view_location + V((0, orig_size)) - V((padding, -padding))
        max_pos = V((0, 0))
        max_pos.x = max([s["pos"].x + s["dimensions"].x for s in self.sections])
        max_pos.y = self.sections[-1]["pos"].y - self.sections[-1]["dimensions"].y
        max_pos += V((padding, -padding))
        self.bounding_box = (min_pos, max_pos)
        vertices = (min_pos, (max_pos.x, min_pos.y), (min_pos.x, max_pos.y), max_pos)

        shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        gpu.state.blend_set("ALPHA")
        batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        shader.bind()
        col = .09
        shader.uniform_float("color", (col, col, col, .9))
        batch.draw(shader)

        # Draw text
        for sect in self.sections:
            font_id = sect["font_id"]
            blf.color(font_id, *sect["color"])
            blf.size(font_id, sect["size"] * orig_size, 72)
            blf.position(font_id, *sect["pos"], 0)
            blf.draw(font_id, sect["text"])


def unregister():
    for handler in handlers:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handler, "WINDOW")
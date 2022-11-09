from pathlib import Path
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
            "default": blf.load(str(path / "DejaVuSansMono.ttf")),
            "bold": blf.load(str(path / "DejaVuSansMono-Bold.ttf")),
            "italic": blf.load(str(path / "DejaVuSansMono-Oblique.ttf")),
            "bolditalic": blf.load(str(path / "DejaVuSansMono-BoldOblique.ttf")),
        }

        url = get_docs_source_url(self.type)
        self.rst_source: str = requests.get(url).content.decode("utf-8").replace("\\n", "\n")
        self.mouse_pos = V((event.mouse_x, event.mouse_y))
        # print(self.rst_source)
        context.window_manager.modal_handler_add(self)
        context.area.tag_redraw()
        return {"RUNNING_MODAL"}

    def modal(self, context, event):

        if event.type == "LEFTMOUSE":
            return self.finish()

        if event.type in {"RIGHTMOUSE", "ESC"}:
            return self.finish()

        return {"PASS_THROUGH"}

    def finish(self):
        bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, "WINDOW")
        handlers.remove(self._handle)
        bpy.context.area.tag_redraw()
        print("finished")
        return {"FINISHED"}

    def draw_callback_px(self):
        print("hahahahahha")
        print("hahahahahha")

        pos = self.mouse_pos.copy()

        size = 100
        size_x = 1
        size_y = 2
        vertices = ((-size, -size), (size, -size), (-size, size), (size, size))
        vertices = [V((p[0] * size_x, p[1] * size_y)) for p in vertices]
        vertices = [pos + p for p in vertices]

        font_id = self.fonts["default"]
        # font_id = 0
        size = 15
        col = .85
        # blf.enable(font_id, blf.WORD_WRAP)
        # blf.word_wrap(font_id)
        blf.color(font_id, col, col, col, 1)
        lines = self.rst_source.splitlines()
        for i, line in enumerate(lines):
            blf.size(font_id, size, 72)
            padding = 2.5
            if line.startswith("="):
                continue
            if lines[min(i + 1, len(lines) - 1)].startswith("="):
                blf.size(font_id, size * 1.5, 72)
                padding = size / 2

            pos.y -= padding
            blf.position(font_id, pos.x, pos.y, 0)
            pos.y -= blf.dimensions(0, line)[1] + padding
            blf.draw(font_id, line)

        blf.disable(font_id, blf.WORD_WRAP)
        indices = ((0, 1, 2), (2, 1, 3))

        # shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
        # batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

        # shader.bind()
        # shader.uniform_float("color", (1, 0, 0, .8))
        # batch.draw(shader)
        pass


def unregister():
    for handler in handlers:
        bpy.types.SpaceNodeEditor.draw_handler_remove(handler, "WINDOW")
# from pathlib import Path
# from random import randint
# import re
# import webbrowser
# import bpy
# import gpu
# import blf
# from gpu_extras.batch import batch_for_shader
# from mathutils import Vector as V
# from ..vendor import requests
# from .npie_helpers import Op, Rectangle, lerp, vec_max, vec_min
# from bpy.types import Operator
# """Modified from the blender python source wm.py file
# Gets the documentation source .rst file for the selected node"""


# def _wm_doc_get_id(doc_id, *, do_url=True, url_prefix="", report=None):

#     def operator_exists_pair(a, b):
#         # Not fast, this is only for docs.
#         return b in dir(getattr(bpy.ops, a))

#     def operator_exists_single(a):
#         a, b = a.partition("_OT_")[::2]
#         return operator_exists_pair(a.lower(), b)

#     id_split = doc_id.split(".")
#     url = rna = None

#     if len(id_split) == 1:  # rna, class
#         if do_url:
#             url = "%s/bpy.types.%s.html" % (url_prefix, id_split[0])
#         else:
#             rna = "bpy.types.%s" % id_split[0]

#     elif len(id_split) == 2:  # rna, class.prop
#         class_name, class_prop = id_split

#         # an operator (common case - just button referencing an op)
#         if operator_exists_pair(class_name, class_prop):
#             if do_url:
#                 url = ("%s/bpy.ops.%s.html#bpy.ops.%s.%s" % (url_prefix, class_name, class_name, class_prop))
#             else:
#                 rna = "bpy.ops.%s.%s" % (class_name, class_prop)
#         elif operator_exists_single(class_name):
#             # note: ignore the prop name since we don't have a way to link into it
#             class_name, class_prop = class_name.split("_OT_", 1)
#             class_name = class_name.lower()
#             if do_url:
#                 url = ("%s/bpy.ops.%s.html#bpy.ops.%s.%s" % (url_prefix, class_name, class_name, class_prop))
#             else:
#                 rna = "bpy.ops.%s.%s" % (class_name, class_prop)
#         else:
#             # An RNA setting, common case.

#             # Check the built-in RNA types.
#             rna_class = getattr(bpy.types, class_name, None)
#             if rna_class is None:
#                 # Check class for dynamically registered types.
#                 rna_class = bpy.types.PropertyGroup.bl_rna_get_subclass_py(class_name)

#             if rna_class is None:
#                 return None

#             # Detect if this is a inherited member and use that name instead.
#             rna_parent = rna_class.bl_rna
#             rna_prop = rna_parent.properties.get(class_prop)
#             if rna_prop:
#                 rna_parent = rna_parent.base
#                 while rna_parent and rna_prop == rna_parent.properties.get(class_prop):
#                     class_name = rna_parent.identifier
#                     rna_parent = rna_parent.base

#                 if do_url:
#                     url = ("%s/bpy.types.%s.html#bpy.types.%s.%s" % (url_prefix, class_name, class_name, class_prop))
#                 else:
#                     rna = "bpy.types.%s.%s" % (class_name, class_prop)
#             else:
#                 # We assume this is custom property, only try to generate generic url/rna_id...
#                 if do_url:
#                     url = ("%s/bpy.types.bpy_struct.html#bpy.types.bpy_struct.items" % (url_prefix,))
#                 else:
#                     rna = "bpy.types.bpy_struct"

#     return url if do_url else rna


# def _find_reference(rna_id, url_mapping):
#     # XXX, for some reason all RNA ID's are stored lowercase
#     # Adding case into all ID's isn't worth the hassle so force lowercase.
#     rna_id = rna_id.lower()

#     # This is about 100x faster than the method currently used in Blender
#     # I might make a patch to fix it.
#     url_mapping = dict(url_mapping)
#     url = url_mapping[rna_id + "*"]
#     return url


# def _lookup_rna_url(rna_id, full_url=False):
#     for prefix, url_manual_mapping in bpy.utils.manual_map():
#         rna_ref = _find_reference(rna_id, url_manual_mapping)
#         if rna_ref is not None:
#             url = prefix + rna_ref if full_url else rna_ref
#             return url


# def get_docs_source_url(doc_id):
#     rna_id = _wm_doc_get_id(doc_id, do_url=False)
#     if rna_id is None:
#         return ""

#     url = _lookup_rna_url(rna_id, full_url=False)
#     url = "https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/" + url.split(".html")[0] + ".rst"

#     if url is None:
#         return ""
#     else:
#         return url


# def draw_rst(layout: bpy.types.UILayout, rst: str):
#     layout.scale_y = .5
#     for line in rst.splitlines():
#         layout.label(text=line)


# def listget(list, idx, default="last_element"):
#     if default == "last_element":
#         return list[min(idx, len(list) - 1)]
#     else:
#         try:
#             return list[idx]
#         except IndexError:
#             return default


# def round_to_nearest(x, base=5):
#     return base * round(x / base)


# def download_file(url: str, path: Path, redownload=False):
#     if not path.exists() or redownload:
#         with open(path, "wb") as f:
#             f.write(requests.get(url).content)


# loaded = {}


# def draw_image(pos, path, offset=0, scale=1):
#     path = Path(path)
#     indices = ((0, 1, 2), (3, 2, 0))

#     name = path.name
#     if loaded.get(path.name):
#         try:
#             image = bpy.data.images[name]
#         except KeyError:
#             image = bpy.data.images.load(str(path))
#             image.name = name
#             loaded[name] = image
#     else:
#         image = bpy.data.images.load(str(path))
#         image.name = name
#         loaded[name] = image
#     texture = gpu.texture.from_image(image)

#     min_pos = pos
#     # min_pos = V((0, 0))
#     size = V(image.size)
#     aspect = size.y / size.x
#     max_pos = V((size.x, -size.y))
#     max_pos *= scale
#     max_pos.x += offset
#     max_pos.y -= offset * aspect
#     # max_pos.y *= (size.y / size.x)
#     max_pos = min_pos + max_pos
#     vertices = (min_pos, (min_pos.x, max_pos.y), max_pos, (max_pos.x, min_pos.y))
#     # vertices = ((100, 100), (100, 200), (200, 200), (200, 100))
#     uvs = ((0, 1), (0, 0), (1, 0), (1, 1))

#     shader = gpu.shader.from_builtin('2D_IMAGE')
#     # shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

#     batch = batch_for_shader(shader, 'TRIS', {"pos": vertices, "texCoord": uvs}, indices=indices)
#     # batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

#     shader.bind()
#     # shader.uniform_float("color", (1, 0, 0, 1))
#     shader.uniform_sampler("image", texture)
#     batch.draw(shader)
#     return min_pos, max_pos


# handlers = []


# # @Op("node_pie")
# class NPIE_OT_show_node_docs(Operator):
#     """Show the documentation for this node"""

#     type: bpy.props.StringProperty()

#     link: bpy.props.StringProperty()

#     prev_pages: bpy.props.StringProperty()

#     pos: bpy.props.IntVectorProperty(size=2)

#     scale: bpy.props.FloatProperty(default=1)

#     def invoke(self, context, event):
#         args = ()
#         self._handle = bpy.types.SpaceNodeEditor.draw_handler_add(
#             self.draw_callback_px,
#             args,
#             "WINDOW",
#             # "PRE_VIEW",
#             "POST_PIXEL",
#         )
#         handlers.append(self._handle)
#         path = Path(__file__).parent / "fonts"
#         self.fonts = {
#             "default": blf.load(str(path / "Lato-Regular.ttf")),
#             "header": blf.load(str(path / "RobotoSlab-Bold.ttf")),
#             "bold": blf.load(str(path / "Lato-Bold.ttf")),
#             "italic": blf.load(str(path / "Lato-Italic.ttf")),
#             "bolditalic": blf.load(str(path / "Lato-BoldItalic.ttf")),
#             "code": blf.load(str(path / "DejaVuSansMono.ttf")),
#         }

#         if self.link:
#             if self.link.startswith("https://"):
#                 url = self.link
#             else:
#                 url = f"https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/{self.link}.rst"
#         else:
#             url = get_docs_source_url(self.type)
#         print(url)
#         self.rst_source: str = requests.get(url).content.decode("utf-8").replace("\\n", "\n")
#         self.url = url
#         if tuple(self.pos) != (0, 0):
#             self.view_location = V(self.pos)
#         else:
#             self.view_location = V((event.mouse_region_x - 400, event.mouse_region_y))
#         self.view_location.y = min(context.area.height - 80, self.view_location.y)

#         self.sections: list[dict] = []
#         self.pages = eval(self.prev_pages) if self.prev_pages else []
#         self.doclink = ""
#         self.dragging = False
#         self.scaling = False
#         self.scale = self.scale
#         self.start_scale = 1
#         self.prev_mouse_pos = self.view_location
#         self.press_pos = V((0, 0))
#         self.bounding_box = Rectangle
#         context.window_manager.modal_handler_add(self)
#         context.area.tag_redraw()
#         return {"RUNNING_MODAL"}

#     def modal(self, context, event):
#         if event.type in {"ESC"}:
#             return self.finish()

#         if not context.area:
#             print("Area removed")
#             return self.finish()

#         mouse_pos = V((event.mouse_region_x, event.mouse_region_y))
#         mouse_pos_win = V((event.mouse_x, event.mouse_y))
#         area = context.area
#         area_rect = Rectangle(V((area.x, area.y)), V((area.x + area.width, area.y + area.height)))
#         scroll_speed = 50
#         if not area_rect.isinside(mouse_pos_win) and not (self.dragging or self.scaling):
#             return {"PASS_THROUGH"}

#         if event.type == "RIGHTMOUSE":
#             if event.value == "PRESS" and not self.scaling:
#                 if self.bounding_box.isinside(mouse_pos):
#                     self.scaling = True
#                     self.start_scale = self.scale
#                     self.press_pos = mouse_pos.copy()
#                 else:
#                     return self.finish()
#             elif event.value == "RELEASE":
#                 self.scaling = False
#             return {"RUNNING_MODAL"}

#         elif event.type == "LEFTMOUSE":
#             if event.value == "PRESS" and not self.dragging:
#                 if self.bounding_box.isinside(mouse_pos):
#                     self.dragging = True
#                     self.press_pos = mouse_pos.copy()
#                 else:
#                     return self.finish()

#             elif event.value == "RELEASE":
#                 # if self.doclink and mouse_pos == self.prev_mouse_pos:
#                 if self.press_pos == mouse_pos:
#                     if self.doclink:
#                         pages = self.pages + [self.url]
#                         bpy.ops.node_pie.show_node_docs(
#                             "INVOKE_DEFAULT",
#                             link=self.doclink,
#                             pos=tuple(int(i) for i in self.view_location),
#                             prev_pages=str(pages),
#                             scale=self.scale,
#                         )
#                         print(self.doclink)
#                         return self.finish()
#                     elif self.weblink:
#                         webbrowser.open(self.weblink)
#                     elif self.term:
#                         pages = self.pages + [self.url]
#                         bpy.ops.node_pie.show_glossary_page(
#                             "INVOKE_DEFAULT",
#                             link=
#                             "https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/glossary/index.rst",
#                             pos=tuple(int(i) for i in self.view_location),
#                             prev_pages=str(pages),
#                             glossary_key=self.term,
#                             scale=self.scale,
#                         )
#                         return self.finish()
#                         # webbrowser.open(self.weblink)
#                 self.dragging = False
#             return {"RUNNING_MODAL"}

#         elif event.type == "Z" and event.ctrl and event.value == "PRESS" and not event.shift and self.pages:
#             bpy.ops.node_pie.show_node_docs(
#                 "INVOKE_DEFAULT",
#                 link=self.pages[-1],
#                 pos=tuple(int(i) for i in self.view_location),
#                 prev_pages=str(self.pages[:-1]),
#             )
#             return self.finish()

#         elif event.type == "WHEELUPMOUSE" and self.bounding_box.isinside(mouse_pos):
#             self.view_location.y -= scroll_speed
#             context.area.tag_redraw()
#             return {"RUNNING_MODAL"}
#         elif event.type == "WHEELDOWNMOUSE" and self.bounding_box.isinside(mouse_pos):
#             self.view_location.y += scroll_speed
#             context.area.tag_redraw()
#             return {"RUNNING_MODAL"}

#         if self.scaling:
#             self.scale = (self.start_scale + (mouse_pos.x - self.press_pos.x) * .03)
#             context.area.tag_redraw()

#         if self.dragging:
#             self.view_location += mouse_pos - self.prev_mouse_pos
#             context.area.tag_redraw()

#         if not self.dragging and not self.scaling:
#             for section in self.sections:
#                 if section.get("doclink"):
#                     weblink_box = Rectangle(section["pos"], section["pos"] + section["dimensions"])
#                     if weblink_box.isinside(mouse_pos):
#                         context.window.cursor_modal_set("HAND")
#                         self.doclink = section.get("doclink")
#                         break
#                     context.window.cursor_modal_restore()
#             else:
#                 self.doclink = ""
#             for section in self.sections:
#                 if section.get("weblink"):
#                     weblink_box = Rectangle(section["pos"], section["pos"] + section["dimensions"])
#                     if weblink_box.isinside(mouse_pos):
#                         context.window.cursor_modal_set("HAND")
#                         self.weblink = section.get("weblink")
#                         break
#                     context.window.cursor_modal_restore()
#             else:
#                 self.weblink = ""
#             for section in self.sections:
#                 if section.get("term"):
#                     term_box = Rectangle(section["pos"], section["pos"] + section["dimensions"])
#                     if term_box.isinside(mouse_pos):
#                         context.window.cursor_modal_set("HAND")
#                         self.term = section.get("term")
#                         break
#                     context.window.cursor_modal_restore()
#             else:
#                 self.term = ""
#         self.prev_mouse_pos = mouse_pos

#         return {"PASS_THROUGH"}

#     def finish(self):
#         bpy.types.SpaceNodeEditor.draw_handler_remove(self._handle, "WINDOW")
#         handlers.remove(self._handle)
#         bpy.context.window.cursor_modal_restore()
#         bpy.context.area.tag_redraw()
#         print("finished")
#         return {"FINISHED"}

#     def draw_callback_px(self):

#         self.sections = []
#         pos = self.view_location.copy()
#         orig_size = 15 + self.scale
#         is_chapter = False

#         lines = self.rst_source.splitlines()
#         new_lines = []
#         for line in lines:
#             new_lines.append(line)

#         lines = new_lines

#         for i, line in enumerate(lines):
#             line = line.replace("	", "    ")
#             font_id = self.fonts["default"]
#             # padding = 2.5
#             size = orig_size
#             sections: list[dict]
#             sections = [{"text": line.replace(" ", "  "), "size": 1}]
#             section = sections[0]

#             # Chapters
#             if is_chapter:
#                 section["size"] = 2
#                 section["font_id"] = self.fonts["header"]
#                 section["padding"] = orig_size / 2
#                 # padding = orig_size / 2
#             is_chapter_header = set(line) == {"*"}
#             is_chapter = is_chapter_header and set(listget(lines, i + 2)) == {"*"}
#             if is_chapter_header:
#                 continue

#             # Headers
#             if line.startswith("="):
#                 continue
#             if listget(lines, i + 1).startswith("="):
#                 section["size"] = 1.5
#                 section["font_id"] = self.fonts["header"]
#                 section["padding"] = size / 2
#                 # padding = size / 2

#             if listget(lines, i + 1).startswith("="):
#                 section["size"] = 1.5
#                 section["font_id"] = self.fonts["header"]
#                 section["padding"] = size / 2
#                 # padding = size / 2

#             def highlight_multi_line_section(prefix: str, attr: str, name: str):
#                 indentation = len(line) - len(line.lstrip())
#                 if prefix in line and not getattr(self, "is" + attr, False):
#                     setattr(self, attr + "initial_indentation", indentation)
#                     setattr(self, "is" + attr, True)
#                     section["text"] = " " * indentation * 2 + name + "  " + line.split(prefix)[-1]
#                     section[attr] = True
#                     return
#                 if getattr(self, "is" + attr, False):
#                     if indentation > getattr(self, attr + "initial_indentation") or not line.strip():
#                         section[attr] = True
#                     else:
#                         setattr(self, "is" + attr, False)

#             highlight_multi_line_section(".. warning::", "warning", "Warning:")
#             highlight_multi_line_section(".. note::", "note", "Note:")
#             highlight_multi_line_section(".. tip::", "tip", "Tip:")
#             highlight_multi_line_section(".. figure::", "figure", "")

#             # TODO: CHECK OUT WHAT THIS IS REMOVING, COULD BE USEFUL
#             if sections[0]["text"].startswith(".."):
#                 continue

#             def highlight_surrounded_section(surrounder: str, attr: str, sections: list[dict], add_suffix=""):
#                 """Split the provided sections into further sections based on the provided surrounder,
#                 and give them the provided attribute"""
#                 new_sections = []
#                 for section in sections:
#                     if section.get("math"):
#                         new_sections.append(section)
#                         continue
#                     text: str = section["text"]
#                     parts = text.split(surrounder)
#                     parts = [s for s in parts if s]
#                     odd = text.startswith(surrounder)
#                     for i, text in enumerate(parts):
#                         # if surrounder not in text:
#                         #     new_sections.append(section)
#                         #     continue
#                         is_surrounded = not bool(i % 2) if odd else bool(i % 2)
#                         new_section = section.copy()
#                         new_section["text"] = text
#                         if is_surrounded:
#                             new_section["text"] += add_suffix
#                         new_section[attr] = is_surrounded
#                         new_sections.append(new_section)
#                 return new_sections

#             def highlight_section(
#                 sections: list[dict],
#                 prefix: str,
#                 attr: str,
#                 suffix: str = "",
#                 surrounding_suffix=False,
#                 set_attr_to_inside_suffix=False,
#                 multi_line = False
#             ):
#                 new_sections = []
#                 for section in sections:
#                     # print(section)
#                     text: str = section["text"]
#                     if prefix not in text or suffix not in text:
#                         new_sections.append(section.copy())
#                         continue

#                     parts = text.split(prefix)

#                     # check if prefix is in suffix and use regex instead
#                     odd = text.startswith(prefix)
#                     if prefix in suffix:
#                         parts = re.split(f"{prefix}(?!{suffix.strip(prefix)})", text)
#                     else:
#                         parts = [s for s in parts if s]

#                     for i, text in enumerate(parts):
#                         new_section = section.copy()
#                         if suffix not in text:
#                             new_section["text"] = text
#                             new_sections.append(new_section)
#                             continue

#                         prefix_found = not bool(i % 2) if odd else bool(i % 2)
#                         if prefix_found:
#                             result = text.split(suffix)[1 if surrounding_suffix else 0]
#                             if set_attr_to_inside_suffix:
#                                 new_section[attr] = result
#                             else:
#                                 new_section[attr] = True
#                         else:
#                             result = text
#                         new_section["text"] = result
#                         new_sections.append(new_section)

#                         # Add section for the text after the new section
#                         if prefix_found:
#                             new_section = section.copy()
#                             new_section["text"] = text.split(suffix)[-1]
#                             new_sections.append(new_section)
#                 return new_sections

#             sections = highlight_section(
#                 sections,
#                 prefix=":doc:`",
#                 attr="doclink",
#                 suffix="`",
#                 set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix=":term:`",
#                 attr="term",
#                 suffix="`",
#                 set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix=":ref:`",
#                 attr="ref",
#                 suffix="`",
#                 set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix=":menuselection:`",
#                 attr="menu",
#                 suffix="`",
#                 # set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix=":kbd:`",
#                 attr="code",
#                 suffix="`",
#                 # set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix=":math:`",
#                 attr="math",
#                 suffix="`",
#                 # set_attr_to_inside_suffix=True,
#             )

#             sections = highlight_section(
#                 sections,
#                 prefix="`",
#                 attr="weblink",
#                 suffix="`__",
#                 set_attr_to_inside_suffix=True,
#             )

#             # Text styling
#             sections = highlight_surrounded_section("**", "bold", sections)
#             sections = highlight_surrounded_section("*", "italic", sections)
#             sections = highlight_surrounded_section("``", "code", sections)

#             # weblinks should have their text processed first so that they don't interfere with the sections
#             for section in sections:
#                 if section.get("weblink"):
#                     parts = section["text"].split("<")
#                     section["text"] = parts[0].lstrip().rstrip()
#                     section["weblink"] = parts[-1][:-1]

#             sections = highlight_surrounded_section(":", "param", sections, add_suffix=":")

#             if not line.startswith("  ") and listget(lines, i + 1).startswith("  "):
#                 for section in sections:
#                     section["bold"] = True

#             # Draw
#             padding = 2.5
#             pos.y -= padding
#             x = pos.x
#             val = .8
#             for section in sections:
#                 font_id = self.fonts["default"]
#                 color = (val, val, val, .8)

#                 if section.get("warning"):
#                     color = (1, 0.56, 0.19, 1)

#                 if section.get("tip"):
#                     color = (.38, 0.89, 0.83, 1)

#                 if section.get("note"):
#                     color = (.42, .69, .87, .8)

#                 if section.get("term"):
#                     color = link_color

#                 if section.get("math"):
#                     section["code"] = True
#                     text = section["text"]
#                     text = text.replace("_", "")
#                     # text = text.replace("\\begin{pmatrix}", "(")
#                     # text = text.replace("\\begin{pmatrix} ", "(")
#                     text = re.sub(" *\\\\end{pmatrix}", ")", text)
#                     text = re.sub("\\\\begin{pmatrix} *", "(", text)
#                     text = re.sub(" +", " ", text)
#                     text = re.sub("\\\\sqrt{(.*)}", "sqrt(\\1)", text)
#                     text = text.replace(" \\\\", ",")
#                     text = text.replace("\\cdot", "*")
#                     section["text"] = text

#                 if section.get("param"):
#                     section["bold"] = True
#                     section["italic"] = True
#                     # color = link_color

#                 if section.get("ref"):
#                     section["text"] = section["text"].split("<")[0]
#                     # color = (1, 0.56, 0.19, 1)

#                 if section.get("figure"):
#                     section["padding"] = 0
#                     section["size"] = .0
#                     pass

#                 link_color = (0.24, 0.53, 1, 1)

#                 if section.get("weblink"):
#                     color = link_color

#                 if section.get("doclink"):
#                     color = link_color
#                     # links can be in these formats:
#                     # Name <the/path/to/the/link>
#                     # the/path/to/the/link
#                     if "<" in section["text"]:
#                         parts = section["text"].split("<")
#                         section["text"] = parts[0]
#                         section["doclink"] = parts[-1][:-1]
#                     else:
#                         section["doclink"] = section["text"]
#                         section["text"] = section["text"].split("/")[-1].replace("_", " ")

#                 if section.get("bold") and section.get("italic"):
#                     font_id = self.fonts["bolditalic"]
#                 elif section.get("bold"):
#                     font_id = self.fonts["bold"]
#                 elif section.get("italic"):
#                     font_id = self.fonts["italic"]
#                 elif section.get("code"):
#                     font_id = self.fonts["code"]
#                     col = .7
#                     color = (col, col, col, .8)
#                     section["size"] = .9

#                 blf.size(font_id, section["size"] * orig_size, 72)
#                 dims = blf.dimensions(font_id, section["text"])
#                 if not section.get("font_id"):
#                     section["font_id"] = font_id
#                 section["color"] = color
#                 section["pos"] = V((x, pos.y))
#                 section["dimensions"] = V(dims)

#                 x += dims[0]
#             pos.y -= blf.dimensions(font_id, "".join([s["text"] for s in sections]))[1] + section.get(
#                 "padding", padding)

#             self.sections += sections

#         # Draw background
#         indices = ((0, 1, 2), (2, 1, 3))
#         padding = 15

#         min_pos = self.view_location + V((0, orig_size)) - V((padding, -padding))
#         max_pos = V((0, 0))
#         max_pos.x = max([s["pos"].x + s["dimensions"].x for s in self.sections])
#         max_pos.y = self.sections[-1]["pos"].y - self.sections[-1]["dimensions"].y
#         max_pos += V((padding, -padding))
#         vertices = (min_pos, (max_pos.x, min_pos.y), (min_pos.x, max_pos.y), max_pos)

#         shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
#         gpu.state.blend_set("ALPHA")
#         batch = batch_for_shader(shader, 'TRIS', {"pos": vertices}, indices=indices)

#         shader.bind()
#         col = .09
#         shader.uniform_float("color", (col, col, col, .99))
#         batch.draw(shader)

#         # Draw text
#         total_max_pos = max_pos.copy()
#         total_min_pos = min_pos.copy()
#         for sect in self.sections:
#             if sect.get("figure"):
#                 if not sect["text"].lstrip().startswith("/"):
#                     continue
#                 path = Path(__file__).parent / "images" / sect["text"].split("/")[-1]
#                 download_file(
#                     "https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual" + sect["text"].lstrip(), path)
#                 pos = sect["pos"]
#                 pos.x = max_pos.x
#                 min_, max_ = draw_image(pos, path, self.scale * 11.5, .75)
#                 # total_max_pos = vec_max(total_max_pos, min_)
#                 # total_min_pos = vec_min(total_min_pos, max_)
#                 continue
#             font_id = sect["font_id"]
#             blf.color(font_id, *sect["color"])
#             blf.size(font_id, sect["size"] * orig_size, 72)
#             blf.position(font_id, *sect["pos"], 0)
#             blf.draw(font_id, sect["text"])

#         self.bounding_box = Rectangle(total_min_pos, total_max_pos)


# # @Op("node_pie")
# class NPIE_OT_show_glossary_page(NPIE_OT_show_node_docs):
#     bl_idname = "node_pie.show_glossary_page"

#     glossary_key: bpy.props.StringProperty()

#     def invoke(self, context: bpy.types.Context, event):
#         ret = super().invoke(context, event)
#         rst = self.rst_source
#         match = next(re.finditer(f"(?m)^   {self.glossary_key}(\n.*)+", rst))

#         text = f"""***************
#    {self.glossary_key}
#         **************""".replace("        ", "")

#         lines = rst[match.start():].splitlines()

#         for line in lines[1:]:
#             if re.findall("(?m)^   [a-z|A-|]", line):
#                 break
#             text += "\n" + line
#         self.rst_source = text
#         return ret


# NPIE_OT_show_node_docs = Op("node_pie")(NPIE_OT_show_node_docs)
# NPIE_OT_show_glossary_page = Op("node_pie")(NPIE_OT_show_glossary_page)


# def draw(self, context):
#     if not context.active_node:
#         return
#     layout: bpy.types.UILayout = self.layout
#     layout.separator()
#     layout.operator_context = "INVOKE_DEFAULT"
#     op: NPIE_OT_show_node_docs = layout.operator("node_pie.show_node_docs", text="", icon="HELP")
#     op.type = context.active_node.bl_idname
#     op.link = ""
#     op.prev_pages = ""


# def register():
#     bpy.types.NODE_MT_context_menu.append(draw)


# def unregister():
#     for handler in handlers:
#         bpy.types.SpaceNodeEditor.draw_handler_remove(handler, "WINDOW")
#     bpy.types.NODE_MT_context_menu.remove(draw)
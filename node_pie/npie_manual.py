import bpy
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


def get_docs_url(doc_id):
    rna_id = _wm_doc_get_id(doc_id, do_url=False)
    if rna_id is None:
        return ""

    url = _lookup_rna_url(rna_id, full_url=False)
    url = "https://svn.blender.org/svnroot/bf-manual/trunk/blender_docs/manual/" + url.split(".html")[0] + ".rst"

    if url is None:
        return ""
    else:
        return url
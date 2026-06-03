import ctypes

from bpy.types import NodeSocket
from mathutils import Vector as V

from ..npie_constants import IS_WINDOWS

# Most of this is shamelessly stolen from VoronoiLinker
# Which seems to be the product of brilliant Schizophrenia


class StructBase(ctypes.Structure):
    _subclasses = []
    __annotations__ = {}

    def __init_subclass__(cls):
        cls._subclasses.append(cls)

    @staticmethod
    def _init_structs():
        functype = type(lambda: None)
        for cls in StructBase._subclasses:
            fields = []
            for field, value in cls.__annotations__.items():
                if isinstance(value, functype):
                    value = value()
                fields.append((field, value))
            if fields:
                cls._fields_ = fields
            cls.__annotations__.clear()
        StructBase._subclasses.clear()

    @classmethod
    def GetFields(cls, tar):
        return cls.from_address(tar.as_pointer())


class UString(StructBase):
    _pad0: ctypes.c_char * 8  # Don't know the implementation but it is 8 bytes


class BNodeSocketRuntimeHandle(StructBase):  # \source\blender\makesdna\DNA_node_types.h
    if IS_WINDOWS:
        _pad0: ctypes.c_char * 8
    declaration: ctypes.c_void_p
    identifier_ustr: UString
    changed_flag: ctypes.c_uint32
    total_inputs: ctypes.c_short

    # This is an enum, but not sure what exact type is used for that, char seems to work.
    inferred_structure_type: ctypes.c_char
    location: ctypes.c_float * 2


class BNodeStack(StructBase):
    vec: ctypes.c_float * 4
    min: ctypes.c_float
    max: ctypes.c_float
    data: ctypes.c_void_p
    hasinput: ctypes.c_short
    hasoutput: ctypes.c_short
    datatype: ctypes.c_short
    sockettype: ctypes.c_short
    is_copy: ctypes.c_short
    external: ctypes.c_short
    _pad: ctypes.c_char * 4


class BNodeSocket(StructBase):
    next: ctypes.c_void_p  # lambda: ctypes.POINTER(BNodeSocket)
    prev: ctypes.c_void_p  # lambda: ctypes.POINTER(BNodeSocket)
    prop: ctypes.c_void_p
    identifier: ctypes.c_char * 64
    name: ctypes.c_char * 64
    storage: ctypes.c_void_p
    type: ctypes.c_short
    flag: ctypes.c_short
    limit: ctypes.c_short
    in_out: ctypes.c_short
    typeinfo: ctypes.c_void_p
    idname: ctypes.c_char * 64
    default_value: ctypes.c_void_p
    stack_index: ctypes.c_int
    display_shape: ctypes.c_char
    attribute_domain: ctypes.c_char

    _pad: ctypes.c_char * 2
    label: ctypes.c_char * 64
    description: ctypes.c_char * 64

    default_attribute_name: ctypes.POINTER(ctypes.c_char)
    own_index: ctypes.c_int  # Deprecated
    to_index: ctypes.c_int  # Deprecated
    link: ctypes.c_void_p

    ns: BNodeStack  # Deprecated
    runtime: ctypes.POINTER(BNodeSocketRuntimeHandle)


StructBase._init_structs()


def get_socket_location_ctypes(socket: NodeSocket) -> V:
    if not socket.is_icon_visible:
        return V((0, 0))
    print(BNodeSocket.GetFields(socket).runtime.contents.location[:])

    return V(BNodeSocket.GetFields(socket).runtime.contents.location[:])

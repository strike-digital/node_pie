import json
import re
from typing import TYPE_CHECKING

from bpy.types import AddonPreferences, Context, Node, NodeTree
from mathutils import Vector as V

from .npie_constants import NODE_DEF_DIR, NODE_DEF_EXAMPLE_PREFIX

if TYPE_CHECKING:
    from .npie_prefs import NodePiePrefs
else:
    NodePiePrefs = AddonPreferences


def get_node_location(node: Node) -> V:
    """Get the actual location of a node, taking parent frame nodes into account"""
    location = node.location.copy()
    while node.parent:
        node = node.parent
        location += node.location
    return location


def get_node_tree(context: Context) -> NodeTree:
    """Get the node tree currently being edited"""
    return context.space_data.edit_tree


def get_prefs(context) -> NodePiePrefs:
    """Return the addon preferences"""
    return context.preferences.addons[__package__.split(".")[0]].preferences


def lerp(fac, a, b) -> float:
    """Linear interpolation (mix) between two values"""
    return (fac * b) + ((1 - fac) * a)


def inv_lerp(fac, a, b) -> float:
    """Inverse Linar Interpolation, get the fraction between a and b on which fac resides."""
    return (fac - a) / (b - a)


def vec_divide(a, b) -> V:
    """Elementwise divide for two vectors"""
    return V(e1 / e2 if e2 != 0 else 0 for e1, e2 in zip(a, b))


def vec_min(a, b) -> V:
    """Elementwise minimum for two vectors"""
    return V(min(e) for e in zip(a, b))


def vec_max(a, b) -> V:
    """Elementwise maximum for two vectors"""
    return V(max(e) for e in zip(a, b))


def map_range(val, from_min=0, from_max=1, to_min=0, to_max=2):
    """Map a value from one input range to another. Works in the same way as the map range node in blender.
    succinct formula from: https://stackoverflow.com/a/45389903"""
    return (val - from_min) / (from_max - from_min) * (to_max - to_min) + to_min


class JSONWithCommentsDecoder(json.JSONDecoder):

    match_trailing_commas: re.Pattern = re.compile(r",(?=\s*?[\}\]])", re.MULTILINE)

    def __init__(self, **kw):
        super().__init__(**kw)

    def decode(self, s: str):
        # Remove comments
        s = "\n".join(l if not l.lstrip().startswith("//") else "" for l in s.split("\n"))
        # Remove trailing commas
        s = self.match_trailing_commas.sub("", s)
        return super().decode(s)


def get_all_def_files():
    files = []
    for file in NODE_DEF_DIR.rglob("*"):
        if file.parent.name == "sockets":
            continue
        if file.is_file() and file.suffix == ".jsonc" and not file.name.startswith(NODE_DEF_EXAMPLE_PREFIX):
            files.append(file)
    return files


class Rectangle:
    """Helper class to represent a rectangle"""

    __slots__ = ["min", "max"]

    def __init__(self, min_co=(0, 0), max_co=(0, 0)):
        min_co = V(min_co)
        max_co = V(max_co)

        self.min = min_co
        self.max = max_co

    # alternate getter syntax
    minx = property(fget=lambda self: self.min.x)
    miny = property(fget=lambda self: self.min.y)
    maxx = property(fget=lambda self: self.max.x)
    maxy = property(fget=lambda self: self.max.y)

    @property
    def coords(self):
        """Return coordinates for drawing"""
        coords = [
            (self.minx, self.miny),
            (self.maxx, self.miny),
            (self.maxx, self.maxy),
            (self.minx, self.maxy),
        ]
        return coords

    @property
    def size(self):
        return self.max - self.min

    # FIXME: This can just be changed to using vec_mean of the min and max
    @property
    def center(self):
        return self.min + vec_divide(self.max - self.min, V((2, 2)))

    # return the actual min/max values. Needed because the class does not check
    # if the min and max values given are actually min and max at init.
    # I could fix it, but a bunch of stuff is built on it already, and I can't really be bothered
    @property
    def true_min(self):
        return vec_min(self.min, self.max)

    @property
    def true_max(self):
        return vec_max(self.min, self.max)

    def __str__(self):
        return f"Rectangle(V({self.minx}, {self.miny}), V({self.maxx}, {self.maxy}))"

    def __repr__(self):
        return self.__str__()

    def __mul__(self, value):
        if not isinstance(value, V):
            value = V((value, value))
        return Rectangle(self.min * value, self.max * value)

    def __add__(self, value):
        if not isinstance(value, V):
            value = V((value, value))
        return Rectangle(self.min + value, self.max + value)

    def isinside(self, point) -> bool:
        """Check if a point is inside this rectangle"""
        point = point
        min = self.true_min
        max = self.true_max
        return min.x <= point[0] <= max.x and min.y <= point[1] <= max.y

    def as_lines(self, individual=False):
        """Return a list of lines that make up this rectangle"""
        lines = []
        add = lines.append if individual else lines.extend
        coords = self.coords
        for i, coord in enumerate(coords):
            add((coord, coords[i - 1]))
        return lines

    def crop(self, rectangle):
        """Crop this rectangle to the inside of another one"""
        self.min = vec_max(self.min, rectangle.min)
        self.max = vec_min(self.max, rectangle.max)
        # prevent min/max overspilling on other side
        self.min = vec_min(self.min, rectangle.max)
        self.max = vec_max(self.max, rectangle.min)

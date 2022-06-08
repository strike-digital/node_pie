import bpy
import numpy as np
from math import pi
from statistics import mean
from dataclasses import dataclass
from mathutils import Vector as V
from mathutils.geometry import intersect_point_tri_2d, interpolate_bezier, area_tri
from bpy.types import NodeTree, Area, Operator
from time import perf_counter
from typing import List
from collections import deque, OrderedDict

# Console text colours
WHITE = '\033[37m'
RED = '\033[91m'
GREEN = '\033[92m'


class Timer():
    """Class that allows easier timing of sections of code.
    This is by no means especially smart, but I couldn't find anything similar
    that is as easy to use."""

    __slots__ = ["start_times", "end_times", "indeces", "average_of"]

    def __init__(self, average_of=20):
        self.start_times = {}
        self.end_times = OrderedDict()
        self.indeces = {}
        self.average_of = average_of

    def start(self, name):
        """Set the start time for this name"""
        self.start_times[name] = perf_counter()

    def stop(self, name):
        """Add an end time for this name"""
        time = perf_counter() - self.start_times[name]
        prev_times = self.end_times.get(name, deque(maxlen=self.average_of))

        prev_times.append(time)
        self.end_times[name] = prev_times
        self.indeces[name] = (self.indeces.get(name, 0) + 1) % self.average_of

    def get_time(self, name):
        return mean(self.end_times[name])

    def get_total(self):
        return sum([mean(self.end_times[name]) for name in self.end_times.keys()])

    def print_average(self, name):
        average = mean(self.end_times[name])
        if self.indeces[name] >= self.average_of - 1:
            print(f"{name}: {' ' * (20 - len(name))}{average:.20f}")
        return average

    def print_all(self, accuracy=6):
        """Print all active timers with formatting.
        Accuracy is the number of decimal places to display"""
        if self.indeces[list(self.indeces.keys())[-1]] >= self.average_of - 1:
            string = ""
            items = sorted(self.end_times.items(), key=lambda i: mean(i[1]), reverse=True)
            for i, (k, v) in enumerate(items):
                if i == 0:
                    color = RED
                elif i == len(items) - 1:
                    color = GREEN
                else:
                    color = WHITE
                average = mean(v)
                string += f"{color}{k}: {' ' * (20 - len(k))}{average:.{accuracy}f}\n"
            string += WHITE
            print(string)


class Polygon():
    """Helper class to represent a polygon of n points"""

    __slots__ = ["_verts", "color", "active", "tri_len"]

    def __init__(self, verts: list[V] = []):
        self.verts: list[V]
        self.verts = verts
        self.tri_len = 0

    @property
    def verts(self):
        return getattr(self, "_verts", [])

    @verts.setter
    def verts(self, points):
        if not points:
            return
        points = [V(p) for p in points]
        self._verts = points

    def center(self):
        """Get the centeroid of this polygon (mean of all points)"""
        arr = np.array(list(tuple(v) for v in self.verts))
        length = arr.shape[0]
        sum_x = np.sum(arr[:, 0])
        sum_y = np.sum(arr[:, 1])
        final = V((sum_x / length, sum_y / length))
        return final

    def bounds(self):
        # TODO: If I ever use this a lot, convert to numpy
        verts = self.verts
        v_min = V(100000, 100000)
        v_max = V(-100000, -100000)
        for v in verts:
            v_min = vec_min(v_min, v)
            v_max = vec_max(v_max, v)
        return Rectangle(v_min, v_max)

    def is_inside(self, point: V) -> bool:
        """Check if a point is inside this polygon"""
        verts = self.verts
        # center = verts[0]
        center = self.center()
        for i, vert in enumerate(verts):
            if intersect_point_tri_2d(point, vert, verts[i - 1], center):
                return True
        return False

    def as_tris(self, individual=False):
        """Return the tris making up this polygon"""
        verts = self.verts
        if not verts:
            return []
        points = []
        add = points.append if individual else points.extend
        center = verts[0]
        for i, vert in enumerate(verts):
            add([vert, self.verts[i - 1], center])
        self.tri_len = len(points)
        return points

    def as_lines(self, individual=False) -> list[list[V]]:
        """Return the lines making up the outline of this polygon as a single list"""
        # TODO: optimise by using slices
        points = []
        add = points.append if individual else points.extend
        verts = self.verts
        for i, v1 in enumerate(verts):
            add([v1, self.verts[i - 1]])
        return points

    def area(self):
        area = 0
        for tri in self.as_tris(individual=True):
            area += area_tri(tri[0], tri[1], tri[2])
        return area

    def normals(self):
        verts = self.verts
        normals = []
        append = normals.append
        for i, v in enumerate(verts):
            v_prev = verts[i - 1]
            v_next = verts[(i + 1) % (len(verts))]

            from_prev = (v - v_prev).normalized()
            from_next = (v - v_next).normalized()
            append((from_prev + from_next).normalized())
        return normals

    def distance_to_edges(self, point: V, edges: List[List[V]] = None) -> float:
        """Get the minimum distance of a point from a list of edges.
        Code adapted from from: https://www.fundza.com/vectors/point2line/index.html"""
        edges = edges if edges else self.as_lines(individual=True)
        distances = []
        append = distances.append
        for edge in edges:
            start = edge[0]
            end = edge[1]

            line_vec = start - end
            pnt_vec = start - point
            line_len = line_vec.length
            line_unitvec = line_vec.normalized()

            try:
                pnt_vec_scaled = pnt_vec * 1.0 / line_len
            except ZeroDivisionError:
                continue
            t = line_unitvec.dot(pnt_vec_scaled)
            t = max(0, min(1, t))

            nearest = line_vec * t
            dist = (nearest - pnt_vec).length
            append(dist)
        if distances:
            return min(distances)
        else:
            return 700000000

    def bevelled(self, radius=15, min_res=3, max_res=6):
        """Smooth the corners by using bezier interpolation between the last point,
        the current point and the next point."""
        bevelled = []
        verts = self.verts
        extend = bevelled.extend
        for i, vert in enumerate(verts):
            vert = V(vert)
            prev_vert = V(verts[i - 1])
            next_vert = V(verts[(i + 1) % len(verts)])

            to_prev = prev_vert - vert
            to_next = next_vert - vert

            # make prev and next vert a set distance away from the current vert
            # in effect, this controls the size of the smoothing
            prev_vert = to_prev.normalized() * min(radius, to_prev.length / radius) + vert
            next_vert = to_next.normalized() * min(radius, to_next.length / radius) + vert

            # Use fewer vertices on angles that need it less
            try:
                angle = to_prev.angle(to_next)
            except ValueError:
                # This happens very rarely when there is a zero length vector
                print("zero length")
                continue
            res = int(map_range(pi - angle, from_min=0, from_max=pi / 2, to_min=min_res, to_max=max_res))

            # interpolate points
            points = interpolate_bezier(prev_vert, vert, vert, next_vert, res)
            extend(points)

        return Polygon(bevelled)

    def __str__(self):
        return f"Polygon({self.verts})"

    def __repr__(self):
        return self.__str__()


class Rectangle():
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


@dataclass
class Op():
    """A decorator for defining blender Operators that helps to cut down on boilerplate code,
    and adds better functionality for autocomplete.
    To use it, add it as a decorator to the operator class, with whatever arguments you want.
    The only required argument is the category of the operator,
    and the rest can be inferred from the class name and __doc__.
    This works best for operators that use the naming convension ADDON_NAME_OT_operator_name.

    Args:
        `category` (str): The first part of the name used to call the operator (e.g. "object" in "object.select_all").
        `idname` (str): The second part of the name used to call the operator (e.g. "select_all" in "object.select_all")
        `label` (str): The name of the operator that is displayed in the UI.
        `description` (str): The description of the operator that is displayed in the UI.
        `register` (bool): Whether to display the operator in the info window and support the redo panel.
        `undo_push` (bool): Whether to push an undo step after the operator is executed.
        `undo_push_grouped` (bool): Whether to group multiple consecutive executions of the operator into one undo step.
        `internal` (bool): Whether the operator is only used internally and should not be shown in menu search
            (doesn't affect the operator search accessible when developer extras is enabled).
        `wrap_cursor` (bool): Whether to wrap the cursor to the other side of the region when it goes outside of it.
        `wrap_cursor_x` (bool): Only wrap the cursor in the horizontal (x) direction.
        `wrap_cursor_y` (bool): Only wrap the cursor in the horizontal (y) direction.
        `preset` (bool): Display a preset button with the operators settings.
        `blocking` (bool): Block anything else from using the cursor.
        `macro` (bool): Use to check if an operator is a macro.
        `logging` (int | bool): Whether to log when this operator is called.
            Default is to use the class logging variable which can be set with set_logging() and is global.
    """

    _logging = False

    @classmethod
    def set_logging(cls, enable):
        """Set the global logging state for all operators"""
        cls._logging = enable

    category: str
    idname: str = ""
    label: str = ""
    description: str = ""
    invoke: bool = True
    register: bool = True
    undo_push: bool = False
    undo_push_grouped: bool = False
    internal: bool = False
    wrap_cursor: bool = False
    wrap_cursor_x: bool = False
    wrap_cursor_y: bool = False
    preset: bool = False
    blocking: bool = False
    macro: bool = False
    # The default is to use the class logging setting, unless this has a value other than -1.
    # ik this is the same name as the module, but I don't care.
    logging: int = -1

    def __call__(self, cls):
        """This takes the decorated class and populate's the bl_ attributes with either the supplied values,
        or a best guess based on the other values"""

        cls_name_end = cls.__name__.split("OT_")[-1]
        idname = self.category + "." + (self.idname if self.idname else cls_name_end)

        if self.label:
            label = self.label
        else:
            label = cls_name_end.replace("_", " ").title()

        if self.description:
            description = self.description
        elif cls.__doc__:
            description = cls.__doc__
        else:
            description = label

        options = {
            "REGISTER": self.register,
            "UNDO": self.undo_push,
            "UNDO_GROUPED": self.undo_push_grouped,
            "GRAB_CURSOR": self.wrap_cursor,
            "GRAB_CURSOR_X": self.wrap_cursor_x,
            "GRAB_CURSOR_Y": self.wrap_cursor_y,
            "BLOCKING": self.blocking,
            "INTERNAL": self.internal,
            "PRESET": self.preset,
            "MACRO": self.macro,
        }
        options = {k for k, v in options.items() if v}

        if hasattr(cls, "bl_options"):
            options = options.union(cls.bl_options)

        if self.logging == -1:
            log = self._logging
        else:
            log = bool(self.logging)

        class Wrapped(cls, Operator):
            bl_idname = idname
            bl_label = label
            bl_description = description
            bl_options = options

            if self.invoke:
                def invoke(_self, context, event):
                    """Here we can log whenever an operator using this decorator is invoked"""
                    if log:
                        # I could use the actual logging module here, but I can't be bothered.
                        print(f"Invoke: {idname}")
                    if hasattr(super(), "invoke"):
                        return super().invoke(context, event)
                    else:
                        return _self.execute(context)

        Wrapped.__doc__ = description
        Wrapped.__name__ = cls.__name__
        return Wrapped


def lerp(fac, a, b) -> float:
    """Linear interpolation (mix) between two values"""
    return (fac * b) + ((1 - fac) * a)


def vec_lerp(fac, a, b) -> V:
    """Elementwise vector linear interpolation (mix) between two vectors"""
    return V(lerp(f, e1, e2) for f, e1, e2 in zip(fac, a, b))


def vec_divide(a, b) -> V:
    """Elementwise divide for two vectors"""
    return V(e1 / e2 if e2 != 0 else 0 for e1, e2 in zip(a, b))


def vec_multiply(a, b) -> V:
    """Elementwise multiply for two vectors"""
    return V(e1 * e2 for e1, e2 in zip(a, b))


def vec_min(a, b) -> V:
    """Elementwise minimum for two vectors"""
    return V(min(e) for e in zip(a, b))


def vec_max(a, b) -> V:
    """Elementwise maximum for two vectors"""
    return V(max(e) for e in zip(a, b))


def vec_mean(vectors: list[V]) -> V:
    """Get the mean of a list of vectors"""
    arr = np.array(list(tuple(v) for v in vectors))
    length = arr.shape[0]
    sum_x = np.sum(arr[:, 0])
    sum_y = np.sum(arr[:, 1])
    return V((sum_x / length, sum_y / length))


def map_range(val, from_min=0, from_max=1, to_min=0, to_max=2):
    """Map a value from one input range to another. Works in the same way as the map range node in blender.
    succinct formula from: https://stackoverflow.com/a/45389903"""
    return (val - from_min) / (from_max - from_min) * (to_max - to_min) + to_min


def get_uid(other_uids):
    """Get a unique value given a list of other values."""
    if not isinstance(other_uids, set):
        # Faster to find items in sets rather than lists
        other_uids = set(other_uids)
    i = 0
    while i < 1000:
        if i not in other_uids:
            break
        i += 1
    return i


def get_active_tree(context, area=None) -> NodeTree:
    """Get nodes from currently edited tree.
    If user is editing a group, space_data.node_tree is still the base level (outside group).
    context.active_node is in the group though, so if space_data.node_tree.nodes.active is not
    the same as context.active_node, the user is in a group.
    source: node_wrangler.py"""

    if not area:
        tree = context.space_data.node_tree
    else:
        tree = area.spaces[0].node_tree

    if tree.nodes.active:
        # Check recursively until we find the real active node_tree
        # This wont work if there are two editors open with the same node tree so that a node that is not the
        # correct group can be selected. In that case, simply the deepest node tree will be returned
        while (tree.nodes.active != context.active_node) and tree.nodes.active.type == "GROUP":
            tree = tree.nodes.active.node_tree
            continue

    return tree


def get_alt_node_tree_name(node_tree) -> str:
    """Get's the name of the parent data block for this node tree
    Only necessary if the tree is attached to a material or scene (shading or compositing)"""
    # "bpy.data.materials['Material'].node_tree"
    # returns 'Material'
    # Not a good way to do it, but I can't find a better one :(
    return repr(node_tree.id_data).split("'")[1]


def view_to_region(area: Area, coords: V) -> V:
    """Convert 2d editor to screen space coordinates"""
    coords = area.regions[3].view2d.view_to_region(coords[0], coords[1], clip=False)
    return V(coords)


def region_to_view(area: Area, coords: V) -> V:
    """Convert screen space to 2d editor coordinates"""
    coords = area.regions[3].view2d.region_to_view(coords[0], coords[1])
    return V(coords)


def dpifac() -> float:
    """Taken from Node Wrangler. Not sure exacly why it works, but it is needed to get the visual position of nodes"""
    prefs = bpy.context.preferences.system
    return prefs.dpi * prefs.pixel_size / 72  # Why 72?
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

bl_info = {
    "name": "Node Pie 1.2.19",
    "author": "Andrew Stevenson",
    "description": "An addon that adds a pie menu containing all nodes for each node editor",
    "blender": (3, 0, 0),
    "version": (1, 2, 19),
    "location": "Node editor > Shortcut",
    "doc_url": "https://github.com/strike-digital/node_pie/wiki",
    "tracker_url": "https://github.com/strike-digital/node_pie/issues",
    "category": "Node"
}

from . import auto_load

auto_load.init()


def register():
    auto_load.register()


def unregister():
    auto_load.unregister()
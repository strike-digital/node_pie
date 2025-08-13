import platform
from pathlib import Path

import bpy

IS_4_0 = bpy.app.version >= (4, 0, 0)
IS_4_5 = bpy.app.version >= (4, 5, 0)
IS_MACOS = platform.system() == "Darwin"

POPULARITY_FILE = Path(__file__).parent / "nodes.json"
if not POPULARITY_FILE.exists():
    with open(POPULARITY_FILE, "w") as f:
        pass
POPULARITY_FILE_VERSION = (0, 0, 1)

NODE_DEF_EXAMPLE_PREFIX = "node_def_"
NODE_DEF_DIR = Path(__file__).parent / "node_def_files"
NODE_DEF_BUILTIN = NODE_DEF_DIR / "builtin"
NODE_DEF_USER = NODE_DEF_DIR / "user"
NODE_DEF_BASE_FILE = NODE_DEF_DIR / "node_def_base.jsonc"
NODE_DEF_EXAMPLE_FILE = NODE_DEF_DIR / "node_def_example.jsonc"
NODE_DEF_SOCKETS = NODE_DEF_DIR / "sockets"

SHADERS_DIR = Path(__file__).parent / "shaders"

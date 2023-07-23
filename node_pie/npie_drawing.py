import gpu
from gpu.types import GPUBatch, GPUShader
from gpu_extras.batch import batch_for_shader
from mathutils import Vector as V


def draw_line(from_pos: V, to_pos: V, color: V, width=1):
    """Draw an antialiased line"""

    normal = V(to_pos - from_pos)
    normal.normalize()

    tangent = V((normal.y, -normal.x))
    tangent *= width

    coords = [
        from_pos + tangent,
        from_pos - tangent,
        to_pos + tangent,
        from_pos - tangent,
        to_pos + tangent,
        to_pos - tangent,
    ]

    shader: GPUShader = gpu.shader.from_builtin("UNIFORM_COLOR")
    batch: GPUBatch = batch_for_shader(shader, "TRIS", {"pos": coords})
    shader.bind()

    gpu.state.blend_set("ALPHA")
    shader.uniform_float("color", color)
    batch.draw(shader)
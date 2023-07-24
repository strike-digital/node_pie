import gpu
from gpu.types import GPUBatch, GPUShaderCreateInfo, GPUStageInterfaceInfo
from gpu_extras.batch import batch_for_shader
from mathutils import Vector as V
from .npie_constants import SHADERS_DIR


# Create the the antialaiased line shader
# This is not trivial...

with open(SHADERS_DIR / "2D_vert.glsl", 'r') as f:
    vert_code = f.read()
with open(SHADERS_DIR / "2D_line_antialiased_frag.glsl", 'r') as f:
    frag_code = f.read()

line_shader_info = GPUShaderCreateInfo()
line_shader_info.define("is_compile", "true")
line_shader_info.push_constant("MAT4", "ModelViewProjectionMatrix")
line_shader_info.push_constant("VEC4", "color")
line_shader_info.vertex_in(0, "VEC2", "pos")
line_shader_info.vertex_in(1, "VEC2", "uvs")

line_shader_interface = GPUStageInterfaceInfo("line_shader")
line_shader_interface.smooth("VEC2", "frag_uvs")
line_shader_info.vertex_out(line_shader_interface)

line_shader_info.fragment_out(0, "VEC4", "fragColor")

line_shader_info.vertex_source(vert_code)
line_shader_info.fragment_source(frag_code)

line_shader = gpu.shader.create_from_info(line_shader_info)


def draw_line(from_pos: V, to_pos: V, color: V, width=1):
    """Draw an antialiased line"""

    # Calculate the tangent
    normal = V(to_pos - from_pos)
    normal.normalize()
    tangent = V((normal.y, -normal.x))
    tangent *= width * 1.9

    # The four corners are the ends shifted along the tangent of the line
    coords = [
        from_pos + tangent,
        from_pos - tangent,
        to_pos + tangent,
        to_pos - tangent
    ]
    indices = [(0, 1, 2), (1, 2, 3)]
    uvs = [(0, 0), (0, 1), (1, 0), (1, 1)]

    batch: GPUBatch = batch_for_shader(line_shader, "TRIS", {"pos": coords, "uvs": uvs}, indices=indices)
    line_shader.bind()

    gpu.state.blend_set("ALPHA")
    line_shader.uniform_float("color", color)
    batch.draw(line_shader)
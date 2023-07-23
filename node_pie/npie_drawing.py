import gpu
from gpu.types import GPUBatch, GPUShader
from gpu_extras.batch import batch_for_shader
from mathutils import Vector as V
from .npie_constants import SHADERS_DIR

vertex_code = """
uniform mat4 ModelViewProjectionMatrix;
uniform vec4 color;
in vec2 pos;

void main()
{
  gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0, 1.0);
}"""

shader_code = """
out vec4 fragColor;
uniform vec4 color;

void main()
{
  fragColor = blender_srgb_to_framebuffer_space(color);
}"""

with open(SHADERS_DIR / "2D_vert.glsl", 'r') as f:
    vert_code = f.read()
with open(SHADERS_DIR / "2D_line_antialiased_frag.glsl", 'r') as f:
    frag_code = f.read()

line_shader = GPUShader(vertexcode=vert_code, fragcode=frag_code)


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

    batch: GPUBatch = batch_for_shader(line_shader, "TRIS", {"pos": coords})
    line_shader.bind()

    gpu.state.blend_set("ALPHA")
    line_shader.uniform_float("color", color)
    batch.draw(line_shader)
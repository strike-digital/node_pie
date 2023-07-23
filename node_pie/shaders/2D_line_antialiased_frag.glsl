out vec4 fragColor;
uniform vec4 color;

void main() {
    fragColor = blender_srgb_to_framebuffer_space(color);
}
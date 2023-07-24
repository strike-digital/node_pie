#ifndef is_compile
uniform vec4 color;

in vec2 frag_uvs;
out vec4 fragColor;
#endif

void main() {

    vec4 color = color;
    // Gradient going from 0 at edges to 1 in middle
    color.a *= 1 - abs(frag_uvs.y - .5f) * 2;
    // Antialias
    color.a = color.a / fwidth(color.a);

    // color = vec4(color.a, color.a, color.a, 1);
    fragColor = color;
    // fragColor = blender_srgb_to_framebuffer_space(color);
}
#ifndef is_compile
uniform vec4 color;

in vec2 frag_uvs;
out vec4 fragColor;
#endif

void main() {

    vec4 main_color = color;
    // Gradient going from 0 at edges to 1 in middle
    main_color.a *= 1 - abs(frag_uvs.y - .5f) * 2;
    // Antialias
    main_color.a = main_color.a / fwidth(main_color.a);

    // color = vec4(color.a, color.a, color.a, 1);
    fragColor = main_color;
    // fragColor = blender_srgb_to_framebuffer_space(color);
}
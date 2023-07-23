uniform mat4 ModelViewProjectionMatrix;

in vec2 pos;
in vec2 uvs;
out vec2 frag_uvs;

void main() {
    frag_uvs = uvs;
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0f, 1.0f);
}
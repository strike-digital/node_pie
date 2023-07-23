uniform mat4 ModelViewProjectionMatrix;
uniform vec4 color;
in vec2 pos;

void main() {
    gl_Position = ModelViewProjectionMatrix * vec4(pos, 0.0f, 1.0f);
}
"""
GPU shader-based glitch effect for pyray.

The fragment shader does:
  - block-based UV displacement (the "digital tearing" look)
  - RGB channel splitting (chromatic aberration)
  - scanline darkening
  - all driven by a `time` uniform and an `intensity` uniform you control
    from Python each frame.

You don't need a separate .fs file — the shader source is just a Python
string passed to load_shader_from_memory.
"""

import random
import pyray as pr

WIDTH, HEIGHT = 800, 450

# Raylib's default vertex shader is fine for a full-screen texture pass,
# so we pass None for the vertex shader and only supply a fragment shader.
FRAGMENT_SHADER = """
#version 330

in vec2 fragTexCoord;
in vec4 fragColor;

uniform sampler2D texture0;
uniform vec4 colDiffuse;

uniform float time;
uniform float intensity;   // 0.0 = no glitch, 1.0 = full glitch
uniform vec2 resolution;

out vec4 finalColor;

// cheap pseudo-random hash
float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

void main()
{
    vec2 uv = fragTexCoord;

    // --- 1. block displacement ---
    // Divide the screen into horizontal bands; each band gets a random
    // x-offset that changes a few times per second (stepped time).
    float bandHeight = 0.06; // fraction of screen height per band
    float band = floor(uv.y / bandHeight);
    float t = floor(time * 12.0); // how often bands re-roll
    float bandRand = hash(band * 13.13 + t);

    float displace = 0.0;
    if (bandRand > 1.0 - 0.35 * intensity) {
        // this band is "glitching" this tick
        displace = (hash(band + t * 7.0) - 0.5) * 0.08 * intensity;
    }
    uv.x += displace;

    // --- 2. RGB channel split (chromatic aberration) ---
    float shift = 0.006 * intensity;
    float r = texture(texture0, uv + vec2(shift, 0.0)).r;
    float g = texture(texture0, uv).g;
    float b = texture(texture0, uv - vec2(shift, 0.0)).b;
    vec3 col = vec3(r, g, b);

    // --- 3. scanlines ---
    float scan = sin(uv.y * resolution.y * 1.5) * 0.04 * intensity;
    col -= scan;

    // --- 4. occasional bright noise flecks ---
    float noise = hash(uv.x * 400.0 + uv.y * 200.0 + time * 60.0);
    if (noise > 0.995 - 0.01 * intensity) {
        col += vec3(1.0) * intensity;
    }

    finalColor = vec4(col, 1.0) * fragColor * colDiffuse;
}
"""


def main():
    pr.init_window(WIDTH, HEIGHT, "pyray shader glitch effect")
    pr.set_target_fps(60)

    target = pr.load_render_texture(WIDTH, HEIGHT)

    # vs_code=None uses raylib's default vertex shader
    shader = pr.load_shader_from_memory(b"", FRAGMENT_SHADER) # type: ignore

    loc_time = pr.get_shader_location(shader, "time")
    loc_intensity = pr.get_shader_location(shader, "intensity")
    loc_resolution = pr.get_shader_location(shader, "resolution")

    resolution = pr.ffi_new_vec2(WIDTH, HEIGHT) if hasattr(pr, "ffi_new_vec2") else [float(WIDTH), float(HEIGHT)] # type: ignore

    intensity = 0.0
    target_intensity = 0.0
    glitch_timer = 0.0
    elapsed = 0.0

    while not pr.window_should_close():
        dt = pr.get_frame_time()
        elapsed += dt

        # Random glitch bursts: occasionally ramp intensity up, then decay
        if glitch_timer <= 0 and random.random() < 0.6 * dt:
            glitch_timer = random.uniform(0.1, 0.3)
            target_intensity = random.uniform(0.5, 1.0)
        if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
            glitch_timer = 0.25
            target_intensity = 1.0

        if glitch_timer > 0:
            glitch_timer -= dt
        else:
            target_intensity = 0.0

        # smooth toward target so it doesn't just snap on/off
        intensity += (target_intensity - intensity) * min(1.0, dt * 15.0)

        # push uniforms to the shader
        pr.set_shader_value(shader, loc_time, pr.ffi.new('float *', float(elapsed)), pr.ShaderUniformDataType.SHADER_UNIFORM_FLOAT)
        pr.set_shader_value(shader, loc_intensity, pr.ffi.new('float *', float(intensity)), pr.ShaderUniformDataType.SHADER_UNIFORM_FLOAT)
        pr.set_shader_value(shader, loc_resolution, pr.ffi.new('float [2]', [float(WIDTH), float(HEIGHT)]), pr.ShaderUniformDataType.SHADER_UNIFORM_VEC2)

        # --- draw scene into render texture ---
        pr.begin_texture_mode(target)
        pr.clear_background(pr.Color(20, 20, 30, 255))
        pr.draw_text("SHADER GLITCH DEMO", 220, 40, 30, pr.RAYWHITE)
        pr.draw_text("Press SPACE to force a glitch burst", 210, 90, 16, pr.GRAY)
        pr.draw_circle(WIDTH // 2, HEIGHT // 2, 60, pr.Color(255, 90, 90, 255))
        pr.draw_rectangle_lines(50, 150, WIDTH - 100, 200, pr.SKYBLUE)
        pr.end_texture_mode()

        # --- composite with shader applied ---
        pr.begin_drawing()
        pr.clear_background(pr.BLACK)
        pr.begin_shader_mode(shader)
        pr.draw_texture_rec(
            target.texture,
            pr.Rectangle(0, 0, WIDTH, -HEIGHT),
            pr.Vector2(0, 0),
            pr.WHITE,
        )
        pr.end_shader_mode()
        pr.draw_fps(10, 10)
        pr.end_drawing()

    pr.unload_shader(shader)
    pr.unload_render_texture(target)
    pr.close_window()


if __name__ == "__main__":
    main()

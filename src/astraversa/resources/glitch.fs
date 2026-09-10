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
"""
CPU-based glitch effect for pyray (no shaders needed).

Techniques combined:
  1. RGB channel split (chromatic-aberration-ish smear)
  2. Random horizontal slice displacement
  3. Random noise blocks
  4. Screen jitter

Draw your scene into `target` (a RenderTexture2D), then call
glitch.draw(target) instead of drawing target directly.
"""

import random
import pyray as pr

WIDTH, HEIGHT = 800, 450


class GlitchController:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.active = False
        self.timer = 0.0
        self.duration = 0.0
        self.intensity = 0.0  # 0..1

    def trigger(self, duration=0.15, intensity=1.0):
        """Start (or extend) a glitch burst."""
        self.active = True
        self.timer = duration
        self.duration = duration
        self.intensity = intensity

    def maybe_random_trigger(self, dt, chance_per_second=0.5):
        """Call every frame to get occasional random glitch bursts."""
        if not self.active and random.random() < chance_per_second * dt:
            self.trigger(
                duration=random.uniform(0.08, 0.25),
                intensity=random.uniform(0.4, 1.0),
            )

    def update(self, dt):
        if self.active:
            self.timer -= dt
            if self.timer <= 0:
                self.active = False

    def get_jitter_offset(self):
        """Small random screen-shake offset while active."""
        if not self.active:
            return pr.Vector2(0, 0)
        mag = 4 * self.intensity
        return pr.Vector2(random.uniform(-mag, mag), random.uniform(-mag, mag))

    def draw(self, texture):
        """
        Draw the render texture to the screen with the glitch effect applied.
        `texture` is a pr.RenderTexture2D.texture (a Texture2D).
        """
        jitter = self.get_jitter_offset()
        full_src = pr.Rectangle(0, 0, self.width, -self.height)  # flip Y for render textures

        if not self.active:
            pr.draw_texture_rec(texture, full_src, jitter, pr.WHITE)
            return

        offset = int(6 * self.intensity)

        # 1. RGB channel split
        pr.draw_texture_rec(
            texture, full_src,
            pr.Vector2(jitter.x - offset, jitter.y),
            pr.Color(255, 0, 60, 140),
        )
        pr.draw_texture_rec(
            texture, full_src,
            pr.Vector2(jitter.x + offset, jitter.y),
            pr.Color(0, 220, 255, 140),
        )
        pr.draw_texture_rec(
            texture, full_src,
            pr.Vector2(jitter.x, jitter.y),
            pr.Color(255, 255, 255, 200),
        )

        # 2. Random horizontal slice displacement
        num_slices = int(4 * self.intensity) + 1
        for _ in range(num_slices):
            y = random.randint(0, self.height - 10)
            h = random.randint(2, int(18 * self.intensity) + 2)
            h = min(h, self.height - y)
            x_off = random.randint(int(-25 * self.intensity), int(25 * self.intensity))
            src = pr.Rectangle(0, y, self.width, -h)
            pr.draw_texture_rec(texture, src, pr.Vector2(x_off, y), pr.WHITE)

        # 3. Random noise blocks
        num_blocks = int(15 * self.intensity)
        for _ in range(num_blocks):
            bw = random.randint(5, 40)
            bh = random.randint(2, 10)
            bx = random.randint(0, self.width - bw)
            by = random.randint(0, self.height - bh)
            color = random.choice([
                pr.Color(255, 0, 100, 180),
                pr.Color(0, 255, 200, 180),
                pr.WHITE,
                pr.BLACK,
            ])
            pr.draw_rectangle(bx, by, bw, bh, color)


def main():
    pr.init_window(WIDTH, HEIGHT, "pyray CPU glitch effect")
    pr.set_target_fps(60)

    target = pr.load_render_texture(WIDTH, HEIGHT)
    glitch = GlitchController(WIDTH, HEIGHT)

    box_x = WIDTH / 2
    angle = 0.0

    while not pr.window_should_close():
        dt = pr.get_frame_time()
        angle += dt * 60

        # Manual trigger with SPACE, or let it happen randomly
        if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
            glitch.trigger(duration=0.2, intensity=1.0)
        glitch.maybe_random_trigger(dt, chance_per_second=0.6)
        glitch.update(dt)

        # --- draw scene into the render texture ---
        pr.begin_texture_mode(target)
        pr.clear_background(pr.Color(20, 20, 30, 255))
        pr.draw_text("GLITCH DEMO", 260, 40, 30, pr.RAYWHITE)
        pr.draw_text("Press SPACE to trigger a glitch burst", 190, 90, 16, pr.GRAY)
        pr.draw_circle(int(box_x), HEIGHT // 2, 60, pr.Color(255, 90, 90, 255))
        pr.draw_rectangle_lines(50, 150, WIDTH - 100, 200, pr.SKYBLUE)
        pr.end_texture_mode()

        # --- composite to screen with glitch ---
        pr.begin_drawing()
        pr.clear_background(pr.BLACK)
        glitch.draw(target.texture)
        pr.draw_fps(10, 10)
        pr.end_drawing()

    pr.unload_render_texture(target)
    pr.close_window()


if __name__ == "__main__":
    main()

import random
from os.path import realpath
from sys import path
import pyray as pr

from astraversa.storage import Storage
from astraversa.runner import ModuleFlag, initialize
from astraversa.shaders import define, ShaderObject
from astraversa.game import BaseGame
from astraversa.modes import RenderTextureMode

WIDTH, HEIGHT = 800, 450

@define(Storage.get("astra-res://glitch.fs"))
class GlitchShader(ShaderObject):
    time: float
    intensity: float
    resolution: tuple[float, float]

class Game(BaseGame):
    def __init__(self) -> None:
        self.root_target: pr.RenderTexture
        self.shader: GlitchShader
        self.elapsed = 0.0
        self.glitch_timer = 0
        self.intensity = 0.0
        self.target_intensity = 0.0

    def load(self):
        self.root_target = pr.load_render_texture(WIDTH, HEIGHT)
        self.shader = GlitchShader()
        self.shader.time = 0.0
        self.shader.intensity = 0.0
        self.shader.resolution = (float(WIDTH), float(HEIGHT))

    def update(self):
        dt = pr.get_frame_time()
        self.elapsed += dt

        # Random glitch bursts: occasionally ramp intensity up, then decay
        if self.glitch_timer <= 0 and random.random() < 0.6 * dt:
            self.glitch_timer = random.uniform(0.1, 0.3)
            self.target_intensity = random.uniform(0.5, 1.0)
        if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
            self.glitch_timer = 0.25
            self.target_intensity = 1.0

        if self.glitch_timer > 0:
            self.glitch_timer -= dt
        else:
            self.target_intensity = 0.0

        # smooth toward target so it doesn't just snap on/off
        self.intensity += (self.target_intensity - self.intensity) * min(1.0, dt * 15.0)

        # push uniforms to the shader (reusing the same buffers)
        self.shader.time = self.elapsed
        self.shader.intensity = self.intensity

    def pre_draw(self):
        with RenderTextureMode(self.root_target):
            pr.clear_background(pr.Color(20, 20, 30, 255))
            pr.draw_text("SHADER GLITCH DEMO", 220, 40, 30, pr.RAYWHITE)
            pr.draw_text("Press SPACE to force a glitch burst", 210, 90, 16, pr.GRAY)
            pr.draw_circle(WIDTH // 2, HEIGHT // 2, 60, pr.Color(255, 90, 90, 255))
            pr.draw_rectangle_lines(50, 150, WIDTH - 100, 200, pr.SKYBLUE)

    def draw(self):
        pr.clear_background(pr.BLACK)
        with self.shader:
            pr.draw_texture_rec(
                self.root_target.texture,
                pr.Rectangle(0, 0, WIDTH, -HEIGHT),
                pr.Vector2(0, 0),
                pr.WHITE,
            )
        pr.draw_fps(10, 10)

    def unload(self):
        self.shader.unload()
        pr.unload_render_texture(self.root_target)

def test_shader():
    pr.init_window(WIDTH, HEIGHT, "Test")
    
    target = pr.load_render_texture(WIDTH, HEIGHT)
    shader = GlitchShader()
    shader.time = 0.0
    shader.intensity = 0.0
    shader.resolution = (float(WIDTH), float(HEIGHT))
    
    shader.unload()
    pr.unload_render_texture(target)
    pr.close_window()

def main():
    with initialize(
        WIDTH, HEIGHT,
        "Shader Test",
        (ModuleFlag.audio,
                ModuleFlag.headless,
                ModuleFlag.transparent,
                ModuleFlag.msaa_4x,
                ModuleFlag.highdpi
        )
    ):
        pr.set_target_fps(60)
        game = Game()
        game.start()

if __name__ == "__main__":
    main()

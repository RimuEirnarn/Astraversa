from dataclasses import dataclass
from random import randint

from pyray import (Image, RenderTexture, Texture, load_image, draw_fps, draw_texture, load_render_texture, load_texture_from_image, clear_background,
                   window_should_close, unload_texture, unload_image, rl_begin, rl_end, draw_texture_pro)
from pyray import (rl_set_texture, rl_color4ub, rl_tex_coord2f, rl_vertex2f, draw_mesh_instanced)
from astraversa import BaseGame, initialize
from astraversa.runner import draw
from astraversa.storage import Storage
from astraversa.modes import RenderTextureMode


@dataclass
class Object:
    x: int
    y: int
    
    def normalize_delta(self, x: int, y: int):
        cx = self.x
        cy = self.y
        self.x = min(max(50, cx - x), Game.width)
        self.y = min(max(50, cy - y), Game.height)

# We hit an issue that each frame calls O(2n) of instances. This is an immediate issue.
# Apparently, it's an issue if we're going normal.

class Game(BaseGame):
    width: int = 1280
    height: int = 920
    iterations = 1_000

    def __init__(self) -> None:
        self._image: Image
        self._imagetexture: Texture
        self._instances: list[Object] = []
        self._buffer: RenderTexture

    def load(self):
        self._image = load_image(str(Storage.get("astra-assets://obj3.png")))
        self._imagetexture = load_texture_from_image(self._image)
        self._buffer = load_render_texture(self.width, self.height)
        for _ in range(self.iterations):
            self._instances.append(Object(randint(20, self.width), randint(20, self.height)))

    def unload(self):
        unload_texture(self._imagetexture)
        unload_image(self._image)

    def update(self):
        # pass
        for inst in self._instances:
            inst.x = randint(20, self.width)
            inst.y = randint(20, self.height)

    def draw(self):
        clear_background((0, 0, 0, 0))
        draw_fps(5, 5)
        for inst in self._instances:
            draw_texture(self._imagetexture, inst.x, inst.y, (255, 255, 255, 255))
            pass

    def oneNrun(self):
        try:
            while not window_should_close():
                with draw():
                    clear_background((0, 0, 0, 0))
                    draw_fps(5, 5)
                    for inst in self._instances:
                        inst.x = randint(20, self.width)
                        inst.y = randint(20, self.height)
                        draw_texture(self._imagetexture, inst.x, inst.y, (255, 255, 255, 255))
        finally:
            self.unload()
    
    def twoNrun(self):
        try:
            while not window_should_close():
                rl_begin(0)
                clear_background((0, 0, 0, 0))
                draw_fps(5, 5)
                for inst in self._instances:
                    # inst.x = randint(20, self.width)
                    # inst.y = randint(20, self.height)
                    draw_texture(self._imagetexture, inst.x, inst.y, (255, 255, 255, 255))
        finally:
            self.unload()
    
    def batched_run(self):
        # Manual immediate-mode batching: one texture bind, one rl_begin/rl_end
        # wrapping ALL quads. rlgl still auto-flushes internally once its vertex
        # buffer fills (default ~8192 quads), but this avoids draw_texture's
        # per-call C-function overhead and lets rlgl coalesce what it can.
        try:
            while not window_should_close():
                with draw():
                    clear_background((0, 0, 0, 0))
                    draw_fps(5, 5)

                    tex_w = float(self._imagetexture.width)
                    tex_h = float(self._imagetexture.height)

                    rl_set_texture(self._imagetexture.id)
                    rl_begin(0x0007) # RL_QUADS
                    rl_color4ub(255, 255, 255, 255)

                    for inst in self._instances:
                        inst.x = randint(20, self.width)
                        inst.y = randint(20, self.height)
                        x, y = float(inst.x), float(inst.y)

                        rl_tex_coord2f(0.0, 0.0)
                        rl_vertex2f(x, y)

                        rl_tex_coord2f(0.0, 1.0)
                        rl_vertex2f(x, y + tex_h)

                        rl_tex_coord2f(1.0, 1.0)
                        rl_vertex2f(x + tex_w, y + tex_h)

                        rl_tex_coord2f(1.0, 0.0)
                        rl_vertex2f(x + tex_w, y)

                    rl_end()
                    rl_set_texture(0)
        finally:
            self.unload()
    
    def batched_run2(self):
        try:
            while not window_should_close():
                for inst in self._instances:
                    inst.x = randint(20, self.width)
                    inst.y = randint(20, self.height)

                with RenderTextureMode(self._buffer):
                    clear_background((0, 0, 0, 0))
                    for inst in self._instances:
                        draw_texture(self._imagetexture, inst.x, inst.y, (255, 255, 255, 255))
                
                with draw():
                    clear_background((0, 0, 0, 0))
                    draw_texture(self._buffer.texture, 0, 0, (255, 255, 255, 255))
                    draw_fps(5, 5)
        finally:
            self.unload()
        

def main():
    with initialize(Game.width, Game.height, "O(2n) test", ()):
        game = Game()
        # game.start() # — 3 FPS
        game.load()
        game.oneNrun()
        # game.batched_run2()

if __name__ == '__main__':
    main()
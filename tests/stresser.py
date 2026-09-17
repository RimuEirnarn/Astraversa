from dataclasses import dataclass
from random import randint

from pyray import Image, Texture, load_image, draw_fps, draw_texture, load_texture_from_image, clear_background, window_should_close, unload_texture, unload_image
from astraversa import BaseGame, initialize
from astraversa.runner import draw
from astraversa.storage import Storage

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
    iterations = 100_000

    def __init__(self) -> None:
        self._image: Image
        self._imagetexture: Texture
        self._instances: list[Object] = []

    def load(self):
        self._image = load_image(str(Storage.get("astra-assets://obj3.png")))
        self._imagetexture = load_texture_from_image(self._image)
        for _ in range(self.iterations):
            self._instances.append(Object(randint(-self.width, self.width), randint(-self.height, self.height)))

    def unload(self):
        unload_texture(self._imagetexture)
        unload_image(self._image)

    def update(self):
        for inst in self._instances:
            inst.x = randint(20, self.width)
            inst.y = randint(20, self.height)

    def draw(self):
        clear_background((0, 0, 0, 0))
        draw_fps(5, 5)
        for inst in self._instances:
            draw_texture(self._imagetexture, inst.x, inst.y, (255, 255, 255, 255))

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

def main():
    with initialize(Game.width, Game.height, "O(2n) test", ()):
        game = Game()
        game.start() # — 3 FPS
        # game.load()
        # game.oneNrun()

if __name__ == '__main__':
    main()
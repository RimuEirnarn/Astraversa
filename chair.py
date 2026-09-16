import pyray as pr

from astraversa.frame_helper import is_on_frame
from astraversa.game import BaseGame
from astraversa.runner import ModuleFlag, draw, initialize
from astraversa.ui.frame import RootFrame

RESOLUTION = (200, 200)

class Game(BaseGame):
    """Game instance"""
    def __init__(self) -> None:
        self.frame = RootFrame(0, 0, *RESOLUTION, background=(0, 0, 0, 150), scale=0)
        self.dragging = False
        self.drag_anchor = pr.Vector2(0, 0)
        self.nonce = False

    def _drag_anchoring(self):
        mouse = pr.get_mouse_position()
        drag_anchor_is_empty = self.drag_anchor.x == 0 and self.drag_anchor.y == 0
        if pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_LEFT) and is_on_frame(
            mouse.x,
            mouse.y,
            self.frame.corner,
            self.frame.vline_w,
            self.frame.hline_h,
            self.frame.width, # type: ignore
            self.frame.height, # type: ignore
        ):
            self.drag_anchor = mouse

        if pr.is_mouse_button_released(pr.MouseButton.MOUSE_BUTTON_LEFT):
            self.dragging = False
            self.drag_anchor = pr.Vector2(0, 0)

        if not drag_anchor_is_empty and pr.is_mouse_button_down(
            pr.MouseButton.MOUSE_BUTTON_LEFT
        ):
            pos = pr.get_window_position()
            abs_ms = pr.Vector2(pos.x + mouse.x, pos.y + mouse.y)
            npos_x = int(abs_ms.x - self.drag_anchor.x)
            npos_y = int(abs_ms.y - self.drag_anchor.y)
            pr.set_window_position(npos_x, npos_y)

    def load(self):
        """load"""
        self.frame.load()

    def update(self):
        """Update""" 
        # self._drag_anchoring()
        #self.frame.set_size(pr.get_screen_width(), pr.get_screen_height())
        if self.nonce is False:
            self.frame.update()
            self.frame.layout()
            self.nonce = True

    def draw(self):
        """Draw"""
        self.frame.draw()

    def run(self):
        """Run"""
        try:
            while not pr.window_should_close():
                self.update()
                with draw():
                    self.draw()
        finally:
            self.unload()

    def unload(self):
        """Unload"""
        self.frame.unload()

def main():


    with initialize(
        *RESOLUTION,
        "Chair",
        (
                # ModuleFlag.borderless,
                ModuleFlag.resizable,
                ModuleFlag.topmost,
                # ModuleFlag.headless,
                ModuleFlag.transparent,
                ModuleFlag.msaa_4x,
                ModuleFlag.always_run,
                # ModuleFlag.maximized,
                ModuleFlag.unfocused,
                # ModuleFlag.passthrough,
                ModuleFlag.highdpi
        )
    ):
        pr.set_target_fps(120)
        game = Game()
        game.start()

if __name__ == '__main__':
    main()

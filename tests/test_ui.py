from sys import path
from os.path import realpath
from astraversa.profiler import profile
import pyray as pr


path.insert(0, realpath(__file__+'/../../'))

from astraversa.fonts import FontManager
from astraversa.game import BaseGame
from astraversa.runner import ModuleFlag, draw, initialize
from astraversa.ui.base import Padding
from astraversa.ui.text import TextGroup, Text, TextStyle, RichTextRenderer
from astraversa.ui.frame import RootFrame

RESOLUTION = (1280, 800)
FRAME_COUNT_LIMIT = 600

class Game(BaseGame):
    """Game instance"""
    def __init__(self) -> None:
        self.frame = RootFrame(0, 0, *RESOLUTION, pr.BLACK)
        self.font_manager = FontManager(["IBMPlexSans"])
        self.style = TextStyle(size=20)
        tg = TextGroup(6, 20, gap=2, padding=Padding(0, 0, 4, 4), style=self.style)
        tg.add(Text("*Hello*, _Cyrene_~"))
        tg.add(Text("***Hello***, **Cyrene**~"))
        tg.add(Text("**Hello**, ***Cyrene***~"))
        tg.add(Text("Hello, Cyrene~"))
        tg.add(Text("Hello, ~~Cyrene~~~"))
        tg.add(Text("Hello, Cyrene~"))
        tg.add(Text("Hello, Cyrene~"))
        tg.add(Text(r"1 + 2 \*\* 3 \_ 5 __ 23 \*\* 3"))
        self.frame.children.append(tg)
        self.frame_count = 0

    def load(self):
        """load"""
        self.frame.load()
        self.font_manager.load()
        self.style.font = self.font_manager.fonts['IBMPlexSans']

    def update(self):
        """Update""" 
        if pr.is_key_pressed(pr.KeyboardKey.KEY_SPACE):
            RichTextRenderer.use_caching = not RichTextRenderer.use_caching
        self.frame_count += 1
        self.frame.update()
        self.frame.layout()

    def draw(self):
        """Draw"""
        self.frame.draw()


    def run(self):
        """Run"""
        try:
            while not pr.window_should_close():
                self.update()
                if self.frame_count > FRAME_COUNT_LIMIT:
                    break
                with draw():
                    self.draw()
        finally:
            self.unload()

    def unload(self):
        """Unload"""
        self.frame.unload()
        self.font_manager.unload()

def main():
    with initialize(
        *RESOLUTION,
        "Desktop Jail",
        (ModuleFlag.audio,
                # ModuleFlag.headless,
                # ModuleFlag.transparent,
                # ModuleFlag.msaa_4x,
                # ModuleFlag.always_run,
                # ModuleFlag.maximized,
                # ModuleFlag.unfocused,
                # ModuleFlag.highdpi
        )
    ):
        pr.set_target_fps(60)
        game = Game()
        game.start()

def test_rich_text_parse_tokens_are_cached():
    text = "**Hello** and *world*~~verbose~~"
    tokens = RichTextRenderer.parse_tokens(text)
    assert tokens == (
        ("Hello", (True, False, False)),
        (" and ", (False, False, False)),
        ("world", (False, True, False)),
        ("verbose", (False, False, True))
    )
    assert RichTextRenderer.parse_tokens(text) is tokens


if __name__ == '__main__':
    main()
# pylint: disable=no-member
"""Game instance"""

import pyray as pr

from astraversa.runner import draw

class BaseGame:
    """Base game"""
    def __init__(self) -> None:
        pass
    
    def load(self):
        """Load game data"""
        pass
    
    def update(self):
        """Update"""
        pass
    
    def pre_draw(self):
        """Pre draw"""
        pass
    
    def draw(self):
        """Draw"""
        pass

    def run(self):
        """Run"""
        try:
            while not pr.window_should_close():
                self.update()
                self.pre_draw()
                with draw():
                    self.draw()
        finally:
            self.unload()
    
    def unload(self):
        """Unload"""
        pass


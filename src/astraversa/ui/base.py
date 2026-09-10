"""Base UI Element"""

from dataclasses import dataclass
from pyray import Texture

@dataclass
class Computed:
    x: float
    y: float
    width: float
    height: float

class UIElement:
    """Base UI Element"""

    def __init__(
        self,
        x: int,
        y: int,
        width: float | None = None,
        height: float | None = None,
        visible: bool = True,
        enabled: bool = True
    ) -> None:
        self.parent: UIElement | None = None
        self.children: list[UIElement] = []
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.visible = visible
        self.enabled = enabled
        self.dirty =  False
        self.computed: Computed | None 
        self.textures: dict[str, Texture] = {}

    def load(self):
        """Do load"""
        return None

    def unload(self):
        """Do unload"""
        return None

    def update(self):
        """Do update"""
        # Default no-op. Subclasses may override.
        return None

    def layout(self):
        """Do layout"""
        # Default no-op. Subclasses may override.
        return None

    def draw(self):
        """Do draw"""
        # Default no-op. Subclasses may override.
        return None

    def mark_dirty(self):
        """Mark current state as dirty"""
        # Mark this element dirty and propagate to ancestors so that
        # layout can run at the root when needed.
        if not self.dirty:
            self.dirty = True
        # Propagate upward
        if self.parent is not None:
            parent = self.parent
            if not parent.dirty:
                parent.mark_dirty()

@dataclass(slots=True)
class Padding:
    left: float
    right: float
    top: float
    bottom: float

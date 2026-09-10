"""Frame"""

from line_profiler import profile
import pyray as pr

from astraversa.assets import Assets
from astraversa.draw import draw_tiled_h, draw_tiled_v
from astraversa.ui.base import Computed, UIElement

INACTIVE_PREFIX = "inactive_"
ACTIVE_PREFIX = ""

class RootFrame(UIElement):
    def __init__(self,
                 x: int,
                 y: int,
                 width: float | None = None,
                 height: float | None = None,
                 background: pr.Color | tuple[int, int, int, int] = (0, 0, 0, 255),
                 scale: int = 2,
                 visible: bool = True,
                 enabled: bool = True) -> None:
        self.width: float
        self.height: float
        if not width:
            width = pr.get_screen_width()
        if not height:
            width = pr.get_screen_height()
        super().__init__(x, y, width, height, visible, enabled)
        self.focus = True
        self.scale = scale
        self.corner = 8 * self.scale
        self.hline_w = 4 * self.scale
        self.hline_h = 2 * self.scale
        self.vline_w = 2 * self.scale
        self.vline_h = 4 * self.scale
        self.background = background

    def load(self):
        for key, path in (
            ("frame_tl", "astra-assets:///{prefix}window_topleft.png"),
            ("frame_tr", "astra-assets:///{prefix}window_topright.png"),
            ("frame_bl", "astra-assets:///{prefix}window_botleft.png"),
            ("frame_br", "astra-assets:///{prefix}window_botright.png"),
            ("frame_v", "astra-assets:///{prefix}window_vertical.png"),
            ("frame_h", "astra-assets:///{prefix}window_horizontal.png"),
        ):
            abspath_active = Assets.get(path.format(prefix=ACTIVE_PREFIX))
            abspath_inactive = Assets.get(path.format(prefix=INACTIVE_PREFIX))
            active_texture = pr.load_texture(str(abspath_active))
            pr.set_texture_filter(active_texture, pr.TextureFilter.TEXTURE_FILTER_POINT)
            self.textures[key] = active_texture

            inactive_texture = pr.load_texture(str(abspath_inactive))
            pr.set_texture_filter(
                inactive_texture, pr.TextureFilter.TEXTURE_FILTER_POINT
            )
            self.textures['i'+key] = inactive_texture
        
        for children in self.children:
            children.load()
    
    def unload(self):
        for key, value in self.textures.copy().items():
            pr.unload_texture(value)
            del self.textures[key]
        
        for children in self.children:
            children.unload()

    def set_focus(self, focus: bool):
        self.focus = focus
        self.mark_dirty()

    def set_size(self, width: float, height: float):
        if width != self.width:
            self.width = width
            self.mark_dirty()
        if height != self.height:
            self.height = height
            self.mark_dirty()

    def update(self):
        self.dirty = False
        for children in self.children:
            children.update()

    def layout(self):
        self.computed = Computed(self.x, self.y, self.width, self.height)
        for children in self.children:
            children.layout()

    def draw(self):
        """Frame"""
        prefix = 'i' if not self.focus else ''
        hline = self.textures[prefix+"frame_h"]
        vline = self.textures[prefix+"frame_v"]
        tl = self.textures[prefix+"frame_tl"]
        tr = self.textures[prefix+"frame_tr"]
        bl = self.textures[prefix+"frame_bl"]
        br = self.textures[prefix+"frame_br"]
        w, h = self.width, self.height
        scale = self.scale
        cw = self.corner  # scaled corner width/height = 32
        hline_h = self.hline_h
        vline_w = self.vline_w

        pr.clear_background((0, 0, 0, 0))
        pr.draw_rectangle(0, 0, int(w), int(h), self.background)

        if self.scale:
            # ── Corners ──────────────────────────────────────────────
            # Top-left
            pr.draw_texture_ex(tl, pr.Vector2(0, 0), 0, scale, pr.WHITE)
            # Top-right
            pr.draw_texture_ex(tr, pr.Vector2(w - cw, 0), 0, scale, pr.WHITE)
            # Bottom-left
            pr.draw_texture_ex(bl, pr.Vector2(0, h - cw), 0, scale, pr.WHITE)
            # Bottom-right
            pr.draw_texture_ex(br, pr.Vector2(w - cw, h - cw), 0, scale, pr.WHITE)

            # ── Horizontal edges (top and bottom) ────────────────────
            inner_w = int(w - cw * 2)
            draw_tiled_h(hline, cw, 0, inner_w, scale)  # top
            draw_tiled_h(hline, cw, int(h) - hline_h, inner_w, scale)  # bottom

            # ── Vertical edges (left and right) ──────────────────────
            inner_h = int(h - cw * 2)
            draw_tiled_v(vline, 0, cw, inner_h, scale)  # left
            draw_tiled_v(vline, int(w) - vline_w, cw, inner_h, scale)  # right

        # pr.draw_fps(vline_w + 2, hline_h + 2)
        for children in self.children:
            children.draw()
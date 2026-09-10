# pylint: disable=no-name-in-module
from collections import OrderedDict
import pyray as pr
from pyray import (draw_texture_pro, Texture, Rectangle, Vector2, WHITE, Texture, RenderTexture, Rectangle, Vector2, WHITE,
    load_render_texture, unload_render_texture,
    begin_texture_mode, end_texture_mode,)

from astraversa.modes import RenderTextureMode

TRANSPARENT = (0, 0, 0, 0)

def draw_scaled(texture: Texture, x: int, y: int, width: int, height: int):
    """Draw texture in scale"""
    src = Rectangle(0, 0, texture.width, texture.height)
    dst = Rectangle(x, y, width, height)
    draw_texture_pro(texture, src, dst, Vector2(0, 0), 0.0, (1, 1, 1, 1))

def draw_tiled_h(tex: Texture, x: int, y: int, total_width: int, scale: int):
    """Tile texture horizontally across total_width."""
    tile_w = tex.width * scale
    x_cursor = x
    remaining = total_width
    while remaining > 0:
        draw_w = min(tile_w, remaining)
        src = Rectangle(0, 0, draw_w / scale, tex.height)
        dst = Rectangle(x_cursor, y, draw_w, tex.height * scale)
        draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)
        x_cursor += draw_w
        remaining -= draw_w

def draw_tiled_v(tex: Texture, x: int, y: int, total_height: int, scale: int):
    """Tile texture vertically across total_height."""
    tile_h = tex.height * scale
    y_cursor = y
    remaining = total_height
    while remaining > 0:
        draw_h = min(tile_h, remaining)
        src = Rectangle(0, 0, tex.width, draw_h / scale)
        dst = Rectangle(x, y_cursor, tex.width * scale, draw_h)
        draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)
        y_cursor += draw_h
        remaining -= draw_h

class TiledEdgeCache:
    """Caches a tiled horizontal/vertical edge into an off-screen render
    texture. LRU-evicts when over max_entries so long-running sessions with
    many distinct frame sizes don't leak GPU textures forever."""

    def __init__(self, max_entries: int = 64):
        self.max_entries = max_entries
        self._cache: OrderedDict[tuple, RenderTexture] = OrderedDict()

    def _touch(self, key):
        self._cache.move_to_end(key)

    def _evict_if_needed(self):
        while len(self._cache) > self.max_entries:
            _, rt = self._cache.popitem(last=False)  # oldest
            unload_render_texture(rt)

    def _build_h(self, tex: Texture, total_width: int, scale: int, h: int) -> RenderTexture:
        rt = load_render_texture(total_width, h)
        with RenderTextureMode(rt):
            pr.clear_background((0, 0, 0, 0))
            tile_w = tex.width * scale
            x_cursor = 0
            remaining = total_width
            while remaining > 0:
                draw_w = min(tile_w, remaining)
                src = Rectangle(0, 0, draw_w / scale, tex.height)
                dst = Rectangle(x_cursor, 0, draw_w, h)
                draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)
                x_cursor += draw_w
                remaining -= draw_w
        return rt

    def _build_v(self, tex: Texture, total_height: int, scale: int, w: int) -> RenderTexture:
        rt = load_render_texture(w, total_height)
        with RenderTextureMode(rt):
            pr.clear_background((0, 0, 0, 0))
            tile_h = tex.height * scale
            y_cursor = 0
            remaining = total_height
            while remaining > 0:
                draw_h = min(tile_h, remaining)
                src = Rectangle(0, 0, tex.width, draw_h / scale)
                dst = Rectangle(0, y_cursor, w, draw_h)
                draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)
                y_cursor += draw_h
                remaining -= draw_h
        return rt

    def get_h(self, tex_id: int, tex: Texture, total_width: int, scale: int, h: int) -> Texture:
        key = ("h", tex_id, total_width, scale, h)
        rt = self._cache.get(key)
        if rt is None:
            rt = self._build_h(tex, total_width, scale, h)
            self._cache[key] = rt
            self._evict_if_needed()
        else:
            self._touch(key)
        return rt.texture

    def get_v(self, tex_id: int, tex: Texture, total_height: int, scale: int, w: int) -> Texture:
        key = ("v", tex_id, total_height, scale, w)
        rt = self._cache.get(key)
        if rt is None:
            rt = self._build_v(tex, total_height, scale, w)
            self._cache[key] = rt
            self._evict_if_needed()
        else:
            self._touch(key)
        return rt.texture

    def clear(self):
        for rt in self._cache.values():
            unload_render_texture(rt)
        self._cache.clear()


def draw_stretched_h(tex: Texture, x: int, y: int, total_width: int, h: int):
    """Option 2: single stretched draw, no tiling, no caching needed.
    Good fallback for frames that resize every frame (animations, drags)."""
    src = Rectangle(0, 0, tex.width, tex.height)
    dst = Rectangle(x, y, total_width, h)
    draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)


def draw_stretched_v(tex: Texture, x: int, y: int, total_height: int, w: int):
    src = Rectangle(0, 0, tex.width, tex.height)
    dst = Rectangle(x, y, w, total_height)
    draw_texture_pro(tex, src, dst, Vector2(0, 0), 0.0, WHITE)
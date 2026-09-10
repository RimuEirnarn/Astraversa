# pylint: disable=no-name-in-module
from pyray import draw_texture_pro, Texture, Rectangle, Vector2, WHITE

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

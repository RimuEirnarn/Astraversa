from collections import OrderedDict
from functools import lru_cache
import re
from typing import NamedTuple

from pyray import (WHITE, Color, Font, Rectangle, RenderTexture, clear_background, draw_texture_rec, get_font_default,
                   load_render_texture, measure_text_ex, draw_text_ex, Vector2, begin_scissor_mode, end_scissor_mode,
                   draw_line_ex, Texture, unload_render_texture, set_texture_filter, TextureFilter, BlendMode as BlendEnum)

from astraversa.profiler import profile
from astraversa.modes import RenderTextureMode, BlendMode
from astraversa.runner import atunload
from astraversa.types import HorizontalAlignment, LayoutDirection, Pos2D, VerticalAlignment
from astraversa.fonts import FontFamily
from astraversa.ui.base import Padding, UIElement, Computed

_measure_cache: dict[tuple, tuple[float, float]] = {}
_MEASURE_CACHE_MAX = 4096


class RendererStyle(NamedTuple):
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False

# @lru_cache
def measure_text(
    font: Font | None = None, text: str = "", size: float = 16, spacing: float = 1
):
    x = measure_text_ex(font if font else get_font_default(), text, size, spacing)
    assert x.x != 0 and size != 0, "Font is not loaded"
    assert x.y != 0 and size != 0, "Font is not loaded"
    return x

def measure_cached(font: Font, text: str, font_size: float, spacing: float) -> Vector2:
    key = (id(font), text, font_size, spacing)
    hit = _measure_cache.get(key)
    if hit is not None:
        return Vector2(hit[0], hit[1])
    size = measure_text_ex(font, text, font_size, spacing)
    if len(_measure_cache) >= _MEASURE_CACHE_MAX:
        _measure_cache.clear()  # crude cap; swap for LRU if this matters
    _measure_cache[key] = (size.x, size.y)
    return size

@lru_cache
def measure_renderer(
        family: FontFamily, 
        text: str,
        font_size: float, 
        spacing: float
):
    cursor_x = 0
    cursor_y = 0

    for clean_text, renderer_style in RichTextRenderer.parse_tokens(text):
        font = family.get_font(renderer_style.bold, renderer_style.italic)
        text_size = measure_text_ex(font, clean_text, font_size, spacing)
        cursor_x += text_size.x
        cursor_y = text_size.y

    return Vector2(cursor_x, cursor_y)

class TextStyle:
    def __init__(
        self,
        font: FontFamily | None = None,
        size: float = 16,
        spacing: float = 2,
        color: Color = WHITE,
    ) -> None:
        self.font = font
        self.size = size
        self.spacing = spacing
        self.color = color


DEFAULT_TEXT_STYLE = TextStyle()

class RichTextCache:
    """Renders a rich-text block to an off-screen texture once and reuses
    it every frame until the underlying text/style/font_size/spacing/color
    changes. LRU-capped so long sessions with many dynamic labels don't
    leak GPU memory."""

    def __init__(self, max_entries: int = 256):
        self.max_entries = max_entries
        self._cache: OrderedDict[tuple, tuple[RenderTexture, float, float]] = OrderedDict()
        atunload(self.clear)

    def _touch(self, key):
        self._cache.move_to_end(key)

    def _evict_if_needed(self):
        while len(self._cache) > self.max_entries:
            _, (rt, _, _) = self._cache.popitem(last=False)
            unload_render_texture(rt)

    def _measure_block(self, family, text, font_size, spacing):
        """First pass: figure out total width/height without drawing."""
        cursor_x = 0.0
        max_h = font_size
        for clean_text, style in RichTextRenderer.parse_tokens(text):
            font = family.get_font(style.bold, style.italic)
            size = measure_text_ex(font, clean_text, font_size, spacing)
            cursor_x += size.x
            max_h = max(max_h, size.y)
        return cursor_x, max_h

    def _build(self, family, text, font_size, spacing, color) -> tuple[RenderTexture, float, float]:
        width, height = self._measure_block(family, text, font_size, spacing)
        width = max(1, int(width) + 1)
        height = max(1, int(height) + 1)

        rt = load_render_texture(width, height)
        set_texture_filter(rt.texture, TextureFilter.TEXTURE_FILTER_POINT)
        with RenderTextureMode(rt):
            clear_background((0, 0, 0, 0))

            cursor_x = 0.0
            for clean_text, style in RichTextRenderer.parse_tokens(text):
                font = family.get_font(style.bold, style.italic)
                current_pos = Vector2(cursor_x, 0)
                text_size = measure_text_ex(font, clean_text, font_size, spacing)
                draw_text_ex(font, clean_text, current_pos, font_size, spacing, color)
                if style.strikethrough:
                    line_y = current_pos.y + font_size // 2
                    start = Vector2(current_pos.x, line_y)
                    end = Vector2(current_pos.x + text_size.x, line_y)
                    draw_line_ex(start, end, 2, color)
                cursor_x += text_size.x

        return rt, width, height

    def get(self, family, text: str, font_size: float, spacing: float, color: Color):
        # color/font_size/spacing/text/family identity all matter — bake them into the key
        key = (id(family), text, font_size, spacing, tuple(color) if not isinstance(color, tuple) else color) # type: ignore
        hit = self._cache.get(key)
        if hit is None:
            rt, w, h = self._build(family, text, font_size, spacing, color)
            self._cache[key] = (rt, w, h)
            self._evict_if_needed()
            return rt.texture, w, h
        self._touch(key)
        rt, w, h = hit
        return rt.texture, w, h

    def invalidate(self, family, text: str, font_size: float, spacing: float, color: Color):
        """Call this when a specific block's content changes, so it re-renders
        instead of serving stale cache."""
        key = (id(family), text, font_size, spacing, tuple(color) if not isinstance(color, tuple) else color) # type: ignore
        hit = self._cache.pop(key, None)
        if hit is not None:
            unload_render_texture(hit[0])

    def clear(self):
        for rt, _, _ in self._cache.values():
            unload_render_texture(rt)
        self._cache.clear()

class RichTextRenderer:
    # Matches ***bold italic***, **bold**, *italic*, or regular plain text
    PATTERN = re.compile(r'(\*\*\*.+?\*\*\*|\*\*.+?\*\*|\*.+?\*|_.+?_|~~.+?~~|\\.|[^\*_~\\]+|.)')
    cache = RichTextCache()
    use_caching: bool = True

    @staticmethod
    @lru_cache(maxsize=256)
    def parse_tokens(text: str):
        tokens: list[tuple[str, RendererStyle]] = []
        for token in RichTextRenderer.PATTERN.findall(text):
            bold = False
            italic = False
            strike = False
            clean_text = token

            if len(token) == 2 and token[0] == '\\' and token[1] in ('*', '_', '~', '\\'):
                clean_text = token[1]
            elif len(token) >= 6 and token.startswith("***") and token.endswith("***"):
                bold, italic = True, True
                clean_text = token[3:-3]
            elif len(token) >= 4 and token.startswith("**") and token.endswith("**"):
                bold = True
                clean_text = token[2:-2]
            elif len(token) >= 2 and ((token.startswith("*") and token.endswith("*")) or (token.startswith('_') and token.endswith('_'))):
                italic = True
                clean_text = token[1:-1]
            elif len(token) >= 4 and token.startswith("~~") and token.endswith("~~"):
                strike = True
                clean_text = token[2:-2]

            tokens.append((clean_text, RendererStyle(bold, italic, strike)))

        return tuple(tokens)

    @profile
    @staticmethod
    def draw(
        family: FontFamily, 
        text: str, 
        position: Vector2, 
        font_size: float, 
        spacing: float, 
        color: Color
    ):
        if RichTextRenderer.use_caching:
            tex, w, h = RichTextRenderer.cache.get(family, text, font_size, spacing, color)
            with BlendMode(BlendEnum.BLEND_ALPHA_PREMULTIPLY):
                draw_texture_rec(tex, Rectangle(0, 0, w, -h), position, WHITE)
            return
        cursor_x = position.x
        cursor_y = position.y

        for clean_text, renderer_style in RichTextRenderer.parse_tokens(text):
            font = family.get_font(renderer_style.bold, renderer_style.italic)
            current_pos = Vector2(cursor_x, cursor_y)
            text_size = measure_cached(font, clean_text, font_size, spacing)
            cursor_x += text_size.x
            
            draw_text_ex(font, clean_text, current_pos, font_size, spacing, color)
            if renderer_style.strikethrough:
                line_y = current_pos.y + font_size // 2
                start = Vector2(current_pos.x, line_y)
                end = Vector2(current_pos.x + text_size.x, line_y)
                draw_line_ex(start, end, 2, color)

class Text(UIElement):
    """Text element"""

    def __init__(
        self,
        text: str,
        x: int | None = None,
        y: int | None = None,
        width: float | None = None,
        height: float | None = None,
        style: TextStyle | None = None,
        visible: bool = True,
        enabled: bool = True,
        wrap: bool = True,
        max_width: float | None = None,
    ) -> None:
        self.text = text
        self.style = style if style else DEFAULT_TEXT_STYLE
        self.wrap = wrap
        self.max_width = max_width
        super().__init__(x, y, width, height, visible, enabled)  # type: ignore

    def measure(self):
        res = measure_renderer(
            self.style.font, self.text, self.style.size, self.style.spacing
        )
        return res

    # @profile
    def layout(self):
        """Calculate measured size and absolute position for this text."""
        # Determine available width for wrapping: prefer explicit width, then parent's content width
        parent = self.parent
        avail_width: float | None = None
        if not parent and None in (self.x, self.y):
            err = ValueError("Cannot determine positioning while there's no parent.")
            err.add_note("Please add the position or push it to a parent element")
            raise err
        elif parent and None in (self.x, self.y):
            assert isinstance(parent, TextGroup)
            relpos = parent.index_position_for(self)
            # print(relpos)
            if self.x is None:
                x = relpos[0]
            if self.y is None:
                y = relpos[1]
        else:
            x, y = self.x, self.y
        assert x is not None, y is not None
        
        if self.width is not None:
            avail_width = self.width
        elif parent is not None and getattr(parent, "width", None) is not None:
            # parent may be a TextGroup and have padding
            pad = getattr(parent, "padding", None)
            if pad is not None:
                avail_width = parent.width - (pad.left + pad.right)
            else:
                avail_width = parent.width

        # If wrapping is requested and we have an available width, wrap text
        if self.wrap and avail_width is not None:
            words = self.text.split()
            lines: list[str] = []
            current = ""
            for w in words:
                candidate = w if current == "" else f"{current} {w}"
                measured = measure_renderer(self.style.font, candidate, self.style.size, self.style.spacing)
                if measured.x <= avail_width:
                    current = candidate
                else:
                    if current == "":
                        # single word longer than width: hard break the word
                        # fall back to placing the word on its own line
                        lines.append(w)
                        current = ""
                    else:
                        lines.append(current)
                        current = w
            if current != "":
                lines.append(current)

            # line height from measuring a representative string
            line_h = measure_renderer(self.style.font, "Ay", self.style.size, self.style.spacing).y
            total_h = int(line_h * len(lines))
            comp_w = int(avail_width)
            comp_h = int(total_h)
        else:
            m = self.measure()
            comp_w = int(m.x)
            comp_h = int(m.y)

        # compute absolute position
        if parent is not None and getattr(parent, "computed", None) is not None:
            assert parent.computed
            abs_x = parent.computed.x + int(x)
            abs_y = parent.computed.y + int(y)
        else:
            abs_x = int(self.x)
            abs_y = int(self.y)

        self.computed = Computed(abs_x, abs_y, comp_w, comp_h)
        # Mark clean
        self.dirty = False

    def update(self):
        """Update the text element.

        If the element is marked dirty, perform layout so computed
        geometry is available before drawing. This is a lightweight
        per-frame hook; heavy work should remain in `layout()`.
        """
        if self.dirty:
            self.layout()
        return None

    @profile
    def draw(self):
        """Render this text using computed geometry and resolved style."""
        if not self.visible:
            return None

        if self.computed is None:
            # Nothing to draw without computed geometry
            return None


        pos = Vector2(self.computed.x, self.computed.y)
        # print(f"Draw {self.text!r} to ({pos.x}, {pos.y})")
        if not self.style.font:
            draw_text_ex(get_font_default(), self.text, pos, self.style.size, self.style.spacing, self.style.color)
        else:
            RichTextRenderer.draw(self.style.font, self.text, pos, self.style.size, self.style.spacing, self.style.color)


class TextGroup(UIElement):
    """Text group"""

    def __init__(
        self,
        x: int,
        y: int,
        width: float | None = None,
        height: float | None = None,
        visible: bool = True,
        enabled: bool = True,
        gap: int = 8,
        padding: Padding | int = 2,
        direction: LayoutDirection = "vertical",
        halign: HorizontalAlignment = "left",
        valign: VerticalAlignment = "top",
        clipping: bool = False,
        scrollable: bool = True,
        style: TextStyle | None = None
    ) -> None:
        super().__init__(x, y, width, height, visible, enabled)
        self.children: list[Text] = []
        self.gap = gap
        self.direction: LayoutDirection = direction
        self.halign: HorizontalAlignment = halign
        self.valign: VerticalAlignment = valign
        if isinstance(padding, int):
            padding = Padding(padding, padding, padding, padding)
        self.padding = padding
        self.clip = clipping
        self.scrollable = scrollable
        self.scroll_y: int = 0
        self.style = style

    def add(self, element: Text):
        # Attach child, set its parent and mark layout dirty
        element.parent = self
        if element.style in (None, DEFAULT_TEXT_STYLE) and self.style is not None:
            element.style = self.style
        self.children.append(element)
        # relpos = self.index_position_for(element)
        # if element.x is None:
        #     element.x = relpos[0] # type: ignore
        # if element.y is None:
        #     element.y = relpos[1] # type: ignore
        self.mark_dirty()
        return self.children.index(element)

    def remove(self, element: Text):
        try:
            index = self.children.index(element)
            self.children.remove(element)
            element.parent = None
            self.mark_dirty()
            return index
        except ValueError:
            return -1

    def index(self, element: Text):
        try:
            return self.children.index(element)
        except ValueError:
            return -1

    def layout(self):
        # Perform full layout for group and its children.
        # If not dirty, skip work.
        if not self.dirty:
            return None

        # absolute position for this group
        parent = self.parent
        if parent is not None and getattr(parent, "computed", None) is not None:
            assert parent.computed
            abs_x = parent.computed.x + int(self.x)
            abs_y = parent.computed.y + int(self.y)
        else:
            abs_x = int(self.x)
            abs_y = int(self.y)

        # ensure padding
        pad = self.padding if getattr(self, "padding", None) is not None else Padding(0, 0, 0, 0)

        # available content width (inside padding)
        avail_content_w: float | None = None
        if self.width is not None:
            avail_content_w = self.width - (pad.left + pad.right)

        children_comps: list[Computed] = []

        # First, set a temporary computed so children can calculate absolute positions
        self.computed = Computed(abs_x, abs_y, int(self.width) if self.width is not None else 0, 0)

        # Layout children to obtain their sizes
        for child in self.children:
            # let children observe parent.width via attributes
            child.layout()
            if child.computed is None:
                # fallback: measure minimal
                child.computed = Computed(abs_x + int(child.x), abs_y + int(child.y), int(child.width) if child.width is not None else 0, int(child.height) if child.height is not None else 0)
            assert child.computed
            children_comps.append(child.computed)

        # Position children and compute content size
        content_w = 0
        content_h = 0
        n = len(children_comps)

        if self.direction == "vertical":
            cursor_y = pad.top
            for idx, (child, comp) in enumerate(zip(self.children, children_comps)):
                # horizontal alignment
                if self.halign == "left":
                    child_x = abs_x + pad.left
                elif self.halign == "center":
                    if avail_content_w is not None:
                        child_x = abs_x + pad.left + int((avail_content_w - comp.width) / 2)
                    else:
                        child_x = abs_x + pad.left
                elif self.halign == "right":
                    if self.width is not None:
                        child_x = abs_x + int(self.width) - pad.right - comp.width
                    else:
                        child_x = abs_x + pad.left
                else:
                    child_x = abs_x + pad.left

                child_y = abs_y + cursor_y
                comp.x = int(child_x)
                comp.y = int(child_y)
                cursor_y += comp.height + (self.gap if idx < n - 1 else 0)

                content_w = max(content_w, comp.width)
                content_h = cursor_y - pad.top

        else:  # horizontal
            cursor_x = pad.left
            max_h = 0
            for idx, (child, comp) in enumerate(zip(self.children, children_comps)):
                # vertical alignment
                if self.valign == "top":
                    child_y = abs_y + pad.top
                elif self.valign == "center":
                    if getattr(self, "height", None) is not None:
                        assert self.height
                        child_y = abs_y + pad.top + int(((self.height - pad.top - pad.bottom) - comp.height) / 2)
                    else:
                        child_y = abs_y + pad.top
                elif self.valign == "bottom":
                    if getattr(self, "height", None) is not None:
                        assert self.height
                        child_y = abs_y + int(self.height) - pad.bottom - comp.height
                    else:
                        child_y = abs_y + pad.top
                else:
                    child_y = abs_y + pad.top

                child_x = abs_x + cursor_x
                comp.x = int(child_x)
                comp.y = int(child_y)
                cursor_x += comp.width + (self.gap if idx < n - 1 else 0)
                content_w = cursor_x - pad.left
                max_h = max(max_h, comp.height)
            content_h = max_h

        # finalize group computed size
        final_w = int(self.width) if self.width is not None else int(pad.left + content_w + pad.right)
        final_h = int(self.height) if self.height is not None else int(pad.top + content_h + pad.bottom)

        self.computed.width = final_w
        self.computed.height = final_h

        # If alignment depended on computed width and width was content-driven, reposition children
        if self.width is None and self.direction == "vertical":
            # recompute children x for center/right alignment
            if self.halign in ("center", "right"):
                avail_content_w = final_w - (pad.left + pad.right)
                for comp in children_comps:
                    if self.halign == "center":
                        comp.x = abs_x + pad.left + int((avail_content_w - comp.width) / 2)
                    else:
                        comp.x = abs_x + final_w - pad.right - comp.width

        # propagate layout into child groups (already called, but ensure nested groups have parent computed available)
        # for child in self.children:
        #     child.layout()

        # clear dirty
        self.dirty = False
        return None

    def index_position_for(self, element: Text):
        index = self.children.index(element)
        summed_x, summed_y = 0, 0
        # x = sum((a.measure().x + self.gap for a in self.children[:index+1]))
        for index, child in enumerate(self.children[:index]):
            measurement = child.measure()
            vgap = self.gap if self.direction == 'vertical' else 0
            hgap = self.gap if self.direction == 'horizontal' else 0
            summed_x += measurement.x + hgap
            summed_y += measurement.y + vgap
            # print(index, summed_x, summed_y, measurement.x, measurement.y)
        return summed_x, summed_y

    def update(self):
        """Update the group and propagate updates to children.

        If the group is dirty, run layout. Then call `update()` on all
        children so they can perform their own per-frame maintenance.
        """
        if self.dirty:
            self.layout()

        for child in self.children:
            child.update()

        return None

    @profile
    def draw(self):
        """Draw children (no background by default)."""
        if not self.visible:
            return None

        used_scissor = False
        if self.clip is False and self.computed is not None and (None, None) != (self.width, self.height):
            pad = self.padding if getattr(self, "padding", None) is not None else Padding(0, 0, 0, 0)
            sx = int(self.computed.x + pad.left)
            sy = int(self.computed.y + pad.top)
            sw = int(max(0, self.computed.width - (pad.left + pad.right)))
            sh = int(max(0, self.computed.height - (pad.top + pad.bottom)))
            begin_scissor_mode(sx, sy, sw, sh)
            used_scissor = True

        # children draw themselves using their computed geometry
        for child in self.children:
            if child.visible:
                child.draw()

        if used_scissor:
            # print("END SCISSOR")
            end_scissor_mode()

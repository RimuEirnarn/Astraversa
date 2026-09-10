from pathlib import Path

import pyray as pr

from astraversa.assets import Assets

def load_font(name: str, size: int, bold: bool = False, italic: bool = False):
    bd = '-bold' if bold else ''
    it = '-italic' if italic else ''
    name = f"{name}{bd}{it}.ttf"
    path = Assets.get(f"assets:///{name}")
    
    if path.exists():
        font = pr.load_font_ex(str(path), size, None, 0)
        pr.set_texture_filter(font.texture, pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
        return font
    
    own = Assets.get(f"astra-assets:///{name}")
    if own.exists():
        font = pr.load_font_ex(str(own), size, None, 0)
        pr.set_texture_filter(font.texture, pr.TextureFilter.TEXTURE_FILTER_BILINEAR)
        return font

class FontFamily:
    def __init__(self, font_name: str, font_size: int = 40):
        self.name = font_name
        self.size = font_size
    
    def load(self):
        # Load variants
        self.regular = load_font(self.name, self.size, bold=False, italic=False)
        self.bold = load_font(self.name, self.size, bold=True, italic=False)
        self.italic = load_font(self.name, self.size, bold=False, italic=True)
        self.bold_italic = load_font(self.name, self.size, bold=True, italic=True)

    def draw(self, text: str, position: pr.Vector2, size: float, spacing: float, color: pr.Color, bold: bool = False, italic: bool = False):
        """Draw text selecting the correct variant automatically."""
        if bold and italic:
            selected_font = self.bold_italic
        elif bold:
            selected_font = self.bold
        elif italic:
            selected_font = self.italic
        else:
            selected_font = self.regular

        assert selected_font
        pr.draw_text_ex(selected_font, text, position, size, spacing, color)

    def get_font(self, bold: bool, italic: bool):
        if bold and italic:
            assert self.bold_italic
            return self.bold_italic
        if bold:
            assert self.bold
            return self.bold
        if italic:
            assert self.italic
            return self.italic
        assert self.regular
        return self.regular

    def unload(self):
        """Unload GPU textures for all loaded variants."""
        if self.regular: pr.unload_font(self.regular)
        if self.bold: pr.unload_font(self.bold)
        if self.italic: pr.unload_font(self.italic)
        if self.bold_italic: pr.unload_font(self.bold_italic)

class FontManager:
    def __init__(self, names: list[str]) -> None:
        self.font_defs = names
        self.fonts: dict[str, FontFamily] = {}

    def load(self):
        for name in self.font_defs:
            ff = FontFamily(name)
            ff.load()
            self.fonts[name] = ff

    def unload(self):
        for name in self.font_defs:
            self.fonts[name].unload()
            del self.fonts[name]
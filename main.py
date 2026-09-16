# pylint: disable=no-member
from time import strftime
from typing import TypedDict
from toml import loads, dumps

import pyray as pr
from astraversa.storage import Storage
from astraversa.draw import draw_tiled_h, draw_tiled_v
from astraversa.frame_helper import is_on_frame
from astraversa.game import  BaseGame
from astraversa.runner import ModuleFlag, initialize, draw
from astraversa.tracer import EventData, Watchdog

type Resolution = tuple[int, int]

CONFIG_PATH = "transient/config.toml"
INACTIVE_PREFIX = "inactive_"
ACTIVE_PREFIX = ""
DEFAULT_CATCH = {
    "Endfield.exe",
    "StarRail.exe",
    "GenshinImpact.exe",
    "TheNOexistenceNofyouANDme.exe",
}

default_config: ConfigSchema = {
    "resolution": (1920, 1080),
    "max_fps": 60,
    "unfocused_fps": 20,
    "watch_processes": [],
    "bg_alpha": 91
}

class ConfigSchema(TypedDict):
    """Configuration"""
    resolution: Resolution
    max_fps: int
    unfocused_fps: int
    bg_alpha: int
    watch_processes: list[str]

def load_config(path: str) -> ConfigSchema:
    """Load config"""
    with open(path, encoding='utf-8') as f:
        return ConfigSchema(**loads(f.read()))

def write_config(path: str, data: ConfigSchema):
    """Write config"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(dumps(data))


class Game(BaseGame):
    """Game instance"""

    def __init__(self, config: ConfigSchema):
        self.config = config
        self.active_frames: dict[str, pr.Texture] = {}
        self.inactive_frames: dict[str, pr.Texture] = {}
        self.frames = self.active_frames
        self.bg_alpha = 100
        if "bg_alpha" in self.config:
            self.bg_alpha = min(max(self.config["bg_alpha"], 0), 100)
        self.scale = 2
        self.corner = 8 * self.scale
        self.hline_w = 4 * self.scale
        self.hline_h = 2 * self.scale
        self.vline_w = 2 * self.scale
        self.vline_h = 4 * self.scale
        self.width, self.height = config["resolution"]
        self.dragging = False
        self.drag_anchor = pr.Vector2(0, 0)
        self.clocked_down = False
        self.active_process: EventData | None = None
        self.should_focused: bool = False
        self.watch_processes = DEFAULT_CATCH
        if "watch_processes" in self.config:
            self.watch_processes.update(self.config["watch_processes"])
        self.watchdog: Watchdog

    def catch_process(self, data: EventData):
        self.active_process = data
        self.should_focused = True

    def load(self):
        """load"""

        for key, path in (
            ("frame_tl", "astra-assets:///{prefix}window_topleft.png"),
            ("frame_tr", "astra-assets:///{prefix}window_topright.png"),
            ("frame_bl", "astra-assets:///{prefix}window_botleft.png"),
            ("frame_br", "astra-assets:///{prefix}window_botright.png"),
            ("frame_v", "astra-assets:///{prefix}window_vertical.png"),
            ("frame_h", "astra-assets:///{prefix}window_horizontal.png"),
        ):
            abspath_active = Storage.get(path.format(prefix=ACTIVE_PREFIX))
            abspath_inactive = Storage.get(path.format(prefix=INACTIVE_PREFIX))
            active_texture = pr.load_texture(str(abspath_active))
            pr.set_texture_filter(active_texture, pr.TextureFilter.TEXTURE_FILTER_POINT)
            self.active_frames[key] = active_texture

            inactive_texture = pr.load_texture(str(abspath_inactive))
            pr.set_texture_filter(
                inactive_texture, pr.TextureFilter.TEXTURE_FILTER_POINT
            )
            self.inactive_frames[key] = inactive_texture

    def _apply_alpha_controls(self):
        """Handle alpha adjustments only on a control-modified key press."""
        if not pr.is_key_down(pr.KeyboardKey.KEY_LEFT_CONTROL):
            return

        if pr.is_key_pressed(pr.KeyboardKey.KEY_EQUAL):
            self.bg_alpha = min(100, round(self.bg_alpha + 0.5, 1))
        elif pr.is_key_pressed(pr.KeyboardKey.KEY_MINUS):
            self.bg_alpha = max(0, round(self.bg_alpha - 0.5, 1))
        elif pr.is_key_pressed(pr.KeyboardKey.KEY_LEFT_BRACKET):
            self.bg_alpha = 0
        elif pr.is_key_pressed(pr.KeyboardKey.KEY_RIGHT_BRACKET):
            self.bg_alpha = 100

    def _sync_window_state(self):
        """Reduce repeated target-FPS churn by only switching when the state changes."""
        window_unfocused = (
            pr.is_window_hidden()
            or pr.is_window_minimized()
            or not pr.is_window_focused()
        )

        if window_unfocused and not self.clocked_down:
            self.clocked_down = True
            self.frames = self.inactive_frames
            pr.set_target_fps(self.config["unfocused_fps"])
            return

        if not window_unfocused and self.clocked_down:
            self.clocked_down = False
            self.frames = self.active_frames
            pr.set_target_fps(self.config["max_fps"])

    def _drag_anchoring(self):
        mouse = pr.get_mouse_position()
        drag_anchor_is_empty = self.drag_anchor.x == 0 and self.drag_anchor.y == 0
        if pr.is_mouse_button_pressed(pr.MouseButton.MOUSE_BUTTON_LEFT) and is_on_frame(
            mouse.x,
            mouse.y,
            self.corner,
            self.vline_w,
            self.hline_h,
            self.width,
            self.height,
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

    def _process_watchdog(self):
        if self.watchdog.has_catched():
            self.watchdog.consume(self.catch_process)

        if not self.active_process:
            return

        if not self.active_process.is_running():
            self.should_focused = False
            self.active_process = None
            return

        if self.should_focused:
            pr.set_window_focused()
            self.should_focused = False

    def update(self):
        """Update"""

        self._drag_anchoring()
        self._apply_alpha_controls()
        self._sync_window_state()
        self._process_watchdog()

    def draw(self):
        """Draw"""

        self.draw_background()
        self.draw_frame()
        self.draw_active_process()
        self.draw_time()
        # pr.draw_fps(2 + self.vline_w, 2 + self.hline_h)

    def draw_time(self):
        timed = strftime("%Y/%m/%d %X")
        pr.draw_text(timed, int(self.hline_h) + 4, int(self.vline_w + 64), 20, (0xFF, 0xC5, 0xD3, 0xFF))

    def draw_active_process(self):
        name = "(unset)" if not self.active_process else self.active_process.name
        text = f"Active Process: {name}"
        pr.draw_text(
            text,
            int(self.hline_h) + 4,
            int(self.vline_w + 44),
            20,
            (0xFF, 0xC5, 0xD3, 0xFF)
        )

    def draw_background(self):
        width, height = self.config["resolution"]
        alpha_multiplier = 0 + (self.bg_alpha / 100)
        alpha = (
            255
            if self.bg_alpha == 100
            else max(min(int(255 * alpha_multiplier), 255), 0)
        )
        background = (0, 0, 0, alpha)
        pr.clear_background((0, 0, 0, 0))
        pr.draw_rectangle(
            0 + self.vline_w,
            0 + self.hline_h,
            width - self.vline_w * 2,
            height - self.hline_h * 2,
            background,
        )
        text = f"BG Alpha: {self.bg_alpha:.2f}% ({255 * alpha_multiplier = :.2f})"
        text_size = pr.measure_text_ex(pr.get_font_default(), text, 20, 2)

        pr.draw_text(
            text,
            int(self.hline_h) + 4,
            int(self.vline_w) + 24,
            20,
            (0xFF, 0xC5, 0xD3, 0xFF),
        )

    def draw_frame(self):
        """Frame"""
        hline = self.frames["frame_h"]
        vline = self.frames["frame_v"]
        tl = self.frames["frame_tl"]
        tr = self.frames["frame_tr"]
        bl = self.frames["frame_bl"]
        br = self.frames["frame_br"]
        w, h = self.width, self.height
        scale = self.scale
        cw = self.corner  # scaled corner width/height = 32
        hline_h = self.hline_h
        vline_w = self.vline_w

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
        inner_w = w - cw * 2
        draw_tiled_h(hline, cw, 0, inner_w, scale)  # top
        draw_tiled_h(hline, cw, h - hline_h, inner_w, scale)  # bottom

        # ── Vertical edges (left and right) ──────────────────────
        inner_h = h - cw * 2
        draw_tiled_v(vline, 0, cw, inner_h, scale)  # left
        draw_tiled_v(vline, w - vline_w, cw, inner_h, scale)  # right

    def run(self):
        """Run"""
        try:
            self.watchdog = Watchdog.spawn(self.watch_processes)
            while not pr.window_should_close():
                self.update()
                self.pre_draw()
                with draw():
                    self.draw()
        finally:
            self.unload()

    def unload(self):
        """Unload"""
        for texture in self.active_frames.values():
            pr.unload_texture(texture)


def main():
    try:
        config = load_config(CONFIG_PATH)
    except FileNotFoundError:
        config = default_config
        write_config(CONFIG_PATH, config)


    with initialize(
        config['resolution'][0],
        config['resolution'][1],
        "Desktop Jail",
        (ModuleFlag.audio,
                ModuleFlag.headless,
                ModuleFlag.transparent,
                ModuleFlag.msaa_4x,
                ModuleFlag.always_run,
                ModuleFlag.maximized,
                ModuleFlag.unfocused,
                ModuleFlag.highdpi
        )
    ):
        pr.set_target_fps(config['max_fps'])
        game = Game(config)
        game.start()


if __name__ == "__main__":
    # if system_name() == "Windows":
    #     if not is_admin():
    #         print("Not an administrator.")
    #         exit(1)
    main()

# pylint: disable=all
from typing import Callable, TypeVar
from contextlib import contextmanager
from functools import wraps
from enum import IntEnum, auto
from atexit import register
import pyray as pr

TCallable = TypeVar("TCallable")


class ModuleFlag(IntEnum):
    audio = auto()
    physics = auto()
    headless = auto()
    transparent = auto()
    msaa_4x = auto()
    always_run = auto()
    vsync = auto()
    borderless = auto()
    fullscreen = auto()
    highdpi = auto()
    maximized = auto()
    minimized = auto()
    passthrough = auto()
    resizable = auto()
    topmost = auto()
    unfocused = auto()


WINDOW_FLAG_BY_MODULE: dict[ModuleFlag, int] = {
    ModuleFlag.headless: pr.ConfigFlags.FLAG_WINDOW_UNDECORATED,
    ModuleFlag.transparent: pr.ConfigFlags.FLAG_WINDOW_TRANSPARENT,
    ModuleFlag.msaa_4x: pr.ConfigFlags.FLAG_MSAA_4X_HINT,
    ModuleFlag.always_run: pr.ConfigFlags.FLAG_WINDOW_ALWAYS_RUN,
    ModuleFlag.vsync: pr.ConfigFlags.FLAG_VSYNC_HINT,
    ModuleFlag.borderless: pr.ConfigFlags.FLAG_BORDERLESS_WINDOWED_MODE,
    ModuleFlag.fullscreen: pr.ConfigFlags.FLAG_FULLSCREEN_MODE,
    ModuleFlag.highdpi: pr.ConfigFlags.FLAG_WINDOW_HIGHDPI,
    ModuleFlag.maximized: pr.ConfigFlags.FLAG_WINDOW_MAXIMIZED,
    ModuleFlag.minimized: pr.ConfigFlags.FLAG_WINDOW_MINIMIZED,
    ModuleFlag.passthrough: pr.ConfigFlags.FLAG_WINDOW_MOUSE_PASSTHROUGH,
    ModuleFlag.resizable: pr.ConfigFlags.FLAG_WINDOW_RESIZABLE,
    ModuleFlag.topmost: pr.ConfigFlags.FLAG_WINDOW_TOPMOST,
    ModuleFlag.unfocused: pr.ConfigFlags.FLAG_WINDOW_UNFOCUSED,
}


def window_flag_for_module(module: ModuleFlag) -> int | None:
    return WINDOW_FLAG_BY_MODULE.get(module)


@contextmanager
def draw():
    try:
        yield pr.begin_drawing()
    finally:
        pr.end_drawing()


def mainloop(fn: Callable[[], None]):
    while not pr.window_should_close():
        with draw():
            fn()
    pr.close_window()


@contextmanager
def initialize(width: int, height: int, title: str, modules: tuple[ModuleFlag, ...]):
    flag: int = 0
    for module in modules:
        if module == ModuleFlag.audio:
            pr.init_audio_device()
            register(pr.close_audio_device)
            continue

        window_flag = window_flag_for_module(module)
        if window_flag is not None:
            flag |= int(window_flag)

    if flag:
        pr.set_config_flags(flag)

    pr.init_window(width, height, title)
    try:
        yield []
    finally:
        pr.close_window()

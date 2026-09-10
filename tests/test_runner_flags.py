import pyray as pr

from astraversa.runner import ModuleFlag, window_flag_for_module


def test_window_flag_for_module_maps_new_window_flags():
    expected = {
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

    for module, flag in expected.items():
        assert window_flag_for_module(module) == flag

    assert window_flag_for_module(ModuleFlag.audio) is None
    assert window_flag_for_module(ModuleFlag.physics) is None

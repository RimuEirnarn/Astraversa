import pyray as pr

from astraversa.game import BaseGame as Game


# def make_game():
#     return Game({
#         "resolution": (100, 100),
#         "max_fps": 60,
#         "unfocused_fps": 20,
#         "bg_alpha": 50,
#         "watch_processes": []
#     })


# def test_apply_alpha_controls_uses_key_press_events(monkeypatch):
#     game = make_game()

#     monkeypatch.setattr(pr, "is_key_pressed", lambda key: key == pr.KeyboardKey.KEY_EQUAL)
#     monkeypatch.setattr(pr, "is_key_down", lambda key: key == pr.KeyboardKey.KEY_LEFT_CONTROL)

#     game._apply_alpha_controls()

#     assert game.bg_alpha == 50.5


# def test_sync_window_state_only_updates_fps_on_transitions(monkeypatch):
#     game = make_game()
#     calls = []

#     monkeypatch.setattr(pr, "is_window_hidden", lambda: False)
#     monkeypatch.setattr(pr, "is_window_minimized", lambda: False)
#     monkeypatch.setattr(pr, "is_window_focused", lambda: False)
#     monkeypatch.setattr(pr, "set_target_fps", lambda fps: calls.append(fps))

#     game._sync_window_state()
#     assert calls == [20]

#     game._sync_window_state()
#     assert calls == [20]

#     monkeypatch.setattr(pr, "is_window_focused", lambda: True)
#     game._sync_window_state()
#     assert calls == [20, 60]

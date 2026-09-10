from pathlib import Path

from astraversa.assets import Assets

def test_assets_loader():
    assert str(Path("src/astraversa/assets/inactive_window_botleft.png")) in str(Assets.get("astra-assets:///inactive_window_botleft.png"))
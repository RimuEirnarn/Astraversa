from pathlib import Path

from astraversa.storage import Storage

def test_assets_loader():
    assert str(Path("src/astraversa/assets/inactive_window_botleft.png")) in str(Storage.get("astra-assets:///inactive_window_botleft.png"))
"""Config"""

from typing import TypedDict
from toml import loads, dumps

type Resolution = tuple[int, int]

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

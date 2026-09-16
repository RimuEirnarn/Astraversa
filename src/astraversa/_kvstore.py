"""KVStore"""

from typing import Any, Protocol

null = object()

class KVBackend(Protocol):
    """KVBackend"""
    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"

    def read(self, key: str, default: Any = None) -> Any:
        """Read data from backend"""
    
    def write(self, key: str, value: Any):
        """Write data to backend"""

class InMemoryKVBackend(KVBackend):
    """In Memory KVBackend"""
    
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
    
    def read(self, key: str, default: Any = null) -> Any:
        if default is null:
            return self._data[key]
        return self._data.get(key, default)

    def write(self, key: str, value: Any):
        self._data[key] = value
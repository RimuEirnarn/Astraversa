"""Profiler"""
from typing import Callable

try:
    from line_profiler import profile # type: ignore
except ImportError:
    def profile(function: Callable[[], None]):
        """No op"""
        return function

__all__ = ["profile"]
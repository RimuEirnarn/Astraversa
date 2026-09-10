"""Typings"""

from typing import Literal

type Pos2D = tuple[int, int]
type Size2D = tuple[int, int]
type HorizontalAlignment = Literal["left"] | Literal["center"] | Literal["right"]
type VerticalAlignment = Literal['top'] | Literal['center'] | Literal['bottom']
type LayoutDirection = Literal["vertical"] | Literal['horizontal']


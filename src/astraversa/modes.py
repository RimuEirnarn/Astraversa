"""Modes"""
from pyray import (RenderTexture, begin_texture_mode, end_texture_mode, begin_blend_mode,
                   begin_mode_2d, begin_mode_3d, end_blend_mode, end_mode_2d, end_mode_3d,
                   begin_scissor_mode, end_scissor_mode,
                   Camera2D, Camera3D)

class RenderTextureMode:
    def __init__(self, texture: RenderTexture) -> None:
        self.texture: RenderTexture = texture

    def __enter__(self):
        begin_texture_mode(self.texture)
    
    def __exit__(self, exc_type, exc, tb):
        end_texture_mode()

class Mode2D:
    def __init__(self, camera: Camera2D) -> None:
        self.camera: Camera2D = camera

    def __enter__(self):
        begin_mode_2d(self.camera)
    
    def __exit__(self, exc_type, exc, tb):
        end_mode_2d()

class Mode3D:
    def __init__(self, camera: Camera3D) -> None:
        self.camera: Camera3D = camera

    def __enter__(self):
        begin_mode_3d(self.camera)
    
    def __exit__(self, exc_type, exc, tb):
        end_mode_3d()

class BlendMode:
    def __init__(self, blending_mode: int) -> None:
        self.blending_mode = blending_mode

    def __enter__(self):
        begin_blend_mode(self.blending_mode)
    
    def __exit__(self, exc_type, exc, tb):
        end_blend_mode()

class ScissorMode:
    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    def __enter__(self):
        begin_scissor_mode(self.x, self.y, self.width, self.height)
    
    def __exit__(self, exc_type, exc, tb):
        end_scissor_mode()

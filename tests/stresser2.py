from dataclasses import dataclass
from random import randint

import numpy as np

from pyray import (
    Camera3D, Image, Texture, Mesh, Material, Matrix, Vector3, begin_mode_3d, end_mode_3d, ffi, CameraProjection,
    load_image, draw_fps, load_texture_from_image,
    clear_background, rl_disable_backface_culling, window_should_close, unload_texture, unload_image,
    gen_mesh_plane, load_material_default, set_material_texture, rl_check_errors,
    draw_mesh_instanced, MaterialMapIndex,
)
from astraversa import BaseGame, initialize
from astraversa.runner import draw
from astraversa.storage import Storage


class Game(BaseGame):
    width: int = 1280
    height: int = 920
    iterations = 100_000

    def __init__(self) -> None:
        self._image: Image
        self._imagetexture: Texture
        self._mesh: Mesh
        self._material: Material
        self._positions: np.ndarray  # (N, 2) float32
        self._camera: Camera3D

    def load(self):
        self._image = load_image(str(Storage.get("astra-assets://obj3.png")))
        self._imagetexture = load_texture_from_image(self._image)
        # set up once in load(), not per-frame
        self._camera = Camera3D(
            Vector3(self.width / 2, self.height / 2, 1.0),  # position - guess, needs tuning
            Vector3(self.width / 2, self.height / 2, 0.0),      # target
            Vector3(0.0, 1.0, 0.0),                              # up
            45.0,
            CameraProjection.CAMERA_PERSPECTIVE,
        )

        # A single quad mesh, reused for every instance.
        self._mesh = gen_mesh_plane(1.0, 1.0, 1, 1)

        self._material = load_material_default()
        set_material_texture(self._material, MaterialMapIndex.MATERIAL_MAP_ALBEDO, self._imagetexture)

        # NOTE: raylib's default plane is on the XZ plane (3D), not screen-space XY.
        # For a 2D sprite-instancing use case you may need a custom mesh/shader
        # instead of gen_mesh_plane + a 3D camera. Flag this to check against
        # what Astraversa's `draw()` context sets up (ortho vs perspective).
        self._positions = np.column_stack([
            np.random.randint(-self.width, self.width, size=self.iterations),
            np.random.randint(-self.height, self.height, size=self.iterations),
        ]).astype(np.float32)

    def unload(self):
        unload_texture(self._imagetexture)
        unload_image(self._image)

    def _build_transforms(self):
        # self._positions[:, 0] = np.random.randint(20, self.width, size=self.iterations)
        # self._positions[:, 1] = np.random.randint(20, self.height, size=self.iterations)a
        self._positions[:, 0] = self.width // 2
        self._positions[:, 1] = self.height // 2

        n = self.iterations
        transforms = np.zeros((n, 4, 4), dtype=np.float32)
        transforms[:, 0, 0] = 1.0
        transforms[:, 1, 1] = 1.0
        transforms[:, 2, 2] = 1.0
        transforms[:, 3, 3] = 1.0
        transforms[:, 3, 0] = self._positions[:, 0]
        transforms[:, 3, 1] = self._positions[:, 1]

        transforms = np.ascontiguousarray(transforms)  # cffi needs a contiguous buffer

        # Cast a raw pointer into the numpy buffer as a Matrix*, avoiding any
        # per-instance struct construction in Python.
        matrix_ptr = ffi.cast("struct Matrix *", ffi.from_buffer(transforms))
        return matrix_ptr, transforms  # keep `transforms` alive — from_buffer doesn't own it


    def instanced_run(self):
        try:
            while not window_should_close():
                with draw():
                    clear_background((0, 0, 0, 0))
                    draw_fps(5, 5)
                    matrix_ptr, _keepalive = self._build_transforms()
                    begin_mode_3d(self._camera)
                    # rl_disable_backface_culling()
                    draw_mesh_instanced(self._mesh, self._material, matrix_ptr, self.iterations)
                    rl_check_errors()
                    end_mode_3d()
        finally:
            self.unload()


def main():
    with initialize(Game.width, Game.height, "instanced test", ()):
        game = Game()
        game.load()
        game.instanced_run()


if __name__ == '__main__':
    main()
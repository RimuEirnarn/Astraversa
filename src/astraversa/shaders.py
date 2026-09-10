from pathlib import Path
import typing
import pyray as rl
from cffi import FFI

ffi = FFI()

class UniformSpec:
    __slots__ = ("rl_enum", "ffi_type", "element_type", "count")

    def __init__(self, rl_enum: int, ffi_type: str, element_type: type, count: int):
        self.rl_enum = rl_enum
        self.ffi_type = ffi_type
        self.element_type = element_type
        self.count = count


def inspect_annotation(annotation: typing.Any) -> UniformSpec:
    """Inspects a Python type annotation and maps it directly to Raylib dynamic uniform memory specs."""
    origin = typing.get_origin(annotation) or annotation
    args = typing.get_args(annotation)

    # 1. Scalar Float
    if origin is float:
        return UniformSpec(rl.ShaderUniformDataType.SHADER_UNIFORM_FLOAT, "float *", float, 1)

    # 2. Scalar Int / Sampler2D
    if origin is int:
        return UniformSpec(rl.ShaderUniformDataType.SHADER_UNIFORM_INT, "int *", int, 1)

    # 3. Fixed-length Tuples or Lists: tuple[float, ...], list[float]
    if origin in (tuple, list):
        if not args:
            raise TypeError("Sequence annotations for uniforms must specify element types (e.g., tuple[float, float]).")

        elem_type = args[0]
        count = len(args)

        # Vector of Floats (vec2, vec3, vec4)
        if elem_type is float:
            vec_map = {
                2: (rl.ShaderUniformDataType.SHADER_UNIFORM_VEC2, "float[2]"),
                3: (rl.ShaderUniformDataType.SHADER_UNIFORM_VEC3, "float[3]"),
                4: (rl.ShaderUniformDataType.SHADER_UNIFORM_VEC4, "float[4]"),
                # 16: (rl.ShaderUniformDataType.SHADER_UNIFORM_MAT4, "float[16]"),
            }
            if count in vec_map:
                rl_enum, ffi_str = vec_map[count]
                return UniformSpec(rl_enum, ffi_str, float, count)

        # Vector of Ints (ivec2, ivec3, ivec4)
        elif elem_type is int:
            ivec_map = {
                2: (rl.ShaderUniformDataType.SHADER_UNIFORM_IVEC2, "int[2]"),
                3: (rl.ShaderUniformDataType.SHADER_UNIFORM_IVEC3, "int[3]"),
                4: (rl.ShaderUniformDataType.SHADER_UNIFORM_IVEC4, "int[4]"),
            }
            if count in ivec_map:
                rl_enum, ffi_str = ivec_map[count]
                return UniformSpec(rl_enum, ffi_str, int, count)

    raise TypeError(f"Cannot map annotation '{annotation}' to a valid Raylib uniform type.")

class ShaderObject:
    _vs_path: str = ""
    _fs_path: str = ""

    def __init__(self):
        # Raylib context must be active
        if self._vs_path and self._fs_path:
            self.shader = rl.load_shader(self._vs_path, self._fs_path)
        elif self._fs_path:
            self.shader = rl.load_shader("", self._fs_path) # type: ignore
        elif self._vs_path:
            self.shader = rl.load_shader(self._vs_path, "") # type: ignore
        else:
            raise ValueError("No shader path provided.")

        self._uniform_specs: dict[str, UniformSpec] = {}
        self._locations: dict[str, int] = {}
        
        self._inspect_and_cache()

    def _inspect_and_cache(self):
        """Inspect annotations structurally and cache GLSL uniform locations."""
        hints = typing.get_type_hints(self.__class__)

        for var_name, type_hint in hints.items():
            if var_name.startswith("_"):
                continue
            
            # Inspect structural validity
            spec = inspect_annotation(type_hint)
            self._uniform_specs[var_name] = spec

            # Cache location ID from driver
            loc = rl.get_shader_location(self.shader, var_name)
            self._locations[var_name] = loc

    def set(self, **kwargs):
        """Perform verified CFFI conversion and update Raylib uniforms."""
        for name, value in kwargs.items():
            if name not in self._uniform_specs:
                raise KeyError(f"'{name}' is not an annotated uniform on {self.__class__.__name__}")

            loc = self._locations[name]
            if loc == -1:
                # Uniform stripped by GLSL compiler or non-existent in GLSL source
                continue

            spec = self._uniform_specs[name]

            # Convert Python types into CFFI buffer pointers
            if spec.count == 1:
                cdata = ffi.new(spec.ffi_type, spec.element_type(value))
            else:
                cdata = ffi.new(spec.ffi_type, [spec.element_type(v) for v in value])

            rl.set_shader_value(self.shader, loc, cdata, spec.rl_enum)

    def unload(self):
        rl.unload_shader(self.shader)
    
    def __setattr__(self, name: str, value: typing.Any) -> None:
        if name.startswith("_") or name in {"shader"}:
            object.__setattr__(self, name, value)
            return

        uniform_specs = self.__dict__.get("_uniform_specs")
        if uniform_specs is None:
            object.__setattr__(self, name, value)
            return

        if name not in uniform_specs:
            raise NameError(f"{name} is not found in the shader.")

        self.set(**{name: value})
    
    def __enter__(self):
        rl.begin_shader_mode(self.shader)

    def __exit__(self, exc_type, exc, tb):
        rl.end_shader_mode()

def define(path: str | Path, ftype: str = ""):
    """Decorator to attach file paths to ShaderObject classes."""
    if isinstance(path, Path):
        path = str(path)
    def decorator(cls):
        is_fs = ftype == "fs" or path.endswith((".fs", ".frag"))
        is_vs = ftype == "vs" or path.endswith((".vs", ".vert"))
        
        if is_fs:
            cls._fs_path = path
        elif is_vs:
            cls._vs_path = path
        else:
            raise ValueError("Could not determine shader type from file extension.")
            
        return cls
    return decorator
# Shader Manager

Basic syntax:

```python
from props.shaders import ShaderObject, define

@define("resources/shaders.fs") # default check by extension, otherwise, ftype="fs" | "vs"
class ShaderOutline01(ShaderObject):
    argument: float # translates to: ffi.new("float *", x)
    argument0: tuple[float, float] # translates to: ff.new("float[2]", (x, y))

variable = 0.0
variabel0 = 1.0
var = 0.1
ShaderOutline01.set(argument=var, argument0=(variable, variable0))
```

from datetime import datetime
from typing import get_type_hints, get_origin, get_args
from copy import deepcopy

from astraversa._kvstore import KVBackend, InMemoryKVBackend
from astraversa.profiler import profile
JSON_SAFE = (str, int, float, bool, list, dict, type(None))

def cast(value, typ):
    # for tuple element types that are themselves JSON-native (int, str, float),
    # this can just be a light coercion/validation step
    if not isinstance(value, typ):
        raise TypeError(f"expected {typ}, got {type(value)}")
    return value

class KVStore:
    _codecs: dict = {}  # populated once, class-level, shared unless overridden

    @classmethod
    def register_codec(cls, origin, encode, decode):
        cls._codecs[origin] = (encode, decode)

    def _encode(self, value, typ):
        origin = get_origin(typ) or typ
        if origin in type(self)._codecs:
            enc, _ = type(self)._codecs[origin]
            return enc(value, typ)
        return value

    def _decode(self, raw, typ):
        origin = get_origin(typ) or typ
        if origin in type(self)._codecs:
            _, dec = type(self)._codecs[origin]
            return dec(raw, typ)
        return raw

    def __init__(self, backend: KVBackend):
        object.__setattr__(self, "_backend", backend)  # bypass our own __setattr__

    def __repr__(self) -> str:
        return f"<{type(self).__name__} backend={self._backend!r}>"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        hints = get_type_hints(cls)
        defaults = {}
        for key, typ in hints.items():
            origin = get_origin(typ) or typ
            if origin not in JSON_SAFE and origin not in cls._codecs:
                raise TypeError(f"{cls.__name__}.{key}: no codec registered for {typ}")
            if key in cls.__dict__:
                defaults[key] = deepcopy(cls.__dict__[key])
                delattr(cls, key)  # remove so it can't shadow __getattr__
        cls._schema = hints
        cls._defaults = defaults

    @profile
    def __getattr__(self, key):
        # only called when normal attribute lookup fails —
        # _backend/_schema found via normal lookup, never land here
        schema = getattr(type(self), "_schema", None)
        defaults = getattr(type(self), "_defaults", None)
        if schema is not None and key not in schema:
            raise AttributeError(f"{key!r} not declared on {type(self).__name__}")
        default = defaults.get(key) if defaults else None
        #print("read:", key, f"(default: {repr(default)})")
        data = self._backend.read(key, default=default)
        if schema is not None:
            typ = schema[key]
        else:
            typ = type(data)

        return self._decode(data, typ)

    @profile
    def __setattr__(self, key, value):
        schema = getattr(type(self), "_schema", None)
        typ = type(value)
        #print(f"set : {key} = {value!r}")
        if schema is not None:
            if key not in schema:
                raise AttributeError(f"{key!r} not declared on {type(self).__name__}")
            typ = schema[key]
            origin = get_origin(typ) or typ
            if not isinstance(value, origin):
                raise TypeError(f"{key!r} expects {typ}, got {type(value)}")
            # optional: also validate element types for parameterized generics
            if get_origin(typ) is tuple:
                args = get_args(typ)
                if len(value) != len(args) or not all(isinstance(v, t) for v, t in zip(value, args)):
                    raise TypeError(f"{key!r} expects {typ}, got {value!r}")
        encoded_val = self._encode(value, typ)
        self._backend.write(key, encoded_val)  # never hits object.__dict__ at all

def register_common_codec(typ: type[KVStore] = KVStore):
    typ.register_codec(
        tuple,
        encode=lambda v, typ: list(v),
        decode=lambda raw, typ: tuple(
            cast(v, t) for v, t in zip(raw, get_args(typ))
        ),
    )
    typ.register_codec(
        datetime,
        encode=lambda v, typ: v.isoformat(),
        decode=lambda raw, typ: datetime.fromisoformat(raw),
    )

register_common_codec()

__all__ = ["KVStore", "InMemoryKVBackend", "register_common_codec"]

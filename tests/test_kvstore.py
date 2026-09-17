from datetime import datetime

import pytest

from astraversa.kvstore import InMemoryKVBackend, KVStore, register_common_codec
from astraversa.db import SQLiteBackend, CachedSQLiteBackend
from astraversa.profiler import profile

test_array = []

class TypedKVStore(KVStore):
    key0: str = "default_value"
    key1: int = 0
    key2: float = 1.0
    key3: list = test_array

class AdvKVStore(KVStore):
    key0: str = "default_value"
    last_used: datetime = datetime(1970, 1, 1)
    resolution: tuple[int, int] = (1080, 800)

register_common_codec(AdvKVStore)

def test_defaultkvstore():
    store = KVStore(InMemoryKVBackend())
    store.key = 0
    assert store.key == 0, "Not as initialized"

def test_sqlkvstore():
    store = KVStore(SQLiteBackend())
    store.key = 0
    assert store.key == 0, "Not as initialized"

def test_arbitrary_sqlkvstore():
    store = KVStore(SQLiteBackend())
    data = {'abc': 'def'}
    store.key = data
    assert store.key == data, "Not as initialized"

def test_typedkv():
    store = TypedKVStore(SQLiteBackend())
    store.key0 = "something"
    
    assert store.key0 != "default_value", "Does not write to backend"
    assert store.key1 == 0, "What???"
    assert isinstance(store.key2, float), "Not as typed"
    assert store.key3 == [], "Not null"
    assert not store.key3 is test_array, "hmm..."
    
    store.key3 = ["0"]
    store.key3 = ["a"]
    assert store.key3 == ['a'], "First assert"
    assert store.key3 != test_array and not store.key3 is test_array, "Hmm..."

def test_cachedkv():
    membackend = CachedSQLiteBackend()
    memstore = KVStore(membackend)
    backend = CachedSQLiteBackend("transient/cached.kvstore.db")
    store = KVStore(backend)
    memstore.key0 = "something"
    store.key0 = "something"

    assert memstore.key0 == "something", "Not stored"
    assert SQLiteBackend.read(membackend, "key0", None) is None, "Should not immediately cached"
    assert store.key0 == "something", "Not stored"
    backend.save()
    assert SQLiteBackend.read(backend, "key0", None) is not None, "Should have written to DB"

def test_advancedkv():
    store = AdvKVStore(SQLiteBackend())
    now = datetime.now()
    store.last_used = now
    store.resolution = (1920, 1080)
    
    assert store.last_used == now, "Invalid ref"
    assert store.resolution == (1920, 1080), "Invalid ref"

    with pytest.raises(TypeError):
        store.last_used = "a" # type: ignore
    with pytest.raises(TypeError):
        store.resolution = ("1920", 1080, 1) # type: ignore
    assert store.resolution != ("1920", 1080, 1)

def setup_vars(store: KVStore):
    store.key0 = "something"

@profile
def perf_check():
    memstore = KVStore(InMemoryKVBackend())
    sqlstore = KVStore(SQLiteBackend())
    csqlstore = KVStore(CachedSQLiteBackend())

    typedmemstore = TypedKVStore(InMemoryKVBackend())
    typedsqlstore = TypedKVStore(SQLiteBackend())
    typedcsqlstore = TypedKVStore(CachedSQLiteBackend())

    advmemstore = AdvKVStore(InMemoryKVBackend())
    advsqlstore = AdvKVStore(SQLiteBackend())
    advcsqlstore = AdvKVStore(CachedSQLiteBackend())
    now = datetime.now()

    # -- WRITE
    for _ in range(10_000):
        # setup_vars(memstore)
        # setup_vars(sqlstore)
        # setup_vars(csqlstore)
        
        # setup_vars(typedmemstore)
        # setup_vars(typedsqlstore)
        # setup_vars(typedcsqlstore)
        
        advmemstore.resolution = (1920, 1080)
        # advmemstore.last_used = now
        # advsqlstore.last_used = now
        # advcsqlstore.last_used = now


    # -- READ
    for _ in range(10_000):
        # assert memstore.key0
        # assert sqlstore.key0
        # assert csqlstore.key0
        
        # assert typedmemstore.key0
        # assert typedsqlstore.key0
        # assert typedcsqlstore.key0
        
        assert advmemstore.resolution
        # assert advmemstore.last_used
        # assert advsqlstore.last_used
        # assert advcsqlstore.last_used

if __name__ == "__main__":
    perf_check()
import json
from sqlite3 import Connection, PARSE_COLNAMES, PARSE_DECLTYPES
from typing import Any
from re import compile as re_compile

from astraversa._kvstore import KVBackend
from astraversa.runner import atunload

names = re_compile("^[A-Za-z0-9_]+$")
null = object()

class SQLiteBackend(KVBackend):
    def __init__(self, path: str | None = None, table: str = "settings", immediate=True) -> None:
        self._db = Connection(path or ":memory:")
        if not names.match(table):
            raise ValueError(f"Check for {table!r} characters; not valid table name")
        self._table = table
        if not path or immediate:
            self.init()

    def init(self):
        with self._db:
            self._db.executescript(f"""\
create table if not exists {self._table} (
    key text unique on conflict replace,
    value blob not null
);""")
            atunload(self.atunload)
    
    def atunload(self):
        self._db.close()

    def read(self, key: str, default: Any = null) -> Any:
        db, table = self._db, self._table
        data = db.execute(f"select value from {table} where key=?", (key,)).fetchone()
        # print(f"{key = }\n{default = }\n{data = }")
        if not data:
            if default is not null:
                return default
            raise KeyError(key)
        #print(data[0])
        return json.loads(data[0])

    def write(self, key: str, value: Any):
        db, table = self._db, self._table
        with db:
            db.execute(f"insert into {table} values (?, ?)", (key, json.dumps(value)))

class CachedSQLiteBackend(SQLiteBackend):
    def __init__(self, path: str | None = None, table: str = "settings", immediate=True) -> None:
        super().__init__(path, table, immediate)
        # tuple[value, dirty?]
        self._memo: dict[str, tuple[Any, bool]] = {}

    def invalidate(self, key: str | None = None):
        """Invalidate all caches (or specified by key)"""
        if key is None:
            self._memo.clear()
            return
        del self._memo[key]

    def atunload(self):
        self.save()
        self._db.close()

    def save(self):
        db, table = self._db, self._table
        mapped = [(key, json.dumps(data)) for key, (data, dirty) in self._memo.items() if dirty]
        if not mapped:
            return
        with db:
            db.executemany(f"insert into {table} values (?, ?)", mapped)
            for key, value in mapped:
                self._memo[key] = (value, False)

    def read(self, key: str, default: Any = null) -> Any:
        if key in self._memo:
            return self._memo[key][0]
        data = super().read(key, default)
        self._memo[key] = (data, False) 
    
    def write(self, key: str, value: Any):
        self._memo[key] = (value, True)
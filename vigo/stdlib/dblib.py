"""Database operations: SQLite"""
import sqlite3
from ..runtime.objects import BuiltinFunction
from ..runtime.errors import ViGoError


class ViGoDatabase:
    def __init__(self, path):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row

    def execute(self, sql, params=None):
        try:
            cur = self.conn.execute(sql, params or [])
            self.conn.commit()
            return True
        except Exception as e:
            raise ViGoError(f"SQL execution failed: {e}")

    def query(self, sql, params=None):
        try:
            cur = self.conn.execute(sql, params or [])
            rows = cur.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            raise ViGoError(f"SQL query failed: {e}")

    def close(self):
        self.conn.close()

    def __repr__(self):
        return "🗄️ <Database connection>"


def register(env):
    def _open_db(path):
        return ViGoDatabase(path)

    def _db_execute(db, sql, params=None):
        if not isinstance(db, ViGoDatabase):
            raise ViGoError("FirstParameterMust be a database connection")
        return db.execute(sql, params)

    def _db_query(db, sql, params=None):
        if not isinstance(db, ViGoDatabase):
            raise ViGoError("FirstParameterMust be a database connection")
        return db.query(sql, params)

    def _db_close(db):
        if not isinstance(db, ViGoDatabase):
            raise ViGoError("ParameterMust be a database connection")
        db.close()
        return True

    env.define('db_open',    BuiltinFunction(_open_db, 'db_open'))
    env.define('db_execute', BuiltinFunction(_db_execute, 'db_execute'))
    env.define('db_query',   BuiltinFunction(_db_query, 'db_query'))
    env.define('db_close',   BuiltinFunction(_db_close, 'db_close'))
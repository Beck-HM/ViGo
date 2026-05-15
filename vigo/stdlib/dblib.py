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
    
    # ── MySQL (optional) ──

    def _db_mysql_open(host="localhost", port=3306, user="root", password="", database="test"):
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=host, port=int(port), user=user, password=password, database=database
            )
            return {"_conn": conn, "_type": "mysql"}
        except ImportError:
            raise ViGoError("mysql-connector-python not installed. Run: pip install mysql-connector-python")
        except Exception as e:
            raise ViGoError(f"MySQL connection failed: {e}")

    def _db_mysql_query(db, sql, params=None):
        if not isinstance(db, dict) or db.get("_type") != "mysql":
            raise ViGoError("Not a MySQL connection")
        conn = db["_conn"]
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return rows

    def _db_mysql_execute(db, sql, params=None):
        if not isinstance(db, dict) or db.get("_type") != "mysql":
            raise ViGoError("Not a MySQL connection")
        conn = db["_conn"]
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        cur.close()
        return True

    def _db_mysql_close(db):
        if not isinstance(db, dict) or db.get("_type") != "mysql":
            raise ViGoError("Not a MySQL connection")
        db["_conn"].close()
        return True

    # ── PostgreSQL (optional) ──

    def _db_pg_open(host="localhost", port=5432, user="postgres", password="", database="postgres"):
        try:
            import psycopg2
            import psycopg2.extras
            conn = psycopg2.connect(
                host=host, port=int(port), user=user, password=password, dbname=database
            )
            return {"_conn": conn, "_type": "postgresql"}
        except ImportError:
            raise ViGoError("psycopg2 not installed. Run: pip install psycopg2-binary")
        except Exception as e:
            raise ViGoError(f"PostgreSQL connection failed: {e}")

    def _db_pg_query(db, sql, params=None):
        if not isinstance(db, dict) or db.get("_type") != "postgresql":
            raise ViGoError("Not a PostgreSQL connection")
        import psycopg2.extras
        conn = db["_conn"]
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cur.close()
        return [dict(r) for r in rows]

    def _db_pg_execute(db, sql, params=None):
        if not isinstance(db, dict) or db.get("_type") != "postgresql":
            raise ViGoError("Not a PostgreSQL connection")
        conn = db["_conn"]
        cur = conn.cursor()
        cur.execute(sql, params or ())
        conn.commit()
        cur.close()
        return True

    def _db_pg_close(db):
        if not isinstance(db, dict) or db.get("_type") != "postgresql":
            raise ViGoError("Not a PostgreSQL connection")
        db["_conn"].close()
        return True

    # ── Redis (optional) ──

    def _db_redis_open(host="localhost", port=6379, password="", db=0):
        try:
            import redis
            r = redis.Redis(host=host, port=int(port), password=password or None, db=int(db),
                           decode_responses=True)
            r.ping()
            return {"_conn": r, "_type": "redis"}
        except ImportError:
            raise ViGoError("redis not installed. Run: pip install redis")
        except Exception as e:
            raise ViGoError(f"Redis connection failed: {e}")

    def _db_redis_set(r, key, value, expire=None):
        if not isinstance(r, dict) or r.get("_type") != "redis":
            raise ViGoError("Not a Redis connection")
        conn = r["_conn"]
        if expire:
            return conn.setex(str(key), int(expire), str(value))
        return conn.set(str(key), str(value))

    def _db_redis_get(r, key):
        if not isinstance(r, dict) or r.get("_type") != "redis":
            raise ViGoError("Not a Redis connection")
        return r["_conn"].get(str(key))

    def _db_redis_delete(r, key):
        if not isinstance(r, dict) or r.get("_type") != "redis":
            raise ViGoError("Not a Redis connection")
        return r["_conn"].delete(str(key))

    def _db_redis_close(r):
        if not isinstance(r, dict) or r.get("_type") != "redis":
            raise ViGoError("Not a Redis connection")
        r["_conn"].close()
        return True

    env.define('db_open',    BuiltinFunction(_open_db, 'db_open'))
    env.define('db_execute', BuiltinFunction(_db_execute, 'db_execute'))
    env.define('db_query',   BuiltinFunction(_db_query, 'db_query'))
    env.define('db_close',   BuiltinFunction(_db_close, 'db_close'))
    env.define('db_mysql_open',    BuiltinFunction(_db_mysql_open, 'db_mysql_open'))
    env.define('db_mysql_query',   BuiltinFunction(_db_mysql_query, 'db_mysql_query'))
    env.define('db_mysql_execute', BuiltinFunction(_db_mysql_execute, 'db_mysql_execute'))
    env.define('db_mysql_close',   BuiltinFunction(_db_mysql_close, 'db_mysql_close'))
    env.define('db_pg_open',       BuiltinFunction(_db_pg_open, 'db_pg_open'))
    env.define('db_pg_query',      BuiltinFunction(_db_pg_query, 'db_pg_query'))
    env.define('db_pg_execute',    BuiltinFunction(_db_pg_execute, 'db_pg_execute'))
    env.define('db_pg_close',      BuiltinFunction(_db_pg_close, 'db_pg_close'))
    env.define('db_redis_open',    BuiltinFunction(_db_redis_open, 'db_redis_open'))
    env.define('db_redis_set',     BuiltinFunction(_db_redis_set, 'db_redis_set'))
    env.define('db_redis_get',     BuiltinFunction(_db_redis_get, 'db_redis_get'))
    env.define('db_redis_delete',  BuiltinFunction(_db_redis_delete, 'db_redis_delete'))
    env.define('db_redis_close',   BuiltinFunction(_db_redis_close, 'db_redis_close'))
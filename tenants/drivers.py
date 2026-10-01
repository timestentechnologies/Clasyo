import os
from pathlib import Path
from django.conf import settings


class BaseTenantDatabaseDriver:
    """Base class for multi-tenant database engine drivers"""
    
    def create_database(self, db_name: str) -> bool:
        raise NotImplementedError
        
    def database_exists(self, db_name: str) -> bool:
        raise NotImplementedError
        
    def delete_database(self, db_name: str) -> bool:
        raise NotImplementedError
        
    def get_connection_config(self, db_name: str) -> dict:
        raise NotImplementedError


class SQLiteTenantDriver(BaseTenantDatabaseDriver):
    """
    SQLite driver for local development.
    Creates a dedicated .sqlite3 file per school.
    """
    def __init__(self):
        self.dbs_dir = getattr(settings, 'TENANT_DBS_DIR', settings.BASE_DIR / 'tenant_dbs')
        os.makedirs(self.dbs_dir, exist_ok=True)
        
    def _get_db_path(self, db_name: str) -> Path:
        clean_name = db_name.replace('.sqlite3', '')
        return self.dbs_dir / f"{clean_name}.sqlite3"
        
    def create_database(self, db_name: str) -> bool:
        db_path = self._get_db_path(db_name)
        if not db_path.exists():
            db_path.touch()
        return True
        
    def database_exists(self, db_name: str) -> bool:
        return self._get_db_path(db_name).exists()
        
    def delete_database(self, db_name: str) -> bool:
        """
        Closes active connections and physically deletes the .sqlite3 file and any journal/WAL files.
        """
        from django.db import connections
        clean_name = db_name.replace('.sqlite3', '')
        if clean_name in connections:
            try:
                connections[clean_name].close()
            except Exception:
                pass
                
        db_path = self._get_db_path(db_name)
        deleted = False
        for ext in ['', '-journal', '-wal', '-shm']:
            target = Path(f"{db_path}{ext}")
            if target.exists():
                try:
                    os.remove(target)
                    deleted = True
                except Exception as e:
                    print(f"[SQLiteTenantDriver] Warning removing {target}: {e}")
        return deleted

    def get_connection_config(self, db_name: str) -> dict:
        cfg = dict(settings.DATABASES.get('default', {}))
        cfg['ENGINE'] = 'django.db.backends.sqlite3'
        cfg['NAME'] = str(self._get_db_path(db_name))
        cfg.setdefault('TIME_ZONE', getattr(settings, 'TIME_ZONE', 'UTC') if getattr(settings, 'USE_TZ', False) else None)
        cfg.setdefault('AUTOCOMMIT', True)
        cfg.setdefault('ATOMIC_REQUESTS', False)
        cfg.setdefault('CONN_MAX_AGE', 0)
        cfg.setdefault('CONN_HEALTH_CHECKS', False)
        cfg.setdefault('OPTIONS', {})
        return cfg


class PostgresTenantDriver(BaseTenantDatabaseDriver):
    """
    PostgreSQL driver for Neon / Production.
    Supports either separate PostgreSQL databases or schema-based isolation.
    """
    def __init__(self):
        self.default_db = settings.DATABASES['default']
        
    def create_database(self, db_name: str) -> bool:
        clean_name = "".join(c for c in db_name if c.isalnum() or c in ('_', '-'))
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        
        try:
            conn = psycopg2.connect(
                dbname=self.default_db.get('NAME', 'postgres'),
                user=self.default_db.get('USER', 'postgres'),
                password=self.default_db.get('PASSWORD', ''),
                host=self.default_db.get('HOST', 'localhost'),
                port=self.default_db.get('PORT', 5432)
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (clean_name,))
            if not cursor.fetchone():
                cursor.execute(f'CREATE DATABASE "{clean_name}"')
                
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[PostgresTenantDriver] Notice: CREATE DATABASE '{clean_name}' failed ({e}). Checking schema fallback...")
            return self._create_schema(clean_name)

    def _create_schema(self, schema_name: str) -> bool:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        try:
            conn = psycopg2.connect(
                dbname=self.default_db.get('NAME', 'postgres'),
                user=self.default_db.get('USER', 'postgres'),
                password=self.default_db.get('PASSWORD', ''),
                host=self.default_db.get('HOST', 'localhost'),
                port=self.default_db.get('PORT', 5432)
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')
            cursor.close()
            conn.close()
            return True
        except Exception as ex:
            print(f"[PostgresTenantDriver] Schema creation error: {ex}")
            return False

    def database_exists(self, db_name: str) -> bool:
        clean_name = "".join(c for c in db_name if c.isalnum() or c in ('_', '-'))
        import psycopg2

        conn = psycopg2.connect(
            dbname=self.default_db.get('NAME', 'postgres'),
            user=self.default_db.get('USER', 'postgres'),
            password=self.default_db.get('PASSWORD', ''),
            host=self.default_db.get('HOST', 'localhost'),
            port=self.default_db.get('PORT', 5432),
        )
        try:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (clean_name,),
                )
                return bool(cursor.fetchone())
            finally:
                cursor.close()
        finally:
            conn.close()

    def delete_database(self, db_name: str) -> bool:
        """
        Terminates active connections and drops the PostgreSQL database or schema.
        """
        from django.db import connections
        clean_name = "".join(c for c in db_name if c.isalnum() or c in ('_', '-'))
        if clean_name in connections:
            try:
                connections[clean_name].close()
            except Exception:
                pass
                
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        try:
            conn = psycopg2.connect(
                dbname=self.default_db.get('NAME', 'postgres'),
                user=self.default_db.get('USER', 'postgres'),
                password=self.default_db.get('PASSWORD', ''),
                host=self.default_db.get('HOST', 'localhost'),
                port=self.default_db.get('PORT', 5432)
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Terminate active connections to this database if it exists
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid();",
                (clean_name,)
            )
            cursor.execute(f'DROP DATABASE IF EXISTS "{clean_name}"')
            
            # Also drop schema fallback in case schema isolation was used
            cursor.execute(f'DROP SCHEMA IF EXISTS "{clean_name}" CASCADE')
            
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[PostgresTenantDriver] Error dropping database/schema '{clean_name}': {e}")
            return False

    def get_connection_config(self, db_name: str) -> dict:
        clean_name = "".join(c for c in db_name if c.isalnum() or c in ('_', '-'))
        cfg = dict(self.default_db)
        cfg['NAME'] = clean_name
        cfg.setdefault('TIME_ZONE', getattr(settings, 'TIME_ZONE', 'UTC') if getattr(settings, 'USE_TZ', False) else None)
        cfg.setdefault('AUTOCOMMIT', True)
        cfg.setdefault('ATOMIC_REQUESTS', False)
        cfg.setdefault('CONN_MAX_AGE', 0)
        cfg.setdefault('CONN_HEALTH_CHECKS', False)
        cfg.setdefault('OPTIONS', {})
        return cfg


class MySQLTenantDriver(BaseTenantDatabaseDriver):
    """
    MySQL driver for cPanel / VPS hosting.
    Handles dynamic database creation via SQL with support for cPanel prefixes.
    """
    def __init__(self):
        self.default_db = settings.DATABASES['default']
        self.prefix = getattr(settings, 'CPANEL_DB_PREFIX', '')
        
    def _format_db_name(self, db_name: str) -> str:
        clean_name = "".join(c for c in db_name if c.isalnum() or c in ('_', '-'))
        if self.prefix and not clean_name.startswith(self.prefix):
            return f"{self.prefix}{clean_name}"
        return clean_name
        
    def create_database(self, db_name: str) -> bool:
        full_name = self._format_db_name(db_name)
        import MySQLdb
        try:
            conn = MySQLdb.connect(
                host=self.default_db.get('HOST', 'localhost'),
                user=self.default_db.get('USER', 'root'),
                passwd=self.default_db.get('PASSWORD', ''),
                port=int(self.default_db.get('PORT', 3306))
            )
            cursor = conn.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{full_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[MySQLTenantDriver] Error creating database `{full_name}`: {e}")
            return False

    def database_exists(self, db_name: str) -> bool:
        full_name = self._format_db_name(db_name)
        import MySQLdb
        try:
            conn = MySQLdb.connect(
                host=self.default_db.get('HOST', 'localhost'),
                user=self.default_db.get('USER', 'root'),
                passwd=self.default_db.get('PASSWORD', ''),
                port=int(self.default_db.get('PORT', 3306))
            )
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES LIKE %s", (full_name,))
            exists = bool(cursor.fetchone())
            cursor.close()
            conn.close()
            return exists
        except Exception:
            return False

    def delete_database(self, db_name: str) -> bool:
        """
        Closes active connections and drops the MySQL database.
        """
        from django.db import connections
        full_name = self._format_db_name(db_name)
        clean_name = db_name.replace('.sqlite3', '')
        if clean_name in connections:
            try:
                connections[clean_name].close()
            except Exception:
                pass
                
        import MySQLdb
        try:
            conn = MySQLdb.connect(
                host=self.default_db.get('HOST', 'localhost'),
                user=self.default_db.get('USER', 'root'),
                passwd=self.default_db.get('PASSWORD', ''),
                port=int(self.default_db.get('PORT', 3306))
            )
            cursor = conn.cursor()
            cursor.execute(f"DROP DATABASE IF EXISTS `{full_name}`")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"[MySQLTenantDriver] Error dropping database `{full_name}`: {e}")
            return False

    def get_connection_config(self, db_name: str) -> dict:
        full_name = self._format_db_name(db_name)
        cfg = dict(self.default_db)
        cfg['NAME'] = full_name
        cfg.setdefault('TIME_ZONE', getattr(settings, 'TIME_ZONE', 'UTC') if getattr(settings, 'USE_TZ', False) else None)
        cfg.setdefault('AUTOCOMMIT', True)
        cfg.setdefault('ATOMIC_REQUESTS', False)
        cfg.setdefault('CONN_MAX_AGE', 0)
        cfg.setdefault('CONN_HEALTH_CHECKS', False)
        cfg.setdefault('OPTIONS', {})
        return cfg


def get_tenant_database_driver() -> BaseTenantDatabaseDriver:
    """Factory function returning the active environment tenant database driver"""
    default_engine = settings.DATABASES.get('default', {}).get('ENGINE', '')
    
    if 'sqlite3' in default_engine:
        return SQLiteTenantDriver()
    elif 'postgresql' in default_engine:
        return PostgresTenantDriver()
    elif 'mysql' in default_engine:
        return MySQLTenantDriver()
    
    return SQLiteTenantDriver()

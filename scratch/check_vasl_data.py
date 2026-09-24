import sys, os
sys.path.insert(0, r'c:\Users\BPI OFFICE\schoolsaas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
import django
django.setup()

from tenants.services import register_tenant_connection
register_tenant_connection('VASL')
from django.db import connections

cursor = connections['VASL'].cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]

for t in sorted(tables):
    if not t.startswith('sqlite_') and not t.startswith('django_'):
        try:
            cursor.execute(f'SELECT count(*) FROM "{t}"')
            c = cursor.fetchone()[0]
            if c > 0:
                print(f"{t}: {c}")
        except Exception as e:
            print(f"Err {t}: {e}")

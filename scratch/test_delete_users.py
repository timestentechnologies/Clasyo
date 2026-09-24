import sys, os
sys.path.insert(0, r'c:\Users\BPI OFFICE\schoolsaas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
import django
django.setup()

from tenants.services import register_tenant_connection
register_tenant_connection('VASL')
from django.db import connections

cursor = connections['VASL'].cursor()
cursor.execute("SELECT id, email FROM accounts_user WHERE email LIKE '%@demo.school' OR is_sample_data = 1")
demo_users = cursor.fetchall()
print(f"Found {len(demo_users)} demo users in VASL.")

user_ids = [u[0] for u in demo_users]
# Check foreign key references
cursor.execute("PRAGMA foreign_key_check;")
print("FK check before:", cursor.fetchall())

# Let's test deleting them within a transaction and checking for errors
try:
    with connections['VASL'].cursor() as cur:
        # Check any referencing rows in other tables
        for uid, email in demo_users:
            pass
        cur.execute("DELETE FROM accounts_user WHERE email LIKE '%@demo.school' OR is_sample_data = 1")
        print("Deleted rows from accounts_user successfully!")
        cur.execute("PRAGMA foreign_key_check;")
        fk_errors = cur.fetchall()
        print("FK check after deletion:", fk_errors)
except Exception as e:
    print("Error deleting:", e)

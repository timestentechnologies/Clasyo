import re
import sqlite3

with open('opulentl_schoolsaas.sql', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

inserts = re.findall(r'INSERT INTO `?([a-zA-Z0-9_]+)`?', content)
print('Tables with inserts in opulentl_schoolsaas.sql count:', len(set(inserts)))
print('Tables with inserts:', sorted(list(set(inserts))))

# Search users in SQL
user_matches = re.findall(r"INSERT INTO `accounts_user`[^;]+;", content)
print('\nNumber of accounts_user insert blocks in SQL dump:', len(user_matches))
for m in user_matches:
    print(m[:300])

# Check SQLite
conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()
cur.execute("SELECT id, email, is_superuser, is_staff, school_id FROM accounts_user")
users = cur.fetchall()
print('\nUsers in local db.sqlite3:')
for u in users:
    print(u)

cur.execute("SELECT id, name, slug FROM tenants_school")
schools = cur.fetchall()
print('\nSchools in local db.sqlite3:')
for s in schools:
    print(s)
conn.close()

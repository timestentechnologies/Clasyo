import sqlite3

con = sqlite3.connect('tenant_dbs/demo-school.sqlite3')
cur = con.cursor()
cur.execute('PRAGMA foreign_keys = OFF;')
cur.execute("DELETE FROM accounts_user WHERE is_sample_data = 0 AND role != 'superadmin'")
con.commit()
print('Deleted old non-sample users from demo-school.sqlite3:', cur.rowcount)
cur.execute('PRAGMA foreign_keys = ON;')

# Check parents
cur.execute("SELECT id, email, first_name, last_name, role FROM accounts_user WHERE role='parent'")
parents = cur.fetchall()
print(f'Total parents now in demo-school: {len(parents)}')
for p in parents:
    print(' ', p)
con.close()

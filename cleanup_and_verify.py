import psycopg2

SUPABASE_URL = "postgresql://postgres.ycizawlcrwynvxquddhl:PpKJONhxgdm8JqG6@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

conn = psycopg2.connect(SUPABASE_URL)
cur = conn.cursor()

# Delete duplicate AnonymousUser before trimming
cur.execute("DELETE FROM accounts_user WHERE id != 1 AND email LIKE '%AnonymousUser%';")

cur.execute("""
    UPDATE accounts_user 
    SET email = TRIM(email), 
        role = TRIM(role), 
        first_name = TRIM(first_name), 
        last_name = TRIM(last_name);
""")

cur.execute("""
    UPDATE tenants_school 
    SET name = TRIM(name), 
        slug = TRIM(slug), 
        email = TRIM(email);
""")

conn.commit()

# Print current users and schools
cur.execute("SELECT id, email, role, is_superuser, is_active, school_id FROM accounts_user WHERE email != 'AnonymousUser' ORDER BY id;")
print("--- ALL RESTORED USERS IN SUPABASE ---")
for row in cur.fetchall():
    print(f"ID {row[0]}: '{row[1]}' | Role: {row[2]} | Superuser: {row[3]} | Active: {row[4]} | School ID: {row[5]}")

cur.execute("SELECT id, name, slug, is_active FROM tenants_school ORDER BY id;")
print("\n--- ALL RESTORED SCHOOLS IN SUPABASE ---")
for row in cur.fetchall():
    print(f"ID {row[0]}: '{row[1]}' | Slug: '{row[2]}' | Active: {row[3]}")

cur.execute("SELECT count(*) FROM students_student;")
print("\nStudents in Supabase:", cur.fetchone()[0])

cur.execute("SELECT count(*) FROM subscriptions_subscriptionplan;")
print("Subscription Plans in Supabase:", cur.fetchone()[0])

cur.execute("SELECT count(*) FROM finance_account;")
print("Finance Accounts in Supabase:", cur.fetchone()[0])

cur.execute("SELECT count(*) FROM clubs_club;")
print("Clubs in Supabase:", cur.fetchone()[0])

conn.close()

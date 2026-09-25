import os
import re
import psycopg2
from psycopg2 import sql

SUPABASE_URL = "postgresql://postgres.ycizawlcrwynvxquddhl:PpKJONhxgdm8JqG6@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

def main():
    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(SUPABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Get all boolean columns across all tables in Supabase public schema
    cur.execute("""
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public' AND data_type = 'boolean';
    """)
    boolean_cols = {}
    for table, col in cur.fetchall():
        boolean_cols.setdefault(table, set()).add(col)

    # Get all tables and their columns in Supabase
    cur.execute("""
        SELECT table_name, column_name 
        FROM information_schema.columns 
        WHERE table_schema = 'public';
    """)
    db_table_cols = {}
    for table, col in cur.fetchall():
        db_table_cols.setdefault(table, set()).add(col)

    print(f"Discovered {len(db_table_cols)} tables in Supabase schema.")

    # Read SQL dump
    with open("opulentl_schoolsaas.sql", "r", encoding="utf-8", errors="ignore") as f:
        sql_content = f.read()

    # Find all INSERT INTO statements
    # Pattern: INSERT INTO `table_name` (`col1`, `col2`, ...) VALUES (...);
    insert_pattern = re.compile(
        r"INSERT INTO `([^`]+)`\s*\(([^)]+)\)\s*VALUES\s*(.+?);\s*$",
        re.MULTILINE | re.DOTALL
    )

    matches = list(insert_pattern.finditer(sql_content))
    print(f"Found {len(matches)} INSERT statements in opulentl_schoolsaas.sql.")

    # Process table by table in dependency-friendly order if possible
    # We will temporarily disable foreign key checks or handle tables
    cur.execute("SET session_replication_role = 'replica';")

    imported_tables = set()
    skipped_tables = set()

    for m in matches:
        table_name = m.group(1)
        raw_cols = m.group(2)
        raw_values = m.group(3)

        if table_name not in db_table_cols:
            skipped_tables.add(table_name)
            continue

        cols = [c.strip().strip("`").strip('"') for c in raw_cols.split(",")]
        
        # Filter only cols that exist in Supabase table
        existing_cols = db_table_cols[table_name]
        valid_col_indices = [i for i, c in enumerate(cols) if c in existing_cols]
        valid_cols = [cols[i] for i in valid_col_indices]

        # Parse tuples from raw_values
        # Splitting rows carefully: rows are enclosed in parentheses: (val1, val2, ...), (val1, val2, ...)
        # We can use a tokenizer or regex
        rows = []
        in_paren = False
        in_str = False
        escape = False
        current_row = []
        current_val = []

        i = 0
        val_chars = []
        row_chars = []
        depth = 0
        quote_char = None

        while i < len(raw_values):
            ch = raw_values[i]
            if escape:
                row_chars.append(ch)
                escape = False
            elif ch == "\\":
                row_chars.append(ch)
                escape = True
            elif quote_char:
                row_chars.append(ch)
                if ch == quote_char:
                    quote_char = None
            elif ch in ("'", '"'):
                quote_char = ch
                row_chars.append(ch)
            elif ch == "(":
                depth += 1
                row_chars = []
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    rows.append("".join(row_chars))
                    row_chars = []
            else:
                if depth > 0:
                    row_chars.append(ch)
            i += 1

        print(f"Table {table_name}: parsed {len(rows)} rows.")

        # For each row, parse fields
        table_bools = boolean_cols.get(table_name, set())
        
        # Prepare insert query
        col_names = ", ".join([f'"{c}"' for c in valid_cols])
        placeholders = ", ".join(["%s"] * len(valid_cols))
        
        # Use ON CONFLICT DO NOTHING
        conflict_clause = ""
        if "id" in valid_cols:
            conflict_clause = 'ON CONFLICT ("id") DO NOTHING'

        insert_sql = f'INSERT INTO "{table_name}" ({col_names}) VALUES ({placeholders}) {conflict_clause};'

        inserted_count = 0
        for r_str in rows:
            # Parse CSV-like row respecting quotes
            fields = []
            cur_f = []
            in_q = False
            q_c = None
            esc = False
            for ch in r_str:
                if esc:
                    cur_f.append(ch)
                    esc = False
                elif ch == "\\":
                    esc = True
                elif in_q:
                    if ch == q_c:
                        in_q = False
                    else:
                        cur_f.append(ch)
                elif ch in ("'", '"'):
                    in_q = True
                    q_c = ch
                elif ch == ",":
                    fields.append("".join(cur_f).strip())
                    cur_f = []
                else:
                    cur_f.append(ch)
            fields.append("".join(cur_f).strip())

            # Map fields
            clean_row = []
            for idx in valid_col_indices:
                if idx < len(fields):
                    val = fields[idx]
                    col_name = cols[idx]

                    if val.upper() == "NULL":
                        clean_row.append(None)
                    elif col_name in table_bools:
                        # Convert 0/1 to boolean
                        clean_row.append(True if val in ("1", "'1'", "true", "TRUE") else False)
                    else:
                        clean_row.append(val)
                else:
                    clean_row.append(None)

            try:
                cur.execute(insert_sql, clean_row)
                inserted_count += 1
            except Exception as e:
                print(f"Error inserting row into {table_name}: {e}")
                conn.rollback()
                cur.execute("SET session_replication_role = 'replica';")
                break
        else:
            conn.commit()
            cur.execute("SET session_replication_role = 'replica';")
            imported_tables.add(table_name)
            print(f"Successfully imported {inserted_count} rows into {table_name}")

    # Re-enable replication role
    cur.execute("SET session_replication_role = 'origin';")
    conn.commit()

    # Update sequences for all tables with an id column
    print("Updating primary key sequences...")
    for table_name in imported_tables:
        if "id" in db_table_cols.get(table_name, set()):
            try:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('"{table_name}"', 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table_name}"), 1)
                    );
                """)
                conn.commit()
            except Exception as e:
                conn.rollback()

    # Check users and schools now in Supabase
    cur.execute("SELECT id, email, is_superuser, is_staff, school_id FROM accounts_user;")
    print("\n--- Current Users in Supabase ---")
    for u in cur.fetchall():
        print(u)

    cur.execute("SELECT id, name, slug FROM tenants_school;")
    print("\n--- Current Schools in Supabase ---")
    for s in cur.fetchall():
        print(s)

    conn.close()
    print("\nSupabase data import finished successfully!")

if __name__ == "__main__":
    main()

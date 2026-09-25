import sys
import os
import psycopg2
from psycopg2 import extras

SUPABASE_URL = "postgresql://postgres.ycizawlcrwynvxquddhl:PpKJONhxgdm8JqG6@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

def parse_sql_values(values_str):
    """
    Parses a MySQL VALUES string like:
    (1, 'abc', NULL, 0), (2, 'def\'s', '2026-01-01', 1)
    into a list of lists of python values.
    Runs in linear O(N) time without regular expression backtracking.
    """
    rows = []
    current_row = []
    current_field = []
    in_string = False
    quote_char = None
    escaped = False
    paren_depth = 0
    was_quoted = False

    i = 0
    length = len(values_str)

    while i < length:
        ch = values_str[i]

        if escaped:
            if ch == '0':
                current_field.append('\0')
            elif ch == 'b':
                current_field.append('\b')
            elif ch == 'n':
                current_field.append('\n')
            elif ch == 'r':
                current_field.append('\r')
            elif ch == 't':
                current_field.append('\t')
            elif ch == 'Z':
                current_field.append('\x1a')
            else:
                current_field.append(ch)
            escaped = False
            i += 1
            continue

        if ch == '\\' and in_string:
            escaped = True
            i += 1
            continue

        if ch in ("'", '"'):
            if not in_string:
                in_string = True
                quote_char = ch
                was_quoted = True
            elif ch == quote_char:
                # Check for double quote escape '' in SQL
                if i + 1 < length and values_str[i + 1] == quote_char:
                    current_field.append(quote_char)
                    i += 2
                    continue
                else:
                    in_string = False
                    quote_char = None
            else:
                current_field.append(ch)
            i += 1
            continue

        if in_string:
            current_field.append(ch)
            i += 1
            continue

        # Outside strings
        if ch == '(':
            paren_depth += 1
            if paren_depth == 1:
                current_row = []
                current_field = []
                was_quoted = False
        elif ch == ')':
            paren_depth -= 1
            if paren_depth == 0:
                raw_val = "".join(current_field).strip()
                if not was_quoted and raw_val.upper() == 'NULL':
                    current_row.append(None)
                elif not was_quoted and raw_val == '':
                    current_row.append(None)
                else:
                    current_row.append("".join(current_field) if was_quoted else raw_val)
                rows.append(current_row)
                current_row = []
                current_field = []
                was_quoted = False
        elif ch == ',':
            if paren_depth == 1:
                raw_val = "".join(current_field).strip()
                if not was_quoted and raw_val.upper() == 'NULL':
                    current_row.append(None)
                elif not was_quoted and raw_val == '':
                    current_row.append(None)
                else:
                    current_row.append("".join(current_field) if was_quoted else raw_val)
                current_field = []
                was_quoted = False
        else:
            if paren_depth == 1:
                current_field.append(ch)

        i += 1

    return rows


def main():
    print("=== Supabase Database Restore Tool ===")
    sql_file = "opulentl_schoolsaas.sql"
    if not os.path.exists(sql_file):
        print(f"Error: {sql_file} not found!")
        return

    print("Connecting to Supabase PostgreSQL...")
    conn = psycopg2.connect(SUPABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Disable foreign key constraints temporarily
    try:
        cur.execute("SET session_replication_role = 'replica';")
        conn.commit()
        print("Set session_replication_role = 'replica' (bypassing foreign keys during bulk load).")
    except Exception as e:
        conn.rollback()
        print(f"Notice: Could not set replica role ({e}), will proceed standard.")

    # Fetch table metadata from Supabase
    cur.execute("""
        SELECT table_name, column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'public';
    """)
    table_metadata = {}
    for table, col, dtype in cur.fetchall():
        if table not in table_metadata:
            table_metadata[table] = {}
        table_metadata[table][col] = dtype

    print(f"Loaded schema for {len(table_metadata)} tables from Supabase.")

    # Read the SQL dump statement by statement
    print("Reading and parsing opulentl_schoolsaas.sql...")
    
    current_statement = []
    in_insert = False
    insert_statements = []

    with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            stripped = line.strip()
            if not in_insert:
                if stripped.startswith("INSERT INTO `") or stripped.startswith("INSERT INTO \""):
                    in_insert = True
                    current_statement = [line]
                    if stripped.endswith(";"):
                        insert_statements.append("".join(current_statement))
                        current_statement = []
                        in_insert = False
            else:
                current_statement.append(line)
                if stripped.endswith(";"):
                    insert_statements.append("".join(current_statement))
                    current_statement = []
                    in_insert = False

    print(f"Found {len(insert_statements)} INSERT blocks in {sql_file}.")

    imported_tables = set()

    for idx, stmt in enumerate(insert_statements):
        # Extract table name and column names
        # Format: INSERT INTO `table_name` (`c1`, `c2`, ...) VALUES ...;
        first_paren = stmt.find("(")
        values_pos = stmt.upper().find("VALUES")
        if first_paren == -1 or values_pos == -1 or first_paren > values_pos:
            continue

        header = stmt[:first_paren]
        cols_part = stmt[first_paren+1:values_pos].strip()
        # Remove trailing ')' before VALUES
        if cols_part.endswith(")"):
            cols_part = cols_part[:-1].strip()

        # Parse table name
        tbl_match = header.replace("INSERT INTO", "").strip().strip("`").strip('"').strip()
        table_name = tbl_match

        # Parse column list
        cols = [c.strip().strip("`").strip('"') for c in cols_part.split(",")]

        # Get values part
        values_str = stmt[values_pos + 6:].strip()
        if values_str.endswith(";"):
            values_str = values_str[:-1].strip()

        if table_name not in table_metadata:
            print(f"[{idx+1}/{len(insert_statements)}] Skipping `{table_name}`: table does not exist in target database.")
            continue

        target_cols = table_metadata[table_name]
        valid_indices = [i for i, c in enumerate(cols) if c in target_cols]
        valid_cols = [cols[i] for i in valid_indices]

        # Parse rows
        rows = parse_sql_values(values_str)
        if not rows:
            continue

        # Format rows for PostgreSQL
        prepared_rows = []
        for row in rows:
            prepared_row = []
            for i in valid_indices:
                if i < len(row):
                    val = row[i]
                    col_name = cols[i]
                    dtype = target_cols[col_name]

                    if val is None:
                        prepared_row.append(None)
                    elif dtype == 'boolean':
                        # Convert 0/1 to boolean
                        if val in ('1', 1, 'true', 'True', 't'):
                            prepared_row.append(True)
                        else:
                            prepared_row.append(False)
                    elif 'timestamp' in dtype or 'date' in dtype:
                        if val in ('0000-00-00 00:00:00', '0000-00-00', ''):
                            prepared_row.append(None)
                        else:
                            prepared_row.append(val)
                    elif dtype in ('integer', 'bigint', 'smallint'):
                        if val == '':
                            prepared_row.append(None)
                        else:
                            try:
                                prepared_row.append(int(val))
                            except ValueError:
                                prepared_row.append(None)
                    elif dtype in ('numeric', 'double precision', 'real'):
                        if val == '':
                            prepared_row.append(None)
                        else:
                            try:
                                prepared_row.append(float(val))
                            except ValueError:
                                prepared_row.append(None)
                    else:
                        prepared_row.append(val)
                else:
                    prepared_row.append(None)
            prepared_rows.append(prepared_row)

        # Build SQL insert with ON CONFLICT DO NOTHING
        quoted_cols = ", ".join([f'"{c}"' for c in valid_cols])
        placeholders = ", ".join(["%s"] * len(valid_cols))

        conflict_clause = ""
        if "id" in valid_cols:
            conflict_clause = 'ON CONFLICT ("id") DO NOTHING'

        insert_sql = f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES ({placeholders}) {conflict_clause};'

        success_count = 0
        for p_row in prepared_rows:
            try:
                cur.execute(insert_sql, p_row)
                success_count += 1
            except Exception as e:
                conn.rollback()
                try:
                    cur.execute("SET session_replication_role = 'replica';")
                except:
                    pass
                # Try continue with remaining rows
                continue

        conn.commit()
        imported_tables.add(table_name)
        print(f"[{idx+1}/{len(insert_statements)}] `{table_name}`: successfully imported {success_count}/{len(rows)} rows.")

    # Reset session_replication_role
    try:
        cur.execute("SET session_replication_role = 'origin';")
        conn.commit()
    except:
        conn.rollback()

    # Update sequence IDs for all tables
    print("\nUpdating PostgreSQL auto-increment sequences...")
    for table_name in imported_tables:
        if "id" in table_metadata.get(table_name, {}):
            try:
                cur.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('"{table_name}"', 'id'),
                        COALESCE((SELECT MAX(id) FROM "{table_name}"), 1)
                    );
                """)
                conn.commit()
            except Exception:
                conn.rollback()

    # Verification queries
    print("\n=== VERIFICATION IN SUPABASE ===")
    cur.execute("SELECT count(*) FROM accounts_user;")
    user_count = cur.fetchone()[0]
    print(f"Total Users: {user_count}")

    cur.execute("SELECT id, email, role, is_superuser, is_staff, is_active FROM accounts_user;")
    for u in cur.fetchall():
        print(f"  User ID {u[0]}: {u[1]} | Role: {u[2]} | Super: {u[3]} | Staff: {u[4]} | Active: {u[5]}")

    cur.execute("SELECT count(*) FROM tenants_school;")
    school_count = cur.fetchone()[0]
    print(f"\nTotal Schools: {school_count}")

    cur.execute("SELECT id, name, slug, is_active FROM tenants_school;")
    for s in cur.fetchall():
        print(f"  School ID {s[0]}: {s[1]} (slug: {s[2]}) | Active: {s[3]}")

    conn.close()
    print("\n[SUCCESS] opulentl_schoolsaas.sql has been uploaded and restored to Supabase!")

if __name__ == "__main__":
    main()

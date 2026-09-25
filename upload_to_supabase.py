import sys
import os
import re
import psycopg2
from psycopg2 import extras

SUPABASE_URL = "postgresql://postgres.ycizawlcrwynvxquddhl:PpKJONhxgdm8JqG6@aws-0-eu-central-1.pooler.supabase.com:5432/postgres"

def parse_sql_values(values_str):
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
            elif ch == 'n':
                current_field.append('\n')
            elif ch == 'r':
                current_field.append('\r')
            elif ch == 't':
                current_field.append('\t')
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


def run():
    print("Connecting to Supabase PostgreSQL...", flush=True)
    conn = psycopg2.connect(SUPABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        cur.execute("SET session_replication_role = 'replica';")
        conn.commit()
    except Exception:
        conn.rollback()

    cur.execute("""
        SELECT table_name, column_name, data_type, character_maximum_length, is_nullable
        FROM information_schema.columns 
        WHERE table_schema = 'public';
    """)
    table_metadata = {}
    col_max_lengths = {}
    col_nullables = {}

    for table, col, dtype, max_len, is_null in cur.fetchall():
        if table not in table_metadata:
            table_metadata[table] = {}
        table_metadata[table][col] = dtype
        col_max_lengths[(table, col)] = max_len
        col_nullables[(table, col)] = (is_null == 'YES')

    sql_file = "opulentl_schoolsaas.sql"
    insert_statements = []
    with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
        in_insert = False
        stmt_acc = []
        for line in f:
            s = line.strip()
            if not in_insert:
                if s.startswith("INSERT INTO `") or s.startswith("INSERT INTO \""):
                    in_insert = True
                    stmt_acc = [line]
                    if s.endswith(";"):
                        insert_statements.append("".join(stmt_acc))
                        stmt_acc = []
                        in_insert = False
            else:
                stmt_acc.append(line)
                if s.endswith(";"):
                    insert_statements.append("".join(stmt_acc))
                    stmt_acc = []
                    in_insert = False

    for idx, stmt in enumerate(insert_statements):
        first_paren = stmt.find("(")
        values_pos = stmt.upper().find("VALUES")
        if first_paren == -1 or values_pos == -1 or first_paren > values_pos:
            continue

        header = stmt[:first_paren]
        cols_part = stmt[first_paren+1:values_pos].strip()
        if cols_part.endswith(")"):
            cols_part = cols_part[:-1].strip()

        table_name = header.replace("INSERT INTO", "").strip().strip("`").strip('"').strip()
        cols = [c.strip().strip("`").strip('"') for c in cols_part.split(",")]
        values_str = stmt[values_pos + 6:].strip()
        if values_str.endswith(";"):
            values_str = values_str[:-1].strip()

        if table_name not in table_metadata:
            continue

        target_cols = table_metadata[table_name]
        valid_indices = [i for i, c in enumerate(cols) if c in target_cols]
        valid_cols = [cols[i] for i in valid_indices]

        # Missing non-nullable columns with defaults
        extra_cols = []
        extra_vals = []
        if table_name == 'accounts_user' and 'navigation_layout' not in valid_cols:
            extra_cols.append('navigation_layout')
            extra_vals.append('sidebar')
        if table_name == 'core_systemsetting':
            if 'accent_color' not in valid_cols:
                extra_cols.append('accent_color')
                extra_vals.append('#4F46E5')
            if 'primary_color' not in valid_cols:
                extra_cols.append('primary_color')
                extra_vals.append('#4F46E5')
            if 'secondary_color' not in valid_cols:
                extra_cols.append('secondary_color')
                extra_vals.append('#06B6D4')
            if 'theme_color' not in valid_cols:
                extra_cols.append('theme_color')
                extra_vals.append('#4F46E5')
        if 'is_sample_data' in target_cols and 'is_sample_data' not in valid_cols:
            extra_cols.append('is_sample_data')
            extra_vals.append(False)

        all_insert_cols = valid_cols + extra_cols

        raw_rows = parse_sql_values(values_str)
        if not raw_rows:
            continue

        prepared_rows = []
        for row in raw_rows:
            p_row = []
            for i in valid_indices:
                if i < len(row):
                    val = row[i]
                    col_name = cols[i]
                    dtype = target_cols[col_name]
                    max_len = col_max_lengths.get((table_name, col_name))
                    is_nullable = col_nullables.get((table_name, col_name), True)

                    # Null handling for not-null columns
                    if (val is None or val == '') and not is_nullable:
                        if col_name == 'is_sample_data':
                            val = False
                        elif col_name in ('accent_color', 'primary_color', 'secondary_color', 'theme_color'):
                            val = '#4F46E5'
                        elif col_name == 'navigation_layout':
                            val = 'sidebar'
                        elif dtype == 'boolean':
                            val = False
                        elif dtype in ('integer', 'bigint', 'smallint'):
                            val = 0
                        else:
                            val = ' '

                    if val is None:
                        p_row.append(None)
                    elif dtype == 'boolean':
                        p_row.append(True if str(val).strip() in ('1', 'true', 'True', 't') else False)
                    elif dtype == 'inet':
                        val_str = str(val).strip()
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', val_str):
                            p_row.append(val_str)
                        else:
                            p_row.append(None)
                    elif 'timestamp' in dtype or 'date' in dtype:
                        p_row.append(None if str(val).strip() in ('0000-00-00 00:00:00', '0000-00-00', '') else val)
                    elif dtype in ('integer', 'bigint', 'smallint'):
                        if str(val).strip() == '':
                            p_row.append(None)
                        else:
                            try:
                                p_row.append(int(str(val).strip()))
                            except ValueError:
                                p_row.append(None)
                    elif dtype in ('numeric', 'double precision', 'real'):
                        if str(val).strip() == '':
                            p_row.append(None)
                        else:
                            try:
                                p_row.append(float(str(val).strip()))
                            except ValueError:
                                p_row.append(None)
                    else:
                        val_str = str(val)
                        if max_len and len(val_str) > max_len:
                            val_str = val_str[:max_len]
                        p_row.append(val_str)
                else:
                    p_row.append(None)
            
            p_row.extend(extra_vals)
            prepared_rows.append(tuple(p_row))

        quoted_cols = ", ".join([f'"{c}"' for c in all_insert_cols])
        
        conflict = ""
        if "id" in all_insert_cols:
            conflict = 'ON CONFLICT ("id") DO NOTHING'
        elif "session_key" in all_insert_cols:
            conflict = 'ON CONFLICT ("session_key") DO NOTHING'

        query = f'INSERT INTO "{table_name}" ({quoted_cols}) VALUES %s {conflict};'

        try:
            extras.execute_values(cur, query, prepared_rows, page_size=500)
            conn.commit()
            print(f"Imported {len(prepared_rows)} rows into `{table_name}`", flush=True)
        except Exception as e:
            conn.rollback()
            try:
                cur.execute("SET session_replication_role = 'replica';")
            except:
                pass
            print(f"Notice on `{table_name}`: {e}", flush=True)

    # Re-enable origin
    try:
        cur.execute("SET session_replication_role = 'origin';")
        conn.commit()
    except:
        conn.rollback()

    print("\nUpdating sequences...", flush=True)
    try:
        cur.execute("""
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN (
                    SELECT c.table_name, c.column_name 
                    FROM information_schema.columns c
                    JOIN information_schema.tables t ON t.table_name = c.table_name
                    WHERE c.column_name = 'id' 
                      AND c.table_schema = 'public' 
                      AND t.table_type = 'BASE TABLE'
                ) LOOP
                    BEGIN
                        EXECUTE format(
                            'SELECT setval(pg_get_serial_sequence(''%I'', ''id''), COALESCE(MAX(id), 1)) FROM %I',
                            r.table_name, r.table_name
                        );
                    EXCEPTION WHEN OTHERS THEN
                        NULL;
                    END;
                END LOOP;
            END $$;
        """)
        conn.commit()
        print("Sequences updated.", flush=True)
    except Exception as e:
        conn.rollback()
        print(f"Sequence notice: {e}", flush=True)

    cur.execute("SELECT count(*) FROM accounts_user;")
    u_count = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM tenants_school;")
    s_count = cur.fetchone()[0]
    print(f"\n==========================================", flush=True)
    print(f"Final Count in Supabase: {u_count} users, {s_count} schools.", flush=True)
    print(f"==========================================", flush=True)
    
    cur.execute("SELECT id, email, role, is_superuser, is_active FROM accounts_user;")
    for row in cur.fetchall():
        print(f"User ID {row[0]}: {row[1]} | Role: {row[2]} | Super: {row[3]} | Active: {row[4]}", flush=True)

    cur.execute("SELECT id, name, slug, is_active FROM tenants_school;")
    for row in cur.fetchall():
        print(f"School ID {row[0]}: {row[1]} (slug: {row[2]}) | Active: {row[3]}", flush=True)

    conn.close()
    print("DONE_ALL_SUCCESS", flush=True)

if __name__ == '__main__':
    run()

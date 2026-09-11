import os
import re
import dj_database_url
import psycopg2
from psycopg2.extras import execute_values
from django.core.management.base import BaseCommand
from django.conf import settings


TABLE_INSERT_ORDER = [
    'django_site',
    'django_content_type',
    'auth_permission',
    'core_systemsetting',
    'core_session',
    'core_academicyear',
    'core_calendarevent',
    'core_todolist',
    'superadmin_globalaiconfiguration',
    'superadmin_paymentconfiguration',
    'tenants_school',
    'accounts_user',
    'superadmin_schoolaiconfiguration',
    'socialaccount_socialapp',
    'socialaccount_socialapp_sites',
    'subscriptions_subscriptionplan',
    'subscriptions_subscription',
    'subscriptions_invoice',
    'human_resource_department',
    'human_resource_designation',
    'dormitory_dormitory',
    'dormitory_room',
    'inventory_itemcategory',
    'inventory_expense',
    'inventory_staffpayment',
    'finance_account',
    'academics_class',
    'academics_classroom',
    'academics_section',
    'academics_subject',
    'lesson_plan_lessonplantemplate',
    'lesson_plan_lessonplan',
    'lesson_plan_lessonplanresource',
    'clubs_club',
    'students_student',
    'attendance_studentattendance',
    'fees_feestructure',
    'communication_notice',
    'frontend_faq',
    'frontend_forumthread',
    'frontend_forumpost',
    'core_auditlog',
    'accounts_userloginlog',
    'django_admin_log',
    'django_session',
]


def parse_sql_values(values_text):
    rows = []
    current_row = []
    in_string = False
    string_char = None
    escaped = False
    current_val = []
    in_paren = False
    
    i = 0
    n = len(values_text)
    
    while i < n:
        c = values_text[i]
        
        if not in_paren:
            if c == '(':
                in_paren = True
                current_row = []
                current_val = []
                in_string = False
                escaped = False
            i += 1
            continue
            
        if in_string:
            if escaped:
                current_val.append(c)
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == string_char:
                if i + 1 < n and values_text[i + 1] == string_char:
                    current_val.append(c)
                    i += 1
                else:
                    in_string = False
            else:
                current_val.append(c)
            i += 1
            continue
            
        if c in ("'", '"'):
            in_string = True
            string_char = c
            escaped = False
            i += 1
            continue
            
        if c == ',':
            val_str = ''.join(current_val).strip()
            current_row.append(clean_val(val_str))
            current_val = []
            i += 1
            continue
            
        if c == ')':
            val_str = ''.join(current_val).strip()
            current_row.append(clean_val(val_str))
            rows.append(current_row)
            current_row = []
            current_val = []
            in_paren = False
            i += 1
            continue
            
        current_val.append(c)
        i += 1
        
    return rows


def clean_val(v):
    if v.upper() == 'NULL':
        return None
    if v.isdigit() or (v.startswith('-') and v[1:].isdigit()):
        return int(v)
    try:
        return float(v)
    except ValueError:
        pass
    return v


class Command(BaseCommand):
    help = "Imports data from a MySQL SQL dump file into the active PostgreSQL database."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='opulentl_schoolsaas.sql',
            help='Path to the MySQL .sql dump file'
        )
        parser.add_argument(
            '--db-url',
            type=str,
            default=None,
            help='Target DATABASE_URL (overrides settings.DATABASES)'
        )

    def handle(self, *args, **options):
        filepath = options['file']
        db_url = options['db_url'] or os.environ.get('DATABASE_URL')

        if not os.path.isabs(filepath):
            filepath = os.path.join(settings.BASE_DIR, filepath)

        if not os.path.exists(filepath):
            self.stderr.write(self.style.ERROR(f"File not found: {filepath}"))
            return

        self.stdout.write(self.style.NOTICE(f"Reading SQL dump from: {filepath}"))
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        insert_pattern = re.compile(
            r'INSERT\s+INTO\s+`([^`]+)`\s*\(([^)]+)\)\s*VALUES\s*(.*?);',
            re.DOTALL | re.IGNORECASE
        )

        blocks = insert_pattern.findall(content)
        self.stdout.write(self.style.SUCCESS(f"Found {len(blocks)} INSERT block(s) in SQL dump."))

        table_data = {}
        for table_name, cols_str, values_str in blocks:
            if table_name in ('django_migrations', 'django_content_type', 'auth_permission'):
                continue
            cols = [c.strip(' `\t\r\n') for c in cols_str.split(',')]
            rows = parse_sql_values(values_str)
            if table_name not in table_data:
                table_data[table_name] = {'cols': cols, 'rows': []}
            table_data[table_name]['rows'].extend(rows)

        self.import_postgresql(db_url, table_data)

    def import_postgresql(self, db_url, table_data):
        self.stdout.write(self.style.NOTICE("Connecting to Neon PostgreSQL..."))
        conn = psycopg2.connect(db_url)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            # Fetch all foreign key constraints from PostgreSQL
            cursor.execute("""
                SELECT
                    kcu.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    cols.is_nullable
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                      ON tc.constraint_name = kcu.constraint_name
                      AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                      ON ccu.constraint_name = tc.constraint_name
                      AND ccu.table_schema = tc.table_schema
                    JOIN information_schema.columns AS cols
                      ON cols.table_name = kcu.table_name
                      AND cols.column_name = kcu.column_name
                WHERE tc.constraint_type = 'FOREIGN KEY';
            """)
            fk_rows = cursor.fetchall()
            # fk_map: table_name -> list of (col_name, foreign_table, foreign_col, is_nullable)
            fk_map = {}
            for t_name, c_name, ft_name, fc_name, is_null in fk_rows:
                fk_map.setdefault(t_name, []).append({
                    'col': c_name,
                    'foreign_table': ft_name,
                    'foreign_col': fc_name,
                    'is_nullable': (is_null == 'YES')
                })

            all_tables = list(table_data.keys())
            ordered_tables = [t for t in TABLE_INSERT_ORDER if t in table_data]
            remaining_tables = [t for t in all_tables if t not in ordered_tables]
            process_order = ordered_tables + remaining_tables

            # Clean existing records in reverse dependency order
            self.stdout.write("Cleaning existing records for fresh import...")
            for table_name in reversed(process_order):
                if table_name in ('django_migrations', 'django_content_type', 'auth_permission'):
                    continue
                try:
                    cursor.execute(f'DELETE FROM "{table_name}";')
                except Exception:
                    pass

            # Cache of existing valid IDs per table: {table_name: set(ids)}
            existing_ids = {}
            # Preload django_site, django_content_type, etc.
            cursor.execute('SELECT "id" FROM "django_site";')
            existing_ids['django_site'] = {r[0] for r in cursor.fetchall()}

            imported_tables = 0
            imported_rows = 0

            for table_name in process_order:
                data = table_data[table_name]
                cols = data['cols']
                rows = data['rows']
                if not rows:
                    continue

                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = %s
                """, (table_name,))
                db_cols_info = cursor.fetchall()
                if not db_cols_info:
                    self.stdout.write(self.style.WARNING(f"  Skipping '{table_name}' (table does not exist in target DB)"))
                    continue

                db_cols_set = {r[0] for r in db_cols_info}
                col_types = {r[0]: r[1] for r in db_cols_info}

                valid_col_indices = [i for i, c in enumerate(cols) if c in db_cols_set]
                valid_cols = [cols[i] for i in valid_col_indices]

                if not valid_cols:
                    continue

                table_fks = fk_map.get(table_name, [])

                filtered_rows = []
                for row in rows:
                    row_dict = {}
                    for i in valid_col_indices:
                        val = row[i] if i < len(row) else None
                        c_name = cols[i]
                        c_type = col_types.get(c_name, '')
                        if c_type == 'boolean' and val is not None:
                            val = bool(val)
                        row_dict[c_name] = val

                    # Validate foreign key references
                    skip_row = False
                    for fk in table_fks:
                        fk_col = fk['col']
                        f_table = fk['foreign_table']
                        f_val = row_dict.get(fk_col)

                        if f_val is not None:
                            # Check if foreign ID exists
                            valid_f_ids = existing_ids.get(f_table)
                            if valid_f_ids is None:
                                # Query from DB if not in cache
                                try:
                                    cursor.execute(f'SELECT "id" FROM "{f_table}";')
                                    valid_f_ids = {r[0] for r in cursor.fetchall()}
                                    existing_ids[f_table] = valid_f_ids
                                except Exception:
                                    valid_f_ids = set()
                                    existing_ids[f_table] = valid_f_ids

                            if f_val not in valid_f_ids:
                                if fk['is_nullable']:
                                    # Set orphaned nullable FK to None
                                    row_dict[fk_col] = None
                                else:
                                    skip_row = True
                                    break

                    if skip_row:
                        continue

                    new_row = tuple(row_dict[c] for c in valid_cols)
                    filtered_rows.append(new_row)

                if not filtered_rows:
                    continue

                quoted_cols = [f'"{c}"' for c in valid_cols]
                col_list_sql = ", ".join(quoted_cols)
                
                if table_name in ('django_content_type', 'auth_permission'):
                    conflict_clause = 'ON CONFLICT DO NOTHING'
                elif 'id' in valid_cols:
                    update_cols = [f'"{c}" = EXCLUDED."{c}"' for c in valid_cols if c != 'id']
                    if update_cols:
                        conflict_clause = f'ON CONFLICT ("id") DO UPDATE SET {", ".join(update_cols)}'
                    else:
                        conflict_clause = 'ON CONFLICT ("id") DO NOTHING'
                else:
                    conflict_clause = 'ON CONFLICT DO NOTHING'

                insert_query = f"""
                    INSERT INTO "{table_name}" ({col_list_sql})
                    VALUES %s
                    {conflict_clause}
                """

                execute_values(cursor, insert_query, filtered_rows, page_size=500)
                imported_tables += 1
                imported_rows += len(filtered_rows)

                # Update existing_ids cache for this table
                if 'id' in valid_cols:
                    id_idx = valid_cols.index('id')
                    new_ids = {r[id_idx] for r in filtered_rows if r[id_idx] is not None}
                    existing_ids.setdefault(table_name, set()).update(new_ids)

                self.stdout.write(f"  [OK] Imported {len(filtered_rows)} row(s) into '{table_name}'")

            # Reset sequences for auto-increment columns
            self.stdout.write("Resetting PostgreSQL primary key sequences...")
            for table_name in process_order:
                data = table_data[table_name]
                if 'id' in data['cols']:
                    try:
                        cursor.execute(f"""
                            SELECT setval(
                                pg_get_serial_sequence('"{table_name}"', 'id'),
                                COALESCE((SELECT MAX("id") FROM "{table_name}"), 1),
                                true
                            );
                        """)
                    except Exception:
                        pass

            conn.commit()
            self.stdout.write(self.style.SUCCESS(
                f"\nSuccessfully imported {imported_rows} rows across {imported_tables} tables into PostgreSQL!"
            ))

        except Exception as e:
            conn.rollback()
            self.stderr.write(self.style.ERROR(f"Error during import: {e}"))
            raise e
        finally:
            cursor.close()
            conn.close()

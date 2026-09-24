"""
Force-clean all demo/sample data from the VASL tenant database.
Uses raw SQL with foreign keys disabled to bypass cascade ordering issues.
"""
import sys, os
sys.path.insert(0, r'c:\Users\BPI OFFICE\schoolsaas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
import django
django.setup()

from tenants.services import register_tenant_connection
register_tenant_connection('VASL')
from django.db import connections

DB_ALIAS = 'VASL'

def run_sql(cursor, sql, params=None):
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        count = cursor.rowcount
        if count and count > 0:
            print(f"  -> {count} rows affected: {sql[:80]}")
        return count
    except Exception as e:
        print(f"  [WARN] Error running SQL: {e}")
        print(f"         SQL: {sql[:100]}")
        return 0

print("=" * 60)
print("FORCE-CLEANING DEMO DATA FROM VASL DATABASE")
print("=" * 60)

conn = connections[DB_ALIAS]
with conn.cursor() as cur:
    # Step 1: Disable FK checks
    cur.execute("PRAGMA foreign_keys = OFF;")
    print("\n[1] Foreign keys disabled.")

    # Step 2: Get demo user IDs
    cur.execute("SELECT id FROM accounts_user WHERE email LIKE '%@demo.school' OR is_sample_data = 1")
    demo_user_ids = [row[0] for row in cur.fetchall()]
    print(f"\n[2] Found {len(demo_user_ids)} demo user records to remove.")

    if demo_user_ids:
        ids_csv = ','.join(str(i) for i in demo_user_ids)
        
        # Step 3: Delete all child/related records first (cascade manually)
        tables_with_user_fk = [
            # allauth
            'account_emailaddress',
            'socialaccount_socialaccount',
            # core
            'core_auditlog',
            'core_notification',
            'core_todo',
            'core_calendarevent',
            'core_loginevent',
            # academics
            'academics_classroutine',
            'academics_assignedsubject',
            # students
            'students_studenttimeline',
            'students_studentdocument',
            'students_studentsubject',
            'students_student',
            # HR
            'human_resource_teacher',
            'human_resource_staff',
            'human_resource_teacherprofile',
            # fees, finance
            'fees_feecollection',
            'finance_transaction',
            'finance_journalentry',
            # attendance
            'attendance_studentattendance',
            'attendance_staffattendance',
            # homework
            'homework_homeworkassignment',
            'homework_homeworksubmission',
            'homework_homeworkcomment',
            # exams
            'examinations_exammark',
            'examinations_examquestion',
            'examinations_exam',
            # library
            'library_bookissue',
            # communication
            'communication_message',
            'communication_notice',
            # clubs
            'clubs_clubmembership',
            'clubs_clubattendance',
            'clubs_clubachievement',
            # leave
            'leave_management_leave',
            # inventory
            'inventory_staffpayment',
            'inventory_expense',
            'inventory_distributionitem',
            # transport
            'transport_vehicleallocation',
            # dormitory
            'dormitory_roomallocation',
            # lesson plan
            'lesson_plan_lessonplan',
            # chat
            'chat_chatmembership',
            'chat_message',
            'chat_messagereaction',
            # certificates
            'certificates_certificate',
            # reports
            'reports_report',
            'reports_reportdistribution',
            # forum
            'chat_forumthread',
            'chat_forumpost',
        ]

        print(f"\n[3] Deleting related records for {len(demo_user_ids)} demo users...")
        for table in tables_with_user_fk:
            # Check if table exists first
            cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cur.fetchone():
                continue
            # Try user_id FK column
            for fk_col in ['user_id', 'teacher_id', 'staff_id', 'parent_id', 'created_by_id', 
                            'sender_id', 'recipient_id', 'member_id', 'student_id']:
                try:
                    cur.execute(f"PRAGMA table_info('{table}')")
                    cols = [r[1] for r in cur.fetchall()]
                    if fk_col in cols:
                        cur.execute(f"DELETE FROM \"{table}\" WHERE {fk_col} IN ({ids_csv})")
                        affected = cur.rowcount
                        if affected > 0:
                            print(f"  -> {affected} rows deleted from {table} (column: {fk_col})")
                except Exception as e:
                    pass

        # Step 4: Remove demo Students (may have FK to parent_user)
        print("\n[4] Removing demo Students...")
        run_sql(cur, f"DELETE FROM students_student WHERE user_id IN ({ids_csv}) OR parent_user_id IN ({ids_csv})")

        # Step 5: Remove demo Users
        print("\n[5] Removing demo User records...")
        cur.execute(f"DELETE FROM accounts_user WHERE id IN ({ids_csv})")
        print(f"  -> {cur.rowcount} demo users deleted from accounts_user.")

    # Step 6: Remove demo academics data
    print("\n[6] Removing demo academic records (subjects, classes, houses, routines)...")
    
    sub_codes = ('MATH101', 'ENG101', 'SCI101', 'SOC101', 'COMP101', 'PE101', 'KIS101')
    sub_codes_csv = ','.join(f"'{c}'" for c in sub_codes)
    
    demo_classes = ('Grade 1','Grade 2','Grade 3','Grade 4','Grade 5',
                    'Grade 6','Grade 7','Grade 8','Grade 9','Grade 10')
    classes_csv = ','.join(f"'{c}'" for c in demo_classes)
    
    # Get class IDs
    cur.execute(f"SELECT id FROM academics_class WHERE name IN ({classes_csv})")
    class_ids = [r[0] for r in cur.fetchall()]
    
    if class_ids:
        class_ids_csv = ','.join(str(i) for i in class_ids)
        run_sql(cur, f"DELETE FROM academics_classroutine WHERE class_name_id IN ({class_ids_csv})")
        run_sql(cur, f"DELETE FROM academics_assignedsubject WHERE class_name_id IN ({class_ids_csv})")
        run_sql(cur, f"DELETE FROM academics_section WHERE class_name_id IN ({class_ids_csv})")
    
    run_sql(cur, f"DELETE FROM academics_assignedsubject WHERE subject_id IN (SELECT id FROM academics_subject WHERE code IN ({sub_codes_csv}))")
    run_sql(cur, f"DELETE FROM academics_subject WHERE code IN ({sub_codes_csv})")
    run_sql(cur, f"DELETE FROM academics_class WHERE name IN ({classes_csv})")
    
    house_names = ('Simba House (Red)', 'Chui House (Blue)', 'Kifaru House (Green)', 'Twiga House (Yellow)')
    houses_csv = ','.join(f"'{h}'" for h in house_names)
    run_sql(cur, f"DELETE FROM academics_house WHERE name IN ({houses_csv})")
    
    # Step 7: Remove demo HR departments & designations
    print("\n[7] Removing demo HR departments and designations...")
    dept_codes = ('SCI_DEPT', 'MATH_DEPT', 'LANG_DEPT', 'HUM_DEPT', 'ADMIN_DEPT')
    dept_csv = ','.join(f"'{c}'" for c in dept_codes)
    des_codes = ('DES_SR_TCH', 'DES_ASST_TCH', 'DES_ACCT', 'DES_LIB', 'DES_RECEPT', 'DES_WARDEN')
    des_csv = ','.join(f"'{c}'" for c in des_codes)
    
    run_sql(cur, f"DELETE FROM human_resource_department WHERE code IN ({dept_csv})")
    run_sql(cur, f"DELETE FROM human_resource_designation WHERE code IN ({des_csv})")
    
    # Step 8: Re-enable FK
    cur.execute("PRAGMA foreign_keys = ON;")
    print("\n[8] Foreign keys re-enabled.")

print("\n[9] Verifying results...")
with conn.cursor() as cur:
    cur.execute("SELECT count(*) FROM accounts_user WHERE email LIKE '%@demo.school' OR is_sample_data = 1")
    remaining = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM accounts_user")
    total = cur.fetchone()[0]
    print(f"  Demo users remaining: {remaining}")
    print(f"  Total users remaining: {total}")

print("\n" + "=" * 60)
print("DONE! Please restart Django dev server for changes to take effect.")
print("=" * 60)

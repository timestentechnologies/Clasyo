import random
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command

from django.db import transaction

logger = logging.getLogger(__name__)

_PASSWORD_HASH_CACHE = {}


def get_cached_hash(password: str) -> str:
    if password not in _PASSWORD_HASH_CACHE:
        from django.contrib.auth.hashers import make_password
        _PASSWORD_HASH_CACHE[password] = make_password(password)
    return _PASSWORD_HASH_CACHE[password]


def generate_all_sample_data_for_school(school, db_alias=None):
    """
    Populates comprehensive, interlinked sample data across ALL platform modules
    inside the school's dedicated tenant database (db_alias).
    """
    if not db_alias:
        db_alias = school.slug

    from tenants.services import register_tenant_connection, ensure_school_database
    from tenants.threadlocals import set_current_tenant_db, get_current_tenant_db
    register_tenant_connection(db_alias)
    ensure_school_database(school)
    set_current_tenant_db(db_alias)

    with transaction.atomic(using=db_alias):
        return _generate_all_sample_data_internal(school, db_alias)


def _generate_all_sample_data_internal(school, db_alias):
    # Import models dynamically
    from tenants.models import School
    from accounts.models import User
    from core.models import AcademicYear
    from academics.models import Class, Section, Subject, AssignedSubject, House, ClassRoutine
    from human_resource.models import Department, Designation, Teacher, Staff
    from students.models import StudentCategory, Student
    from fees.models import FeeStructure, FeeCollection
    from finance.models import Account, Transaction, ensure_default_accounts_for_school
    from inventory.models import Expense
    from library.models import BookCategory, Author, Publisher, Book, BookCopy, BookIssue
    from dormitory.models import Dormitory, Room, RoomAllocation
    from examinations.models import Exam, Grade, ExamMark, ExamQuestion, ExamSubjectConfig
    from leave_management.models import LeaveType, Leave
    from clubs.models import Club, ClubMembership, ClubActivity
    from attendance.models import StudentAttendance, StaffAttendance
    from communication.models import Notice
    from transport.models import Route, Vehicle, RouteStop

    logger.info(f"[SampleData] Starting sample data generation for school '{school.name}' on DB '{db_alias}'...")

    # Ensure School record exists in tenant DB with active subscription
    from subscriptions.models import SubscriptionPlan, Subscription, Payment, Invoice
    school_obj = School.objects.using(db_alias).filter(pk=school.pk).first()
    if not school_obj:
        school_obj = School.objects.using('default').get(pk=school.pk)

    plan_obj = SubscriptionPlan.objects.using(db_alias).filter(id=3).first() or SubscriptionPlan.objects.using(db_alias).first()
    school_obj.subscription_plan = plan_obj
    school_obj.subscription_start_date = date(2026, 1, 1)
    school_obj.subscription_end_date = date(2027, 12, 31)
    school_obj.is_trial = False
    school_obj.is_active = True
    school_obj.save(using=db_alias)

    if plan_obj:
        sub_obj, _ = Subscription.objects.using(db_alias).get_or_create(
            school=school_obj,
            plan=plan_obj,
            defaults={
                'start_date': date(2026, 1, 1),
                'end_date': date(2027, 12, 31),
                'status': 'active',
                'is_trial': False,
                'auto_renew': True,
            }
        )
        sub_obj.status = 'active'
        sub_obj.start_date = date(2026, 1, 1)
        sub_obj.end_date = date(2027, 12, 31)
        sub_obj.save(using=db_alias)

    stats = {}

    # -------------------------------------------------------------
    # 1. ACADEMIC YEAR
    # -------------------------------------------------------------
    current_year = date.today().year
    academic_year, _ = AcademicYear.objects.using(db_alias).get_or_create(
        school=school_obj,
        name=f"{current_year}-{current_year+1}",
        defaults={
            'start_date': date(current_year, 1, 10),
            'end_date': date(current_year, 12, 15),
            'is_active': True
        }
    )

    # -------------------------------------------------------------
    # 2. ACADEMICS (Classes, Sections, Subjects, Houses)
    # -------------------------------------------------------------
    house_colors = [('Red House', '#ef4444'), ('Blue House', '#3b82f6'), ('Green House', '#22c55e'), ('Yellow House', '#eab308')]
    houses = []
    for h_name, color in house_colors:
        h, _ = House.objects.using(db_alias).get_or_create(
            name=h_name,
            defaults={'color': color, 'description': f'The prestigious {h_name}'}
        )
        houses.append(h)

    class_names = [
        ('Grade 1', 1, 'lower_primary'),
        ('Grade 2', 2, 'lower_primary'),
        ('Grade 3', 3, 'lower_primary'),
        ('Grade 4', 4, 'upper_primary'),
        ('Grade 5', 5, 'upper_primary'),
        ('Grade 6', 6, 'upper_primary'),
        ('Grade 7', 7, 'junior_secondary'),
        ('Grade 8', 8, 'junior_secondary'),
        ('Grade 9', 9, 'junior_secondary'),
        ('Grade 10', 10, 'senior_secondary'),
    ]

    created_classes = []
    created_sections = []
    for order, (c_name, num, level) in enumerate(class_names, start=1):
        cls_obj, _ = Class.objects.using(db_alias).get_or_create(
            school=school_obj,
            name=c_name,
            defaults={
                'numeric_name': num,
                'education_level': level,
                'order': order,
                'is_active': True
            }
        )
        created_classes.append(cls_obj)

        for sec_letter in ['A', 'B']:
            sec_obj, _ = Section.objects.using(db_alias).get_or_create(
                class_name=cls_obj,
                name=sec_letter,
                defaults={'max_students': 35, 'is_active': True}
            )
            created_sections.append(sec_obj)

    subjects_data = [
        ('Mathematics', 'MATH101', 'both', 4),
        ('English Language', 'ENG101', 'theory', 4),
        ('General Science', 'SCI101', 'both', 3),
        ('Social Studies', 'SOC101', 'theory', 3),
        ('Computer Studies', 'COMP101', 'practical', 3),
        ('Physical Education', 'PE101', 'practical', 2),
        ('Kiswahili Language', 'KIS101', 'theory', 3),
    ]

    created_subjects = []
    for s_name, code, s_type, credits_val in subjects_data:
        sub_obj, _ = Subject.objects.using(db_alias).get_or_create(
            code=code,
            defaults={
                'school': school_obj,
                'name': s_name,
                'subject_type': s_type,
                'credits': credits_val,
                'is_active': True
            }
        )
        created_subjects.append(sub_obj)

    # -------------------------------------------------------------
    # 3. HR DEPARTMENTS & DESIGNATIONS
    # -------------------------------------------------------------
    depts_data = [
        ('Science & Technology', 'SCI_DEPT', 'Science and ICT faculty'),
        ('Mathematics', 'MATH_DEPT', 'Mathematics faculty'),
        ('Languages', 'LANG_DEPT', 'English, French, Kiswahili languages'),
        ('Humanities', 'HUM_DEPT', 'History, Geography, Social studies'),
        ('Administration & Finance', 'ADMIN_DEPT', 'Accounts and administrative staff'),
    ]

    created_depts = []
    for d_name, code, desc in depts_data:
        dept, _ = Department.objects.using(db_alias).get_or_create(
            code=code,
            defaults={'school': school_obj, 'name': d_name, 'description': desc, 'is_active': True}
        )
        created_depts.append(dept)

    designations_data = [
        ('Senior Teacher', 'DES_SR_TCH', 1),
        ('Assistant Teacher', 'DES_ASST_TCH', 2),
        ('Chief Accountant', 'DES_ACCT', 1),
        ('Senior Librarian', 'DES_LIB', 2),
        ('Receptionist', 'DES_RECEPT', 3),
        ('Hostel Warden', 'DES_WARDEN', 3),
    ]

    created_designations = []
    for des_name, code, level in designations_data:
        des, _ = Designation.objects.using(db_alias).get_or_create(
            code=code,
            defaults={'school': school_obj, 'name': des_name, 'level': level, 'is_active': True}
        )
        created_designations.append(des)

    # -------------------------------------------------------------
    # 4. TEACHERS (5)
    # -------------------------------------------------------------
    teachers_list = [
        ('Robert', 'Anderson', 'robert.anderson@demo.school', 'MATH_DEPT', 'DES_SR_TCH', 3200),
        ('Sarah', 'Jenkins', 'sarah.jenkins@demo.school', 'SCI_DEPT', 'DES_SR_TCH', 3100),
        ('Michael', 'Clark', 'michael.clark@demo.school', 'LANG_DEPT', 'DES_ASST_TCH', 2800),
        ('Emily', 'Watson', 'emily.watson@demo.school', 'HUM_DEPT', 'DES_ASST_TCH', 2750),
        ('David', 'Miller', 'david.miller@demo.school', 'SCI_DEPT', 'DES_ASST_TCH', 2900),
    ]

    created_teachers = []
    for i, (fn, ln, email, d_code, des_code, salary) in enumerate(teachers_list, start=1):
        user, u_created = User.objects.using(db_alias).get_or_create(
            email=email,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'teacher',
                'school': school_obj,
                'is_active': True,
                'is_sample_data': True,
                'phone': f'+155501000{i}'
            }
        )
        if u_created:
            user.password = get_cached_hash('teacher123')
            user.save(using=db_alias)

        dept = next((d for d in created_depts if d.code == d_code), created_depts[0])
        des = next((d for d in created_designations if d.code == des_code), created_designations[0])

        tch, _ = Teacher.objects.using(db_alias).get_or_create(
            user=user,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'employee_id': f'EMP-T10{i}',
                'department': dept,
                'designation': des,
                'basic_salary': Decimal(str(salary)),
                'allowances': Decimal('300.00'),
                'date_of_joining': date(2022, 1, 15),
                'phone': f'+155501000{i}',
                'email': email,
                'address': f'{100+i} Academic Avenue, Campus City',
                'is_active': True,
                'is_sample_data': True
            }
        )
        created_teachers.append(tch)

    stats['teachers'] = len(created_teachers)

    # Assign Class Teachers & Subjects
    for idx, sec in enumerate(created_sections[:len(created_teachers)]):
        sec.class_teacher = created_teachers[idx].user
        sec.save(using=db_alias)

    for cls_item in created_classes[:3]:
        for sub_item in created_subjects[:3]:
            AssignedSubject.objects.using(db_alias).get_or_create(
                class_name=cls_item,
                subject=sub_item,
                academic_year=academic_year,
                defaults={
                    'teacher': created_teachers[0].user,
                    'is_active': True
                }
            )

    # -------------------------------------------------------------
    # 5. STAFF (4)
    # -------------------------------------------------------------
    staff_list = [
        ('James', 'Wilson', 'accountant@demo.school', 'accountant', 'ADMIN_DEPT', 'DES_ACCT', 2600),
        ('Patricia', 'Taylor', 'librarian@demo.school', 'librarian', 'ADMIN_DEPT', 'DES_LIB', 2200),
        ('Linda', 'Martinez', 'receptionist@demo.school', 'receptionist', 'ADMIN_DEPT', 'DES_RECEPT', 1800),
        ('Thomas', 'White', 'warden@demo.school', 'staff', 'ADMIN_DEPT', 'DES_WARDEN', 2000),
    ]

    created_staff = []
    for i, (fn, ln, email, role, d_code, des_code, salary) in enumerate(staff_list, start=1):
        st_user, u_created = User.objects.using(db_alias).get_or_create(
            email=email,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': role,
                'school': school_obj,
                'is_active': True,
                'is_sample_data': True,
                'phone': f'+155502000{i}'
            }
        )
        if u_created:
            st_user.password = get_cached_hash('staff123')
            st_user.save(using=db_alias)

        dept = next((d for d in created_depts if d.code == d_code), created_depts[-1])
        des = next((d for d in created_designations if d.code == des_code), created_designations[-1])

        st_obj, _ = Staff.objects.using(db_alias).get_or_create(
            user=st_user,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'employee_id': f'EMP-S10{i}',
                'department': dept,
                'designation': des,
                'basic_salary': Decimal(str(salary)),
                'allowances': Decimal('200.00'),
                'date_of_joining': date(2023, 3, 1),
                'phone': f'+155502000{i}',
                'email': email,
                'address': f'{200+i} Administrative Way, Campus City',
                'is_active': True,
                'is_sample_data': True
            }
        )
        created_staff.append(st_obj)

    stats['staff'] = len(created_staff)

    # -------------------------------------------------------------
    # 6. PARENTS (10)
    # -------------------------------------------------------------
    parents_list = [
        ('Arthur', 'Pendelton', 'parent1@demo.school', 'Engineer'),
        ('Beatrice', 'Gomez', 'parent2@demo.school', 'Doctor'),
        ('Charles', 'Harris', 'parent3@demo.school', 'Architect'),
        ('Diana', 'Prince', 'parent4@demo.school', 'Lawyer'),
        ('Edward', 'Norton', 'parent5@demo.school', 'Accountant'),
        ('Fiona', 'Gallagher', 'parent6@demo.school', 'Business Owner'),
        ('George', 'Stacy', 'parent7@demo.school', 'Police Officer'),
        ('Helen', 'Mirren', 'parent8@demo.school', 'Professor'),
        ('Ian', 'Malcolm', 'parent9@demo.school', 'Data Scientist'),
        ('Julia', 'Roberts', 'parent10@demo.school', 'Journalist'),
    ]

    created_parents = []
    for i, (fn, ln, email, occ) in enumerate(parents_list, start=1):
        p_user, u_created = User.objects.using(db_alias).get_or_create(
            email=email,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'parent',
                'school': school_obj,
                'is_active': True,
                'is_sample_data': True,
                'phone': f'+155503000{i}',
                'address': f'{300+i} Residential Boulevard, Metro City'
            }
        )
        if u_created:
            p_user.password = get_cached_hash('parent123')
            p_user.save(using=db_alias)
        created_parents.append(p_user)

    stats['parents'] = len(created_parents)

    # -------------------------------------------------------------
    # 7. STUDENTS (15)
    # -------------------------------------------------------------
    student_category, _ = StudentCategory.objects.using(db_alias).get_or_create(
        name='General Student',
        defaults={'description': 'Regular enrolled full-time student', 'is_active': True}
    )

    students_names = [
        ('Ethan', 'Pendelton', 'male', date(2014, 5, 12)),
        ('Sophia', 'Gomez', 'female', date(2015, 3, 22)),
        ('Lucas', 'Harris', 'male', date(2013, 11, 8)),
        ('Emma', 'Prince', 'female', date(2014, 8, 14)),
        ('Oliver', 'Norton', 'male', date(2015, 1, 30)),
        ('Amelia', 'Gallagher', 'female', date(2013, 7, 19)),
        ('Mason', 'Stacy', 'male', date(2014, 12, 5)),
        ('Harper', 'Mirren', 'female', date(2015, 4, 17)),
        ('Logan', 'Malcolm', 'male', date(2013, 9, 25)),
        ('Charlotte', 'Roberts', 'female', date(2014, 2, 10)),
        ('Benjamin', 'Pendelton', 'male', date(2016, 6, 11)),
        ('Mia', 'Gomez', 'female', date(2016, 10, 2)),
        ('Elijah', 'Harris', 'male', date(2012, 12, 14)),
        ('Evelyn', 'Prince', 'female', date(2013, 1, 9)),
        ('Alexander', 'Norton', 'male', date(2012, 4, 28)),
    ]

    created_students = []
    for i, (fn, ln, gender, dob) in enumerate(students_names, start=1):
        email = f'student{i}@demo.school'
        s_user, u_created = User.objects.using(db_alias).get_or_create(
            email=email,
            defaults={
                'first_name': fn,
                'last_name': ln,
                'role': 'student',
                'school': school_obj,
                'is_active': True,
                'is_sample_data': True,
                'gender': gender,
                'date_of_birth': dob
            }
        )
        if u_created:
            s_user.password = get_cached_hash('student123')
            s_user.save(using=db_alias)

        assigned_class = created_classes[(i-1) % len(created_classes)]
        assigned_sec = created_sections[(i-1) % len(created_sections)]
        parent_user = created_parents[(i-1) % len(created_parents)]
        house_obj = houses[(i-1) % len(houses)]

        stu_obj, _ = Student.objects.using(db_alias).get_or_create(
            user=s_user,
            defaults={
                'admission_number': f'ADM-2026-{i:03d}',
                'roll_number': f'R-10{i}',
                'first_name': fn,
                'last_name': ln,
                'gender': gender,
                'date_of_birth': dob,
                'admission_date': date(2024, 1, 10),
                'current_class': assigned_class,
                'section': assigned_sec,
                'category': student_category,
                'house': house_obj,
                'academic_year': academic_year,
                'school': school_obj,
                'parent_user': parent_user,
                'father_name': f"{parent_user.first_name} {parent_user.last_name}",
                'father_phone': parent_user.phone,
                'mother_name': f"Mary {parent_user.last_name}",
                'current_address': f'{400+i} Student Residence, Campus Town',
                'city': 'Campus Town',
                'state': 'State Region',
                'country': 'US',
                'postal_code': '90210',
                'is_active': True,
                'is_sample_data': True
            }
        )
        created_students.append(stu_obj)

    stats['students'] = len(created_students)

    # -------------------------------------------------------------
    # 8. FEES & INVOICES (12)
    # -------------------------------------------------------------
    fee_structures_data = [
        ('Term Tuition Fee', 'tuition', Decimal('500.00')),
        ('School Transport Fee', 'transport', Decimal('150.00')),
        ('Digital Library Access', 'library', Decimal('50.00')),
        ('Annual Science & IT Lab Fee', 'lab', Decimal('80.00')),
    ]

    created_fee_structs = []
    for f_name, f_type, f_amt in fee_structures_data:
        fs, _ = FeeStructure.objects.using(db_alias).get_or_create(
            name=f_name,
            class_name=created_classes[0],
            defaults={
                'fee_type': f_type,
                'amount': f_amt,
                'description': f'{f_name} for current term',
                'is_active': True,
                'is_sample_data': True
            }
        )
        created_fee_structs.append(fs)

    ensure_default_accounts_for_school(school_obj)
    bank_account = Account.objects.using(db_alias).filter(school=school_obj, sub_type='bank').first()

    statuses = ['paid', 'paid', 'partial', 'pending', 'paid', 'pending', 'paid', 'paid', 'partial', 'pending', 'paid', 'paid']
    created_invoices = []
    for i, stu in enumerate(created_students[:12], start=1):
        status = statuses[i-1]
        struct = created_fee_structs[(i-1) % len(created_fee_structs)]
        amount = struct.amount
        paid_amt = amount if status == 'paid' else (amount / Decimal('2.00') if status == 'partial' else Decimal('0.00'))

        fc, _ = FeeCollection.objects.using(db_alias).get_or_create(
            receipt_number=f'REC-2026-{i:04d}',
            defaults={
                'student': stu,
                'fee_structure': struct,
                'amount': amount,
                'paid_amount': paid_amt,
                'payment_status': status,
                'payment_method': 'bank_transfer' if status != 'pending' else None,
                'payment_date': date.today() - timedelta(days=i*2) if status != 'pending' else None,
                'due_date': date.today() + timedelta(days=15),
                'deposit_account': bank_account,
                'collected_by': created_staff[0].user,
                'notes': f'Sample fee collection invoice {i}',
                'is_sample_data': True
            }
        )
        created_invoices.append(fc)

    stats['invoices'] = len(created_invoices)

    # -------------------------------------------------------------
    # 9. EXPENSES (8)
    # -------------------------------------------------------------
    expenses_data = [
        ('EXP-2026-001', 'purchase', 'Science Laboratory Chemicals & Equipment', Decimal('450.00'), 'Scientific Supplies Co.'),
        ('EXP-2026-002', 'utility', 'Monthly Electricity & Water Utility Bill', Decimal('680.00'), 'City Power & Water Ltd'),
        ('EXP-2026-003', 'maintenance', 'School Bus #1 Brake Repair & Servicing', Decimal('320.00'), 'AutoCare Service Hub'),
        ('EXP-2026-004', 'other', 'Library Management Software License Renewal', Decimal('150.00'), 'EdTech Solutions Inc.'),
        ('EXP-2026-005', 'purchase', 'Sports Footballs and Basketballs Gear', Decimal('280.00'), 'Nike Sports Supplier'),
        ('EXP-2026-006', 'utility', 'High-Speed Fiber Internet Bill', Decimal('220.00'), 'Telecom Communications'),
        ('EXP-2026-007', 'other', 'Printer Paper and Examination Printing Supplies', Decimal('190.00'), 'Paper World Ltd'),
        ('EXP-2026-008', 'maintenance', 'Classroom Air Conditioning Servicing', Decimal('410.00'), 'Cooling Tech Services'),
    ]

    created_expenses = []
    for exp_num, e_type, desc, amt, payee in expenses_data:
        exp_obj, _ = Expense.objects.using(db_alias).get_or_create(
            expense_number=exp_num,
            defaults={
                'school': school_obj,
                'expense_type': e_type,
                'description': desc,
                'amount': amt,
                'expense_date': date.today() - timedelta(days=random.randint(5, 30)),
                'payment_method': 'bank_transfer',
                'payee_name': payee,
                'created_by': created_staff[0].user,
                'is_sample_data': True
            }
        )
        created_expenses.append(exp_obj)

    stats['expenses'] = len(created_expenses)

    # -------------------------------------------------------------
    # 10. LIBRARY (Categories, Authors, Publishers, Books, Issues)
    # -------------------------------------------------------------
    cat_names = ['Fiction & Literature', 'Science & Technology', 'Mathematics', 'History & Geography', 'Biographies']
    created_book_cats = []
    for c_name in cat_names:
        cat, _ = BookCategory.objects.using(db_alias).get_or_create(
            school=school_obj,
            name=c_name,
            defaults={'description': f'Books in {c_name}', 'is_active': True}
        )
        created_book_cats.append(cat)

    publisher, _ = Publisher.objects.using(db_alias).get_or_create(
        school=school_obj,
        name='Oxford Educational Press',
        defaults={'contact_person': 'Sales Desk', 'email': 'sales@oxfordpress.demo'}
    )

    authors_data = ['William Shakespeare', 'Albert Einstein', 'Isaac Newton', 'J.K. Rowling', 'Stephen Hawking']
    created_authors = []
    for a_name in authors_data:
        aut, _ = Author.objects.using(db_alias).get_or_create(
            school=school_obj,
            name=a_name
        )
        created_authors.append(aut)

    books_data = [
        ('Fundamentals of Algebra', '978-0134494074', created_book_cats[2], 5, Decimal('45.00')),
        ('Principles of Physics', '978-0321973611', created_book_cats[1], 4, Decimal('55.00')),
        ('World History: Ancient Civilizations', '978-0078799815', created_book_cats[3], 6, Decimal('40.00')),
        ('Classic Literature Anthology', '978-0140449136', created_book_cats[0], 8, Decimal('25.00')),
        ('Brief History of Time', '978-0553380163', created_book_cats[1], 3, Decimal('30.00')),
    ]

    created_books = []
    for i, (title, isbn, cat_obj, qty, price) in enumerate(books_data, start=1):
        bk, _ = Book.objects.using(db_alias).get_or_create(
            title=title,
            school=school_obj,
            defaults={
                'isbn': isbn,
                'category': cat_obj,
                'publisher': publisher,
                'quantity': qty,
                'available_quantity': qty - 1,
                'price': price,
                'call_number': f'CALL-{100+i}',
                'location': f'Shelf {i}A',
                'status': 'available',
                'is_sample_data': True
            }
        )
        bk.authors.add(created_authors[(i-1) % len(created_authors)])
        created_books.append(bk)

        # Create Book Copy & Book Issue
        copy_obj, _ = BookCopy.objects.using(db_alias).get_or_create(
            accession_number=f'ACC-2026-00{i}',
            defaults={'book': bk, 'status': 'issued', 'condition': 'good'}
        )

        BookIssue.objects.using(db_alias).get_or_create(
            book_copy=copy_obj,
            student=created_students[(i-1) % len(created_students)],
            defaults={
                'book': bk,
                'user': created_students[(i-1) % len(created_students)].user,
                'issue_date': date.today() - timedelta(days=7),
                'due_date': date.today() + timedelta(days=7),
                'status': 'issued',
                'issued_by': created_staff[1].user,
            }
        )

    stats['books'] = len(created_books)

    # -------------------------------------------------------------
    # 11. DORMITORIES (Hostels, Rooms, Allocations)
    # -------------------------------------------------------------
    dorm_boys, _ = Dormitory.objects.using(db_alias).get_or_create(
        school=school_obj,
        name='Sunrise Boys Hostel',
        defaults={'dormitory_type': 'boys', 'total_capacity': 40, 'is_active': True, 'is_sample_data': True}
    )

    room101, _ = Room.objects.using(db_alias).get_or_create(
        dormitory=dorm_boys,
        room_number='101',
        defaults={'capacity': 4, 'current_occupancy': 2, 'floor': 1, 'is_active': True}
    )

    RoomAllocation.objects.using(db_alias).get_or_create(
        student=created_students[0],
        defaults={
            'room': room101,
            'bed_number': 'Bed-A',
            'monthly_fee': Decimal('120.00'),
            'start_date': date(2026, 1, 10),
            'is_active': True,
        }
    )

    stats['dormitories'] = 1

    # -------------------------------------------------------------
    # 12. EXAMS & MARKS
    # -------------------------------------------------------------
    exam_obj, _ = Exam.objects.using(db_alias).get_or_create(
        name='Term 1 Mid-Term Examination 2026',
        school=school_obj,
        defaults={
            'exam_type': 'midterm',
            'start_date': date.today() - timedelta(days=14),
            'end_date': date.today() - timedelta(days=7),
            'class_assigned': created_classes[0],
            'subject': created_subjects[0],
            'is_published': True,
            'created_by': created_teachers[0].user,
            'is_sample_data': True
        }
    )

    grade_a, _ = Grade.objects.using(db_alias).get_or_create(
        school=school_obj,
        name='A',
        defaults={'min_percentage': Decimal('80.00'), 'max_percentage': Decimal('100.00'), 'point': Decimal('4.00')}
    )

    for i, stu in enumerate(created_students[:5], start=1):
        ExamMark.objects.using(db_alias).get_or_create(
            exam=exam_obj,
            student=stu,
            subject=created_subjects[0],
            defaults={
                'marks_obtained': Decimal(str(75 + i*4)),
                'total_marks': Decimal('100.00'),
                'grade': grade_a,
                'remarks': 'Excellent academic performance'
            }
        )

    stats['exams'] = 1

    # -------------------------------------------------------------
    # 13. LEAVES
    # -------------------------------------------------------------
    l_type, _ = LeaveType.objects.using(db_alias).get_or_create(
        school=school_obj,
        name='Medical / Sick Leave',
        defaults={'max_days': 10, 'description': 'Medical sick leave', 'is_active': True}
    )

    Leave.objects.using(db_alias).get_or_create(
        applicant_type='teacher',
        teacher=created_teachers[1].user,
        leave_type=l_type,
        defaults={
            'school': school_obj,
            'from_date': date.today() - timedelta(days=3),
            'to_date': date.today() - timedelta(days=1),
            'total_days': 3,
            'reason': 'High flu and fever doctor recommended rest',
            'status': 'approved',
            'approved_by': created_staff[0].user,
            'is_sample_data': True
        }
    )

    stats['leaves'] = 1

    # -------------------------------------------------------------
    # 14. CLUBS
    # -------------------------------------------------------------
    club_obj, _ = Club.objects.using(db_alias).get_or_create(
        name='Science & Robotics Society',
        school=school_obj,
        defaults={
            'description': 'Building innovative STEM and robotics projects',
            'club_type': 'technology',
            'teacher_advisor': created_teachers[1].user,
            'meeting_day': 'wednesday',
            'meeting_venue': 'Science Lab 2',
            'max_members': 30,
            'is_active': True,
            'is_sample_data': True
        }
    )

    ClubMembership.objects.using(db_alias).get_or_create(
        student=created_students[0].user,
        club=club_obj,
        defaults={
            'status': 'active',
            'application_reason': 'Passionate about robotics and AI programming',
            'position_held': 'President',
            'parent_consent': True,
            'fee_paid': True
        }
    )

    ClubActivity.objects.using(db_alias).get_or_create(
        club=club_obj,
        title='Annual High School Robotics Workshop',
        defaults={
            'description': 'Hands-on workshop building micro-controller bots',
            'activity_type': 'workshop',
            'date': timezone.now() + timedelta(days=5),
            'duration': timedelta(hours=2),
            'venue': 'Main Auditorium'
        }
    )

    stats['clubs'] = 1

    # -------------------------------------------------------------
    # 15. COMMUNICATION (Notices)
    # -------------------------------------------------------------
    Notice.objects.using(db_alias).get_or_create(
        title='Welcome to New Academic Term 2026',
        defaults={
            'content': 'We welcome all students, parents, and faculty staff to the new academic term!',
            'target_audience': 'all',
            'priority': 'normal',
            'created_by': created_staff[0].user
        }
    )

    # -------------------------------------------------------------
    # 16. TRANSPORT & ROUTES
    # -------------------------------------------------------------
    route_obj, _ = Route.objects.using(db_alias).get_or_create(
        name='North Metro Express Route',
        defaults={
            'school': school_obj,
            'route_number': 'R-01',
            'fare': Decimal('150.00'),
            'start_place': 'North Terminal Station',
            'end_place': 'Main School Gate',
            'is_active': True
        }
    )

    Vehicle.objects.using(db_alias).get_or_create(
        vehicle_number='KAA 890B',
        defaults={
            'school': school_obj,
            'vehicle_model': 'Toyota Coaster 35-Seater',
            'vehicle_type': 'bus',
            'capacity': 35,
            'route': route_obj,
            'is_active': True
        }
    )

    # -------------------------------------------------------------
    # 17. ATTENDANCE (Students & Staff)
    # -------------------------------------------------------------
    try:
        from attendance.models import StudentAttendance, StaffAttendance
        today = date.today()
        yesterday = today - timedelta(days=1)
        for stu in created_students[:10]:
            StudentAttendance.objects.using(db_alias).get_or_create(
                student=stu,
                date=today,
                defaults={
                    'school': school_obj,
                    'class_name': stu.current_class,
                    'section': stu.section,
                    'status': 'present',
                    'marked_by': created_teachers[0].user
                }
            )
            StudentAttendance.objects.using(db_alias).get_or_create(
                student=stu,
                date=yesterday,
                defaults={
                    'school': school_obj,
                    'class_name': stu.current_class,
                    'section': stu.section,
                    'status': 'present',
                    'marked_by': created_teachers[0].user
                }
            )

        for tch in created_teachers[:3]:
            StaffAttendance.objects.using(db_alias).get_or_create(
                staff=tch.user,
                date=today,
                defaults={
                    'school': school_obj,
                    'status': 'present'
                }
            )
    except Exception as e:
        logger.warning(f"Error seeding sample attendance: {e}")

    # -------------------------------------------------------------
    # 18. HOMEWORK
    # -------------------------------------------------------------
    try:
        from homework.models import HomeworkAssignment
        HomeworkAssignment.objects.using(db_alias).get_or_create(
            title='Algebra & Linear Equations Practice 1',
            class_ref=created_classes[0],
            subject=created_subjects[0],
            academic_year=academic_year,
            defaults={
                'description': 'Solve exercises 1 through 10 on page 42 of the Algebra textbook.',
                'instructions': 'Show all calculation steps clearly. Due next Monday.',
                'status': 'published',
                'is_published': True,
                'submission_type': 'both',
                'assigned_date': timezone.now().date(),
                'due_date': timezone.now() + timedelta(days=5),
                'points': Decimal('20.00'),
                'created_by': created_teachers[0].user
            }
        )
    except Exception as e:
        logger.warning(f"Error seeding sample homework: {e}")

    # -------------------------------------------------------------
    # 19. CALENDAR EVENTS
    # -------------------------------------------------------------
    try:
        from core.models import CalendarEvent
        events_data = [
            ('Annual Science & Robotics Exhibition', 'Showcase of student STEM inventions and engineering projects.', 'event', 3, 'Main Assembly Hall'),
            ('Term 1 Parents-Teachers Conference', 'Comprehensive review of academic progress with parents and guardians.', 'meeting', 7, 'School Auditorium & Classrooms'),
            ('Inter-House Athletics Championship', 'Annual sports competitions across houses: track, football, and relays.', 'event', 12, 'School Sports Complex'),
            ('Midterm Examination Week', 'Standardized mid-term examinations for all grades.', 'exam', 18, 'All Classrooms'),
            ('National Public Holiday', 'School closed in celebration of the national public holiday.', 'holiday', 25, 'Campus-wide'),
        ]
        now = timezone.now()
        for title, desc, ev_type, days_offset, loc in events_data:
            start_dt = now + timedelta(days=days_offset, hours=9)
            end_dt = start_dt + timedelta(hours=4)
            CalendarEvent.objects.using(db_alias).get_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'event_type': ev_type,
                    'start_date': start_dt,
                    'end_date': end_dt,
                    'all_day': False,
                    'location': loc,
                    'is_public': True,
                    'created_by': created_staff[0].user
                }
            )
        stats['events'] = len(events_data)
    except Exception as e:
        logger.warning(f"Error seeding sample calendar events: {e}")

    logger.info(f"[SampleData] Successfully completed sample data generation for '{school.name}': {stats}")
    return stats


def clear_all_sample_data_for_school(school, db_alias=None):
    """
    Safely purges only the generated sample/demo data from the school tenant database,
    restoring it back to the school's real/clean database without affecting any
    real user data or custom non-sample records.
    Uses raw SQL with FK disabled to handle cascade ordering correctly.
    """
    if not db_alias:
        db_alias = school.slug

    from tenants.services import register_tenant_connection
    register_tenant_connection(db_alias)

    from django.db import connections

    total_deleted = 0

    conn = connections[db_alias]
    with conn.cursor() as cur:
        # Disable FK enforcement so we can delete in any order
        cur.execute("PRAGMA foreign_keys = OFF;")

        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = set(r[0] for r in cur.fetchall())

        def _table_exists(c, table_name):
            return table_name in existing_tables

        def _has_column(c, table_name, col_name):
            if table_name not in existing_tables:
                return False
            c.execute(f"PRAGMA table_info('{table_name}')")
            return col_name in [r[1] for r in c.fetchall()]

        def _safe_delete(c, table_name, where_clause, silent=True):
            if table_name not in existing_tables:
                return 0
            try:
                c.execute(f'DELETE FROM "{table_name}" WHERE {where_clause}')
                return c.rowcount or 0
            except Exception as e:
                if not silent:
                    logger.warning(f"[SampleData] Error deleting from {table_name}: {e}")
                return 0

        # ---- Identify demo user IDs ----
        if _table_exists(cur, 'accounts_user'):
            cur.execute(
                "SELECT id FROM accounts_user WHERE email LIKE '%@demo.school' OR is_sample_data = 1"
            )
            demo_user_ids = [row[0] for row in cur.fetchall()]
        else:
            demo_user_ids = []

        logger.info(f"[SampleData] Found {len(demo_user_ids)} demo user records to purge in '{db_alias}'.")

        if demo_user_ids:
            ids_csv = ','.join(str(i) for i in demo_user_ids)

            # Cascade: delete all child records referencing demo user IDs
            user_fk_tables = [
                # allauth / social auth
                ('account_emailaddress', 'user_id'),
                ('socialaccount_socialaccount', 'user_id'),
                # core
                ('core_auditlog', 'user_id'),
                ('core_notification', 'user_id'),
                ('core_todo', 'created_by_id'),
                ('core_calendarevent', 'created_by_id'),
                ('core_loginevent', 'user_id'),
                ('core_loginlog', 'user_id'),
                # academics
                ('academics_classroutine', 'teacher_id'),
                ('academics_assignedsubject', 'teacher_id'),
                ('academics_section', 'class_teacher_id'),
                ('academics_class', 'created_by_id'),
                # students
                ('students_studenttimeline', 'added_by_id'),
                ('students_studentdocument', 'uploaded_by_id'),
                ('students_studentsubject', 'added_by_id'),
                ('students_student', 'parent_user_id'),
                ('students_student', 'user_id'),
                ('students_student', 'created_by_id'),
                ('students_student', 'disabled_by_id'),
                # human resource
                ('human_resource_teacher', 'user_id'),
                ('human_resource_staff', 'user_id'),
                # fees & finance
                ('fees_feecollection', 'collected_by_id'),
                ('fees_feestructure', 'created_by_id'),
                ('finance_transaction', 'created_by_id'),
                ('finance_transaction', 'posted_by_id'),
                ('finance_journalentry', 'posted_by_id'),
                # attendance
                ('attendance_studentattendance', 'marked_by_id'),
                ('attendance_staffattendance', 'teacher_id'),
                # homework
                ('homework_homeworkassignment', 'teacher_id'),
                ('homework_homeworksubmission', 'student_id'),
                ('homework_homeworkcomment', 'user_id'),
                # exams
                ('examinations_exammark', 'student_id'),
                ('examinations_examquestion', 'created_by_id'),
                ('examinations_exam', 'created_by_id'),
                # library
                ('library_bookissue', 'issued_by_id'),
                ('library_bookissue', 'received_by_id'),
                # communication
                ('communication_message', 'sender_id'),
                ('communication_message', 'recipient_id'),
                ('communication_notice', 'created_by_id'),
                # clubs
                ('clubs_clubmembership', 'member_id'),
                ('clubs_clubattendance', 'member_id'),
                ('clubs_clubachievement', 'member_id'),
                # leave
                ('leave_management_leave', 'teacher_id'),
                ('leave_management_leave', 'staff_id'),
                ('leave_management_leave', 'approved_by_id'),
                # inventory
                ('inventory_staffpayment', 'teacher_id'),
                ('inventory_staffpayment', 'staff_id'),
                ('inventory_expense', 'created_by_id'),
                # dormitory
                ('dormitory_roomallocation', 'student_id'),
                # lesson plan
                ('lesson_plan_lessonplan', 'teacher_id'),
                # chat
                ('chat_chatmembership', 'user_id'),
                ('chat_message', 'sender_id'),
                ('chat_messagereaction', 'user_id'),
                # certificates
                ('certificates_certificate', 'issued_by_id'),
                # reports
                ('reports_report', 'created_by_id'),
                ('reports_reportdistribution', 'user_id'),
            ]

            for (table, fk_col) in user_fk_tables:
                if _table_exists(cur, table) and _has_column(cur, table, fk_col):
                    count = _safe_delete(cur, table, f'{fk_col} IN ({ids_csv})')
                    total_deleted += count
                    if count:
                        logger.info(f"[SampleData] Deleted {count} rows from {table} ({fk_col})")

            # Delete demo Students linked by parent / user
            total_deleted += _safe_delete(cur, 'students_student',
                f'user_id IN ({ids_csv}) OR parent_user_id IN ({ids_csv})')

            # Finally delete the demo User rows
            cur.execute(f"DELETE FROM accounts_user WHERE id IN ({ids_csv})")
            deleted_users = cur.rowcount or 0
            total_deleted += deleted_users
            logger.info(f"[SampleData] Deleted {deleted_users} demo user accounts from {db_alias}.")

        # Also purge from master 'default' db (demo users stored there for auth)
        try:
            from django.db import connections as _conns
            with _conns['default'].cursor() as dcur:
                dcur.execute("PRAGMA foreign_keys = OFF;")
                dcur.execute(
                    "DELETE FROM accounts_user WHERE email LIKE '%@demo.school' OR email LIKE '%@demo-school.com' OR is_sample_data = 1"
                )
                cnt = dcur.rowcount or 0
                dcur.execute("PRAGMA foreign_keys = ON;")
                if cnt:
                    logger.info(f"[SampleData] Deleted {cnt} demo users from default/master database.")
                    total_deleted += cnt
        except Exception as e:
            logger.warning(f"[SampleData] Could not purge demo users from default db: {e}")

        # ---- Remove demo academic data ----
        sub_codes = ('MATH101', 'ENG101', 'SCI101', 'SOC101', 'COMP101', 'PE101', 'KIS101')
        sub_csv = ','.join(f"'{c}'" for c in sub_codes)

        demo_classes = ('Grade 1','Grade 2','Grade 3','Grade 4','Grade 5',
                        'Grade 6','Grade 7','Grade 8','Grade 9','Grade 10')
        cls_csv = ','.join(f"'{c}'" for c in demo_classes)

        if _table_exists(cur, 'academics_class'):
            cur.execute(f"SELECT id FROM academics_class WHERE name IN ({cls_csv})")
            class_ids = [r[0] for r in cur.fetchall()]
            if class_ids:
                cids_csv = ','.join(str(i) for i in class_ids)
                total_deleted += _safe_delete(cur, 'academics_classroutine', f'class_name_id IN ({cids_csv})')
                total_deleted += _safe_delete(cur, 'academics_assignedsubject', f'class_name_id IN ({cids_csv})')
                total_deleted += _safe_delete(cur, 'academics_section', f'class_name_id IN ({cids_csv})')

        if _table_exists(cur, 'academics_subject'):
            cur.execute(f"SELECT id FROM academics_subject WHERE code IN ({sub_csv})")
            sub_ids = [r[0] for r in cur.fetchall()]
            if sub_ids:
                sids_csv = ','.join(str(i) for i in sub_ids)
                total_deleted += _safe_delete(cur, 'academics_assignedsubject', f'subject_id IN ({sids_csv})')
            total_deleted += _safe_delete(cur, 'academics_subject', f'code IN ({sub_csv})')

        total_deleted += _safe_delete(cur, 'academics_class', f'name IN ({cls_csv})')

        house_names = (
            'Red House', 'Blue House', 'Green House', 'Yellow House',
            'Simba House (Red)', 'Chui House (Blue)', 'Kifaru House (Green)', 'Twiga House (Yellow)'
        )
        houses_csv = ','.join(f"'{h}'" for h in house_names)
        total_deleted += _safe_delete(cur, 'academics_house', f'name IN ({houses_csv})')

        # ---- Remove demo HR data ----
        total_deleted += _safe_delete(cur, 'human_resource_teacher', "is_sample_data = 1 OR employee_id LIKE 'EMP-T10%'")
        total_deleted += _safe_delete(cur, 'human_resource_staff', "is_sample_data = 1 OR employee_id LIKE 'EMP-S10%'")

        dept_codes = ('SCI_DEPT', 'MATH_DEPT', 'LANG_DEPT', 'HUM_DEPT', 'ADMIN_DEPT')
        dept_csv = ','.join(f"'{c}'" for c in dept_codes)
        des_codes = ('DES_SR_TCH', 'DES_ASST_TCH', 'DES_ACCT', 'DES_LIB', 'DES_RECEPT', 'DES_WARDEN')
        des_csv = ','.join(f"'{c}'" for c in des_codes)

        total_deleted += _safe_delete(cur, 'human_resource_department', f'code IN ({dept_csv})')
        total_deleted += _safe_delete(cur, 'human_resource_designation', f'code IN ({des_csv})')

        # ---- Remove demo fees & finance ----
        total_deleted += _safe_delete(cur, 'fees_feecollection', "receipt_number LIKE 'REC-2026-%' OR is_sample_data = 1")
        total_deleted += _safe_delete(cur, 'fees_feestructure', "is_sample_data = 1 OR name IN ('Term Tuition Fee', 'School Transport Fee', 'Digital Library Access', 'Annual Science & IT Lab Fee')")

        if _table_exists(cur, 'finance_journalentryline') and _table_exists(cur, 'finance_journalentry'):
            cur.execute("SELECT id FROM finance_journalentry WHERE reference LIKE 'FEE-%' OR memo LIKE '%Fee collection%'")
            je_ids = [r[0] for r in cur.fetchall()]
            if je_ids:
                je_csv = ','.join(str(i) for i in je_ids)
                total_deleted += _safe_delete(cur, 'finance_journalentryline', f'entry_id IN ({je_csv})')
            total_deleted += _safe_delete(cur, 'finance_journalentry', "reference LIKE 'FEE-%' OR memo LIKE '%Fee collection%'")

        # ---- Remove demo expenses ----
        total_deleted += _safe_delete(cur, 'inventory_expense', "expense_number LIKE 'EXP-2026-%' OR is_sample_data = 1")

        # ---- Remove demo library data ----
        total_deleted += _safe_delete(cur, 'library_bookissue', '1=1')
        total_deleted += _safe_delete(cur, 'library_bookcopy', "accession_number LIKE 'ACC-2026-%'")
        if _table_exists(cur, 'library_book_authors'):
            total_deleted += _safe_delete(cur, 'library_book_authors', '1=1')
        total_deleted += _safe_delete(cur, 'library_book', "is_sample_data = 1 OR isbn IN ('978-0134494074', '978-0321973611', '978-0078799815', '978-0140449136', '978-0553380163')")
        total_deleted += _safe_delete(cur, 'library_author', "name IN ('William Shakespeare', 'Albert Einstein', 'Isaac Newton', 'J.K. Rowling', 'Stephen Hawking')")
        total_deleted += _safe_delete(cur, 'library_publisher', "name = 'Oxford Educational Press' OR email = 'sales@oxfordpress.demo'")
        total_deleted += _safe_delete(cur, 'library_bookcategory', "name IN ('Fiction & Literature', 'Science & Technology', 'Mathematics', 'History & Geography', 'Biographies')")

        # ---- Remove demo dormitory ----
        total_deleted += _safe_delete(cur, 'dormitory_roomallocation', '1=1')
        total_deleted += _safe_delete(cur, 'dormitory_room', "room_number = '101'")
        total_deleted += _safe_delete(cur, 'dormitory_dormitory', "name = 'Sunrise Boys Hostel' OR is_sample_data = 1")

        # ---- Remove demo examinations ----
        total_deleted += _safe_delete(cur, 'examinations_exammark', '1=1')
        total_deleted += _safe_delete(cur, 'examinations_exam', "name = 'Term 1 Mid-Term Examination 2026' OR is_sample_data = 1")
        total_deleted += _safe_delete(cur, 'examinations_grade', "name = 'A' AND min_percentage = 80 AND max_percentage = 100")

        # ---- Remove demo leave ----
        total_deleted += _safe_delete(cur, 'leave_management_leave', 'is_sample_data = 1')
        total_deleted += _safe_delete(cur, 'leave_management_leavetype', "name = 'Medical / Sick Leave' AND max_days = 10")

        # ---- Remove demo clubs ----
        total_deleted += _safe_delete(cur, 'clubs_clubactivity', '1=1')
        total_deleted += _safe_delete(cur, 'clubs_clubmembership', '1=1')
        total_deleted += _safe_delete(cur, 'clubs_club', "name = 'Science & Robotics Society' OR is_sample_data = 1")

        # ---- Remove demo communication ----
        total_deleted += _safe_delete(cur, 'communication_notice', "title = 'Welcome to New Academic Term 2026'")

        # ---- Remove demo homework ----
        total_deleted += _safe_delete(cur, 'homework_homeworksubmission', '1=1')
        total_deleted += _safe_delete(cur, 'homework_homeworkassignment', "title = 'Algebra & Linear Equations Practice 1'")

        # ---- Remove demo calendar events ----
        cal_titles = (
            'Annual Science & Robotics Exhibition',
            'Term 1 Parents-Teachers Conference',
            'Inter-House Athletics Championship',
            'Midterm Examination Week',
            'National Public Holiday'
        )
        c_csv = ','.join(f"'{t}'" for t in cal_titles)
        total_deleted += _safe_delete(cur, 'core_calendarevent', f'title IN ({c_csv})')

        # ---- Remove demo student category ----
        total_deleted += _safe_delete(cur, 'students_studentcategory', "name = 'General Student' AND description = 'Regular enrolled full-time student'")

        # ---- Remove demo transport ----
        total_deleted += _safe_delete(cur, 'transport_routestop', '1=1')
        total_deleted += _safe_delete(cur, 'transport_vehicle', "vehicle_number = 'KAA 890B'")
        total_deleted += _safe_delete(cur, 'transport_route', "name = 'North Metro Express Route'")

        # Re-enable FK enforcement
        cur.execute("PRAGMA foreign_keys = ON;")

    logger.info(f"[SampleData] Finished clearing sample data for '{school.name}'. Total records removed: {total_deleted}")
    return total_deleted


def wipe_and_reseed_demo_school(school=None):
    """
    Completely erases all existing operational and legacy data in the demo-school database,
    ensures all migrations are up to date, and regenerates a full, comprehensive suite of
    pristine sample demo records.
    """
    from tenants.models import School
    from tenants.services import register_tenant_connection, ensure_school_database
    from tenants.threadlocals import set_current_tenant_db, get_current_tenant_db
    from django.db import connections

    if not school:
        school = School.objects.using('default').filter(slug='demo-school').first()
    if not school:
        logger.error("[DemoReset] demo-school tenant not found in master database.")
        return {}

    db_alias = school.slug
    register_tenant_connection(db_alias)
    ensure_school_database(school)

    prev_db = get_current_tenant_db()
    set_current_tenant_db(db_alias)

    logger.info(f"[DemoReset] Wiping all existing data in '{db_alias}' database...")

    try:
        conn = connections[db_alias]
        with conn.cursor() as cur:
            cur.execute("PRAGMA foreign_keys = OFF;")

            tables_to_clear = [
                'attendance_studentattendance', 'attendance_staffattendance',
                'homework_homeworksubmission', 'homework_homeworkassignment',
                'examinations_exammark', 'examinations_examquestion',
                'examinations_examsubjectconfig', 'examinations_exam', 'examinations_grade',
                'library_bookissue', 'library_bookcopy', 'library_book',
                'library_author', 'library_publisher', 'library_bookcategory',
                'dormitory_roomallocation', 'dormitory_room', 'dormitory_dormitory',
                'leave_management_leave', 'leave_management_leavetype',
                'clubs_clubmembership', 'clubs_clubactivity', 'clubs_club',
                'fees_feecollection', 'fees_feestructure',
                'finance_transaction',
                'inventory_staffpayment', 'inventory_expense',
                'inventory_item', 'inventory_itemcategory', 'inventory_supplier',
                'communication_message', 'communication_notice',
                'transport_routestop', 'transport_vehicle', 'transport_route',
                'students_student', 'students_studentcategory',
                'human_resource_teacher', 'human_resource_staff',
                'academics_classroutine', 'academics_assignedsubject',
                'academics_section', 'academics_class',
                'academics_subject', 'academics_house',
                'human_resource_department', 'human_resource_designation',
                'core_session', 'core_academicyear',
            ]

            for table in tables_to_clear:
                try:
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table])
                    if cur.fetchone():
                        cur.execute(f'DELETE FROM "{table}"')
                        count = cur.rowcount
                        if count:
                            logger.info(f"[DemoReset] Cleared {count} rows from {table}")
                except Exception as e:
                    logger.warning(f"[DemoReset] Error clearing {table}: {e}")

            # Delete non-superadmin users
            try:
                cur.execute("DELETE FROM accounts_user WHERE role != 'superadmin'")
                logger.info(f"[DemoReset] Cleared non-superadmin users.")
            except Exception as e:
                logger.warning(f"[DemoReset] Error clearing users in {db_alias}: {e}")

            cur.execute("PRAGMA foreign_keys = ON;")

    finally:
        set_current_tenant_db(prev_db)

    # Now generate the clean, full sample data
    return generate_all_sample_data_for_school(school, db_alias=db_alias)

import random
import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.core.management import call_command

logger = logging.getLogger(__name__)


def generate_all_sample_data_for_school(school, db_alias=None):
    """
    Populates comprehensive, interlinked sample data across ALL platform modules
    inside the school's dedicated tenant database (db_alias).
    """
    if not db_alias:
        db_alias = school.slug

    from tenants.services import register_tenant_connection, ensure_school_database
    register_tenant_connection(db_alias)
    ensure_school_database(school)

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
    from homework.models import Homework, HomeworkSubmission
    from communication.models import Notice
    from transport.models import Route, Vehicle, RouteStop

    logger.info(f"[SampleData] Starting sample data generation for school '{school.name}' on DB '{db_alias}'...")

    # Ensure School record exists in tenant DB
    school_obj = School.objects.using(db_alias).filter(pk=school.pk).first()
    if not school_obj:
        school_obj = School.objects.using('default').get(pk=school.pk)
        school_obj.subscription_plan = None
        school_obj.save(using=db_alias)

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
            defaults={'color_code': color, 'description': f'The prestigious {h_name}'}
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
            user.set_password('teacher123')
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
            st_user.set_password('staff123')
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
            p_user.set_password('parent123')
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
            s_user.set_password('student123')
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
        student=created_students[0],
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
            'school': school_obj,
            'content': 'We welcome all students, parents, and faculty staff to the new academic term!',
            'notice_date': date.today() - timedelta(days=5),
            'publish_date': date.today() - timedelta(days=5),
            'is_published': True,
            'posted_by': created_staff[0].user,
            'target_audience': 'all'
        }
    )

    # -------------------------------------------------------------
    # 16. TRANSPORT & ROUTES
    # -------------------------------------------------------------
    route_obj, _ = Route.objects.using(db_alias).get_or_create(
        title='North Metro Express Route',
        defaults={
            'school': school_obj,
            'route_fare': Decimal('150.00'),
            'start_place': 'North Terminal Station',
            'end_place': 'Main School Gate'
        }
    )

    Vehicle.objects.using(db_alias).get_or_create(
        vehicle_number='KAA 890B',
        defaults={
            'school': school_obj,
            'vehicle_model': 'Toyota Coaster 35-Seater',
            'driver_name': 'Robert Driver',
            'driver_phone': '+1555998877'
        }
    )

    logger.info(f"[SampleData] Successfully completed sample data generation for '{school.name}': {stats}")
    return stats


def clear_all_sample_data_for_school(school, db_alias=None):
    """
    Safely purges only the generated sample/demo data from the school tenant database,
    restoring it back to the school's real/clean database without affecting any
    real user data or custom non-sample records.
    """
    if not db_alias:
        db_alias = school.slug

    from tenants.services import register_tenant_connection
    register_tenant_connection(db_alias)

    total_deleted = 0

    # 1. Attendance
    try:
        from attendance.models import StudentAttendance, StaffAttendance
        c1, _ = StudentAttendance.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = StaffAttendance.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2)
    except Exception as e:
        logger.warning(f"Error clearing sample attendance: {e}")

    # 2. Homework
    try:
        from homework.models import HomeworkSubmission, Homework
        c1, _ = HomeworkSubmission.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = Homework.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2)
    except Exception as e:
        logger.warning(f"Error clearing sample homework: {e}")

    # 3. Examinations
    try:
        from examinations.models import ExamMark, ExamQuestion, ExamSubjectConfig, Exam
        c1, _ = ExamMark.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = ExamQuestion.objects.using(db_alias).filter(is_sample_data=True).delete()
        c3, _ = ExamSubjectConfig.objects.using(db_alias).filter(is_sample_data=True).delete()
        c4, _ = Exam.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2 + c3 + c4)
    except Exception as e:
        logger.warning(f"Error clearing sample exams: {e}")

    # 4. Library
    try:
        from library.models import BookIssue, BookCopy, Book
        c1, _ = BookIssue.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = BookCopy.objects.using(db_alias).filter(is_sample_data=True).delete()
        c3, _ = Book.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2 + c3)
    except Exception as e:
        logger.warning(f"Error clearing sample library: {e}")

    # 5. Dormitory
    try:
        from dormitory.models import RoomAllocation, Room, Dormitory
        c1, _ = RoomAllocation.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = Room.objects.using(db_alias).filter(is_sample_data=True).delete()
        c3, _ = Dormitory.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2 + c3)
    except Exception as e:
        logger.warning(f"Error clearing sample dormitory: {e}")

    # 6. Leaves
    try:
        from leave_management.models import Leave
        c1, _ = Leave.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample leaves: {e}")

    # 7. Clubs
    try:
        from clubs.models import ClubMembership, ClubActivity, Club
        c1, _ = ClubMembership.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = ClubActivity.objects.using(db_alias).filter(is_sample_data=True).delete()
        c3, _ = Club.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2 + c3)
    except Exception as e:
        logger.warning(f"Error clearing sample clubs: {e}")

    # 8. Finance & Fees
    try:
        from fees.models import FeeCollection, FeeStructure
        c1, _ = FeeCollection.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = FeeStructure.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2)
    except Exception as e:
        logger.warning(f"Error clearing sample fees: {e}")

    try:
        from finance.models import Transaction
        c1, _ = Transaction.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample transactions: {e}")

    try:
        from inventory.models import Expense
        c1, _ = Expense.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample expenses: {e}")

    # 9. Communication
    try:
        from communication.models import Notice
        c1, _ = Notice.objects.using(db_alias).filter(title__icontains='Welcome to New Academic Term 2026').delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample notices: {e}")

    # 10. Transport
    try:
        from transport.models import RouteStop, Vehicle, Route
        c1, _ = RouteStop.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = Vehicle.objects.using(db_alias).filter(vehicle_number='KAA 890B').delete()
        c3, _ = Route.objects.using(db_alias).filter(title='North Metro Express Route').delete()
        total_deleted += (c1 + c2 + c3)
    except Exception as e:
        logger.warning(f"Error clearing sample transport: {e}")

    # 11. Students
    try:
        from students.models import Student
        c1, _ = Student.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample students: {e}")

    # 12. Teachers & Staff
    try:
        from human_resource.models import Teacher, Staff
        c1, _ = Teacher.objects.using(db_alias).filter(is_sample_data=True).delete()
        c2, _ = Staff.objects.using(db_alias).filter(is_sample_data=True).delete()
        total_deleted += (c1 + c2)
    except Exception as e:
        logger.warning(f"Error clearing sample staff/teachers: {e}")

    # 13. Demo Users
    try:
        from accounts.models import User
        c1, _ = User.objects.using(db_alias).filter(is_sample_data=True, email__endswith='@demo.school').delete()
        total_deleted += c1
    except Exception as e:
        logger.warning(f"Error clearing sample users: {e}")

    logger.info(f"[SampleData] Finished clearing sample data for '{school.name}'. Total records removed: {total_deleted}")
    return total_deleted


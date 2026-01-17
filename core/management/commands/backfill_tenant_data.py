from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    help = "Backfill missing school links for legacy data in Inventory, Academics, and Examinations so data is visible per tenant."

    def add_arguments(self, parser):
        parser.add_argument('--school', type=str, required=True, help='Target school slug (e.g., demo)')
        parser.add_argument('--dry-run', action='store_true', help='Run without saving changes')

    @transaction.atomic
    def handle(self, *args, **options):
        from tenants.models import School
        from accounts.models import User

        # Inventory
        from inventory.models import (
            Expense,
            StaffPayment,
            ItemCategory,
            Item,
            Supplier,
            PurchaseOrder,
            ItemDistribution,
        )
        # HR
        from human_resource.models import Department, Designation
        # Leave
        from leave_management.models import LeaveType, Leave
        # Academics and core
        from core.models import AcademicYear
        from academics.models import ClassRoom, ClassTime, ClassRoutine
        # Examinations
        from examinations.models import Grade
        # Library
        from library.models import BookCategory, Publisher, Author, Book
        # Homework
        from homework.models import HomeworkAssignment
        # Lesson plans
        from lesson_plan.models import LessonPlanTemplate, LessonPlan
        # Online exams
        from online_exam.models import OnlineExam

        slug = options['school']
        dry_run = options['dry_run']

        school = School.objects.filter(slug=slug).first()
        if not school:
            raise CommandError(f"School with slug '{slug}' not found")

        summary = {}

        # Helper to persist if not dry run
        def save(obj, fields):
            if not dry_run:
                obj.save(update_fields=fields)

        # Inventory: Expenses
        fixed_expenses = 0
        for exp in Expense.objects.select_related('created_by').filter(school__isnull=True):
            inferred = getattr(exp.created_by, 'school', None)
            target = inferred or school
            if target:
                exp.school = target
                save(exp, ['school'])
                fixed_expenses += 1
        summary['expenses_fixed'] = fixed_expenses

        # HR: Teacher/Staff user accounts (Teacher/Staff profiles don't have a school FK; the User does)
        fixed_hr_users = 0
        for u in User.objects.filter(role__in=['teacher', 'staff'], school__isnull=True):
            u.school = school
            save(u, ['school'])
            fixed_hr_users += 1
        summary['hr_users_fixed'] = fixed_hr_users

        # HR: Departments / Designations
        fixed_departments = 0
        for d in Department.objects.filter(school__isnull=True):
            inferred = getattr(getattr(d, 'head', None), 'school', None)
            target = inferred or school
            d.school = target
            save(d, ['school'])
            fixed_departments += 1
        summary['departments_fixed'] = fixed_departments

        fixed_designations = 0
        for des in Designation.objects.filter(school__isnull=True):
            des.school = school
            save(des, ['school'])
            fixed_designations += 1
        summary['designations_fixed'] = fixed_designations

        # Leave: Leave types and leaves
        fixed_leave_types = 0
        for lt in LeaveType.objects.filter(school__isnull=True):
            lt.school = school
            save(lt, ['school'])
            fixed_leave_types += 1
        summary['leave_types_fixed'] = fixed_leave_types

        fixed_leaves = 0
        for lv in Leave.objects.select_related('teacher', 'staff', 'leave_type', 'student__user').filter(school__isnull=True):
            inferred = None
            if lv.teacher and getattr(lv.teacher, 'school', None):
                inferred = lv.teacher.school
            elif lv.staff and getattr(lv.staff, 'school', None):
                inferred = lv.staff.school
            elif lv.student and getattr(getattr(lv.student, 'user', None), 'school', None):
                inferred = lv.student.user.school
            elif lv.leave_type and getattr(lv.leave_type, 'school', None):
                inferred = lv.leave_type.school
            target = inferred or school
            lv.school = target
            save(lv, ['school'])
            fixed_leaves += 1
        summary['leaves_fixed'] = fixed_leaves

        # Inventory: Categories / Items
        fixed_item_categories = 0
        for cat in ItemCategory.objects.filter(school__isnull=True):
            cat.school = school
            save(cat, ['school'])
            fixed_item_categories += 1
        summary['item_categories_fixed'] = fixed_item_categories

        fixed_items = 0
        for it in Item.objects.select_related('category').filter(school__isnull=True):
            inferred = getattr(getattr(it, 'category', None), 'school', None)
            target = inferred or school
            it.school = target
            save(it, ['school'])
            fixed_items += 1
        summary['items_fixed'] = fixed_items

        # Inventory: Suppliers
        fixed_suppliers = 0
        for sup in Supplier.objects.filter(school__isnull=True):
            sup.school = school
            save(sup, ['school'])
            fixed_suppliers += 1
        summary['suppliers_fixed'] = fixed_suppliers

        # Inventory: Purchase Orders
        fixed_purchase_orders = 0
        for po in PurchaseOrder.objects.select_related('created_by', 'supplier').filter(school__isnull=True):
            inferred = getattr(getattr(po, 'created_by', None), 'school', None)
            if not inferred and getattr(getattr(po, 'supplier', None), 'school', None):
                inferred = po.supplier.school
            target = inferred or school
            po.school = target
            save(po, ['school'])
            fixed_purchase_orders += 1
        summary['purchase_orders_fixed'] = fixed_purchase_orders

        # Inventory: Item Distributions
        fixed_distributions = 0
        for dist in ItemDistribution.objects.select_related('distributed_by', 'item').filter(school__isnull=True):
            inferred = getattr(getattr(dist, 'distributed_by', None), 'school', None)
            if not inferred and getattr(getattr(dist, 'item', None), 'school', None):
                inferred = dist.item.school
            target = inferred or school
            dist.school = target
            save(dist, ['school'])
            fixed_distributions += 1
        summary['item_distributions_fixed'] = fixed_distributions

        # Inventory: Staff Payments (also cascade to related Expense if present)
        fixed_payments = 0
        fixed_payment_expenses = 0
        for pay in StaffPayment.objects.select_related('created_by', 'expense').filter(school__isnull=True):
            inferred = getattr(pay.created_by, 'school', None)
            target = inferred or school
            if target:
                pay.school = target
                save(pay, ['school'])
                fixed_payments += 1
            if pay.expense and pay.expense.school_id is None:
                pay.expense.school = target
                save(pay.expense, ['school'])
                fixed_payment_expenses += 1
        summary['staff_payments_fixed'] = fixed_payments
        summary['staff_payment_expenses_fixed'] = fixed_payment_expenses

        # Core: Academic Years
        fixed_years = 0
        for year in AcademicYear.objects.filter(school__isnull=True):
            year.school = school
            save(year, ['school'])
            fixed_years += 1
        summary['academic_years_fixed'] = fixed_years

        # Academics: ClassTime
        fixed_times = 0
        for ct in ClassTime.objects.filter(school__isnull=True):
            ct.school = school
            save(ct, ['school'])
            fixed_times += 1
        summary['class_times_fixed'] = fixed_times

        # Academics: ClassRoom
        fixed_rooms = 0
        for cr in ClassRoom.objects.filter(school__isnull=True):
            cr.school = school
            save(cr, ['school'])
            fixed_rooms += 1
        summary['class_rooms_fixed'] = fixed_rooms

        # Academics: ClassRoutine
        fixed_routines = 0
        for r in ClassRoutine.objects.filter(school__isnull=True):
            r.school = school
            save(r, ['school'])
            fixed_routines += 1
        summary['class_routines_fixed'] = fixed_routines

        # Examinations: Grades
        fixed_grades = 0
        for g in Grade.objects.filter(school__isnull=True):
            g.school = school
            save(g, ['school'])
            fixed_grades += 1
        summary['grades_fixed'] = fixed_grades

        # Library: Book categories (avoid unique name conflicts per school)
        fixed_book_categories = 0
        for cat in BookCategory.objects.filter(school__isnull=True):
            if BookCategory.objects.filter(school=school, name=cat.name).exists():
                continue
            cat.school = school
            save(cat, ['school'])
            fixed_book_categories += 1
        summary['book_categories_fixed'] = fixed_book_categories

        # Library: Publishers
        fixed_publishers = 0
        for pub in Publisher.objects.filter(school__isnull=True):
            pub.school = school
            save(pub, ['school'])
            fixed_publishers += 1
        summary['publishers_fixed'] = fixed_publishers

        # Library: Authors
        fixed_authors = 0
        for author in Author.objects.filter(school__isnull=True):
            author.school = school
            save(author, ['school'])
            fixed_authors += 1
        summary['authors_fixed'] = fixed_authors

        # Library: Books
        fixed_books = 0
        for book in Book.objects.select_related('category', 'publisher', 'created_by').filter(school__isnull=True):
            inferred = None
            if book.category and getattr(book.category, 'school', None):
                inferred = book.category.school
            elif book.publisher and getattr(book.publisher, 'school', None):
                inferred = book.publisher.school
            elif getattr(book, 'created_by', None) and getattr(book.created_by, 'school', None):
                inferred = book.created_by.school
            if not inferred:
                subject = book.subjects.first()
                if subject and getattr(subject, 'school', None):
                    inferred = subject.school
            target = inferred or school
            book.school = target
            save(book, ['school'])
            fixed_books += 1
        summary['books_fixed'] = fixed_books

        # Homework: Assignments
        fixed_homework = 0
        for hw in HomeworkAssignment.objects.select_related('academic_year', 'class_ref', 'subject', 'created_by').filter(school__isnull=True):
            inferred = None
            if hw.academic_year and getattr(hw.academic_year, 'school', None):
                inferred = hw.academic_year.school
            elif hw.class_ref and getattr(hw.class_ref, 'school', None):
                inferred = hw.class_ref.school
            elif hw.subject and getattr(hw.subject, 'school', None):
                inferred = hw.subject.school
            elif getattr(hw, 'created_by', None) and getattr(hw.created_by, 'school', None):
                inferred = hw.created_by.school
            target = inferred or school
            hw.school = target
            save(hw, ['school'])
            fixed_homework += 1
        summary['homework_assignments_fixed'] = fixed_homework

        # Lesson plans: Templates
        fixed_lp_templates = 0
        for tmpl in LessonPlanTemplate.objects.filter(school__isnull=True):
            tmpl.school = school
            save(tmpl, ['school'])
            fixed_lp_templates += 1
        summary['lesson_plan_templates_fixed'] = fixed_lp_templates

        # Lesson plans: LessonPlan records
        fixed_lesson_plans = 0
        for lp in LessonPlan.objects.select_related('academic_year', 'class_ref', 'section__class_name', 'subject', 'created_by').filter(school__isnull=True):
            inferred = None
            if lp.academic_year and getattr(lp.academic_year, 'school', None):
                inferred = lp.academic_year.school
            elif lp.class_ref and getattr(lp.class_ref, 'school', None):
                inferred = lp.class_ref.school
            elif lp.section and getattr(getattr(lp.section, 'class_name', None), 'school', None):
                inferred = lp.section.class_name.school
            elif lp.subject and getattr(lp.subject, 'school', None):
                inferred = lp.subject.school
            elif getattr(lp, 'created_by', None) and getattr(lp.created_by, 'school', None):
                inferred = lp.created_by.school
            target = inferred or school
            lp.school = target
            save(lp, ['school'])
            fixed_lesson_plans += 1
        summary['lesson_plans_fixed'] = fixed_lesson_plans

        # Online exams
        fixed_online_exams = 0
        for exam in OnlineExam.objects.select_related('subject', 'class_ref', 'created_by').filter(school__isnull=True):
            inferred = None
            if exam.subject and getattr(exam.subject, 'school', None):
                inferred = exam.subject.school
            elif exam.class_ref and getattr(exam.class_ref, 'school', None):
                inferred = exam.class_ref.school
            elif getattr(exam, 'created_by', None) and getattr(exam.created_by, 'school', None):
                inferred = exam.created_by.school
            target = inferred or school
            exam.school = target
            save(exam, ['school'])
            fixed_online_exams += 1
        summary['online_exams_fixed'] = fixed_online_exams

        # Report
        self.stdout.write(self.style.SUCCESS(
            "Backfill complete for '%s' (dry_run=%s)\n" % (slug, dry_run)
        ))
        for k, v in summary.items():
            self.stdout.write(f" - {k}: {v}")

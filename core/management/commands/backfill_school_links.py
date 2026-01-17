from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

class Command(BaseCommand):
    help = "Backfill school links for legacy data: set Class.school, User.school for students/parents based on provided school slug or inferred relations."

    def add_arguments(self, parser):
        parser.add_argument('--school', type=str, required=True, help='School slug to backfill (e.g., demo-school)')
        parser.add_argument('--dry-run', action='store_true', help='Run without saving changes')

    @transaction.atomic
    def handle(self, *args, **options):
        from tenants.models import School
        from academics.models import Class
        from students.models import Student
        from accounts.models import User

        slug = options['school']
        dry_run = options['dry_run']

        school = School.objects.filter(slug=slug).first()
        if not school:
            raise CommandError(f"School with slug '{slug}' not found")

        # Summary counters
        fixed_classes = 0
        fixed_student_users = 0
        fixed_parents = 0
        fixed_students_by_parent = 0
        fixed_students_by_creator = 0

        # 1) Ensure Classes have school set
        for cls in Class.objects.filter(school__isnull=True):
            # Simple heuristic: if any student in this class has user.school set, re-use it; else fall back to provided school
            any_student = Student.objects.filter(current_class=cls).select_related('user').first()
            inferred_school = getattr(getattr(any_student, 'user', None), 'school', None) if any_student else None
            target_school = inferred_school or school
            if target_school:
                cls.school = target_school
                if not dry_run:
                    cls.save(update_fields=['school'])
                fixed_classes += 1

        # 2) Ensure Student.user.school is set
        students = Student.objects.select_related('user', 'current_class__school', 'parent_user').all()
        for s in students:
            u = s.user
            if not u:
                continue
            if getattr(u, 'school', None):
                continue
            # infer from class, then parent_user, then creator
            target_school = None
            if s.current_class and s.current_class.school:
                target_school = s.current_class.school
            elif s.parent_user and getattr(s.parent_user, 'school', None):
                target_school = s.parent_user.school
            elif s.created_by and getattr(s.created_by, 'school', None):
                target_school = s.created_by.school
            else:
                target_school = school
            if target_school:
                u.school = target_school
                if not dry_run:
                    u.save(update_fields=['school'])
                fixed_student_users += 1

        # 3) Ensure Parent users have school set based on any child
        parents = User.objects.filter(role='parent', school__isnull=True)
        for p in parents:
            child = Student.objects.filter(parent_user=p).select_related('current_class__school', 'user__school').first()
            target_school = None
            if child:
                if child.current_class and child.current_class.school:
                    target_school = child.current_class.school
                elif child.user and getattr(child.user, 'school', None):
                    target_school = child.user.school
            if not target_school:
                target_school = school
            if target_school:
                p.school = target_school
                if not dry_run:
                    p.save(update_fields=['school'])
                fixed_parents += 1

        # Optional: ensure students missing both class and user.school are still visible by linking to fallback school via user
        for s in Student.objects.select_related('user').all():
            if not s.current_class and s.user and not getattr(s.user, 'school', None):
                s.user.school = school
                if not dry_run:
                    s.user.save(update_fields=['school'])
                fixed_students_by_creator += 1

        self.stdout.write(self.style.SUCCESS(
            f"Backfill complete for '{slug}' (dry_run={dry_run}).\n"
            f"Classes fixed: {fixed_classes}\n"
            f"Student users fixed: {fixed_student_users}\n"
            f"Parents fixed: {fixed_parents}\n"
            f"Students fallback fixes: {fixed_students_by_creator}"
        ))

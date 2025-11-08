"""
Notification and Email Service
Handles sending emails and system notifications for various events
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Notification

User = get_user_model()


class NotificationService:
    """Service for handling notifications and emails"""
    
    @staticmethod
    def get_superadmins():
        """Get all superadmin users"""
        return User.objects.filter(role='super_admin', is_active=True)
    
    @staticmethod
    def create_notification(user, title, message, notification_type='info', link=None):
        """Create a system notification for a user"""
        try:
            notification = Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link
            )
            return notification
        except Exception as e:
            print(f"Error creating notification: {e}")
            return None
    
    @staticmethod
    def send_email(subject, recipient_list, template_name, context, from_email=None):
        """Send HTML email using template"""
        try:
            if from_email is None:
                from_email = settings.DEFAULT_FROM_EMAIL
            
            # Render HTML content
            html_content = render_to_string(template_name, context)
            
            # Create plain text version (strip HTML tags)
            from django.utils.html import strip_tags
            text_content = strip_tags(html_content)
            
            # Create email
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipient_list
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=False)
            
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    @staticmethod
    def notify_user_created(user, created_by, password=None):
        """Notify when a new user is created"""
        # Email to the new user
        context = {
            'user': user,
            'created_by': created_by,
            'password': password,
            'login_url': settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        }
        
        NotificationService.send_email(
            subject=f'Welcome to Clasyo - Your Account Has Been Created',
            recipient_list=[user.email],
            template_name='emails/user_created.html',
            context=context
        )
        
        # System notification for the user
        NotificationService.create_notification(
            user=user,
            title='Welcome to Clasyo!',
            message=f'Your account has been created by {created_by.get_full_name()}. Please check your email for login details.',
            notification_type='success',
            link='/accounts/profile/'
        )
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New User Created',
                message=f'{created_by.get_full_name()} created a new user: {user.get_full_name()} ({user.role})',
                notification_type='info'
            )
            
            NotificationService.send_email(
                subject=f'New User Created - {user.get_full_name()}',
                recipient_list=[admin.email],
                template_name='emails/admin_user_created.html',
                context={'user': user, 'created_by': created_by}
            )
    
    @staticmethod
    def notify_student_created(student, created_by, school):
        """Notify when a new student is created"""
        # Notify school admins
        school_admins = User.objects.filter(
            role='school_admin',
            is_active=True
        )
        
        for admin in school_admins:
            NotificationService.create_notification(
                user=admin,
                title='New Student Enrolled',
                message=f'{student.get_full_name()} has been enrolled by {created_by.get_full_name()}',
                notification_type='success',
                link=f'/school/{school.slug}/students/{student.id}/'
            )
        
        # Notify parent if exists
        if hasattr(student, 'parent') and student.parent:
            NotificationService.create_notification(
                user=student.parent,
                title='Student Enrolled',
                message=f'Your child {student.get_full_name()} has been enrolled in {school.name}',
                notification_type='success'
            )
            
            NotificationService.send_email(
                subject=f'Student Enrollment Confirmation - {school.name}',
                recipient_list=[student.parent.email],
                template_name='emails/student_enrolled.html',
                context={'student': student, 'school': school}
            )
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New Student Enrolled',
                message=f'New student {student.get_full_name()} enrolled at {school.name}',
                notification_type='info'
            )
    
    @staticmethod
    def notify_teacher_created(teacher, created_by, school):
        """Notify when a new teacher is created"""
        # Email to teacher
        context = {
            'teacher': teacher,
            'school': school,
            'created_by': created_by
        }
        
        NotificationService.send_email(
            subject=f'Welcome to {school.name} - Teacher Account Created',
            recipient_list=[teacher.email],
            template_name='emails/teacher_created.html',
            context=context
        )
        
        # System notification
        NotificationService.create_notification(
            user=teacher,
            title=f'Welcome to {school.name}!',
            message=f'Your teacher account has been created. You can now access the system.',
            notification_type='success'
        )
        
        # Notify school admins
        school_admins = User.objects.filter(role='school_admin', is_active=True)
        for admin in school_admins:
            NotificationService.create_notification(
                user=admin,
                title='New Teacher Added',
                message=f'{teacher.get_full_name()} has been added as a teacher by {created_by.get_full_name()}',
                notification_type='info'
            )
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New Teacher Added',
                message=f'New teacher {teacher.get_full_name()} added at {school.name}',
                notification_type='info'
            )
    
    @staticmethod
    def notify_exam_created(exam, created_by, school):
        """Notify when an exam is created"""
        # Notify all teachers
        teachers = User.objects.filter(role='teacher', is_active=True)
        for teacher in teachers:
            NotificationService.create_notification(
                user=teacher,
                title='New Exam Scheduled',
                message=f'Exam "{exam.name}" has been scheduled for {exam.start_date}',
                notification_type='warning',
                link=f'/school/{school.slug}/examinations/{exam.id}/'
            )
            
            # Send email to teacher
            try:
                NotificationService.send_email(
                    subject=f'New Exam Scheduled - {exam.name}',
                    recipient_list=[teacher.email],
                    template_name='emails/exam_created_teacher.html',
                    context={'exam': exam, 'teacher': teacher, 'school': school}
                )
            except Exception as e:
                print(f"Error sending email to teacher: {e}")
        
        # Notify affected students (if exam has class/section)
        if hasattr(exam, 'class_assigned') and exam.class_assigned:
            from students.models import Student
            students = Student.objects.filter(
                current_class=exam.class_assigned,
                is_active=True
            )
            
            for student in students:
                # Notify student
                if hasattr(student, 'user') and student.user:
                    NotificationService.create_notification(
                        user=student.user,
                        title='Upcoming Exam',
                        message=f'You have an exam "{exam.name}" scheduled for {exam.start_date}',
                        notification_type='warning',
                        link=f'/school/{school.slug}/examinations/student/{exam.id}/'
                    )
                    
                    # Send email to student
                    try:
                        NotificationService.send_email(
                            subject=f'Upcoming Exam - {exam.name}',
                            recipient_list=[student.user.email],
                            template_name='emails/exam_created_student.html',
                            context={'exam': exam, 'student': student, 'school': school}
                        )
                    except Exception as e:
                        print(f"Error sending email to student: {e}")
                
                # Notify parent
                if hasattr(student, 'parent_user') and student.parent_user:
                    NotificationService.create_notification(
                        user=student.parent_user,
                        title='Exam Notification',
                        message=f'Your child {student.first_name} has an exam "{exam.name}" scheduled for {exam.start_date}',
                        notification_type='info'
                    )
                    
                    # Send email to parent
                    try:
                        NotificationService.send_email(
                            subject=f'Exam Notification for {student.first_name} - {exam.name}',
                            recipient_list=[student.parent_user.email],
                            template_name='emails/exam_created_parent.html',
                            context={'exam': exam, 'student': student, 'school': school}
                        )
                    except Exception as e:
                        print(f"Error sending email to parent: {e}")
        
        # Notify school admins
        school_admins = User.objects.filter(role='school_admin', is_active=True)
        for admin in school_admins:
            NotificationService.create_notification(
                user=admin,
                title='New Exam Created',
                message=f'Exam "{exam.name}" created by {created_by.get_full_name()}',
                notification_type='info',
                link=f'/school/{school.slug}/examinations/{exam.id}/'
            )
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New Exam Created',
                message=f'Exam "{exam.name}" created at {school.name} by {created_by.get_full_name()}',
                notification_type='info'
            )
            
            # Send email to superadmin
            try:
                NotificationService.send_email(
                    subject=f'New Exam Created - {school.name}',
                    recipient_list=[admin.email],
                    template_name='emails/exam_created_admin.html',
                    context={'exam': exam, 'created_by': created_by, 'school': school}
                )
            except Exception as e:
                print(f"Error sending email to superadmin: {e}")
    
    @staticmethod
    def notify_book_added(book, created_by, school):
        """Notify when a book is added to library"""
        # Notify librarian if exists
        librarians = User.objects.filter(role='librarian', is_active=True)
        for librarian in librarians:
            NotificationService.create_notification(
                user=librarian,
                title='New Book Added',
                message=f'"{book.title}" by {book.author} has been added to the library',
                notification_type='success',
                link=f'/school/{school.slug}/library/books/{book.id}/'
            )
        
        # Notify students (optional - could be overwhelming)
        # Can be configured to only notify if book is popular or requested
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New Book Added',
                message=f'Book "{book.title}" added to {school.name} library',
                notification_type='info'
            )
    
    @staticmethod
    def notify_parent_created(parent, student, created_by, school):
        """Notify when a parent account is created"""
        # Email to parent
        context = {
            'parent': parent,
            'student': student,
            'school': school,
            'created_by': created_by
        }
        
        NotificationService.send_email(
            subject=f'Parent Account Created - {school.name}',
            recipient_list=[parent.email],
            template_name='emails/parent_created.html',
            context=context
        )
        
        # System notification
        NotificationService.create_notification(
            user=parent,
            title=f'Welcome to {school.name}!',
            message=f'Your parent account has been created. You can now track your child\'s progress.',
            notification_type='success'
        )
        
        # Notify superadmins
        for admin in NotificationService.get_superadmins():
            NotificationService.create_notification(
                user=admin,
                title='New Parent Account',
                message=f'Parent account created for {parent.get_full_name()} at {school.name}',
                notification_type='info'
            )

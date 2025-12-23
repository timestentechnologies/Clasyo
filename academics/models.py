from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from tenants.models import School


class Class(models.Model):
    """Class/Grade Model"""
    EDUCATION_LEVEL_CHOICES = [
        ('unspecified', 'Unspecified'),
        ('pre_primary', 'Pre-Primary'),
        ('lower_primary', 'Lower Primary (Grades 1-3)'),
        ('upper_primary', 'Upper Primary (Grades 4-6)'),
        ('junior_secondary', 'Junior Secondary (Grades 7-9)'),
        ('senior_secondary', 'Senior Secondary (Grades 10-12)'),
        ('tvet', 'TVET'),
        ('college', 'College'),
    ]
    education_level = models.CharField(_("Education Level"), max_length=50,
                                       choices=EDUCATION_LEVEL_CHOICES, default='unspecified')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='classes', null=True, blank=True)
    name = models.CharField(_("Class Name"), max_length=100)
    numeric_name = models.IntegerField(_("Numeric Name"), null=True, blank=True)
    description = models.TextField(_("Description"), blank=True)
    
    # Order for display
    order = models.IntegerField(_("Display Order"), default=0)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")
        ordering = ['order', 'numeric_name', 'name']
    
    def __str__(self):
        return self.name


class Section(models.Model):
    """Section Model (like A, B, C)"""
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(_("Section Name"), max_length=50)
    
    # Capacity
    max_students = models.IntegerField(_("Maximum Students"), default=40)
    
    # Class Teacher
    class_teacher = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='class_sections',
                                     limit_choices_to={'role': 'teacher'})
    
    # Room
    room = models.ForeignKey('ClassRoom', on_delete=models.SET_NULL, 
                           null=True, blank=True, related_name='sections')
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Section")
        verbose_name_plural = _("Sections")
        ordering = ['class_name', 'name']
        unique_together = ['class_name', 'name']
    
    def __str__(self):
        return f"{self.class_name.name} - {self.name}"


class Subject(models.Model):
    """Subject Model"""
    SUBJECT_TYPE_CHOICES = [
        ('theory', 'Theory'),
        ('practical', 'Practical'),
        ('both', 'Theory + Practical'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='subjects', null=True, blank=True)
    name = models.CharField(_("Subject Name"), max_length=100)
    code = models.CharField(_("Subject Code"), max_length=20, unique=True)
    subject_type = models.CharField(_("Subject Type"), max_length=20, 
                                   choices=SUBJECT_TYPE_CHOICES, default='theory')
    description = models.TextField(_("Description"), blank=True)
    
    # Credits
    credits = models.IntegerField(_("Credits"), default=0)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Subject")
        verbose_name_plural = _("Subjects")
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class OptionalSubject(models.Model):
    """Optional Subject Configuration"""
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='optional_subjects')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='optional_for_classes')
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Optional Subject")
        verbose_name_plural = _("Optional Subjects")
        unique_together = ['class_name', 'subject']
    
    def __str__(self):
        return f"{self.subject.name} (Optional for {self.class_name.name})"


class AssignedSubject(models.Model):
    """Subject Assignment to Class"""
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assigned_subjects')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, 
                               related_name='assigned_subjects', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='subject_assignments')
    teacher = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='assigned_subjects',
                               limit_choices_to={'role': 'teacher'})
    
    # Academic Year
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE,
                                     related_name='subject_assignments')
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Assigned Subject")
        verbose_name_plural = _("Assigned Subjects")
        ordering = ['class_name', 'subject']
    
    def __str__(self):
        return f"{self.subject.name} - {self.class_name.name}"


class ClassRoom(models.Model):
    """Classroom Model"""
    ROOM_TYPE_CHOICES = [
        ('lecture', 'Lecture Hall'),
        ('lab', 'Laboratory'),
        ('computer', 'Computer Lab'),
        ('library', 'Library'),
        ('auditorium', 'Auditorium'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(_("Room Name"), max_length=100)
    room_number = models.CharField(_("Room Number"), max_length=50, unique=True)
    room_type = models.CharField(_("Room Type"), max_length=20, choices=ROOM_TYPE_CHOICES)
    
    capacity = models.IntegerField(_("Capacity"), default=40)
    floor = models.CharField(_("Floor"), max_length=20, blank=True)
    building = models.CharField(_("Building"), max_length=100, blank=True)
    
    # Facilities
    has_projector = models.BooleanField(_("Has Projector"), default=False)
    has_ac = models.BooleanField(_("Has AC"), default=False)
    has_smartboard = models.BooleanField(_("Has Smart Board"), default=False)
    
    description = models.TextField(_("Description"), blank=True)
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Classroom")
        verbose_name_plural = _("Classrooms")
        ordering = ['building', 'floor', 'room_number']
    
    def __str__(self):
        return f"{self.room_number} - {self.name}"


class ClassTime(models.Model):
    """Class Time Periods"""
    name = models.CharField(_("Period Name"), max_length=100)
    start_time = models.TimeField(_("Start Time"))
    end_time = models.TimeField(_("End Time"))
    
    # Period type
    is_break = models.BooleanField(_("Is Break"), default=False)
    
    order = models.IntegerField(_("Display Order"), default=0)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    class Meta:
        verbose_name = _("Class Time")
        verbose_name_plural = _("Class Times")
        ordering = ['order', 'start_time']
    
    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"


class ClassRoutine(models.Model):
    """Class Routine/Timetable"""
    WEEKDAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]
    
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='routines')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='routines')
    
    day_of_week = models.IntegerField(_("Day of Week"), choices=WEEKDAY_CHOICES)
    class_time = models.ForeignKey(ClassTime, on_delete=models.CASCADE, related_name='routines')
    
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='routines')
    teacher = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='class_routines',
                               limit_choices_to={'role': 'teacher'})
    room = models.ForeignKey(ClassRoom, on_delete=models.SET_NULL, 
                           null=True, blank=True, related_name='routines')
    
    # Academic Year
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE,
                                     related_name='class_routines')
    
    notes = models.TextField(_("Notes"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Class Routine")
        verbose_name_plural = _("Class Routines")
        ordering = ['day_of_week', 'class_time__start_time']
        unique_together = ['class_name', 'section', 'day_of_week', 'class_time', 'academic_year']
    
    def __str__(self):
        return f"{self.class_name} {self.section} - {self.get_day_of_week_display()} - {self.class_time}"


class House(models.Model):
    """House System for Students"""
    name = models.CharField(_("House Name"), max_length=100)
    color = models.CharField(_("House Color"), max_length=50, blank=True)
    description = models.TextField(_("Description"), blank=True)
    
    # House Captain
    captain = models.ForeignKey('students.Student', on_delete=models.SET_NULL,
                               null=True, blank=True, related_name='captained_house')
    
    # House Teacher/In-charge
    teacher_incharge = models.ForeignKey('accounts.User', on_delete=models.SET_NULL,
                                        null=True, blank=True, related_name='managed_houses',
                                        limit_choices_to={'role': 'teacher'})
    
    # Points (for house competitions)
    total_points = models.IntegerField(_("Total Points"), default=0)
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("House")
        verbose_name_plural = _("Houses")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class StudyMaterial(models.Model):
    """Study Material/Content Upload"""
    CONTENT_TYPE_CHOICES = [
        ('assignment', 'Assignment'),
        ('syllabus', 'Syllabus'),
        ('notes', 'Notes'),
        ('video', 'Video'),
        ('other', 'Other Downloads'),
    ]
    
    title = models.CharField(_("Title"), max_length=200)
    content_type = models.CharField(_("Content Type"), max_length=20, choices=CONTENT_TYPE_CHOICES)
    description = models.TextField(_("Description"), blank=True)
    
    # Classification
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='study_materials')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, 
                               related_name='study_materials', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='study_materials')
    
    # File
    file = models.FileField(_("File"), upload_to='study_materials/')
    file_type = models.CharField(_("File Type"), max_length=50, blank=True)
    file_size = models.BigIntegerField(_("File Size (bytes)"), default=0)
    
    # Visibility
    is_public = models.BooleanField(_("Is Public"), default=True)
    available_from = models.DateField(_("Available From"), null=True, blank=True)
    available_until = models.DateField(_("Available Until"), null=True, blank=True)
    
    # Upload details
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE,
                                   related_name='uploaded_materials')
    uploaded_at = models.DateTimeField(_("Uploaded At"), auto_now_add=True)
    
    # Downloads tracking
    download_count = models.IntegerField(_("Download Count"), default=0)
    
    class Meta:
        verbose_name = _("Study Material")
        verbose_name_plural = _("Study Materials")
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return self.title


class Syllabus(models.Model):
    """Syllabus Model"""
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='syllabi')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='syllabi')
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE,
                                     related_name='syllabi')
    
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"), blank=True)
    
    # Syllabus content
    content = models.TextField(_("Syllabus Content"))
    
    # File attachment
    file = models.FileField(_("Syllabus File"), upload_to='syllabus/', null=True, blank=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE,
                                  related_name='created_syllabi')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Syllabus")
        verbose_name_plural = _("Syllabi")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.class_name} - {self.subject} - {self.academic_year}"


class Assignment(models.Model):
    """Assignment Model"""
    title = models.CharField(_("Assignment Title"), max_length=200)
    description = models.TextField(_("Description"))
    
    # Classification
    class_name = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='assignments')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, 
                               related_name='assignments', null=True, blank=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='assignments')
    
    # Assignment file
    assignment_file = models.FileField(_("Assignment File"), upload_to='assignments/', 
                                      null=True, blank=True)
    
    # Dates
    assigned_date = models.DateField(_("Assigned Date"))
    due_date = models.DateField(_("Due Date"))
    
    # Marks
    max_marks = models.IntegerField(_("Maximum Marks"), default=100)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE,
                                  related_name='created_assignments')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Assignment")
        verbose_name_plural = _("Assignments")
        ordering = ['-assigned_date']
    
    def __str__(self):
        return f"{self.title} - {self.class_name} {self.subject}"


class AssignmentSubmission(models.Model):
    """Student Assignment Submission"""
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, 
                               related_name='assignment_submissions')
    
    # Submission
    submission_file = models.FileField(_("Submission File"), upload_to='assignment_submissions/')
    submission_text = models.TextField(_("Submission Text"), blank=True)
    submitted_at = models.DateTimeField(_("Submitted At"), auto_now_add=True)
    
    # Evaluation
    marks_obtained = models.DecimalField(_("Marks Obtained"), max_digits=5, decimal_places=2,
                                        null=True, blank=True)
    feedback = models.TextField(_("Feedback"), blank=True)
    evaluated_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL,
                                    null=True, blank=True, related_name='evaluated_assignments')
    evaluated_at = models.DateTimeField(_("Evaluated At"), null=True, blank=True)
    
    # Status
    is_late = models.BooleanField(_("Is Late Submission"), default=False)
    
    class Meta:
        verbose_name = _("Assignment Submission")
        verbose_name_plural = _("Assignment Submissions")
        ordering = ['-submitted_at']
        unique_together = ['assignment', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.assignment.title}"

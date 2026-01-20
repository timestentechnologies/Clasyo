from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from django_countries.fields import CountryField
from django.core.validators import MinValueValidator, MaxValueValidator


class StudentCategory(models.Model):
    """Student Category Model"""
    name = models.CharField(_("Category Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    
    class Meta:
        verbose_name = _("Student Category")
        verbose_name_plural = _("Student Categories")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Student(models.Model):
    """Student Model"""
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]
    
    # Link to User
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='student_profile')
    
    # Student Basic Information
    admission_number = models.CharField(_("Admission Number"), max_length=50, unique=True)
    roll_number = models.CharField(_("Roll Number"), max_length=50, blank=True)
    
    # Personal Information
    first_name = models.CharField(_("First Name"), max_length=150)
    last_name = models.CharField(_("Last Name"), max_length=150)
    gender = models.CharField(_("Gender"), max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(_("Date of Birth"))
    place_of_birth = models.CharField(_("Place of Birth"), max_length=200, blank=True)
    nationality = CountryField(_("Nationality"), blank=True)
    religion = models.CharField(_("Religion"), max_length=100, blank=True)
    caste = models.CharField(_("Caste"), max_length=100, blank=True)
    mother_tongue = models.CharField(_("Mother Tongue"), max_length=100, blank=True)
    
    # Physical Information
    blood_group = models.CharField(_("Blood Group"), max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)
    height = models.DecimalField(_("Height (cm)"), max_digits=5, decimal_places=2, null=True, blank=True)
    weight = models.DecimalField(_("Weight (kg)"), max_digits=5, decimal_places=2, null=True, blank=True)
    measurement_date = models.DateField(_("Measurement Date"), null=True, blank=True)
    
    # Photos
    photo = models.ImageField(_("Photo"), upload_to='students/photos/', blank=True, null=True)
    
    # Contact Information
    email = models.EmailField(_("Email"), blank=True)
    phone = PhoneNumberField(_("Phone Number"), blank=True, null=True)
    mobile = PhoneNumberField(_("Mobile Number"), blank=True, null=True)
    
    # Address
    current_address = models.TextField(_("Current Address"))
    permanent_address = models.TextField(_("Permanent Address"), blank=True)
    city = models.CharField(_("City"), max_length=100)
    state = models.CharField(_("State"), max_length=100)
    country = CountryField(_("Country"))
    postal_code = models.CharField(_("Postal Code"), max_length=20)
    
    # Academic Information
    category = models.ForeignKey(StudentCategory, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='students')
    current_class = models.ForeignKey('academics.Class', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='students')
    section = models.ForeignKey('academics.Section', on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='students')
    # Tenant (School) linkage
    school = models.ForeignKey('tenants.School', on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    # Admission Details
    admission_date = models.DateField(_("Admission Date"))
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='students')
    
    # Previous School Information
    previous_school = models.CharField(_("Previous School"), max_length=255, blank=True)
    previous_class = models.CharField(_("Previous Class"), max_length=50, blank=True)
    transfer_certificate_number = models.CharField(_("TC Number"), max_length=100, blank=True)
    
    # Parent/Guardian Information
    father_name = models.CharField(_("Father's Name"), max_length=200)
    father_phone = PhoneNumberField(_("Father's Phone"), blank=True, null=True)
    father_email = models.EmailField(_("Father's Email"), blank=True)
    father_occupation = models.CharField(_("Father's Occupation"), max_length=200, blank=True)
    father_photo = models.ImageField(_("Father's Photo"), upload_to='students/parents/', blank=True, null=True)
    
    mother_name = models.CharField(_("Mother's Name"), max_length=200)
    mother_phone = PhoneNumberField(_("Mother's Phone"), blank=True, null=True)
    mother_email = models.EmailField(_("Mother's Email"), blank=True)
    mother_occupation = models.CharField(_("Mother's Occupation"), max_length=200, blank=True)
    mother_photo = models.ImageField(_("Mother's Photo"), upload_to='students/parents/', blank=True, null=True)
    
    guardian_name = models.CharField(_("Guardian's Name"), max_length=200, blank=True)
    guardian_phone = PhoneNumberField(_("Guardian's Phone"), blank=True, null=True)
    guardian_email = models.EmailField(_("Guardian's Email"), blank=True)
    guardian_relation = models.CharField(_("Guardian's Relation"), max_length=100, blank=True)
    guardian_occupation = models.CharField(_("Guardian's Occupation"), max_length=200, blank=True)
    guardian_address = models.TextField(_("Guardian's Address"), blank=True)
    guardian_photo = models.ImageField(_("Guardian's Photo"), upload_to='students/parents/', blank=True, null=True)
    
    # Parent User Link
    parent_user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                   null=True, blank=True, related_name='children',
                                   limit_choices_to={'role': 'parent'})
    
    # Medical Information
    medical_history = models.TextField(_("Medical History"), blank=True)
    allergies = models.TextField(_("Allergies"), blank=True)
    disabilities = models.TextField(_("Disabilities"), blank=True)
    current_medications = models.TextField(_("Current Medications"), blank=True)
    
    # Documents
    birth_certificate = models.FileField(_("Birth Certificate"), upload_to='students/documents/', blank=True, null=True)
    transfer_certificate = models.FileField(_("Transfer Certificate"), upload_to='students/documents/', blank=True, null=True)
    previous_marksheet = models.FileField(_("Previous Marksheet"), upload_to='students/documents/', blank=True, null=True)
    other_documents = models.FileField(_("Other Documents"), upload_to='students/documents/', blank=True, null=True)
    
    # Transport & Hostel
    is_transport_required = models.BooleanField(_("Transport Required"), default=False)
    route = models.ForeignKey('transport.Route', on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='students')
    
    is_hostel_required = models.BooleanField(_("Hostel Required"), default=False)
    dormitory = models.ForeignKey('dormitory.Dormitory', on_delete=models.SET_NULL, 
                                 null=True, blank=True, related_name='students')
    room = models.ForeignKey('dormitory.Room', on_delete=models.SET_NULL, 
                            null=True, blank=True, related_name='students')
    
    # House System
    house = models.ForeignKey('academics.House', on_delete=models.SET_NULL, 
                             null=True, blank=True, related_name='students')
    
    # Sibling Information
    siblings = models.ManyToManyField('self', blank=True, symmetrical=True)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_alumni = models.BooleanField(_("Is Alumni"), default=False)
    leaving_date = models.DateField(_("Leaving Date"), null=True, blank=True)
    leaving_reason = models.TextField(_("Leaving Reason"), blank=True)
    
    # Metadata
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='created_students')
    
    class Meta:
        verbose_name = _("Student")
        verbose_name_plural = _("Students")
        ordering = ['admission_number']
        indexes = [
            models.Index(fields=['admission_number']),
            models.Index(fields=['first_name', 'last_name']),
            models.Index(fields=['current_class', 'section']),
        ]
    
    def __str__(self):
        return f"{self.admission_number} - {self.get_full_name()}"
    
    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()
    
    @property
    def age(self):
        """Calculate student's age"""
        from django.utils import timezone
        today = timezone.now().date()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @staticmethod
    def generate_admission_number(prefix='STU'):
        """Generate next admission number with prefix"""
        last_student = Student.objects.order_by('-id').first()
        if last_student and last_student.admission_number:
            # Extract number from last admission number
            try:
                last_number = int(''.join(filter(str.isdigit, last_student.admission_number)))
                new_number = last_number + 1
            except ValueError:
                new_number = 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:05d}"  # e.g., STU00001


class StudentGroup(models.Model):
    """Student Group Model for organizing students"""
    name = models.CharField(_("Group Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    students = models.ManyToManyField(Student, related_name='groups', blank=True)
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='created_student_groups')
    
    class Meta:
        verbose_name = _("Student Group")
        verbose_name_plural = _("Student Groups")
        ordering = ['name']
    
    def __str__(self):
        return self.name


class StudentPromotion(models.Model):
    """Student Promotion Model"""
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='promotions')
    from_class = models.ForeignKey('academics.Class', on_delete=models.CASCADE, 
                                  related_name='promoted_from')
    from_section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, 
                                    related_name='promoted_from', null=True, blank=True)
    to_class = models.ForeignKey('academics.Class', on_delete=models.CASCADE, 
                                related_name='promoted_to')
    to_section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, 
                                  related_name='promoted_to', null=True, blank=True)
    
    from_academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE, 
                                          related_name='promotions_from')
    to_academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.CASCADE, 
                                        related_name='promotions_to')
    
    promotion_date = models.DateField(_("Promotion Date"))
    remarks = models.TextField(_("Remarks"), blank=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='student_promotions')
    
    class Meta:
        verbose_name = _("Student Promotion")
        verbose_name_plural = _("Student Promotions")
        ordering = ['-promotion_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.from_class} to {self.to_class}"


class DisabledStudent(models.Model):
    """Disabled Students Record"""
    student = models.OneToOneField(Student, on_delete=models.CASCADE, related_name='disability_record')
    reason = models.TextField(_("Reason for Disabling"))
    disabled_date = models.DateField(_("Disabled Date"))
    
    can_reactivate = models.BooleanField(_("Can Reactivate"), default=True)
    notes = models.TextField(_("Notes"), blank=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='disabled_students')
    
    class Meta:
        verbose_name = _("Disabled Student")
        verbose_name_plural = _("Disabled Students")
        ordering = ['-disabled_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - Disabled on {self.disabled_date}"


class StudentDocument(models.Model):
    """Additional Student Documents"""
    DOCUMENT_TYPE_CHOICES = [
        ('certificate', 'Certificate'),
        ('marksheet', 'Marksheet'),
        ('id_proof', 'ID Proof'),
        ('photo', 'Photo'),
        ('medical', 'Medical Document'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(_("Document Type"), max_length=50, choices=DOCUMENT_TYPE_CHOICES)
    title = models.CharField(_("Title"), max_length=200)
    document_file = models.FileField(_("Document File"), upload_to='students/documents/')
    description = models.TextField(_("Description"), blank=True)
    
    uploaded_at = models.DateTimeField(_("Uploaded At"), auto_now_add=True)
    uploaded_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                   null=True, related_name='uploaded_student_documents')
    
    class Meta:
        verbose_name = _("Student Document")
        verbose_name_plural = _("Student Documents")
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"


class StudentTimeline(models.Model):
    """Student Timeline/History Model"""
    TIMELINE_TYPE_CHOICES = [
        ('admission', 'Admission'),
        ('promotion', 'Promotion'),
        ('achievement', 'Achievement'),
        ('discipline', 'Discipline'),
        ('medical', 'Medical'),
        ('leave', 'Leave'),
        ('fee_payment', 'Fee Payment'),
        ('exam', 'Examination'),
        ('other', 'Other'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='timeline')
    timeline_type = models.CharField(_("Type"), max_length=50, choices=TIMELINE_TYPE_CHOICES)
    title = models.CharField(_("Title"), max_length=200)
    description = models.TextField(_("Description"))
    date = models.DateField(_("Date"))
    document = models.FileField(_("Document"), upload_to='students/timeline/', blank=True, null=True)
    
    is_visible_to_parent = models.BooleanField(_("Visible to Parent"), default=True)
    is_visible_to_student = models.BooleanField(_("Visible to Student"), default=True)
    
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='student_timeline_entries')
    
    class Meta:
        verbose_name = _("Student Timeline")
        verbose_name_plural = _("Student Timelines")
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.title}"

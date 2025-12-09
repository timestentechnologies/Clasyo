from django.db import models
from django.contrib.auth import get_user_model
from academics.models import Class, Section
from tenants.models import School

User = get_user_model()

class Club(models.Model):
    """Club model for different school clubs and communities"""
    
    CLUB_TYPES = [
        ('academic', 'Academic'),
        ('sports', 'Sports'),
        ('arts', 'Arts & Culture'),
        ('service', 'Service & Leadership'),
        ('technology', 'Technology'),
        ('religious', 'Religious'),
        ('social', 'Social & Welfare'),
    ]
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    club_type = models.CharField(max_length=20, choices=CLUB_TYPES)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='clubs')
    
    # Club leadership
    teacher_advisor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                      related_name='advised_clubs', limit_choices_to={'role': 'teacher'})
    student_president = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='president_clubs', limit_choices_to={'role': 'student'})
    student_secretary = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='secretary_clubs', limit_choices_to={'role': 'student'})
    
    # Club details
    meeting_day = models.CharField(max_length=20, choices=[
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ], blank=True)
    meeting_time = models.TimeField(blank=True, null=True)
    meeting_venue = models.CharField(max_length=100, blank=True)
    
    # Club requirements
    max_members = models.PositiveIntegerField(default=50, help_text="Maximum number of members")
    membership_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    requires_application = models.BooleanField(default=True, help_text="Students must apply to join")
    application_deadline = models.DateField(blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        unique_together = ['school', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.school.name}"
    
    def get_current_members_count(self):
        return self.memberships.filter(status='active').count()
    
    def is_full(self):
        return self.get_current_members_count() >= self.max_members

class ClubMembership(models.Model):
    """Membership model for students joining clubs"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('graduated', 'Graduated'),
    ]
    
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_memberships')
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='memberships')
    
    # Application details
    application_date = models.DateTimeField(auto_now_add=True)
    application_reason = models.TextField(help_text="Why do you want to join this club?")
    parent_consent = models.BooleanField(default=False, help_text="Parent consent obtained")
    
    # Membership details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    join_date = models.DateField(blank=True, null=True)
    position_held = models.CharField(max_length=50, blank=True, help_text="e.g., Member, Treasurer, etc.")
    
    # Payment tracking
    fee_paid = models.BooleanField(default=False)
    fee_paid_date = models.DateField(blank=True, null=True)
    fee_amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['student', 'club']
        ordering = ['-application_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.club.name}"

class ClubActivity(models.Model):
    """Activities and events organized by clubs"""
    
    ACTIVITY_TYPES = [
        ('meeting', 'Regular Meeting'),
        ('event', 'Special Event'),
        ('competition', 'Competition'),
        ('workshop', 'Workshop'),
        ('community_service', 'Community Service'),
        ('fundraiser', 'Fundraiser'),
        ('trip', 'Field Trip'),
        ('other', 'Other'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=200)
    description = models.TextField()
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    
    # Schedule
    date = models.DateTimeField()
    duration = models.DurationField(help_text="Duration of the activity")
    venue = models.CharField(max_length=200)
    
    # Participation
    max_participants = models.PositiveIntegerField(blank=True, null=True)
    is_mandatory = models.BooleanField(default=False)
    points_awarded = models.PositiveIntegerField(default=0, help_text="Club points for participation")
    
    # Status
    is_cancelled = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.title} - {self.club.name}"

class ClubAttendance(models.Model):
    """Attendance tracking for club activities"""
    
    activity = models.ForeignKey(ClubActivity, on_delete=models.CASCADE, related_name='attendances')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='club_attendances')
    
    # Attendance status
    ATTENDANCE_STATUS = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('excused', 'Excused'),
    ]
    
    status = models.CharField(max_length=10, choices=ATTENDANCE_STATUS, default='present')
    check_in_time = models.DateTimeField(blank=True, null=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['activity', 'student']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.activity.title}"

class ClubAchievement(models.Model):
    """Achievements and awards for clubs"""
    
    ACHIEVEMENT_TYPES = [
        ('competition', 'Competition'),
        ('award', 'Award'),
        ('recognition', 'Recognition'),
        ('project', 'Project'),
        ('other', 'Other'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='achievements')
    title = models.CharField(max_length=200)
    description = models.TextField()
    achievement_type = models.CharField(max_length=20, choices=ACHIEVEMENT_TYPES)
    
    # Achievement details
    date_achieved = models.DateField()
    level = models.CharField(max_length=50, help_text="e.g., School, Regional, National")
    participants = models.ManyToManyField(User, related_name='club_achievements', blank=True)
    
    # Documentation
    certificate = models.ImageField(upload_to='clubs/achievements/', blank=True, null=True)
    photos = models.ImageField(upload_to='clubs/achievements/photos/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_achieved']
    
    def __str__(self):
        return f"{self.title} - {self.club.name}"

class ClubResource(models.Model):
    """Resources and materials for clubs"""
    
    RESOURCE_TYPES = [
        ('document', 'Document'),
        ('video', 'Video'),
        ('image', 'Image'),
        ('link', 'Link'),
        ('other', 'Other'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name='resources')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    resource_type = models.CharField(max_length=10, choices=RESOURCE_TYPES)
    
    # File/URL storage
    file = models.FileField(upload_to='clubs/resources/', blank=True, null=True)
    url = models.URLField(blank=True)
    
    # Access control
    is_public = models.BooleanField(default=True, help_text="Available to all members")
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.club.name}"

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from tenants.models import School
from django.utils import timezone
from datetime import timedelta


class BookCategory(models.Model):
    """Book Category Model"""
    name = models.CharField(_('Category Name'), max_length=100)
    code = models.CharField(_('Category Code'), max_length=20, blank=True)
    description = models.TextField(_('Description'), blank=True)
    
    # School association for multi-tenant
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='book_categories', null=True, blank=True)
    
    parent_category = models.ForeignKey('self', on_delete=models.SET_NULL, 
                                       null=True, blank=True, related_name='subcategories')
    
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Book Category')
        verbose_name_plural = _('Book Categories')
        ordering = ['name']
        unique_together = ['school', 'name']
    
    def __str__(self):
        return self.name


class Publisher(models.Model):
    """Publisher Model"""
    name = models.CharField(_('Publisher Name'), max_length=100)
    contact_person = models.CharField(_('Contact Person'), max_length=100, blank=True)
    phone = models.CharField(_('Phone Number'), max_length=20, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    address = models.TextField(_('Address'), blank=True)
    website = models.URLField(_('Website'), blank=True)
    
    # School association for multi-tenant
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='publishers', null=True, blank=True)
    
    is_active = models.BooleanField(_('Is Active'), default=True)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Publisher')
        verbose_name_plural = _('Publishers')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Author(models.Model):
    """Author Model"""
    name = models.CharField(_('Author Name'), max_length=100)
    description = models.TextField(_('Description/Biography'), blank=True)
    
    # School association for multi-tenant
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='authors', null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Author')
        verbose_name_plural = _('Authors')
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Book(models.Model):
    """Book Model"""
    BOOK_STATUS_CHOICES = [
        ('available', 'Available'),
        ('issued', 'Issued'),
        ('reserved', 'Reserved'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
        ('under_repair', 'Under Repair'),
        ('discarded', 'Discarded'),
    ]
    
    # Basic book information
    title = models.CharField(_('Title'), max_length=200)
    subtitle = models.CharField(_('Subtitle'), max_length=200, blank=True)
    authors = models.ManyToManyField(Author, related_name='books')
    isbn = models.CharField(_('ISBN'), max_length=20, blank=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='books')
    publication_date = models.DateField(_('Publication Date'), null=True, blank=True)
    edition = models.CharField(_('Edition'), max_length=50, blank=True)
    
    # Categorization
    category = models.ForeignKey(BookCategory, on_delete=models.SET_NULL, 
                               null=True, blank=True, related_name='books')
    subjects = models.ManyToManyField('academics.Subject', related_name='books', blank=True)
    
    # Physical attributes
    pages = models.PositiveIntegerField(_('Number of Pages'), null=True, blank=True)
    dimensions = models.CharField(_('Dimensions'), max_length=50, blank=True)
    weight = models.DecimalField(_('Weight (g)'), max_digits=6, decimal_places=2, null=True, blank=True)
    
    # Content information
    description = models.TextField(_('Description'), blank=True)
    table_of_contents = models.TextField(_('Table of Contents'), blank=True)
    language = models.CharField(_('Language'), max_length=50, default='English')
    
    # Library information
    call_number = models.CharField(_('Call Number'), max_length=50, blank=True)
    location = models.CharField(_('Location/Shelf'), max_length=100, blank=True)
    acquisition_date = models.DateField(_('Acquisition Date'), null=True, blank=True)
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Stock information
    quantity = models.PositiveIntegerField(_('Total Quantity'), default=1)
    available_quantity = models.PositiveIntegerField(_('Available Quantity'), default=1)
    
    # Media
    cover_image = models.ImageField(_('Cover Image'), upload_to='library/covers/', blank=True, null=True)
    digital_copy = models.FileField(_('Digital Copy'), upload_to='library/digital/', blank=True, null=True)
    is_digital = models.BooleanField(_('Is Digital'), default=False)
    
    # Status and settings
    status = models.CharField(_('Status'), max_length=20, choices=BOOK_STATUS_CHOICES, default='available')
    is_reference = models.BooleanField(_('Is Reference Book'), default=False, 
                                     help_text=_('Reference books cannot be checked out'))
    loan_period_days = models.PositiveIntegerField(_('Loan Period (days)'), default=14)
    max_renewals = models.PositiveSmallIntegerField(_('Maximum Renewals'), default=2)
    
    # School association for multi-tenant
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='books', null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                 null=True, related_name='added_books')
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Book')
        verbose_name_plural = _('Books')
        ordering = ['title']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['isbn']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_available(self):
        return self.status == 'available' and self.available_quantity > 0


class BookCopy(models.Model):
    """Individual copy of a book for tracking purposes"""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='copies')
    accession_number = models.CharField(_('Accession Number'), max_length=50, unique=True)
    
    # Copy status (mirroring book statuses)
    status = models.CharField(_('Status'), max_length=20, choices=Book.BOOK_STATUS_CHOICES, default='available')
    condition = models.CharField(_('Condition'), max_length=50, 
                              choices=[('new', 'New'), ('good', 'Good'), 
                                      ('fair', 'Fair'), ('poor', 'Poor')],
                              default='good')
    
    acquisition_date = models.DateField(_('Acquisition Date'), default=timezone.now)
    price = models.DecimalField(_('Price'), max_digits=10, decimal_places=2, null=True, blank=True)
    notes = models.TextField(_('Notes'), blank=True)
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Book Copy')
        verbose_name_plural = _('Book Copies')
        ordering = ['accession_number']
    
    def __str__(self):
        return f"{self.book.title} ({self.accession_number})"


class BookIssue(models.Model):
    """Book Issue/Checkout Model"""
    ISSUE_STATUS_CHOICES = [
        ('issued', 'Issued'),
        ('returned', 'Returned'),
        ('overdue', 'Overdue'),
        ('lost', 'Lost'),
        ('damaged', 'Damaged'),
    ]
    
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='issues')
    book_copy = models.ForeignKey(BookCopy, on_delete=models.SET_NULL, 
                                null=True, blank=True, related_name='issues')
    
    # Who checked out the book
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='book_issues')
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, 
                              null=True, blank=True, related_name='book_issues')
    
    # Issue details
    issue_date = models.DateField(_('Issue Date'), default=timezone.now)
    due_date = models.DateField(_('Due Date'))
    returned_date = models.DateField(_('Returned Date'), null=True, blank=True)
    
    # Renewals
    renewal_count = models.PositiveSmallIntegerField(_('Renewal Count'), default=0)
    last_renewed_date = models.DateField(_('Last Renewed Date'), null=True, blank=True)
    
    # Fine calculation
    fine_amount = models.DecimalField(_('Fine Amount'), max_digits=8, decimal_places=2, default=0)
    fine_paid = models.DecimalField(_('Fine Paid'), max_digits=8, decimal_places=2, default=0)
    fine_payment_date = models.DateField(_('Fine Payment Date'), null=True, blank=True)
    fine_payment_reference = models.CharField(_('Payment Reference'), max_length=100, blank=True)
    
    # Status tracking
    status = models.CharField(_('Status'), max_length=20, choices=ISSUE_STATUS_CHOICES, default='issued')
    condition_on_issue = models.CharField(_('Condition on Issue'), max_length=50, 
                                       choices=[('new', 'New'), ('good', 'Good'), 
                                               ('fair', 'Fair'), ('poor', 'Poor')],
                                       default='good')
    condition_on_return = models.CharField(_('Condition on Return'), max_length=50, 
                                        choices=[('new', 'New'), ('good', 'Good'), 
                                                ('fair', 'Fair'), ('poor', 'Poor')],
                                        null=True, blank=True)
    
    notes = models.TextField(_('Notes'), blank=True)
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                null=True, related_name='issued_books')
    received_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='received_books')
    
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    
    class Meta:
        verbose_name = _('Book Issue')
        verbose_name_plural = _('Book Issues')
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.book.title} - {self.user.get_full_name()} ({self.issue_date})"
    
    def save(self, *args, **kwargs):
        # If this is a new issue and due_date is not set, calculate it
        if not self.pk and not self.due_date:
            self.due_date = self.issue_date + timedelta(days=self.book.loan_period_days)
        
        # Update book and copy status on issue/return
        if self.status == 'issued':
            if self.book_copy:
                self.book_copy.status = 'issued'
                self.book_copy.save(update_fields=['status'])
            
            # Update book available quantity
            self.book.available_quantity = max(0, self.book.available_quantity - 1)
            self.book.save(update_fields=['available_quantity'])
        
        elif self.status == 'returned' and not self.returned_date:
            self.returned_date = timezone.now().date()
            
            if self.book_copy:
                self.book_copy.status = 'available'
                self.book_copy.condition = self.condition_on_return or self.condition_on_issue
                self.book_copy.save(update_fields=['status', 'condition'])
            
            # Update book available quantity
            self.book.available_quantity = min(self.book.quantity, self.book.available_quantity + 1)
            self.book.save(update_fields=['available_quantity'])
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        if self.returned_date:
            return False
        return timezone.now().date() > self.due_date
    
    def renew(self, days=None):
        """Renew the loan for additional days"""
        if self.renewal_count >= self.book.max_renewals:
            return False
        
        if not days:
            days = self.book.loan_period_days
        
        self.renewal_count += 1
        self.last_renewed_date = timezone.now().date()
        self.due_date = self.last_renewed_date + timedelta(days=days)
        self.save(update_fields=['renewal_count', 'last_renewed_date', 'due_date'])
        return True
    
    def calculate_fine(self, fine_rate_per_day=1.0):
        """Calculate fine for overdue books"""
        if not self.is_overdue:
            return 0
        
        today = timezone.now().date()
        overdue_days = (today - self.due_date).days
        return overdue_days * fine_rate_per_day

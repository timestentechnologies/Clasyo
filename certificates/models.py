from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import School
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from PIL import Image, ImageDraw, ImageFont
import uuid


class CertificateType(models.Model):
    """Certificate Type Model"""
    CERTIFICATE_CATEGORY_CHOICES = [
        ('academic', 'Academic'),
        ('achievement', 'Achievement'),
        ('participation', 'Participation'),
        ('completion', 'Completion'),
        ('attendance', 'Attendance'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(_("Certificate Name"), max_length=100)
    code = models.CharField(_("Certificate Code"), max_length=20, unique=True)
    category = models.CharField(_("Category"), max_length=20, choices=CERTIFICATE_CATEGORY_CHOICES, default='academic')
    description = models.TextField(_("Description"), blank=True)
    
    # Design Template
    template_html = models.TextField(_("Template HTML"), blank=True,
                                    help_text=_("HTML template with placeholders for certificate data. Use {{variable}} syntax."))
    background_image = models.ImageField(_("Background Image"), upload_to='certificates/templates/', blank=True, null=True)
    
    # School association
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='certificate_types', null=True, blank=True)
    
    # Settings
    include_qr_code = models.BooleanField(_("Include QR Code"), default=True)
    enable_verification = models.BooleanField(_("Enable Online Verification"), default=True)
    default_width_mm = models.PositiveIntegerField(_("Default Width (mm)"), default=210)  # A4 width
    default_height_mm = models.PositiveIntegerField(_("Default Height (mm)"), default=297)  # A4 height
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Certificate Type")
        verbose_name_plural = _("Certificate Types")
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"


class Certificate(models.Model):
    """Certificate Model"""
    certificate_type = models.ForeignKey(CertificateType, on_delete=models.CASCADE, related_name='certificates')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='certificates')
    
    # Certificate details
    certificate_number = models.CharField(_("Certificate Number"), max_length=50, unique=True)
    title = models.CharField(_("Title"), max_length=200)
    issue_date = models.DateField(_("Issue Date"))
    expiry_date = models.DateField(_("Expiry Date"), null=True, blank=True)
    
    # Academic details (if applicable)
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.SET_NULL, 
                                     null=True, blank=True, related_name='certificates')
    class_name = models.ForeignKey('academics.Class', on_delete=models.SET_NULL, 
                                  null=True, blank=True, related_name='certificates')
    
    # Content
    description = models.TextField(_("Description"), blank=True)
    remarks = models.TextField(_("Remarks"), blank=True)
    
    # Certificate data (for template rendering)
    certificate_data = models.JSONField(_("Certificate Data"), default=dict, blank=True,
                                       help_text=_("JSON data used to render the certificate template"))
    
    # Generated certificate
    certificate_file = models.FileField(_("Certificate File"), upload_to='certificates/issued/', blank=True, null=True)
    qr_code = models.ImageField(_("QR Code"), upload_to='certificates/qrcodes/', blank=True, null=True)
    
    # Verification
    verification_code = models.CharField(_("Verification Code"), max_length=50, unique=True, blank=True, null=True)
    is_verified = models.BooleanField(_("Is Verified"), default=True)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_revoked = models.BooleanField(_("Is Revoked"), default=False)
    revocation_reason = models.TextField(_("Revocation Reason"), blank=True)
    revoked_at = models.DateTimeField(_("Revoked At"), null=True, blank=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='issued_certificates')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("Certificate")
        verbose_name_plural = _("Certificates")
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.certificate_number} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate certificate number if not provided
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        
        # Generate verification code if not provided
        if not self.verification_code and self.certificate_type.enable_verification:
            self.verification_code = self.generate_verification_code()
        
        # Generate QR code if enabled
        if self.certificate_type.include_qr_code and not self.qr_code:
            self.generate_qr_code()
            
        super().save(*args, **kwargs)
    
    def generate_certificate_number(self):
        """Generate a unique certificate number"""
        year = self.issue_date.year
        ct_code = self.certificate_type.code
        count = Certificate.objects.filter(certificate_type=self.certificate_type).count() + 1
        return f"{ct_code}-{year}-{count:04d}"
    
    def generate_verification_code(self):
        """Generate a unique verification code"""
        return str(uuid.uuid4()).replace('-', '')[:12].upper()
    
    def generate_qr_code(self):
        """Generate QR code for certificate verification"""
        if not self.verification_code:
            self.verification_code = self.generate_verification_code()
            
        # Generate QR code containing verification URL
        verification_url = f"/certificates/verify/{self.verification_code}/"
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        self.qr_code.save(f"qr_{self.verification_code}.png", 
                         ContentFile(buffer.getvalue()), save=False)


class IDCard(models.Model):
    """Student ID Card Model"""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='id_cards')
    
    # ID Card details
    card_number = models.CharField(_("Card Number"), max_length=50, unique=True)
    issue_date = models.DateField(_("Issue Date"))
    valid_from = models.DateField(_("Valid From"))
    valid_until = models.DateField(_("Valid Until"))
    
    # School details
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='id_cards', null=True)
    academic_year = models.ForeignKey('core.AcademicYear', on_delete=models.SET_NULL, 
                                     null=True, related_name='id_cards')
    
    # Card template
    card_template = models.ForeignKey('IDCardTemplate', on_delete=models.SET_NULL, 
                                     null=True, related_name='cards')
    
    # Card content
    barcode = models.CharField(_("Barcode"), max_length=50, blank=True)
    qr_code = models.ImageField(_("QR Code"), upload_to='id_cards/qrcodes/', blank=True, null=True)
    
    # Generated ID card
    front_image = models.ImageField(_("Front Image"), upload_to='id_cards/issued/', blank=True, null=True)
    back_image = models.ImageField(_("Back Image"), upload_to='id_cards/issued/', blank=True, null=True)
    
    # Status
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_lost = models.BooleanField(_("Is Lost"), default=False)
    lost_date = models.DateField(_("Lost Date"), null=True, blank=True)
    
    created_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, 
                                  null=True, related_name='issued_id_cards')
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("ID Card")
        verbose_name_plural = _("ID Cards")
        ordering = ['-issue_date']
    
    def __str__(self):
        return f"{self.card_number} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Generate card number if not provided
        if not self.card_number:
            self.card_number = self.generate_card_number()
            
        # Generate QR code if not exists
        if not self.qr_code:
            self.generate_qr_code()
            
        super().save(*args, **kwargs)
    
    def generate_card_number(self):
        """Generate a unique ID card number"""
        year = self.issue_date.year
        student_id = self.student.admission_number
        return f"IDCARD-{year}-{student_id}"
    
    def generate_qr_code(self):
        """Generate QR code for ID card"""
        # Generate QR code containing student info and card number
        qr_data = f"ID:{self.card_number}|Name:{self.student.get_full_name()}|Class:{self.student.current_class}"
        
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        self.qr_code.save(f"qr_{self.card_number}.png", 
                         ContentFile(buffer.getvalue()), save=False)
    
    def generate_card_images(self):
        """Generate front and back ID card images"""
        if self.card_template:
            # Use the template to generate card images
            self.card_template.generate_id_card(self)


class IDCardTemplate(models.Model):
    """ID Card Template Model"""
    name = models.CharField(_("Template Name"), max_length=100)
    description = models.TextField(_("Description"), blank=True)
    
    # School association
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='id_card_templates', null=True, blank=True)
    
    # Design elements
    front_background = models.ImageField(_("Front Background"), upload_to='id_cards/templates/', blank=True, null=True)
    back_background = models.ImageField(_("Back Background"), upload_to='id_cards/templates/', blank=True, null=True)
    
    # Dimensions (in mm)
    width_mm = models.PositiveIntegerField(_("Width (mm)"), default=86)  # Standard credit card width
    height_mm = models.PositiveIntegerField(_("Height (mm)"), default=54)  # Standard credit card height
    
    # Layout configuration (stored as JSON)
    front_layout = models.JSONField(_("Front Layout"), default=dict, blank=True,
                                   help_text=_("JSON configuration for front layout elements"))
    back_layout = models.JSONField(_("Back Layout"), default=dict, blank=True,
                                  help_text=_("JSON configuration for back layout elements"))
    
    # Design settings
    school_logo_position = models.CharField(_("School Logo Position"), max_length=20, 
                                          default='top-left', blank=True)
    photo_position = models.CharField(_("Photo Position"), max_length=20, 
                                     default='top-right', blank=True)
    signature_position = models.CharField(_("Signature Position"), max_length=20, 
                                         default='bottom-right', blank=True)
    
    # Accent colors
    primary_color = models.CharField(_("Primary Color"), max_length=10, default='#003366')
    secondary_color = models.CharField(_("Secondary Color"), max_length=10, default='#ffffff')
    
    is_active = models.BooleanField(_("Is Active"), default=True)
    is_default = models.BooleanField(_("Is Default"), default=False)
    created_at = models.DateTimeField(_("Created At"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Updated At"), auto_now=True)
    
    class Meta:
        verbose_name = _("ID Card Template")
        verbose_name_plural = _("ID Card Templates")
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # If this template is set as default, unset default for other templates
        if self.is_default:
            IDCardTemplate.objects.filter(
                school=self.school, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
            
        super().save(*args, **kwargs)
    
    def generate_id_card(self, id_card):
        """Generate front and back ID card images for a student"""
        # This method would contain the logic to generate the ID card images
        # using PIL or another image manipulation library
        # The implementation would use the template settings to place
        # student information, photo, QR code, etc. on the card template
        
        # Simplified example (actual implementation would be more complex):
        try:
            # Front side
            if self.front_background:
                # Load the template background
                front_img = Image.open(self.front_background.path).convert('RGBA')
                front_draw = ImageDraw.Draw(front_img)
                
                # Add student name
                # (In a real implementation, this would use the layout configuration)
                try:
                    font = ImageFont.truetype("arial.ttf", 20)
                except IOError:
                    font = ImageFont.load_default()
                
                front_draw.text((50, 150), id_card.student.get_full_name(), font=font, fill="black")
                
                # Add student photo if available
                if id_card.student.photo:
                    try:
                        student_photo = Image.open(id_card.student.photo.path)
                        # Resize photo to fit on card
                        student_photo = student_photo.resize((100, 120))
                        # Paste photo onto card
                        front_img.paste(student_photo, (220, 50))
                    except Exception as e:
                        print(f"Error adding photo: {e}")
                
                # Save front image
                front_buffer = BytesIO()
                front_img.save(front_buffer, format="PNG")
                id_card.front_image.save(f"front_{id_card.card_number}.png",
                                      ContentFile(front_buffer.getvalue()), save=False)
            
            # Back side (similar process)
            if self.back_background:
                # Implement back side generation
                pass
                
            return True
        except Exception as e:
            print(f"Error generating ID card: {e}")
            return False


class CertificateVerification(models.Model):
    """Certificate Verification Log"""
    certificate = models.ForeignKey(Certificate, on_delete=models.CASCADE, related_name='verifications')
    verification_code = models.CharField(_("Verification Code"), max_length=50)
    
    # Verification details
    verification_date = models.DateTimeField(_("Verification Date"), auto_now_add=True)
    verified_by_ip = models.GenericIPAddressField(_("Verified By IP"), null=True, blank=True)
    user_agent = models.TextField(_("User Agent"), blank=True)
    
    # Result
    is_valid = models.BooleanField(_("Is Valid"), default=True)
    verification_message = models.CharField(_("Verification Message"), max_length=255, blank=True)
    
    class Meta:
        verbose_name = _("Certificate Verification")
        verbose_name_plural = _("Certificate Verifications")
        ordering = ['-verification_date']
    
    def __str__(self):
        return f"{self.certificate} - {self.verification_date}"

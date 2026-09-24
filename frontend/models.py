from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone


class FAQ(models.Model):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.CharField(max_length=100, default='General')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'category', 'question']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question


class PageContent(models.Model):
    """Manage static page content"""
    PAGE_CHOICES = [
        ('about', 'About Us'),
        ('home_hero', 'Home - Hero Section'),
        ('home_features', 'Home - Features'),
        ('contact', 'Contact Info'),
    ]
    
    page = models.CharField(max_length=50, choices=PAGE_CHOICES, unique=True)
    title = models.CharField(max_length=255)
    subtitle = models.CharField(max_length=255, blank=True)
    content = models.TextField()
    extra_data = models.JSONField(null=True, blank=True, help_text='Additional structured data')
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Page Content'
        verbose_name_plural = 'Page Contents'
    
    def __str__(self):
        return f"{self.get_page_display()} - {self.title}"


class ContactMessage(models.Model):
    """Contact form submissions"""
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class ForumThread(models.Model):
    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forum_threads'
    )
    author_name = models.CharField(max_length=100, blank=True)
    author_email = models.EmailField(blank=True)
    is_locked = models.BooleanField(default=False)
    views_count = models.PositiveIntegerField(default=0)
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_activity', '-created_at']

    def __str__(self):
        return self.title


class ForumPost(models.Model):
    thread = models.ForeignKey(ForumThread, on_delete=models.CASCADE, related_name='posts')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='forum_posts'
    )
    author_name = models.CharField(max_length=100, blank=True)
    author_email = models.EmailField(blank=True)
    content = models.TextField()
    attachment = models.FileField(upload_to='forum/attachments/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Post in {self.thread.title}"


class HeroContent(models.Model):
    """Dynamic Hero Section CMS Configuration"""
    BG_TYPE_CHOICES = [
        ('gradient', 'Modern Dark Gradient'),
        ('color', 'Solid Color'),
        ('image', 'Background Image with Overlay'),
    ]

    HEIGHT_CHOICES = [
        ('compact', 'Compact (500px)'),
        ('medium', 'Medium (620px)'),
        ('large', 'Large (750px - Default)'),
        ('xlarge', 'Extra Large (850px)'),
        ('full', 'Full Screen (90vh)'),
    ]

    title_prefix = models.CharField(max_length=150, default="Transform Your", help_text="First part of hero title")
    typing_texts = models.TextField(
        default="School Management\nAcademic Operations\nLearning Experiences\nCBC & TVET Institutions",
        help_text="Line-separated phrases for the typing effect"
    )
    subtitle = models.TextField(
        default="Complete cloud-based solution for modern education management. Streamline operations and enhance learning experiences."
    )
    primary_btn_text = models.CharField(max_length=60, default="Start Free Trial")
    primary_btn_url = models.CharField(max_length=255, default="#registerModal", help_text="URL or modal target like #registerModal")
    secondary_btn_text = models.CharField(max_length=60, default="Sign In")
    secondary_btn_url = models.CharField(max_length=255, default="#loginModal", help_text="URL or modal target like #loginModal")
    
    bg_type = models.CharField(max_length=20, choices=BG_TYPE_CHOICES, default='gradient', blank=True)
    bg_image = models.ImageField(upload_to='frontend/hero/', null=True, blank=True)
    bg_color = models.CharField(max_length=30, default="#0f172a", blank=True, help_text="Hex code or CSS color")
    bg_gradient = models.CharField(
        max_length=255, 
        default="linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #164e63 100%)",
        blank=True,
        help_text="Custom CSS gradient string"
    )
    overlay_color = models.CharField(
        max_length=30,
        default="#0f172a",
        blank=True,
        help_text="Hex overlay color code e.g. #0f172a or #000000"
    )
    overlay_opacity = models.FloatField(
        default=0.85, 
        blank=True,
        help_text="Overlay darkness from 0.0 (transparent) to 1.0 (solid)"
    )
    min_height = models.CharField(
        max_length=20,
        choices=HEIGHT_CHOICES,
        default='large',
        help_text="Hero section height sizing"
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Hero Section Content"
        verbose_name_plural = "Hero Section Content"

    def __str__(self):
        return f"Hero Content (Updated {self.updated_at.strftime('%Y-%m-%d')})"

    def get_typing_list(self):
        return [t.strip() for t in self.typing_texts.split('\n') if t.strip()]


class FloatingParallaxElement(models.Model):
    """Customizable Floating Parallax Icons / Elements on Hero and Landing pages"""
    ANIMATION_CHOICES = [
        ('float', 'Float Up & Down (Smooth)'),
        ('pulse', 'Pulse / Scale Glow'),
        ('rotate', 'Slow Rotation'),
        ('parallax', 'Scroll Parallax Shift'),
    ]

    SECTION_TARGET_CHOICES = [
        ('hero', 'Hero Section (Top of Page)'),
        ('parallax', 'Parallax Showcase Banners'),
        ('all', 'All Hero & Parallax Sections'),
    ]

    PRESET_POSITION_CHOICES = [
        ('custom', 'Custom Coordinates (Enter Top/Left/Right/Bottom below)'),
        ('top_left', 'Top Left Corner (12% Top, 8% Left)'),
        ('top_right', 'Top Right Corner (20% Top, 12% Right)'),
        ('center_left', 'Center Left (48% Top, 10% Left)'),
        ('center_right', 'Center Right (50% Top, 8% Right)'),
        ('bottom_left', 'Bottom Left Corner (18% Bottom, 14% Left)'),
        ('bottom_right', 'Bottom Right Corner (22% Bottom, 20% Right)'),
    ]

    title = models.CharField(max_length=100, blank=True, help_text="Optional reference title or label")
    icon = models.CharField(max_length=100, default="fas fa-graduation-cap", help_text="FontAwesome icon class e.g. fas fa-book")
    section_target = models.CharField(
        max_length=30,
        choices=SECTION_TARGET_CHOICES,
        default='hero',
        help_text="Select section where this icon appears on homepage"
    )
    preset_position = models.CharField(
        max_length=30,
        choices=PRESET_POSITION_CHOICES,
        default='custom',
        help_text="Quick preset position location or custom coordinates"
    )
    position_top = models.CharField(max_length=20, default="10%", help_text="Top CSS value (e.g. 10%, 50px, auto)")
    position_left = models.CharField(max_length=20, default="10%", help_text="Left CSS value (e.g. 10%, 40px, auto)")
    position_bottom = models.CharField(max_length=20, default="auto", help_text="Bottom CSS value (e.g. 15%, auto)")
    position_right = models.CharField(max_length=20, default="auto", help_text="Right CSS value (e.g. 15%, auto)")
    font_size = models.CharField(max_length=20, default="3rem", help_text="Icon font size (e.g. 2.5rem, 40px)")
    opacity = models.FloatField(default=0.15, help_text="Opacity from 0.05 to 1.0")
    animation_type = models.CharField(max_length=30, choices=ANIMATION_CHOICES, default='float')
    animation_duration = models.CharField(max_length=20, default="18s", help_text="Speed duration e.g. 15s, 20s")
    animation_delay = models.CharField(max_length=20, default="0s", help_text="Delay offset e.g. 0s, 2s")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Floating Parallax Element"
        verbose_name_plural = "Floating Parallax Elements"

    def __str__(self):
        return f"{self.title or self.icon} ({self.get_section_target_display()})"

    def get_positions(self):
        if self.preset_position == 'top_left':
            return {'top': '12%', 'left': '8%', 'bottom': 'auto', 'right': 'auto'}
        elif self.preset_position == 'top_right':
            return {'top': '20%', 'left': 'auto', 'bottom': 'auto', 'right': '12%'}
        elif self.preset_position == 'center_left':
            return {'top': '48%', 'left': '10%', 'bottom': 'auto', 'right': 'auto'}
        elif self.preset_position == 'center_right':
            return {'top': '50%', 'left': 'auto', 'bottom': 'auto', 'right': '8%'}
        elif self.preset_position == 'bottom_left':
            return {'top': 'auto', 'left': '14%', 'bottom': '18%', 'right': 'auto'}
        elif self.preset_position == 'bottom_right':
            return {'top': 'auto', 'left': 'auto', 'bottom': '22%', 'right': '20%'}
        return {
            'top': self.position_top,
            'left': self.position_left,
            'bottom': self.position_bottom,
            'right': self.position_right
        }


class ProcessStep(models.Model):
    """How It Works / Production Process Stepper"""
    step_number = models.PositiveIntegerField(default=1, help_text="Order and display number (e.g. 1, 2, 3...)")
    phase_tag = models.CharField(max_length=50, default="PHASE 1", help_text="e.g. PHASE 1, STEP 1")
    title = models.CharField(max_length=150, help_text="e.g. Discovery & Strategy")
    subtitle = models.CharField(max_length=200, blank=True, help_text="Short one-line summary")
    description = models.TextField(help_text="Detailed description of this step")
    icon = models.CharField(max_length=60, default="fas fa-compass", help_text="FontAwesome icon class, e.g. fas fa-cogs")
    accent_color = models.CharField(max_length=30, default="#f59e0b", help_text="Accent color hex code (e.g. #f59e0b, #06b6d4)")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'step_number']
        verbose_name = "How It Works Step"
        verbose_name_plural = "How It Works Steps"

    def __str__(self):
        return f"{self.phase_tag}: {self.title}"

    @property
    def formatted_step_number(self):
        return f"{self.step_number:02d}"


class FeatureItem(models.Model):
    """Homepage Features Card"""
    title = models.CharField(max_length=100)
    description = models.TextField()
    icon = models.CharField(max_length=60, default="fas fa-star", help_text="FontAwesome class e.g. fas fa-user-graduate")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Feature Item"
        verbose_name_plural = "Feature Items"

    def __str__(self):
        return self.title


class ParallaxSection(models.Model):
    """Customizable Parallax Banner Section"""
    SCROLL_EFFECT_CHOICES = [
        ('fixed_bg', 'Fixed Background (Classic Parallax)'),
        ('zoom_in', 'Scroll Zoom In (Expands on Scroll)'),
        ('zoom_out', 'Scroll Zoom Out (Subtle Shrink)'),
        ('standard', 'Standard Smooth Translation'),
        ('none', 'None (Static Background)'),
    ]

    TARGET_POSITION_CHOICES = [
        ('after_hero', 'After Hero Section'),
        ('after_stats', 'After Stats Section'),
        ('after_process', 'After How It Works / Stepper'),
        ('after_features', 'After Comprehensive Features'),
        ('after_cta', 'After CTA Section (Before Footer)'),
    ]

    badge_text = models.CharField(max_length=60, default="", blank=True)
    title = models.CharField(max_length=200, default="Empowering Kenyan Schools with Cutting-Edge Cloud SaaS")
    subtitle = models.CharField(max_length=255, blank=True, default="Seamless CBC compliance, automated financial ledger, and AI-driven performance tracking.")
    content = models.TextField(blank=True)
    
    target_position = models.CharField(
        max_length=30,
        choices=TARGET_POSITION_CHOICES,
        default='after_process',
        help_text="Where on the home page this parallax section appears"
    )
    
    primary_btn_text = models.CharField(max_length=60, default="Explore Pricing", blank=True)
    primary_btn_url = models.CharField(max_length=255, default="/pricing/", blank=True)
    secondary_btn_text = models.CharField(max_length=60, default="Get in Touch", blank=True)
    secondary_btn_url = models.CharField(max_length=255, default="/contact/", blank=True)
    
    bg_image = models.ImageField(upload_to='frontend/parallax/', null=True, blank=True)
    bg_color = models.CharField(max_length=30, default="#0f172a", help_text="Fallback background color")
    overlay_opacity = models.FloatField(
        default=0.75, 
        help_text="Overlay darkness from 0.0 (transparent) to 1.0 (black/solid)"
    )
    scroll_effect = models.CharField(
        max_length=20, 
        choices=SCROLL_EFFECT_CHOICES, 
        default='fixed_bg',
        help_text="Parallax movement effect as user scrolls"
    )
    
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        verbose_name = "Parallax Section"
        verbose_name_plural = "Parallax Sections"

    def __str__(self):
        return f"{self.title} ({self.get_target_position_display()})"


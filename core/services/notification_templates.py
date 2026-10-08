"""
Notification Template Service
Handles dynamic rendering of Email, SMS, and WhatsApp templates with standardized
header/footer branding layouts and multi-tenant fallbacks.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.utils import timezone

logger = logging.getLogger(__name__)


def get_branding_dict(school=None, request=None) -> Dict[str, Any]:
    """
    Resolve dynamic branding context for emails.
    If school is provided, extracts school branding.
    Otherwise, resolves global system/platform branding.
    """
    from core.models import SystemSetting

    current_year = timezone.now().year

    if school:
        # Resolve School Branding
        logo_url = None
        if school.logo:
            try:
                logo_url = school.logo.url
                if request and not logo_url.startswith(('http://', 'https://')):
                    logo_url = request.build_absolute_uri(logo_url)
            except Exception:
                logo_url = None

        address_parts = [p for p in [school.address, school.city, school.state, school.country] if p]
        address_str = ", ".join(address_parts) if address_parts else ""

        tagline = getattr(school, 'motto', None) or "Empowering education through technology and excellence."

        return {
            'name': school.name,
            'tagline': tagline,
            'logo_url': logo_url,
            'footer_logo_url': logo_url,
            'address': address_str,
            'phone': school.phone or "",
            'email': school.email or "",
            'website': school.website or "",
            'accent_color': '#ea580c',  # Vibrant orange accent bar & button matching design
            'button_color': '#ea580c',
            'disclaimer': f"You received this email because you are registered as a parent, student, or staff member at {school.name}.",
            'current_year': current_year,
        }

    # Resolve Global Platform Branding
    sys_setting = SystemSetting.objects.first()
    logo_url = None
    if sys_setting and sys_setting.school_logo:
        try:
            logo_url = sys_setting.school_logo.url
            if request and not logo_url.startswith(('http://', 'https://')):
                logo_url = request.build_absolute_uri(logo_url)
        except Exception:
            logo_url = None

    platform_name = sys_setting.school_name if (sys_setting and sys_setting.school_name) else "TimesTen Technologies"
    platform_phone = sys_setting.school_phone if (sys_setting and sys_setting.school_phone) else "0795155230"
    platform_email = sys_setting.school_email if (sys_setting and sys_setting.school_email) else "info@timestentechnologies.co.ke"
    platform_address = sys_setting.school_address if (sys_setting and sys_setting.school_address) else "Westlands, Nairobi Kenya 00100"

    return {
        'name': platform_name,
        'tagline': "Empowering your business with cutting-edge technology and innovation.",
        'logo_url': logo_url,
        'footer_logo_url': logo_url,
        'address': platform_address,
        'phone': platform_phone,
        'email': platform_email,
        'website': "https://timestentechnologies.co.ke",
        'accent_color': '#ea580c',
        'button_color': '#ea580c',
        'disclaimer': "You received this email regarding your Clasyo school management platform subscription or account.",
        'current_year': current_year,
    }


def get_notification_template(code: str, channel: str = 'email', school=None):
    """
    Retrieve active NotificationTemplate by code and channel.
    Checks for school-specific template first, then falls back to global system template.
    """
    from superadmin.models import NotificationTemplate

    if school:
        school_tpl = NotificationTemplate.objects.filter(
            school=school,
            code=code,
            channel=channel,
            is_active=True
        ).first()
        if school_tpl:
            return school_tpl

    # Fallback to global template (school is null)
    return NotificationTemplate.objects.filter(
        school__isnull=True,
        code=code,
        channel=channel,
        is_active=True
    ).first()


def render_email_template(
    template_or_code,
    context: Dict[str, Any],
    school=None,
    request=None,
    subject_prefix: Optional[str] = None,
    subject_override: Optional[str] = None
) -> Tuple[str, str, str]:
    """
    Render standard email with header, accent divider, body, CTA button, and dark footer.
    Returns: (subject, html_content, text_content)
    """
    from superadmin.models import NotificationTemplate

    if isinstance(template_or_code, str):
        template = get_notification_template(template_or_code, channel='email', school=school)
    else:
        template = template_or_code

    branding = get_branding_dict(school=school, request=request)

    # Base defaults if template not found in DB
    if not template:
        subject = context.get('subject', 'Notification from ' + branding['name'])
        heading = context.get('heading', '')
        body = context.get('body', '')
        button_text = context.get('button_text', '')
        button_url = context.get('button_url', '')
        hero_image_url = context.get('hero_image_url', None)
    else:
        rendered = template.render_content(context)
        subject = rendered['subject'] or context.get('subject', template.name)
        heading = rendered['heading'] or context.get('heading', '')
        body = rendered['body']
        button_text = rendered['button_text']
        button_url = rendered['button_url']
        hero_image_url = None
        if template.hero_image:
            try:
                hero_image_url = template.hero_image.url
                if request and not hero_image_url.startswith(('http://', 'https://')):
                    hero_image_url = request.build_absolute_uri(hero_image_url)
            except Exception:
                hero_image_url = None
        if not hero_image_url:
            hero_image_url = context.get('hero_image_url', None)

    if subject_override:
        subject = subject_override
    if subject_prefix:
        subject = f"{subject_prefix} {subject}".strip()

    # Convert newlines to paragraphs/breaks if body is plain text
    formatted_body = body
    if '<p>' not in body and '<br>' not in body and '<div' not in body:
        paragraphs = [p.strip() for p in body.split('\n\n') if p.strip()]
        if paragraphs:
            formatted_body = ''.join([f'<p style="margin: 0 0 16px 0;">{p.replace(chr(10), "<br>")}</p>' for p in paragraphs])

    email_context = {
        'subject': subject,
        'heading': heading,
        'body': formatted_body,
        'button_text': button_text,
        'button_url': button_url,
        'hero_image_url': hero_image_url,
        'branding': branding,
        'current_year': timezone.now().year,
    }

    html_content = render_to_string('emails/standard_email_base.html', email_context)
    text_content = strip_tags(html_content)

    return subject, html_content, text_content


def send_notification_by_template(
    code: str,
    channel: str,
    recipients: List[str],
    context: Dict[str, Any],
    school=None,
    request=None,
    from_email: Optional[str] = None,
    subject_prefix: Optional[str] = None,
    subject_override: Optional[str] = None,
    fail_silently: bool = True
) -> Dict[str, Any]:
    """
    Send dynamic notification via template across Email, SMS, or WhatsApp.
    """
    template = get_notification_template(code=code, channel=channel, school=school)
    
    if channel == 'email':
        subject, html_content, text_content = render_email_template(
            template_or_code=template or code,
            context=context,
            school=school,
            request=request,
            subject_prefix=subject_prefix,
            subject_override=subject_override
        )

        if not from_email:
            # Check for school from_email or platform default
            from superadmin.models import GlobalEmailConfiguration, SchoolEmailConfiguration
            if school:
                school_email_cfg = SchoolEmailConfiguration.objects.filter(school=school, is_active=True).first()
                if school_email_cfg and school_email_cfg.default_from_email:
                    from_email = f"{school_email_cfg.default_from_name or school.name} <{school_email_cfg.default_from_email}>"
            if not from_email:
                global_email_cfg = GlobalEmailConfiguration.objects.filter(is_active=True).first()
                if global_email_cfg and global_email_cfg.default_from_email:
                    from_email = f"{global_email_cfg.default_from_name or 'Clasyo'} <{global_email_cfg.default_from_email}>"
                else:
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', None)

        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=from_email,
                to=recipients
            )
            msg.attach_alternative(html_content, "text/html")
            sent_count = msg.send(fail_silently=fail_silently)
            return {'success': True, 'channel': 'email', 'sent': sent_count, 'subject': subject}
        except Exception as e:
            logger.error(f"Failed to send email notification template [{code}] to {recipients}: {e}")
            if not fail_silently:
                raise
            return {'success': False, 'channel': 'email', 'error': str(e)}

    elif channel == 'sms':
        if template:
            message_text = template.interpolate(template.body, context)
        else:
            message_text = context.get('body', context.get('message', ''))

        from core.services.mobilesasa import MobileSasaClient
        from superadmin.models import GlobalSMSConfiguration, SchoolSMSConfiguration

        client = None
        if school:
            school_sms = SchoolSMSConfiguration.objects.filter(school=school, is_active=True).first()
            if school_sms and school_sms.provider == 'mobilesasa' and school_sms.mobilesasa_api_token:
                client = MobileSasaClient(
                    api_token=school_sms.mobilesasa_api_token,
                    sender_id=school_sms.mobilesasa_sender_id or school_sms.default_sender_id
                )

        if not client:
            # Fall back to global SMS only if system-level or Superadmin granted allow_system_sms
            if not school or getattr(school, 'allow_system_sms', False):
                global_sms = GlobalSMSConfiguration.objects.filter(provider='mobilesasa', is_active=True).first()
                if global_sms and global_sms.mobilesasa_api_token:
                    client = MobileSasaClient(
                        api_token=global_sms.mobilesasa_api_token,
                        sender_id=global_sms.mobilesasa_sender_id or global_sms.default_sender_id
                    )

        if client:
            success_count = 0
            for phone in recipients:
                try:
                    res = client.send_sms(phone=phone, message=message_text)
                    if res.get('status') in ('success', 'pending', 'sent') or res.get('responseCode') == '0200':
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send SMS to {phone}: {e}")
            return {'success': True, 'channel': 'sms', 'sent': success_count, 'message': message_text}
        else:
            logger.warning("No active SMS provider configured for sending SMS template")
            return {'success': False, 'channel': 'sms', 'error': 'No active SMS provider configured and system SMS default not granted.'}

    elif channel == 'whatsapp':
        if template:
            message_text = template.interpolate(template.body, context)
        else:
            message_text = context.get('body', context.get('message', ''))

        from core.services.mobilesasa import MobileSasaClient
        from superadmin.models import GlobalWhatsAppConfiguration, SchoolWhatsAppConfiguration

        client = None
        if school:
            school_wa = SchoolWhatsAppConfiguration.objects.filter(school=school, is_active=True).first()
            if school_wa and school_wa.provider == 'mobilesasa' and school_wa.mobilesasa_api_token:
                client = MobileSasaClient(
                    api_token=school_wa.mobilesasa_api_token,
                    account_uuid=school_wa.mobilesasa_account_uuid,
                    sender_phone=school_wa.mobilesasa_sender_phone or school_wa.default_sender_phone
                )

        if not client:
            # Fall back to global WhatsApp only if system-level or Superadmin granted allow_system_whatsapp
            if not school or getattr(school, 'allow_system_whatsapp', False):
                global_wa = GlobalWhatsAppConfiguration.objects.filter(provider='mobilesasa', is_active=True).first()
                if global_wa and global_wa.mobilesasa_api_token:
                    client = MobileSasaClient(
                        api_token=global_wa.mobilesasa_api_token,
                        account_uuid=global_wa.mobilesasa_account_uuid,
                        sender_phone=global_wa.mobilesasa_sender_phone or global_wa.default_sender_phone
                    )

        if client:
            success_count = 0
            for phone in recipients:
                try:
                    res = client.send_whatsapp_message(phone=phone, message=message_text)
                    if res.get('status') in ('success', 'sent') or res.get('responseCode') == '0200':
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send WhatsApp message to {phone}: {e}")
            return {'success': True, 'channel': 'whatsapp', 'sent': success_count, 'message': message_text}
        else:
            logger.warning("No active WhatsApp provider configured")
            return {'success': False, 'channel': 'whatsapp', 'error': 'No active WhatsApp provider configured.'}

    return {'success': False, 'error': f'Unsupported channel {channel}'}


# Backward-compatibility alias
send_notification_template = send_notification_by_template


def seed_default_notification_templates():
    """
    Populate standard default notification templates in database if not already present.
    Creates default Global templates so school admins and superadmins have a full suite of templates.
    """
    from superadmin.models import NotificationTemplate

    DEFAULT_TEMPLATES = [
        # --- FEES & FINANCE (School Templates) ---
        {
            'code': 'fee_reminder',
            'channel': 'email',
            'category': 'fees',
            'name': 'Fee Payment Reminder',
            'subject': 'Fee Payment Reminder - {{ student_name }}',
            'heading': 'School Fee Payment Reminder',
            'body': (
                "Dear {{ parent_name }},\n\n"
                "This is a gentle reminder regarding the outstanding school fees for <strong>{{ student_name }}</strong> "
                "(Admission No: <strong>{{ admission_number }}</strong>, Class: <strong>{{ class_name }}</strong>).\n\n"
                "The outstanding balance of <strong>{{ currency }} {{ balance }}</strong> is due by <strong>{{ due_date }}</strong>.\n\n"
                "<strong>Payment Methods:</strong><br>"
                "• Paybill / Business No: <strong>{{ paybill_number }}</strong><br>"
                "• Account Number: <strong>{{ account_number }}</strong><br>"
                "• Bank: {{ bank_name }} | Acc: {{ bank_account }}\n\n"
                "Kindly settle the payment to ensure uninterrupted learning and access to school services. "
                "If you have already made the payment, please disregard this notice."
            ),
            'button_text': 'PAY ONLINE NOW',
            'button_url': '{{ payment_url }}',
            'available_tags': 'parent_name, student_name, admission_number, class_name, currency, balance, due_date, paybill_number, account_number, bank_name, bank_account, payment_url',
            'is_system': True,
        },
        {
            'code': 'fee_reminder',
            'channel': 'sms',
            'category': 'fees',
            'name': 'Fee Payment Reminder (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Dear {{ parent_name }}, please note that {{ student_name }} has a fee balance of {{ currency }} {{ balance }} "
                "due by {{ due_date }}. Pay via Paybill {{ paybill_number }}, Acc: {{ account_number }}. Thank you."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, balance, currency, due_date, paybill_number, account_number',
            'is_system': True,
        },
        {
            'code': 'fee_reminder',
            'channel': 'whatsapp',
            'category': 'fees',
            'name': 'Fee Payment Reminder (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📢 *FEE PAYMENT REMINDER*\n\n"
                "Dear *{{ parent_name }}*,\n"
                "This is a reminder that *{{ student_name }}* ({{ class_name }}) has an outstanding fee balance of *{{ currency }} {{ balance }}*.\n\n"
                "🗓 *Due Date:* {{ due_date }}\n"
                "💳 *Paybill:* {{ paybill_number }}\n"
                "🔢 *Account:* {{ account_number }}\n\n"
                "Thank you for your continued support."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, class_name, currency, balance, due_date, paybill_number, account_number',
            'is_system': True,
        },
        {
            'code': 'payment_receipt',
            'channel': 'email',
            'category': 'fees',
            'name': 'Fee Payment Receipt / Confirmation',
            'subject': 'Payment Received - Receipt #{{ receipt_number }} - {{ student_name }}',
            'heading': 'Payment Confirmation & Official Receipt',
            'body': (
                "Dear {{ parent_name }},\n\n"
                "We gratefully acknowledge receipt of your school fee payment for <strong>{{ student_name }}</strong>.\n\n"
                "<strong>Transaction Summary:</strong><br>"
                "• Receipt Number: <strong>{{ receipt_number }}</strong><br>"
                "• Amount Paid: <strong>{{ currency }} {{ amount_paid }}</strong><br>"
                "• Payment Method: {{ payment_method }} (Ref: {{ transaction_reference }})<br>"
                "• Date Received: {{ payment_date }}<br>"
                "• Remaining Fee Balance: <strong>{{ currency }} {{ remaining_balance }}</strong>\n\n"
                "You can view and download your full printable official receipt through the link below."
            ),
            'button_text': 'DOWNLOAD OFFICIAL RECEIPT',
            'button_url': '{{ receipt_url }}',
            'available_tags': 'parent_name, student_name, receipt_number, currency, amount_paid, payment_method, transaction_reference, payment_date, remaining_balance, receipt_url',
            'is_system': True,
        },
        {
            'code': 'payment_receipt',
            'channel': 'sms',
            'category': 'fees',
            'name': 'Payment Receipt (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Payment of {{ currency }} {{ amount_paid }} for {{ student_name }} received. "
                "Receipt #{{ receipt_number }}. Remaining Balance: {{ currency }} {{ remaining_balance }}. Thank you."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'student_name, currency, amount_paid, receipt_number, remaining_balance',
            'is_system': True,
        },
        {
            'code': 'payment_receipt',
            'channel': 'whatsapp',
            'category': 'fees',
            'name': 'Payment Receipt (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "🧾 *PAYMENT RECEIPT ACKNOWLEDGEMENT*\n\n"
                "Dear *{{ parent_name }}*,\n\n"
                "We confirm receipt of *{{ currency }} {{ amount_paid }}* for *{{ student_name }}* (Receipt #{{ receipt_number }}).\n\n"
                "💳 *Method:* {{ payment_method }}\n"
                "🗓 *Date:* {{ payment_date }}\n"
                "⚖️ *Remaining Balance:* {{ currency }} {{ remaining_balance }}\n\n"
                "Thank you for your prompt payment."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, receipt_number, currency, amount_paid, payment_method, payment_date, remaining_balance',
            'is_system': True,
        },
        {
            'code': 'fee_structure',
            'channel': 'email',
            'category': 'fees',
            'name': 'Fee Structure Notification',
            'subject': 'School Fee Structure for {{ academic_year }} - Term {{ term_name }}',
            'heading': 'Approved Fee Structure & Payment Guidelines',
            'body': (
                "Dear Parents and Guardians,\n\n"
                "We wish to inform you that the approved fee structure for <strong>{{ academic_year }} ({{ term_name }})</strong> "
                "is now available for your review.\n\n"
                "The breakdown covers tuition, activity fees, examination fees, and boarding / transport where applicable.\n\n"
                "Please review the detailed schedule and ensure payment deadlines are observed."
            ),
            'button_text': 'VIEW FULL FEE STRUCTURE',
            'button_url': '{{ fee_structure_url }}',
            'available_tags': 'academic_year, term_name, fee_structure_url',
            'is_system': True,
        },
        {
            'code': 'fee_structure',
            'channel': 'whatsapp',
            'category': 'fees',
            'name': 'Fee Structure Notification (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📋 *APPROVED FEE STRUCTURE - {{ academic_year }} ({{ term_name }})*\n\n"
                "Dear Parents & Guardians,\n\n"
                "The official term fee schedule has been released. You may access the complete breakdown through your school portal:\n\n"
                "🔗 {{ fee_structure_url }}\n\n"
                "Thank you, School Administration."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'academic_year, term_name, fee_structure_url',
            'is_system': True,
        },
        {
            'code': 'fee_overdue',
            'channel': 'email',
            'category': 'fees',
            'name': 'Urgent: Overdue School Fee Demand',
            'subject': 'URGENT: Outstanding School Fee Notice - {{ student_name }}',
            'heading': 'Important Notice: Overdue Fee Balance',
            'body': (
                "Dear {{ parent_name }},\n\n"
                "Our records show that school fees for <strong>{{ student_name }}</strong> (Class: <strong>{{ class_name }}</strong>) "
                "are significantly overdue with a balance of <strong>{{ currency }} {{ overdue_amount }}</strong>.\n\n"
                "The deadline elapsed on <strong>{{ cutoff_date }}</strong>. We kindly request that this balance be cleared immediately "
                "to prevent disruptions to your student's examinations and classroom attendance.\n\n"
                "<strong>Payment Details:</strong><br>"
                "• Paybill: <strong>{{ paybill_number }}</strong><br>"
                "• Account: <strong>{{ account_number }}</strong>"
            ),
            'button_text': 'CLEAR BALANCE NOW',
            'button_url': '{{ payment_url }}',
            'available_tags': 'parent_name, student_name, class_name, currency, overdue_amount, cutoff_date, paybill_number, account_number, payment_url',
            'is_system': True,
        },
        {
            'code': 'fee_overdue',
            'channel': 'sms',
            'category': 'fees',
            'name': 'Overdue Fee Notice (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "URGENT: {{ student_name }} has an overdue fee balance of {{ currency }} {{ overdue_amount }}. "
                "Kindly clear today via Paybill {{ paybill_number }}, Acc: {{ account_number }} to avoid interruption."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'student_name, currency, overdue_amount, paybill_number, account_number',
            'is_system': True,
        },
        {
            'code': 'fee_overdue',
            'channel': 'whatsapp',
            'category': 'fees',
            'name': 'Overdue Fee Notice (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "⚠️ *URGENT FEE OVERDUE NOTICE*\n\n"
                "Dear *{{ parent_name }}*,\n\n"
                "The fee balance for *{{ student_name }}* of *{{ currency }} {{ overdue_amount }}* was due on {{ cutoff_date }}.\n\n"
                "💳 *Paybill:* {{ paybill_number }}\n"
                "🔢 *Account:* {{ account_number }}\n\n"
                "Please clear this balance immediately or contact the accounts office."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, currency, overdue_amount, cutoff_date, paybill_number, account_number',
            'is_system': True,
        },

        # --- NOTICES & ANNOUNCEMENTS (School Templates) ---
        {
            'code': 'general_notice',
            'channel': 'email',
            'category': 'notices',
            'name': 'School Announcement / General Notice',
            'subject': '{{ notice_title }}',
            'heading': '{{ notice_title }}',
            'body': (
                "Dear Parents, Students, and Staff,\n\n"
                "{{ notice_content }}\n\n"
                "For any inquiries or further clarification, please do not hesitate to contact the school administration office."
            ),
            'button_text': 'VIEW NOTICE BOARD',
            'button_url': '{{ notice_url }}',
            'available_tags': 'notice_title, notice_content, notice_date, notice_url',
            'is_system': True,
        },
        {
            'code': 'general_notice',
            'channel': 'sms',
            'category': 'notices',
            'name': 'General Notice (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Notice from {{ school_name }}: {{ notice_summary }}. Please log in to your portal for full details."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, notice_summary',
            'is_system': True,
        },
        {
            'code': 'general_notice',
            'channel': 'whatsapp',
            'category': 'notices',
            'name': 'General Notice (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📢 *ANNOUNCEMENT FROM {{ school_name }}*\n\n"
                "*{{ notice_title }}*\n\n"
                "{{ notice_content }}\n\n"
                "🔗 Read on portal: {{ notice_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, notice_title, notice_content, notice_url',
            'is_system': True,
        },
        {
            'code': 'urgent_notice',
            'channel': 'email',
            'category': 'notices',
            'name': 'Urgent / Emergency School Notice',
            'subject': '🚨 URGENT NOTICE: {{ notice_title }}',
            'heading': 'Urgent School Announcement',
            'body': (
                "Dear Parents, Students, and Staff,\n\n"
                "<strong>Please read this urgent communication carefully:</strong>\n\n"
                "{{ notice_content }}\n\n"
                "Please take appropriate action as outlined and check your portal or school communications channel for updates."
            ),
            'button_text': 'READ FULL ADVISORY',
            'button_url': '{{ notice_url }}',
            'available_tags': 'notice_title, notice_content, notice_url',
            'is_system': True,
        },
        {
            'code': 'urgent_notice',
            'channel': 'sms',
            'category': 'notices',
            'name': 'Urgent School Notice (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "🚨 URGENT from {{ school_name }}: {{ notice_title }} - {{ notice_summary }}. Check portal for details."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, notice_title, notice_summary',
            'is_system': True,
        },
        {
            'code': 'urgent_notice',
            'channel': 'whatsapp',
            'category': 'notices',
            'name': 'Urgent School Notice (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "🚨 *URGENT NOTICE - {{ school_name }}*\n\n"
                "*{{ notice_title }}*\n\n"
                "{{ notice_content }}\n\n"
                "⚠️ *Action Required:* Please review and adhere to this instruction immediately."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, notice_title, notice_content',
            'is_system': True,
        },

        # --- EVENTS & ACTIVITIES (School Templates) ---
        {
            'code': 'event_invitation',
            'channel': 'email',
            'category': 'events',
            'name': 'School Event Announcement & Invitation',
            'subject': 'Upcoming Event: {{ event_title }} at {{ school_name }}',
            'heading': 'You are Cordially Invited',
            'body': (
                "Dear Parents, Students, and School Community,\n\n"
                "We are pleased to invite you to <strong>{{ event_title }}</strong> scheduled to take place at "
                "<strong>{{ school_name }}</strong>.\n\n"
                "<strong>Event Details:</strong><br>"
                "• Date: <strong>{{ event_date }}</strong><br>"
                "• Time: <strong>{{ event_time }}</strong><br>"
                "• Venue / Location: <strong>{{ event_location }}</strong>\n\n"
                "<strong>Event Overview:</strong><br>"
                "{{ event_description }}\n\n"
                "We warmly welcome your presence and participation. Please click below to view the schedule and RSVP."
            ),
            'button_text': 'VIEW EVENT DETAILS & SCHEDULE',
            'button_url': '{{ event_url }}',
            'available_tags': 'event_title, school_name, event_date, event_time, event_location, event_description, event_url',
            'is_system': True,
        },
        {
            'code': 'event_invitation',
            'channel': 'sms',
            'category': 'events',
            'name': 'School Event Invitation (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "{{ school_name }}: You are invited to {{ event_title }} on {{ event_date }} at {{ event_time }}, "
                "Venue: {{ event_location }}. Details: {{ event_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, event_title, event_date, event_time, event_location, event_url',
            'is_system': True,
        },
        {
            'code': 'event_invitation',
            'channel': 'whatsapp',
            'category': 'events',
            'name': 'School Event Invitation (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "🎉 *YOU'RE INVITED: {{ event_title }}*\n\n"
                "Dear *{{ recipient_name }}*,\n\n"
                "{{ school_name }} cordially invites you to join us for *{{ event_title }}*.\n\n"
                "🗓 *Date:* {{ event_date }}\n"
                "⏰ *Time:* {{ event_time }}\n"
                "📍 *Venue:* {{ event_location }}\n\n"
                "{{ event_description }}\n\n"
                "We look forward to having you with us!"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'recipient_name, school_name, event_title, event_date, event_time, event_location, event_description',
            'is_system': True,
        },
        {
            'code': 'event_reminder',
            'channel': 'email',
            'category': 'events',
            'name': 'Upcoming Event Reminder',
            'subject': 'Reminder: {{ event_title }} is Happening Soon ({{ event_date }})',
            'heading': 'Event Reminder: {{ event_title }}',
            'body': (
                "Dear Parents, Students, and Staff,\n\n"
                "This is a friendly reminder that <strong>{{ event_title }}</strong> will take place on "
                "<strong>{{ event_date }}</strong> starting at <strong>{{ event_time }}</strong>.\n\n"
                "<strong>Location:</strong> {{ event_location }}\n\n"
                "Please plan to arrive on time and ensure all necessary preparations are made. "
                "Click the button below to view the event schedule and guidelines."
            ),
            'button_text': 'VIEW EVENT SCHEDULE',
            'button_url': '{{ event_url }}',
            'available_tags': 'event_title, event_date, event_time, event_location, event_url',
            'is_system': True,
        },
        {
            'code': 'event_reminder',
            'channel': 'sms',
            'category': 'events',
            'name': 'Event Reminder (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Reminder: {{ event_title }} is on {{ event_date }} at {{ event_time }} ({{ event_location }}). "
                "Please arrive promptly. {{ school_name }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, event_title, event_date, event_time, event_location',
            'is_system': True,
        },
        {
            'code': 'event_reminder',
            'channel': 'whatsapp',
            'category': 'events',
            'name': 'Event Reminder (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "⏰ *REMINDER: {{ event_title }}*\n\n"
                "Dear *{{ recipient_name }}*,\n\n"
                "This is a reminder that *{{ event_title }}* takes place on *{{ event_date }}* at *{{ event_time }}*.\n\n"
                "📍 *Venue:* {{ event_location }}\n\n"
                "Kindly arrive 15 minutes before the start time."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'recipient_name, event_title, event_date, event_time, event_location',
            'is_system': True,
        },
        {
            'code': 'event_rescheduled',
            'channel': 'email',
            'category': 'events',
            'name': 'Event Rescheduled / Change of Date',
            'subject': 'Notice of Schedule Change: {{ event_title }}',
            'heading': 'Event Schedule Update',
            'body': (
                "Dear Parents, Students, and Staff,\n\n"
                "Please take note that the schedule for <strong>{{ event_title }}</strong> has been updated.\n\n"
                "<strong>New Schedule:</strong><br>"
                "• Revised Date: <strong>{{ event_date }}</strong><br>"
                "• Revised Time: <strong>{{ event_time }}</strong><br>"
                "• Venue: <strong>{{ event_location }}</strong>\n\n"
                "We apologize for any inconvenience caused by this adjustment and appreciate your understanding."
            ),
            'button_text': 'VIEW REVISED SCHEDULE',
            'button_url': '{{ event_url }}',
            'available_tags': 'event_title, event_date, event_time, event_location, event_url',
            'is_system': True,
        },
        {
            'code': 'event_rescheduled',
            'channel': 'sms',
            'category': 'events',
            'name': 'Event Rescheduled (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Notice: {{ event_title }} has been rescheduled to {{ event_date }} at {{ event_time }}, "
                "Venue: {{ event_location }}. Details on your portal. {{ school_name }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, event_title, event_date, event_time, event_location',
            'is_system': True,
        },
        {
            'code': 'event_rescheduled',
            'channel': 'whatsapp',
            'category': 'events',
            'name': 'Event Rescheduled (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📅 *SCHEDULE UPDATE: {{ event_title }}*\n\n"
                "Please note that *{{ event_title }}* has been rescheduled.\n\n"
                "🗓 *New Date:* {{ event_date }}\n"
                "⏰ *New Time:* {{ event_time }}\n"
                "📍 *Venue:* {{ event_location }}\n\n"
                "We appreciate your understanding and look forward to seeing you."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'event_title, event_date, event_time, event_location',
            'is_system': True,
        },

        # --- ATTENDANCE & ACADEMICS (School Templates) ---
        {
            'code': 'attendance_alert',
            'channel': 'email',
            'category': 'attendance',
            'name': 'Student Absence Notification',
            'subject': 'Daily Attendance Alert: {{ student_name }} Marked Absent',
            'heading': 'Student Absence Notice',
            'body': (
                "Dear {{ parent_name }},\n\n"
                "Our attendance register indicates that <strong>{{ student_name }}</strong> (Class: <strong>{{ class_name }}</strong>) "
                "was marked absent on <strong>{{ date }}</strong>.\n\n"
                "If this absence was pre-arranged or due to illness, kindly update the school office. "
                "If this absence is unexpected, please contact the administration immediately."
            ),
            'button_text': 'CONTACT SCHOOL OFFICE',
            'button_url': '{{ school_contact_url }}',
            'available_tags': 'parent_name, student_name, class_name, date, school_contact_url',
            'is_system': True,
        },
        {
            'code': 'attendance_alert',
            'channel': 'sms',
            'category': 'attendance',
            'name': 'Student Absence Alert (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Dear Parent, {{ student_name }} was marked absent on {{ date }}. "
                "If this is unexpected, please contact the school office immediately."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'student_name, date, school_name',
            'is_system': True,
        },
        {
            'code': 'attendance_alert',
            'channel': 'whatsapp',
            'category': 'attendance',
            'name': 'Student Absence Alert (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "⚠️ *STUDENT ABSENCE NOTICE*\n\n"
                "Dear *{{ parent_name }}*,\n\n"
                "Your child *{{ student_name }}* ({{ class_name }}) was recorded absent today, *{{ date }}*.\n\n"
                "If this is unexpected, please contact the school office immediately."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, class_name, date',
            'is_system': True,
        },
        {
            'code': 'exam_schedule',
            'channel': 'email',
            'category': 'academics',
            'name': 'Examination Timetable & Schedule',
            'subject': 'Examination Timetable Released - {{ exam_name }}',
            'heading': 'Examination Timetable & Guidelines',
            'body': (
                "Dear Parents and Students,\n\n"
                "The official timetable for <strong>{{ exam_name }}</strong> has been published.\n\n"
                "Examinations will commence on <strong>{{ start_date }}</strong> and conclude on <strong>{{ end_date }}</strong>.\n\n"
                "Please review the schedule carefully, ensure all revision materials are ready, and observe examination room regulations."
            ),
            'button_text': 'VIEW EXAM TIMETABLE',
            'button_url': '{{ exam_url }}',
            'available_tags': 'exam_name, start_date, end_date, exam_url',
            'is_system': True,
        },
        {
            'code': 'exam_schedule',
            'channel': 'sms',
            'category': 'academics',
            'name': 'Exam Timetable Release (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "{{ school_name }}: The timetable for {{ exam_name }} is now available. Exams run from {{ start_date }} to {{ end_date }}. Check portal."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, exam_name, start_date, end_date',
            'is_system': True,
        },
        {
            'code': 'exam_schedule',
            'channel': 'whatsapp',
            'category': 'academics',
            'name': 'Exam Timetable Release (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📚 *EXAMINATION TIMETABLE - {{ exam_name }}*\n\n"
                "Dear Parents and Students,\n\n"
                "The exam schedule has been released. Exams will take place from *{{ start_date }}* to *{{ end_date }}*.\n\n"
                "🔗 Access the timetable: {{ exam_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'exam_name, start_date, end_date, exam_url',
            'is_system': True,
        },
        {
            'code': 'exam_results',
            'channel': 'email',
            'category': 'academics',
            'name': 'Exam Results & Report Card',
            'subject': 'Term Examination Results - {{ student_name }}',
            'heading': 'Student Academic Performance Report',
            'body': (
                "Dear {{ parent_name }},\n\n"
                "The examination results for <strong>{{ student_name }}</strong> for <strong>{{ exam_name }}</strong> "
                "have been officially released.\n\n"
                "• Mean Grade: <strong>{{ mean_grade }}</strong><br>"
                "• Total Marks: <strong>{{ total_marks }} / {{ max_marks }}</strong><br>"
                "• Class Position: <strong>{{ class_position }}</strong>\n\n"
                "Click the button below to view the comprehensive report card and teacher comments."
            ),
            'button_text': 'VIEW FULL REPORT CARD',
            'button_url': '{{ report_card_url }}',
            'available_tags': 'parent_name, student_name, exam_name, mean_grade, total_marks, max_marks, class_position, report_card_url',
            'is_system': True,
        },
        {
            'code': 'exam_results',
            'channel': 'sms',
            'category': 'academics',
            'name': 'Exam Results (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Results for {{ student_name }} ({{ exam_name }}): Mean Grade {{ mean_grade }}, Marks: {{ total_marks }}/{{ max_marks }}, "
                "Pos: {{ class_position }}. Full report on portal."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'student_name, exam_name, mean_grade, total_marks, max_marks, class_position',
            'is_system': True,
        },
        {
            'code': 'exam_results',
            'channel': 'whatsapp',
            'category': 'academics',
            'name': 'Exam Results (WhatsApp)',
            'subject': '',
            'heading': '',
            'body': (
                "📊 *EXAM RESULTS RELEASE*\n\n"
                "Dear *{{ parent_name }}*,\n\n"
                "Results for *{{ student_name }}* ({{ exam_name }}):\n\n"
                "🎖 *Mean Grade:* {{ mean_grade }}\n"
                "📝 *Total Score:* {{ total_marks }} / {{ max_marks }}\n"
                "🏆 *Class Rank:* {{ class_position }}\n\n"
                "🔗 View complete report card: {{ report_card_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'parent_name, student_name, exam_name, mean_grade, total_marks, max_marks, class_position, report_card_url',
            'is_system': True,
        },

        # --- SYSTEM & ACCOUNT (Global SuperAdmin Templates) ---
        {
            'code': 'welcome_user',
            'channel': 'email',
            'category': 'system',
            'name': 'Welcome User / Account Created',
            'subject': 'Welcome to {{ school_name }} - Your Account is Ready',
            'heading': 'Welcome to Your Account',
            'body': (
                "Dear <strong>{{ user_full_name }}</strong>,<br><br>"
                "Welcome to <strong>{{ school_name }}</strong>! Your portal account has been created successfully.<br><br>"
                "<strong>Your Account Details:</strong><br>"
                "• <strong>Role:</strong> {{ role }}<br>"
                "• <strong>Email / Username:</strong> {{ email }}<br>"
                "{{ credentials_info }}"
                "<br>"
                "Please log in to access your dashboard. For your security, we recommend that you change your password upon your first login."
            ),
            'button_text': 'LOG IN TO YOUR ACCOUNT',
            'button_url': '{{ login_url }}',
            'available_tags': 'user_full_name, school_name, role, email, username, temporary_password, credentials_info, school_slug, login_url',
            'is_system': True,
        },
        {
            'code': 'welcome_user',
            'channel': 'sms',
            'category': 'system',
            'name': 'Welcome User (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Welcome to {{ school_name }}! Your account has been created. "
                "Role: {{ role }} | Email: {{ email }} | Login: {{ login_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, user_full_name, role, email, temporary_password, login_url',
            'is_system': True,
        },
        {
            'code': 'password_reset',
            'channel': 'email',
            'category': 'system',
            'name': 'Password Reset Request',
            'subject': 'Reset Your Account Password',
            'heading': 'Password Reset Request',
            'body': (
                "Hello {{ user_full_name }},\n\n"
                "We received a request to reset your password. If you initiated this request, please click the button "
                "below to set a new secure password.\n\n"
                "This password reset link will expire in 24 hours. If you did not make this request, please ignore this email."
            ),
            'button_text': 'RESET PASSWORD',
            'button_url': '{{ reset_url }}',
            'available_tags': 'user_full_name, reset_url',
            'is_system': True,
        },
        {
            'code': 'password_reset',
            'channel': 'sms',
            'category': 'system',
            'name': 'Password Reset OTP / Link (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "{{ school_name }}: Your password reset code/link is: {{ reset_url }}. Valid for 24 hours. Do not share."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, reset_url',
            'is_system': True,
        },

        # --- SUBSCRIPTIONS & PLATFORM PAYMENTS ---
        {
            'code': 'payment_submitted',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Payment Submitted',
            'subject': 'Payment Submitted - {{ school_name }} - {{ plan_name }}',
            'heading': 'Payment Submitted & Pending Verification',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "A subscription payment has been received and is currently pending verification by our finance team.<br><br>"
                "<strong>Transaction Details:</strong><br>"
                "• <strong>Payment ID:</strong> {{ payment_id }}<br>"
                "• <strong>School:</strong> {{ school_name }}<br>"
                "• <strong>Subscription Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Amount:</strong> {{ currency }} {{ amount }}<br>"
                "• <strong>Payment Method:</strong> {{ payment_method }}<br>"
                "• <strong>Status:</strong> Pending Verification<br><br>"
                "You will receive an automated confirmation once the payment is approved and your subscription is activated."
            ),
            'button_text': 'VIEW BILLING DASHBOARD',
            'button_url': '{{ billing_url }}',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency, payment_method, status, billing_url',
            'is_system': True,
        },
        {
            'code': 'payment_submitted',
            'channel': 'sms',
            'category': 'system',
            'name': 'Payment Submitted (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Payment of {{ currency }} {{ amount }} for {{ school_name }} ({{ plan_name }}) submitted. "
                "Ref: {{ payment_id }}. Status: Pending Verification."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency',
            'is_system': True,
        },
        {
            'code': 'payment_verified',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Payment Verified',
            'subject': 'Payment Verified - {{ school_name }} - {{ plan_name }}',
            'heading': 'Payment Verified',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "Your subscription payment has been successfully verified.<br><br>"
                "<strong>Payment Summary:</strong><br>"
                "• <strong>Payment ID:</strong> {{ payment_id }}<br>"
                "• <strong>Subscription Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Amount:</strong> {{ currency }} {{ amount }}<br>"
                "• <strong>Status:</strong> Verified<br><br>"
                "Your subscription activation is being finalized. Thank you for choosing Clasyo."
            ),
            'button_text': 'VIEW BILLING & SUBSCRIPTION',
            'button_url': '{{ billing_url }}',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency, status, billing_url',
            'is_system': True,
        },
        {
            'code': 'payment_verified',
            'channel': 'sms',
            'category': 'system',
            'name': 'Payment Verified (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Your payment of {{ currency }} {{ amount }} for {{ plan_name }} has been verified (ID: {{ payment_id }}). Thank you."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency',
            'is_system': True,
        },
        {
            'code': 'payment_approved',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Payment Approved',
            'subject': 'Payment Approved - {{ school_name }} - {{ plan_name }}',
            'heading': 'Payment Approved & Subscription Active',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "We are pleased to inform you that your payment has been approved and your subscription is now active!<br><br>"
                "<strong>Subscription Summary:</strong><br>"
                "• <strong>Payment ID:</strong> {{ payment_id }}<br>"
                "• <strong>Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Amount Paid:</strong> {{ currency }} {{ amount }}<br>"
                "• <strong>Status:</strong> Approved & Active<br><br>"
                "All features included in the {{ plan_name }} plan are now fully enabled for your school portal."
            ),
            'button_text': 'GO TO DASHBOARD',
            'button_url': '{{ billing_url }}',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency, status, billing_url',
            'is_system': True,
        },
        {
            'code': 'payment_approved',
            'channel': 'sms',
            'category': 'system',
            'name': 'Payment Approved (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Your payment of {{ currency }} {{ amount }} for {{ school_name }} is approved. "
                "Subscription for {{ plan_name }} is now active. Thank you for choosing Clasyo."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, payment_id, amount, currency',
            'is_system': True,
        },
        {
            'code': 'payment_rejected',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Payment Rejected',
            'subject': 'Payment Rejected - {{ school_name }} - {{ plan_name }}',
            'heading': 'Subscription Payment Notice',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "Your subscription payment could not be approved at this time.<br><br>"
                "<strong>Details:</strong><br>"
                "• <strong>Payment ID:</strong> {{ payment_id }}<br>"
                "• <strong>Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Reason for Rejection:</strong> {{ rejection_reason }}<br><br>"
                "Please review the reason above and resubmit your payment with the correct transaction details, or contact our support team."
            ),
            'button_text': 'REVIEW BILLING & RESUBMIT',
            'button_url': '{{ billing_url }}',
            'available_tags': 'school_name, plan_name, payment_id, rejection_reason, billing_url',
            'is_system': True,
        },
        {
            'code': 'payment_rejected',
            'channel': 'sms',
            'category': 'system',
            'name': 'Payment Rejected (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Your payment for {{ plan_name }} (ID: {{ payment_id }}) was not approved. "
                "Reason: {{ rejection_reason }}. Please check your billing dashboard."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, payment_id, rejection_reason',
            'is_system': True,
        },
        {
            'code': 'subscription_expiring',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Expiring Soon',
            'subject': 'Subscription Expiring Soon - {{ school_name }} - {{ plan_name }}',
            'heading': 'Subscription Renewal Reminder',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "This is a reminder that your subscription for the <strong>{{ plan_name }}</strong> plan "
                "will expire on <strong>{{ end_date }}</strong>.<br><br>"
                "To ensure uninterrupted access to your school portal and avoid service suspension, "
                "please renew your subscription before the expiration date."
            ),
            'button_text': 'RENEW SUBSCRIPTION NOW',
            'button_url': '{{ renewal_url }}',
            'available_tags': 'school_name, plan_name, end_date, renewal_url',
            'is_system': True,
        },
        {
            'code': 'subscription_expiring',
            'channel': 'sms',
            'category': 'system',
            'name': 'Subscription Expiring (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Reminder: Subscription for {{ school_name }} ({{ plan_name }}) expires on {{ end_date }}. "
                "Please renew to avoid interruption: {{ renewal_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, end_date, renewal_url',
            'is_system': True,
        },
        {
            'code': 'subscription_expired',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Expired Notice',
            'subject': 'Subscription Expired - {{ school_name }}',
            'heading': 'Your Subscription Has Expired',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "Your subscription for the <strong>{{ plan_name }}</strong> plan expired on <strong>{{ end_date }}</strong>.<br><br>"
                "Your school portal services have been temporarily suspended. "
                "Please renew your subscription immediately to restore complete access for your staff, students, and parents."
            ),
            'button_text': 'REACTIVATE SUBSCRIPTION',
            'button_url': '{{ renewal_url }}',
            'available_tags': 'school_name, plan_name, end_date, renewal_url',
            'is_system': True,
        },
        {
            'code': 'subscription_expired',
            'channel': 'sms',
            'category': 'system',
            'name': 'Subscription Expired (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Your subscription for {{ school_name }} ({{ plan_name }}) has expired. "
                "Please renew immediately to reactivate services: {{ renewal_url }}"
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, end_date, renewal_url',
            'is_system': True,
        },
        {
            'code': 'subscription_renewed',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Auto-Renewed',
            'subject': 'Subscription Auto-Renewed - {{ school_name }} - {{ plan_name }}',
            'heading': 'Subscription Renewed Successfully',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "Your subscription for <strong>{{ plan_name }}</strong> has been automatically renewed "
                "and is now active through <strong>{{ end_date }}</strong>.<br><br>"
                "All features and modules remain fully operational. Thank you for your continued partnership with Clasyo!"
            ),
            'button_text': 'VIEW BILLING DASHBOARD',
            'button_url': '{{ billing_url }}',
            'available_tags': 'school_name, plan_name, end_date, billing_url',
            'is_system': True,
        },
        {
            'code': 'subscription_renewed',
            'channel': 'sms',
            'category': 'system',
            'name': 'Subscription Renewed (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Subscription for {{ school_name }} ({{ plan_name }}) renewed until {{ end_date }}. Thank you."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, plan_name, end_date',
            'is_system': True,
        },
        {
            'code': 'invoice_reminder',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Invoice Due Reminder',
            'subject': 'Invoice Reminder: {{ invoice_number }} - Due {{ due_date }}',
            'heading': 'Invoice Due Reminder',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "This is a reminder regarding invoice <strong>{{ invoice_number }}</strong> for your <strong>{{ plan_name }}</strong> subscription.<br><br>"
                "<strong>Invoice Details:</strong><br>"
                "• <strong>Invoice Number:</strong> {{ invoice_number }}<br>"
                "• <strong>Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Amount Due:</strong> {{ currency }} {{ total_amount }}<br>"
                "• <strong>Due Date:</strong> {{ due_date }}<br><br>"
                "Please settle this invoice before the due date to ensure continuous service."
            ),
            'button_text': 'VIEW & PAY INVOICE',
            'button_url': '{{ invoice_url }}',
            'available_tags': 'school_name, invoice_number, plan_name, currency, total_amount, due_date, invoice_url',
            'is_system': True,
        },
        {
            'code': 'invoice_reminder',
            'channel': 'sms',
            'category': 'system',
            'name': 'Invoice Reminder (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "Reminder: Invoice {{ invoice_number }} for {{ school_name }} ({{ currency }} {{ total_amount }}) is due on {{ due_date }}."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, invoice_number, total_amount, currency, due_date',
            'is_system': True,
        },
        {
            'code': 'invoice_overdue',
            'channel': 'email',
            'category': 'system',
            'name': 'Subscription Invoice Overdue Notice',
            'subject': 'OVERDUE: Invoice {{ invoice_number }} - {{ school_name }}',
            'heading': 'Important: Overdue Subscription Invoice',
            'body': (
                "Dear <strong>{{ school_name }}</strong> Administrator,<br><br>"
                "Invoice <strong>{{ invoice_number }}</strong> for your <strong>{{ plan_name }}</strong> subscription was due on <strong>{{ due_date }}</strong> and is now overdue.<br><br>"
                "<strong>Invoice Details:</strong><br>"
                "• <strong>Invoice Number:</strong> {{ invoice_number }}<br>"
                "• <strong>Plan:</strong> {{ plan_name }}<br>"
                "• <strong>Amount Due:</strong> {{ currency }} {{ total_amount }}<br>"
                "• <strong>Due Date:</strong> {{ due_date }}<br><br>"
                "Please make payment as soon as possible to avoid service disruption."
            ),
            'button_text': 'PAY OVERDUE INVOICE',
            'button_url': '{{ invoice_url }}',
            'available_tags': 'school_name, invoice_number, plan_name, currency, total_amount, due_date, invoice_url',
            'is_system': True,
        },
        {
            'code': 'invoice_overdue',
            'channel': 'sms',
            'category': 'system',
            'name': 'Invoice Overdue (SMS)',
            'subject': '',
            'heading': '',
            'body': (
                "OVERDUE: Invoice {{ invoice_number }} for {{ school_name }} ({{ currency }} {{ total_amount }}) is overdue. Please pay now."
            ),
            'button_text': '',
            'button_url': '',
            'available_tags': 'school_name, invoice_number, total_amount, currency',
            'is_system': True,
        },
    ]

    created_count = 0
    updated_count = 0
    for t_data in DEFAULT_TEMPLATES:
        obj, created = NotificationTemplate.objects.get_or_create(
            school__isnull=True,
            code=t_data['code'],
            channel=t_data['channel'],
            defaults={
                'name': t_data['name'],
                'category': t_data['category'],
                'subject': t_data['subject'],
                'heading': t_data['heading'],
                'body': t_data['body'],
                'button_text': t_data['button_text'],
                'button_url': t_data['button_url'],
                'available_tags': t_data['available_tags'],
                'is_active': True,
                'is_system': True,
            }
        )
        if created:
            created_count += 1
        elif obj.is_system:
            obj.name = t_data['name']
            obj.category = t_data['category']
            obj.subject = t_data['subject']
            obj.heading = t_data['heading']
            obj.body = t_data['body']
            obj.button_text = t_data['button_text']
            obj.button_url = t_data['button_url']
            obj.available_tags = t_data['available_tags']
            obj.save()
            updated_count += 1

    return created_count + updated_count

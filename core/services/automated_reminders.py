"""
Automated Reminders & Event / Notice Dispatch Service
Handles automatic triggering of:
1. Notice announcements & urgent alerts upon creation/publication
2. Calendar Event invitations upon event creation
3. Automated upcoming event reminders (1-2 days before start)
4. Automated fee balance reminders & overdue notices
5. Scheduled reminder management across Email, SMS, and WhatsApp channels
"""
import logging
from datetime import timedelta
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db.models import Q
from django.conf import settings

from accounts.models import User
from tenants.models import School
from core.models import CalendarEvent
from core.services.notification_templates import send_notification_template

logger = logging.getLogger(__name__)


def _get_school_for_user(user: User) -> Optional[School]:
    """Helper to extract active school from a user"""
    if hasattr(user, 'school') and user.school:
        return user.school
    return School.objects.first()


def dispatch_notice_notifications(notice, request=None) -> Dict[str, Any]:
    """
    Automatically triggered when a Notice is created or published.
    Dispatches to target audience (parents, students, teachers, staff, or all)
    using the active general_notice or urgent_notice template.
    """
    try:
        school = _get_school_for_user(notice.created_by)
        is_urgent = getattr(notice, 'priority', 'normal') == 'high'
        template_code = 'urgent_notice' if is_urgent else 'general_notice'

        # Resolve audience users
        audience = getattr(notice, 'target_audience', 'all')
        users_qs = User.objects.filter(is_active=True)
        if school:
            users_qs = users_qs.filter(Q(school=school) | Q(student_profile__school=school)).distinct()

        if audience == 'parent':
            users_qs = users_qs.filter(role='parent')
        elif audience == 'student':
            users_qs = users_qs.filter(role='student')
        elif audience == 'teacher':
            users_qs = users_qs.filter(role='teacher')
        elif audience == 'staff':
            users_qs = users_qs.filter(role__in=['staff', 'accountant', 'librarian', 'receptionist'])
        elif audience != 'all':
            users_qs = users_qs.filter(role=audience)

        # Collect email & phone recipients
        recipients_email = []
        recipients_phone = []
        for u in users_qs:
            if u.email:
                recipients_email.append(u.email)
            phone = str(u.phone or u.mobile or '').strip()
            if phone:
                recipients_phone.append(phone)

        # Context
        content = notice.content or ''
        summary = (content[:140] + '...') if len(content) > 140 else content
        created_str = notice.created_at.strftime('%d %b %Y') if hasattr(notice, 'created_at') and notice.created_at else timezone.now().strftime('%d %b %Y')
        school_name = school.name if school else 'Clasyo School Management'

        notice_url = f"/portal/notices/{notice.pk}/"
        if request:
            notice_url = request.build_absolute_uri(notice_url)

        context = {
            'notice_title': notice.title,
            'notice_content': content,
            'notice_summary': summary,
            'notice_date': created_str,
            'notice_url': notice_url,
            'school_name': school_name,
        }

        results = {'email': None, 'sms': None, 'whatsapp': None}

        # 1. Email
        if recipients_email:
            results['email'] = send_notification_template(
                template_code=template_code,
                channel='email',
                recipients=recipients_email,
                context=context,
                school=school,
                request=request
            )

        # 2. SMS (if urgent or configured)
        if recipients_phone:
            results['sms'] = send_notification_template(
                template_code=template_code,
                channel='sms',
                recipients=recipients_phone[:100],  # batch limit
                context=context,
                school=school
            )

        # 3. WhatsApp (if urgent or configured)
        if recipients_phone:
            results['whatsapp'] = send_notification_template(
                template_code=template_code,
                channel='whatsapp',
                recipients=recipients_phone[:100],
                context=context,
                school=school
            )

        logger.info(f"Automatically dispatched notice '{notice.title}' (ID {notice.pk}): {results}")
        return {'success': True, 'notice_id': notice.pk, 'results': results}

    except Exception as e:
        logger.error(f"Error dispatching notice notifications for {notice.pk}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def dispatch_event_invitation(event: CalendarEvent, request=None) -> Dict[str, Any]:
    """
    Automatically triggered when a Calendar Event is created.
    Sends event_invitation across active channels.
    """
    try:
        school = _get_school_for_user(event.created_by)
        template_code = 'event_invitation'

        # Resolve audience
        participants = list(event.participants.filter(is_active=True))
        if not participants and event.is_public:
            # If public with no specific participants, invite school community
            users_qs = User.objects.filter(is_active=True)
            if school:
                users_qs = users_qs.filter(Q(school=school) | Q(student_profile__school=school)).distinct()
            participants = list(users_qs[:200])

        recipients_email = [u.email for u in participants if u.email]
        recipients_phone = [str(u.phone or u.mobile).strip() for u in participants if (u.phone or u.mobile)]

        start_dt = event.start_date
        end_dt = event.end_date

        date_str = start_dt.strftime('%A, %d %B %Y') if start_dt else timezone.now().strftime('%A, %d %B %Y')
        time_str = start_dt.strftime('%I:%M %p') if start_dt else 'All Day'
        if end_dt and not event.all_day:
            time_str += f" - {end_dt.strftime('%I:%M %p')}"

        school_name = school.name if school else 'Clasyo School Management'
        event_url = f"/portal/events/{event.pk}/"
        if request:
            event_url = request.build_absolute_uri(event_url)

        context = {
            'event_title': event.title,
            'event_date': date_str,
            'event_time': time_str,
            'event_location': event.location or 'School Campus',
            'event_description': event.description or 'We look forward to your presence.',
            'event_url': event_url,
            'school_name': school_name,
            'recipient_name': 'Parents, Students & Staff',
        }

        results = {'email': None, 'sms': None, 'whatsapp': None}

        if recipients_email:
            results['email'] = send_notification_template(
                template_code=template_code,
                channel='email',
                recipients=recipients_email,
                context=context,
                school=school,
                request=request
            )

        if recipients_phone:
            results['sms'] = send_notification_template(
                template_code=template_code,
                channel='sms',
                recipients=recipients_phone[:100],
                context=context,
                school=school
            )

            results['whatsapp'] = send_notification_template(
                template_code=template_code,
                channel='whatsapp',
                recipients=recipients_phone[:100],
                context=context,
                school=school
            )

        logger.info(f"Automatically dispatched event invitation for '{event.title}': {results}")
        return {'success': True, 'event_id': event.pk, 'results': results}

    except Exception as e:
        logger.error(f"Error dispatching event invitation for {event.pk}: {e}", exc_info=True)
        return {'success': False, 'error': str(e)}


def trigger_event_reminders(school=None, hours_ahead=48) -> Dict[str, Any]:
    """
    Automated job: Scans for upcoming calendar events occurring within the next
    `hours_ahead` hours and triggers event_reminder across Email, SMS, WhatsApp.
    """
    now = timezone.now()
    window_end = now + timedelta(hours=hours_ahead)

    qs = CalendarEvent.objects.filter(
        start_date__gte=now,
        start_date__lte=window_end
    )
    if school:
        qs = qs.filter(Q(created_by__school=school) | Q(participants__school=school)).distinct()

    events = list(qs)
    total_sent = 0
    event_summaries = []

    for ev in events:
        try:
            ev_school = school or _get_school_for_user(ev.created_by)
            participants = list(ev.participants.filter(is_active=True))
            if not participants and ev.is_public:
                users_qs = User.objects.filter(is_active=True)
                if ev_school:
                    users_qs = users_qs.filter(Q(school=ev_school) | Q(student_profile__school=ev_school)).distinct()
                participants = list(users_qs[:200])

            emails = [u.email for u in participants if u.email]
            phones = [str(u.phone or u.mobile).strip() for u in participants if (u.phone or u.mobile)]

            start_dt = ev.start_date
            date_str = start_dt.strftime('%A, %d %B %Y') if start_dt else ''
            time_str = start_dt.strftime('%I:%M %p') if start_dt else 'All Day'

            context = {
                'event_title': ev.title,
                'event_date': date_str,
                'event_time': time_str,
                'event_location': ev.location or 'School Campus',
                'event_url': f"/portal/events/{ev.pk}/",
                'school_name': ev_school.name if ev_school else 'Clasyo School Management',
                'recipient_name': 'Parents, Students & Staff',
            }

            res_email = send_notification_template('event_reminder', 'email', emails, context, school=ev_school) if emails else None
            res_sms = send_notification_template('event_reminder', 'sms', phones[:100], context, school=ev_school) if phones else None
            res_wa = send_notification_template('event_reminder', 'whatsapp', phones[:100], context, school=ev_school) if phones else None

            sent_count = (1 if res_email and res_email.get('success') else 0) + \
                         (1 if res_sms and res_sms.get('success') else 0) + \
                         (1 if res_wa and res_wa.get('success') else 0)

            total_sent += sent_count
            event_summaries.append({
                'event_id': ev.pk,
                'title': ev.title,
                'start_date': str(ev.start_date),
                'email': res_email,
                'sms': res_sms,
                'whatsapp': res_wa,
            })
        except Exception as e:
            logger.error(f"Error triggering reminder for event {ev.pk}: {e}")

    return {
        'status': 'completed',
        'events_processed': len(events),
        'reminders_dispatched': total_sent,
        'details': event_summaries
    }


def trigger_fee_reminders(school=None, min_balance=100.0) -> Dict[str, Any]:
    """
    Automated job: Finds students with active fee balances in FeeCollection and triggers fee_reminder
    or fee_overdue to parents.
    """
    from fees.models import FeeCollection
    from django.utils import timezone

    today = timezone.now().date()
    collections_qs = FeeCollection.objects.filter(
        payment_status__in=['pending', 'partial', 'overdue']
    ).select_related('student', 'fee_structure')

    if school:
        collections_qs = collections_qs.filter(student__school=school)

    sent_count = 0
    summaries = []

    # Group by student so a parent gets 1 aggregated notice instead of spam
    student_collections = {}
    for col in collections_qs:
        st = col.student
        if not st:
            continue
        balance = float(col.amount) - float(col.paid_amount)
        if balance <= 0:
            continue
        if st.pk not in student_collections:
            student_collections[st.pk] = {
                'student': st,
                'total_balance': 0.0,
                'is_overdue': False,
                'earliest_due_date': col.due_date,
            }
        student_collections[st.pk]['total_balance'] += balance
        if col.due_date and col.due_date < today:
            student_collections[st.pk]['is_overdue'] = True
        if col.due_date and (student_collections[st.pk]['earliest_due_date'] is None or col.due_date < student_collections[st.pk]['earliest_due_date']):
            student_collections[st.pk]['earliest_due_date'] = col.due_date

    for st_id, data in list(student_collections.items())[:100]:
        try:
            st = data['student']
            total_balance = data['total_balance']
            if total_balance < min_balance:
                continue

            is_overdue = data['is_overdue']
            template_code = 'fee_overdue' if is_overdue else 'fee_reminder'
            st_school = school or st.school

            parent_email = st.father_email or st.mother_email or st.guardian_email or (st.user.email if st.user else None)
            parent_phone = st.father_phone or st.mother_phone or st.guardian_phone or (st.user.phone if st.user else None)
            parent_name = st.father_name or st.mother_name or st.guardian_name or "Parent / Guardian"

            class_name = st.current_class.name if st.current_class else "Grade Class"
            due_str = data['earliest_due_date'].strftime('%d %b %Y') if data['earliest_due_date'] else today.strftime('%d %b %Y')

            context = {
                'parent_name': parent_name,
                'student_name': f"{st.first_name} {st.last_name}".strip(),
                'admission_number': st.admission_number,
                'class_name': class_name,
                'currency': 'KES',
                'balance': f"{total_balance:,.2f}",
                'overdue_amount': f"{total_balance:,.2f}",
                'due_date': due_str,
                'cutoff_date': due_str,
                'paybill_number': '522123',
                'account_number': st.admission_number,
                'bank_name': 'School Bank Account',
                'bank_account': '01129384756',
                'payment_url': '/portal/fees/pay/',
            }

            emails = [parent_email] if parent_email else []
            phones = [str(parent_phone).strip()] if parent_phone else []

            res_email = send_notification_template(template_code, 'email', emails, context, school=st_school) if emails else None
            res_sms = send_notification_template(template_code, 'sms', phones, context, school=st_school) if phones else None
            res_wa = send_notification_template(template_code, 'whatsapp', phones, context, school=st_school) if phones else None

            sent_count += 1
            summaries.append({
                'student_id': st.pk,
                'student_name': f"{st.first_name} {st.last_name}".strip(),
                'balance': total_balance,
                'template': template_code,
                'email': res_email,
                'sms': res_sms,
                'whatsapp': res_wa,
            })
        except Exception as e:
            logger.error(f"Error triggering fee reminder for student {st_id}: {e}")

    return {
        'status': 'completed',
        'reminders_sent': sent_count,
        'details': summaries
    }


def trigger_all_automated_reminders(school=None) -> Dict[str, Any]:
    """
    Master runner: Executes all scheduled reminder routines (events, fees, etc.)
    """
    event_res = trigger_event_reminders(school=school)
    fee_res = trigger_fee_reminders(school=school)

    return {
        'timestamp': timezone.now().isoformat(),
        'events': event_res,
        'fees': fee_res,
    }

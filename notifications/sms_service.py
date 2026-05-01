"""
SMS notification service using Arkesel (https://arkesel.com) — popular in Ghana/West Africa.
Uses their SMS API v2 with a simple HTTP POST, no extra library needed.

Configuration per school:
  school.sms_enabled          – master switch
  school.arkesel_api_key      – API key from Arkesel dashboard
  school.sms_sender_name      – Sender ID (max 11 alphanumeric chars), e.g. "SchoolSMS"

Fallback global config (settings.py):
  ARKESEL_API_KEY             – used when school has no key set
  ARKESEL_SENDER_NAME         – default sender ID
"""

import logging
import requests as http_requests
from django.conf import settings

logger = logging.getLogger(__name__)

ARKESEL_API_URL = 'https://sms.arkesel.com/api/v2/sms/send'


class SmsService:

    @staticmethod
    def _get_api_key(school=None):
        if school and getattr(school, 'arkesel_api_key', ''):
            return school.arkesel_api_key
        return getattr(settings, 'ARKESEL_API_KEY', '')

    @staticmethod
    def _get_sender(school=None):
        if school and getattr(school, 'sms_sender_name', ''):
            return school.sms_sender_name[:11]
        return getattr(settings, 'ARKESEL_SENDER_NAME', 'SchoolSMS')[:11]

    @staticmethod
    def _normalise_phone(phone: str) -> str:
        """
        Convert a local Ghana number to E.164-ish format Arkesel accepts.
        Examples: 0244123456 → 233244123456,  +233244123456 → 233244123456
        """
        phone = phone.strip().replace(' ', '').replace('-', '')
        if phone.startswith('+'):
            phone = phone[1:]
        if phone.startswith('0') and len(phone) == 10:
            phone = '233' + phone[1:]
        return phone

    @classmethod
    def send(cls, recipients: list[str], message: str, school=None) -> bool:
        """
        Send an SMS to one or more phone numbers.

        Checks the school's sms_balance before sending and deducts on success.
        Uses the platform-level Arkesel API key (school's key is an optional override).

        Args:
            recipients: list of phone numbers (local or international format)
            message:    SMS body text (max ~160 chars for single segment)
            school:     School instance — used for balance check and sender name

        Returns True on success, False on failure.
        """
        api_key = cls._get_api_key(school)
        if not api_key:
            logger.warning('SmsService.send called but no ARKESEL_API_KEY configured.')
            return False

        clean_numbers = [cls._normalise_phone(p) for p in recipients if p]
        if not clean_numbers:
            return False

        # ── Balance check ──────────────────────────────────────────────────
        if school:
            current_balance = getattr(school, 'sms_balance', 0)
            num_to_send = len(clean_numbers)
            if current_balance < num_to_send:
                logger.warning(
                    f'School "{school.name}" has insufficient SMS balance '
                    f'({current_balance} < {num_to_send}). SMS not sent.'
                )
                return False

        payload = {
            'sender': cls._get_sender(school),
            'message': message,
            'recipients': clean_numbers,
        }
        headers = {
            'api-key': api_key,
            'Content-Type': 'application/json',
        }

        try:
            resp = http_requests.post(ARKESEL_API_URL, json=payload, headers=headers, timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get('status') == 'success':
                logger.info(f'SMS sent to {len(clean_numbers)} recipient(s). Ref: {data.get("data", {}).get("id", "")}')
                # ── Deduct balance ─────────────────────────────────────────
                if school:
                    try:
                        from django.db.models import F
                        from schools.models import School as SchoolModel
                        SchoolModel.objects.filter(pk=school.pk).update(
                            sms_balance=F('sms_balance') - len(clean_numbers)
                        )
                        school.sms_balance = max(0, getattr(school, 'sms_balance', 0) - len(clean_numbers))
                    except Exception as deduct_err:
                        logger.error(f'Failed to deduct SMS balance: {deduct_err}')
                return True
            else:
                logger.error(f'Arkesel SMS error: {data}')
                return False
        except Exception as e:
            logger.error(f'Arkesel SMS exception: {e}')
            return False

    # ─── convenience helpers ─────────────────────────────────────────────────

    @classmethod
    def send_attendance_alert(cls, student, status: str, date_str: str, school) -> bool:
        """Send an SMS to a student's guardian when attendance is recorded."""
        if not getattr(school, 'sms_enabled', False):
            return False
        if not getattr(school, 'sms_attendance_enabled', False):
            return False

        phone = getattr(student, 'guardian_phone', '') or ''
        if not phone:
            return False

        student_name = student.get_full_name()
        school_name = school.name

        status_map = {
            'present': f'{student_name} was marked PRESENT at {school_name} on {date_str}.',
            'absent':  f'{student_name} was marked ABSENT at {school_name} on {date_str}. Please contact the school if this is incorrect.',
            'late':    f'{student_name} was marked LATE at {school_name} on {date_str}.',
        }
        message = status_map.get(status, f'Attendance recorded for {student_name} on {date_str} at {school_name}.')

        return cls.send([phone], message, school)

    @classmethod
    def send_fee_reminder(cls, student, bill_summary: str, school) -> bool:
        """Send a fee-reminder SMS to a student's guardian."""
        if not getattr(school, 'sms_enabled', False):
            return False
        if not getattr(school, 'sms_fee_reminder_enabled', False):
            return False

        phone = getattr(student, 'guardian_phone', '') or ''
        if not phone:
            return False

        school_name = school.name
        message = (
            f'Dear {student.guardian_name}, {bill_summary} '
            f'Please visit {school_name} to clear outstanding fees. Thank you.'
        )
        return cls.send([phone], message, school)

"""
Super Admin API views — full SaaS management visibility.
All endpoints require SUPER_ADMIN role.
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from datetime import date, timedelta
import logging
import re

from .permissions import IsSuperAdmin

logger = logging.getLogger(__name__)


def require_superadmin(request):
    """Returns error Response if user is not SUPER_ADMIN, else None."""
    if not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=401)
    if getattr(request.user, 'role', None) != 'SUPER_ADMIN':
        return Response({'error': 'Super admin access required'}, status=403)
    return None


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/schools/
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def superadmin_schools(request):
    """List all schools with user counts and subscription status."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from schools.models import School
        from students.models import Student
        from teachers.models import Teacher
        from accounts.models import User
        from subscriptions.models import Subscription

        schools = School.objects.all().order_by('-created_at')
        data = []
        for s in schools:
            # Active subscription
            sub = Subscription.objects.filter(school=s, status='ACTIVE').order_by('-end_date').first()
            data.append({
                'id': s.id,
                'name': s.name,
                'location': getattr(s, 'location', '') or '',
                'email': getattr(s, 'email', '') or '',
                'phone': getattr(s, 'phone', '') or '',
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'is_active': getattr(s, 'is_active', True),
                'student_count': Student.objects.filter(school=s, is_active=True).count(),
                'teacher_count': Teacher.objects.filter(school=s).count(),
                'admin_count': User.objects.filter(school=s, role__in=['SCHOOL_ADMIN', 'PRINCIPAL']).count(),
                'subscription': {
                    'plan': sub.plan.name if sub else None,
                    'status': sub.status if sub else 'NONE',
                    'end_date': sub.end_date.isoformat() if sub else None,
                } if sub else {'plan': None, 'status': 'NONE', 'end_date': None},
            })
        return Response({'schools': data, 'total': len(data)})
    except Exception as e:
        logger.error(f"superadmin_schools error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/schools/<id>/
# PATCH /api/auth/superadmin/schools/<id>/
# ─────────────────────────────────────────────
@api_view(['GET', 'PATCH'])
@permission_classes([IsSuperAdmin])
def superadmin_school_detail(request, school_id):
    err = require_superadmin(request)
    if err:
        return err
    try:
        from schools.models import School
        from students.models import Student
        from teachers.models import Teacher
        from accounts.models import User
        from subscriptions.models import Subscription

        school = School.objects.get(pk=school_id)

        if request.method == 'PATCH':
            allowed = ['name', 'location', 'email', 'phone', 'is_active']
            errors = {}

            # Validate and sanitise each allowed field
            for field in allowed:
                if field not in request.data:
                    continue
                value = request.data[field]

                if field == 'is_active':
                    if not isinstance(value, bool):
                        errors['is_active'] = 'Must be a boolean.'
                        continue
                    school.is_active = value

                elif field == 'email':
                    email_str = str(value).strip()[:254]
                    if not re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email_str):
                        errors['email'] = 'Enter a valid email address.'
                        continue
                    school.email = email_str

                elif field == 'phone':
                    phone_str = re.sub(r'[^\d+\-\s()]', '', str(value))[:20]
                    school.phone = phone_str

                else:  # name, location
                    text = str(value).strip()[:255]
                    # Strip HTML tags
                    text = re.sub(r'<[^>]+>', '', text)
                    if not text:
                        errors[field] = f'{field} cannot be empty.'
                        continue
                    setattr(school, field, text)

            if errors:
                return Response({'errors': errors}, status=400)

            school.save()
            return Response({'status': 'updated'})

        sub = Subscription.objects.filter(school=school, status='ACTIVE').order_by('-end_date').first()
        all_subs = Subscription.objects.filter(school=school).order_by('-created_at')[:10]
        users = User.objects.filter(school=school).values('id', 'email', 'first_name', 'last_name', 'role', 'is_active', 'last_login')

        return Response({
            'id': school.id,
            'name': school.name,
            'location': getattr(school, 'location', '') or '',
            'email': getattr(school, 'email', '') or '',
            'phone': getattr(school, 'phone', '') or '',
            'created_at': school.created_at.isoformat() if school.created_at else None,
            'is_active': getattr(school, 'is_active', True),
            'student_count': Student.objects.filter(school=school, is_active=True).count(),
            'teacher_count': Teacher.objects.filter(school=school).count(),
            'admin_count': User.objects.filter(school=school, role__in=['SCHOOL_ADMIN', 'PRINCIPAL']).count(),
            'users': list(users),
            'active_subscription': {
                'id': sub.id,
                'plan': sub.plan.name,
                'plan_type': sub.plan.plan_type,
                'status': sub.status,
                'start_date': sub.start_date.isoformat(),
                'end_date': sub.end_date.isoformat(),
                'auto_renew': sub.auto_renew,
            } if sub else None,
            'subscription_history': [{
                'id': s.id,
                'plan': s.plan.name,
                'status': s.status,
                'start_date': s.start_date.isoformat(),
                'end_date': s.end_date.isoformat(),
            } for s in all_subs],
        })
    except School.DoesNotExist:
        return Response({'error': 'School not found'}, status=404)
    except Exception as e:
        logger.error(f"superadmin_school_detail error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/users/
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def superadmin_users(request):
    """List all users across all schools with filters."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import User
        qs = User.objects.select_related('school').order_by('-date_joined')

        role_filter = request.query_params.get('role')
        school_filter = request.query_params.get('school_id')
        search = request.query_params.get('search', '').strip()

        if role_filter:
            qs = qs.filter(role=role_filter)
        if school_filter:
            qs = qs.filter(school_id=school_filter)
        if search:
            from django.db.models import Q
            qs = qs.filter(
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        data = [{
            'id': u.id,
            'email': u.email,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'role': u.role,
            'is_active': u.is_active,
            'date_joined': u.date_joined.isoformat() if u.date_joined else None,
            'last_login': u.last_login.isoformat() if u.last_login else None,
            'school_id': u.school_id,
            'school_name': u.school.name if u.school else None,
        } for u in qs[:500]]

        return Response({'users': data, 'total': qs.count()})
    except Exception as e:
        logger.error(f"superadmin_users error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# PATCH /api/auth/superadmin/users/<id>/
# ─────────────────────────────────────────────
@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def superadmin_user_update(request, user_id):
    """Activate/deactivate a user."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import User
        user = User.objects.get(pk=user_id)
        if 'is_active' in request.data:
            user.is_active = bool(request.data['is_active'])
            user.save(update_fields=['is_active'])
        return Response({'status': 'updated', 'is_active': user.is_active})
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/subscriptions/
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def superadmin_subscriptions(request):
    """List all subscriptions across all schools."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import Subscription, SubscriptionPlan, Payment

        status_filter = request.query_params.get('status')
        qs = Subscription.objects.select_related('school', 'plan').order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)

        today = date.today()
        data = [{
            'id': s.id,
            'school_id': s.school_id,
            'school_name': s.school.name,
            'plan_name': s.plan.name,
            'plan_type': s.plan.plan_type,
            'price': str(s.plan.price),
            'status': s.status,
            'start_date': s.start_date.isoformat(),
            'end_date': s.end_date.isoformat(),
            'days_remaining': (s.end_date - today).days if s.end_date >= today else 0,
            'auto_renew': s.auto_renew,
            'created_at': s.created_at.isoformat(),
        } for s in qs[:200]]

        plans = SubscriptionPlan.objects.filter(is_active=True).values(
            'id', 'name', 'plan_type', 'price', 'duration_days',
            'max_students', 'max_teachers'
        )

        # Revenue stats
        from django.db.models import Sum
        total_revenue = Payment.objects.filter(status='COMPLETED').aggregate(t=Sum('amount'))['t'] or 0
        monthly_revenue = Payment.objects.filter(
            status='COMPLETED',
            payment_date__gte=date.today().replace(day=1)
        ).aggregate(t=Sum('amount'))['t'] or 0

        return Response({
            'subscriptions': data,
            'total': qs.count(),
            'active_count': qs.filter(status='ACTIVE').count(),
            'expired_count': qs.filter(status='EXPIRED').count(),
            'plans': list(plans),
            'revenue': {
                'total': float(total_revenue),
                'this_month': float(monthly_revenue),
            }
        })
    except Exception as e:
        logger.error(f"superadmin_subscriptions error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# POST /api/auth/superadmin/subscriptions/
# POST /api/auth/superadmin/subscriptions/<id>/extend/
# PATCH /api/auth/superadmin/subscriptions/<id>/
# ─────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def superadmin_subscription_create(request):
    """Create a new subscription for a school."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import Subscription, SubscriptionPlan
        from schools.models import School

        school = School.objects.get(pk=request.data['school_id'])
        plan = SubscriptionPlan.objects.get(pk=request.data['plan_id'])
        start = date.fromisoformat(request.data.get('start_date', date.today().isoformat()))
        end = start + timedelta(days=plan.duration_days)

        sub = Subscription.objects.create(
            school=school,
            plan=plan,
            start_date=start,
            end_date=end,
            status='ACTIVE',
            auto_renew=request.data.get('auto_renew', False),
        )
        return Response({'id': sub.id, 'status': 'created', 'end_date': sub.end_date.isoformat()}, status=201)
    except Exception as e:
        logger.error(f"superadmin_subscription_create error: {e}")
        return Response({'error': str(e)}, status=400)


@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def superadmin_subscription_extend(request, sub_id):
    """Extend a subscription by N days."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import Subscription
        sub = Subscription.objects.get(pk=sub_id)
        days = int(request.data.get('days', 30))
        base = max(sub.end_date, date.today())
        sub.end_date = base + timedelta(days=days)
        sub.status = 'ACTIVE'
        sub.save(update_fields=['end_date', 'status'])
        return Response({'status': 'extended', 'new_end_date': sub.end_date.isoformat()})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['PATCH'])
@permission_classes([IsSuperAdmin])
def superadmin_subscription_update(request, sub_id):
    """Change subscription status."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import Subscription
        sub = Subscription.objects.get(pk=sub_id)
        allowed = ['status', 'auto_renew']
        for f in allowed:
            if f in request.data:
                setattr(sub, f, request.data[f])
        sub.save()
        return Response({'status': 'updated'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/analytics/
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def superadmin_analytics(request):
    """System-wide analytics for the SaaS platform."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from schools.models import School
        from students.models import Student
        from teachers.models import Teacher
        from accounts.models import User
        from subscriptions.models import Subscription, Payment
        from django.db.models import Sum, Count
        from django.db.models.functions import TruncMonth

        today = date.today()

        # Schools over time (last 12 months)
        schools_by_month = (
            School.objects
            .filter(created_at__gte=today - timedelta(days=365))
            .annotate(month=TruncMonth('created_at'))
            .values('month')
            .annotate(count=Count('id'))
            .order_by('month')
        )

        # Revenue over time
        revenue_by_month = (
            Payment.objects
            .filter(status='COMPLETED', payment_date__gte=today - timedelta(days=365))
            .annotate(month=TruncMonth('payment_date'))
            .values('month')
            .annotate(total=Sum('amount'))
            .order_by('month')
        )

        # Subscription breakdown by plan
        sub_by_plan = (
            Subscription.objects
            .filter(status='ACTIVE')
            .values('plan__name')
            .annotate(count=Count('id'))
        )

        # Expiring soon (within 30 days)
        expiring_soon = Subscription.objects.filter(
            status='ACTIVE',
            end_date__lte=today + timedelta(days=30),
            end_date__gte=today,
        ).select_related('school', 'plan').order_by('end_date')[:20]

        total_revenue = Payment.objects.filter(status='COMPLETED').aggregate(t=Sum('amount'))['t'] or 0

        return Response({
            'overview': {
                'total_schools': School.objects.count(),
                'active_schools': Subscription.objects.filter(status='ACTIVE').values('school').distinct().count(),
                'total_students': Student.objects.count(),
                'total_teachers': Teacher.objects.count(),
                'total_users': User.objects.count(),
                'total_revenue': float(total_revenue),
                'active_subscriptions': Subscription.objects.filter(status='ACTIVE').count(),
                'expired_subscriptions': Subscription.objects.filter(status='EXPIRED').count(),
            },
            'schools_by_month': [
                {'month': r['month'].strftime('%Y-%m'), 'count': r['count']}
                for r in schools_by_month
            ],
            'revenue_by_month': [
                {'month': r['month'].strftime('%Y-%m'), 'total': float(r['total'])}
                for r in revenue_by_month
            ],
            'subscriptions_by_plan': [
                {'plan': r['plan__name'], 'count': r['count']}
                for r in sub_by_plan
            ],
            'expiring_soon': [{
                'id': s.id,
                'school': s.school.name,
                'plan': s.plan.name,
                'end_date': s.end_date.isoformat(),
                'days_remaining': (s.end_date - today).days,
            } for s in expiring_soon],
        })
    except Exception as e:
        logger.error(f"superadmin_analytics error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET /api/auth/superadmin/plans/
# POST /api/auth/superadmin/plans/
# PATCH /api/auth/superadmin/plans/<id>/
# ─────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def superadmin_plans(request):
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import SubscriptionPlan
        if request.method == 'POST':
            plan = SubscriptionPlan.objects.create(
                name=request.data['name'],
                plan_type=request.data['plan_type'],
                price=request.data['price'],
                duration_days=request.data['duration_days'],
                max_students=request.data.get('max_students'),
                max_teachers=request.data.get('max_teachers'),
                bulk_upload=request.data.get('bulk_upload', True),
                pdf_generation=request.data.get('pdf_generation', True),
                custom_branding=request.data.get('custom_branding', True),
                analytics=request.data.get('analytics', True),
                support_level=request.data.get('support_level', 'Standard'),
            )
            return Response({'id': plan.id, 'name': plan.name}, status=201)

        plans = list(SubscriptionPlan.objects.values())
        return Response({'plans': plans})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@api_view(['PATCH', 'DELETE'])
@permission_classes([IsSuperAdmin])
def superadmin_plan_detail(request, plan_id):
    err = require_superadmin(request)
    if err:
        return err
    try:
        from subscriptions.models import SubscriptionPlan
        plan = SubscriptionPlan.objects.get(pk=plan_id)
        if request.method == 'DELETE':
            plan.is_active = False
            plan.save(update_fields=['is_active'])
            return Response({'status': 'deactivated'})
        editable = ['name', 'price', 'duration_days', 'max_students', 'max_teachers',
                    'bulk_upload', 'pdf_generation', 'custom_branding', 'analytics',
                    'support_level', 'is_active']
        for f in editable:
            if f in request.data:
                setattr(plan, f, request.data[f])
        plan.save()
        return Response({'status': 'updated'})
    except Exception as e:
        return Response({'error': str(e)}, status=400)


# ─────────────────────────────────────────────
# POST /api/auth/superadmin/admins/<id>/disable/
# Disable a school admin + ALL users under their school.
# ─────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def superadmin_disable_admin_cascade(request, user_id):
    """
    Disable a SCHOOL_ADMIN or PRINCIPAL and cascade-disable every
    user (teachers, students, parents, other admins) belonging to
    that same school.
    """
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import User
        admin_user = User.objects.select_related('school').get(pk=user_id)

        if admin_user.role not in ('SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response(
                {'error': 'Target user must be a SCHOOL_ADMIN or PRINCIPAL.'},
                status=400,
            )

        school = admin_user.school
        if not school:
            return Response({'error': 'Admin has no associated school.'}, status=400)

        # Cascade-disable every user tied to this school
        affected = User.objects.filter(school=school, is_active=True).exclude(role='SUPER_ADMIN')
        count = affected.count()
        affected.update(is_active=False)

        logger.info(
            f"SuperAdmin {request.user.email} cascade-disabled {count} users "
            f"in school '{school.name}' (id={school.id})."
        )
        return Response({
            'status': 'disabled',
            'school': school.name,
            'affected_users': count,
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
    except Exception as e:
        logger.error(f"superadmin_disable_admin_cascade error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# POST /api/auth/superadmin/admins/<id>/enable/
# Re-enable all accounts for a school admin's school.
# ─────────────────────────────────────────────
@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def superadmin_enable_admin_cascade(request, user_id):
    """Re-enable all users in the admin's school."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import User
        admin_user = User.objects.select_related('school').get(pk=user_id)

        if admin_user.role not in ('SCHOOL_ADMIN', 'PRINCIPAL'):
            return Response(
                {'error': 'Target user must be a SCHOOL_ADMIN or PRINCIPAL.'},
                status=400,
            )

        school = admin_user.school
        if not school:
            return Response({'error': 'Admin has no associated school.'}, status=400)

        affected = User.objects.filter(school=school, is_active=False).exclude(role='SUPER_ADMIN')
        count = affected.count()
        affected.update(is_active=True)

        logger.info(
            f"SuperAdmin {request.user.email} cascade-enabled {count} users "
            f"in school '{school.name}' (id={school.id})."
        )
        return Response({
            'status': 'enabled',
            'school': school.name,
            'affected_users': count,
        })
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=404)
    except Exception as e:
        logger.error(f"superadmin_enable_admin_cascade error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET  /api/auth/superadmin/messages/        — superadmin: list sent
# POST /api/auth/superadmin/messages/        — superadmin: send message
# ─────────────────────────────────────────────
@api_view(['GET', 'POST'])
@permission_classes([IsSuperAdmin])
def superadmin_messages(request):
    """Superadmin send / list sent direct messages to school admins."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import DirectMessage, User

        if request.method == 'POST':
            recipient_id = request.data.get('recipient_id')
            subject = str(request.data.get('subject', '')).strip()[:255]
            body = str(request.data.get('body', '')).strip()

            if not recipient_id or not subject or not body:
                return Response({'error': 'recipient_id, subject and body are required.'}, status=400)

            # Strip any HTML to prevent stored XSS
            subject = re.sub(r'<[^>]+>', '', subject)
            body = re.sub(r'<[^>]+>', '', body)

            try:
                recipient = User.objects.get(
                    pk=recipient_id,
                    role__in=['SCHOOL_ADMIN', 'PRINCIPAL'],
                )
            except User.DoesNotExist:
                return Response({'error': 'Recipient not found or not an admin.'}, status=404)

            msg = DirectMessage.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=subject,
                body=body,
            )
            return Response({
                'id': msg.id,
                'recipient': f"{recipient.get_full_name()} ({recipient.email})",
                'subject': msg.subject,
                'created_at': msg.created_at.isoformat(),
            }, status=201)

        # GET — list all messages sent by this superadmin
        msgs = DirectMessage.objects.filter(sender=request.user).select_related('recipient')[:200]
        data = [{
            'id': m.id,
            'recipient_id': m.recipient_id,
            'recipient_name': m.recipient.get_full_name(),
            'recipient_email': m.recipient.email,
            'recipient_school': m.recipient.school.name if m.recipient.school else '—',
            'subject': m.subject,
            'body': m.body,
            'is_read': m.is_read,
            'read_at': m.read_at.isoformat() if m.read_at else None,
            'created_at': m.created_at.isoformat(),
        } for m in msgs]
        return Response({'messages': data, 'total': len(data)})
    except Exception as e:
        logger.error(f"superadmin_messages error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET  /api/auth/superadmin/messages/inbox/
# Admin reads messages sent to them.
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_messages_inbox(request):
    """School admin/principal reads their inbox from superadmin."""
    if request.user.role not in ('SCHOOL_ADMIN', 'PRINCIPAL', 'SUPER_ADMIN'):
        return Response({'error': 'Forbidden'}, status=403)
    try:
        from accounts.models import DirectMessage
        if request.user.role == 'SUPER_ADMIN':
            # Superadmin can see all messages for monitoring
            msgs = DirectMessage.objects.select_related('sender', 'recipient').all()[:200]
        else:
            msgs = DirectMessage.objects.filter(recipient=request.user).select_related('sender')[:200]

        data = [{
            'id': m.id,
            'sender_name': m.sender.get_full_name(),
            'subject': m.subject,
            'body': m.body,
            'is_read': m.is_read,
            'created_at': m.created_at.isoformat(),
        } for m in msgs]
        unread_count = sum(1 for m in msgs if not m.is_read)
        return Response({'messages': data, 'unread_count': unread_count})
    except Exception as e:
        logger.error(f"admin_messages_inbox error: {e}")
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# PATCH /api/auth/superadmin/messages/<id>/read/
# ─────────────────────────────────────────────
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def admin_message_mark_read(request, msg_id):
    """Mark a message as read. Only the recipient may mark it."""
    try:
        from accounts.models import DirectMessage
        from django.utils import timezone
        msg = DirectMessage.objects.get(pk=msg_id, recipient=request.user)
        if not msg.is_read:
            msg.is_read = True
            msg.read_at = timezone.now()
            msg.save(update_fields=['is_read', 'read_at'])
        return Response({'status': 'read'})
    except DirectMessage.DoesNotExist:
        return Response({'error': 'Message not found.'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)


# ─────────────────────────────────────────────
# GET  /api/auth/superadmin/admins/
# List only SCHOOL_ADMIN + PRINCIPAL users (for message recipient picker)
# ─────────────────────────────────────────────
@api_view(['GET'])
@permission_classes([IsSuperAdmin])
def superadmin_list_admins(request):
    """Quick list of all SCHOOL_ADMIN and PRINCIPAL users for the compose dialog."""
    err = require_superadmin(request)
    if err:
        return err
    try:
        from accounts.models import User
        admins = User.objects.filter(
            role__in=['SCHOOL_ADMIN', 'PRINCIPAL'],
        ).select_related('school').order_by('school__name', 'first_name')

        data = [{
            'id': u.id,
            'name': u.get_full_name(),
            'email': u.email,
            'role': u.role,
            'school': u.school.name if u.school else '—',
            'is_active': u.is_active,
        } for u in admins]
        return Response({'admins': data})
    except Exception as e:
        return Response({'error': str(e)}, status=500)

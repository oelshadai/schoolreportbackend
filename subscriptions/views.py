"""Subscription API views."""
from datetime import date

from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    PLAN_CHOICES, PLAN_DURATIONS, PLAN_FREE, PLAN_MONTHLY, PLAN_PRICES,
    PLAN_YEARLY, Subscription,
)


def _subscription_payload(school):
    """Build a consistent subscription-status dict for *school*."""
    sub = (
        school.subscriptions
        .filter(status=Subscription.STATUS_ACTIVE)
        .order_by('-end_date')
        .first()
    )

    if not sub:
        # Fall back to the plain School fields (legacy / no subscription row)
        plan = school.subscription_plan or PLAN_FREE
        expires = school.subscription_expires
        is_locked = False
        if expires:
            is_locked = plan == PLAN_FREE and expires < date.today()
        days_left = None
        if expires:
            days_left = max((expires - date.today()).days, 0)
        return {
            'plan': plan,
            'status': 'LOCKED' if is_locked else 'ACTIVE',
            'start_date': None,
            'end_date': str(expires) if expires else None,
            'days_remaining': days_left,
            'is_locked': is_locked,
            'prices': PLAN_PRICES,
        }

    is_locked = not sub.is_valid()
    return {
        'plan': sub.plan_type,
        'status': sub.status,
        'start_date': str(sub.start_date),
        'end_date': str(sub.end_date),
        'days_remaining': sub.days_remaining(),
        'is_locked': is_locked,
        'prices': PLAN_PRICES,
    }


class SubscriptionStatusView(APIView):
    """GET  /api/subscriptions/status/
    Returns the current subscription status for the requesting school.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        school = getattr(request.user, 'school', None)
        if not school:
            return Response({'error': 'No school associated with this account.'}, status=400)

        # Auto-lock expired FREE trials
        active_sub = (
            school.subscriptions
            .filter(status=Subscription.STATUS_ACTIVE)
            .order_by('-end_date')
            .first()
        )
        if active_sub and active_sub.plan_type == PLAN_FREE and active_sub.end_date < date.today():
            active_sub.status = Subscription.STATUS_LOCKED
            active_sub.save(update_fields=['status', 'updated_at'])
            school.subscription_plan = PLAN_FREE
            school.is_active = False
            school.save(update_fields=['subscription_plan', 'is_active'])

        return Response(_subscription_payload(school))


class SubscriptionUpgradeView(APIView):
    """POST /api/subscriptions/upgrade/
    Body: { "plan": "MONTHLY" | "YEARLY" }

    In production this would integrate with a payment gateway.
    For now it upgrades immediately (admin-confirmed workflow).
    Only SCHOOL_ADMIN can call this.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('SCHOOL_ADMIN', 'SUPER_ADMIN'):
            return Response({'error': 'Permission denied.'}, status=403)

        school = getattr(request.user, 'school', None)
        if not school:
            return Response({'error': 'No school associated with this account.'}, status=400)

        plan = request.data.get('plan', '').upper()
        if plan not in (PLAN_MONTHLY, PLAN_YEARLY):
            return Response(
                {'error': f'Invalid plan. Choose MONTHLY or YEARLY.'},
                status=400,
            )

        # Expire any existing active subscription
        school.subscriptions.filter(status=Subscription.STATUS_ACTIVE).update(
            status=Subscription.STATUS_CANCELLED
        )

        # Create a new active subscription
        new_sub = Subscription.create_for_school(school, plan)

        # Sync the simple School fields for backward-compat
        school.subscription_plan = plan
        school.subscription_expires = new_sub.end_date
        school.is_active = True
        school.save(update_fields=['subscription_plan', 'subscription_expires', 'is_active'])

        return Response(
            {
                'message': f'Subscription upgraded to {plan}.',
                'subscription': _subscription_payload(school),
            },
            status=200,
        )


class SubscriptionPlansView(APIView):
    """GET /api/subscriptions/plans/
    Returns the available plans and their prices (no auth required).
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        plans = [
            {
                'key': PLAN_FREE,
                'name': 'Free Trial',
                'price': PLAN_PRICES[PLAN_FREE],
                'duration_days': PLAN_DURATIONS[PLAN_FREE],
                'description': '14-day free trial. Full access. No credit card needed.',
                'badge': '14 days',
            },
            {
                'key': PLAN_MONTHLY,
                'name': 'Monthly',
                'price': PLAN_PRICES[PLAN_MONTHLY],
                'duration_days': PLAN_DURATIONS[PLAN_MONTHLY],
                'description': 'Full access billed monthly.',
                'badge': 'KES 400/mo',
            },
            {
                'key': PLAN_YEARLY,
                'name': 'Yearly',
                'price': PLAN_PRICES[PLAN_YEARLY],
                'duration_days': PLAN_DURATIONS[PLAN_YEARLY],
                'description': 'Pay for 11 months, get 12. Save KES 400.',
                'badge': 'Save 1 month',
            },
        ]
        return Response(plans)

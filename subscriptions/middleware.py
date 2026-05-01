"""Subscription lock middleware.

Blocks API requests from schools whose FREE trial has expired.
Safe paths (auth, subscription management, admin) are always allowed.
"""
import json
from datetime import date

from django.http import JsonResponse


# Paths that are always allowed regardless of subscription status
ALLOWED_PATH_PREFIXES = (
    '/admin/',
    '/api/auth/',
    '/api/subscriptions/',
    '/static/',
    '/media/',
)


class SubscriptionLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only check authenticated API requests
        if self._is_exempt(request):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if not user or not user.is_authenticated:
            return self.get_response(request)

        # Only affect school-level users (not super admins)
        if getattr(user, 'is_super_admin', False) or user.role == 'SUPER_ADMIN':
            return self.get_response(request)

        school = getattr(user, 'school', None)
        if not school:
            return self.get_response(request)

        # Check if the FREE trial has expired
        if school.subscription_plan == 'FREE':
            expires = school.subscription_expires
            if expires and date.today() > expires:
                # Lock the school account
                if school.is_active:
                    school.is_active = False
                    school.save(update_fields=['is_active'])
                return JsonResponse(
                    {
                        'error': 'subscription_locked',
                        'message': (
                            'Your 14-day free trial has ended. '
                            'Please upgrade to continue using the platform.'
                        ),
                        'upgrade_url': '/school/subscription',
                    },
                    status=402,
                )

        return self.get_response(request)

    def _is_exempt(self, request):
        path = request.path_info
        return any(path.startswith(prefix) for prefix in ALLOWED_PATH_PREFIXES)

import json
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_push_to_user(user, title, body, url='/'):
    """Send a Web Push notification to all subscriptions for a given user."""
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        logger.warning("pywebpush not installed — skipping push notification")
        return

    from .models import PushSubscription

    subscriptions = PushSubscription.objects.filter(user=user)
    if not subscriptions.exists():
        return

    vapid_private = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    vapid_claims = {"sub": f"mailto:{getattr(settings, 'VAPID_EMAIL', 'admin@schoolreport.app')}"}

    payload = json.dumps({"title": title, "body": body, "url": url})

    dead_endpoints = []
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
            )
        except WebPushException as e:
            if e.response is not None and e.response.status_code in (404, 410):
                # Endpoint is gone — delete it
                dead_endpoints.append(sub.pk)
            else:
                logger.error("WebPush failed for user %s: %s", user.pk, e)
        except Exception as e:
            logger.error("Unexpected push error for user %s: %s", user.pk, e)

    if dead_endpoints:
        PushSubscription.objects.filter(pk__in=dead_endpoints).delete()

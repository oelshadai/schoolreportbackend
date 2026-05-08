from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, SupportTicketViewSet, SmsLogViewSet, push_subscribe, push_unsubscribe, vapid_public_key

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'support-tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'sms-logs', SmsLogViewSet, basename='sms-log')

urlpatterns = [
    path('', include(router.urls)),
    path('push/subscribe/', push_subscribe, name='push-subscribe'),
    path('push/unsubscribe/', push_unsubscribe, name='push-unsubscribe'),
    path('push/vapid-public-key/', vapid_public_key, name='vapid-public-key'),
]
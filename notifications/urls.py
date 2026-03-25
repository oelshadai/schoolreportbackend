from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, SupportTicketViewSet

router = DefaultRouter()
router.register(r'notifications', NotificationViewSet, basename='notification')
router.register(r'support-tickets', SupportTicketViewSet, basename='support-ticket')

urlpatterns = [
    path('', include(router.urls)),
]
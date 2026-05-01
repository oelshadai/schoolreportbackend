# Subscription routes
from django.urls import path
from .views import SubscriptionStatusView, SubscriptionUpgradeView, SubscriptionPlansView

urlpatterns = [
    path('status/', SubscriptionStatusView.as_view(), name='subscription_status'),
    path('upgrade/', SubscriptionUpgradeView.as_view(), name='subscription_upgrade'),
    path('plans/', SubscriptionPlansView.as_view(), name='subscription_plans'),
]

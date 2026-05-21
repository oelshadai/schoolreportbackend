from django.urls import path, include
from django.conf import settings
from rest_framework.routers import DefaultRouter
from .views import (
    SchoolViewSet, AcademicYearViewSet, TermViewSet,
    ClassViewSet, SubjectViewSet, ClassSubjectViewSet,
    GradingScaleViewSet, SchoolDashboardView, SchoolSettingsView,
    ParentPortalSettingsView, ParentManagementViewSet,
    StaffPermissionViewSet, SmsSettingsView,
    SmsPurchaseView, SmsPurchaseInitiateView, SmsPurchaseVerifyView,
    PaystackWebhookView,
)

FINANCIAL_AVAILABLE = False
try:
    from financial.views import (
        StaffViewSet, StaffSalaryViewSet, PayrollRecordViewSet,
        IncomeViewSet, ExpenseViewSet, BudgetViewSet,
        BudgetItemViewSet, FinancialDashboardView
    )
    FINANCIAL_AVAILABLE = True
except ImportError:
    FINANCIAL_AVAILABLE = False

router = DefaultRouter()
router.register(r'academic-years', AcademicYearViewSet, basename='academic-year')
router.register(r'terms', TermViewSet, basename='term')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'class-subjects', ClassSubjectViewSet, basename='class-subject')
router.register(r'grading-scales', GradingScaleViewSet, basename='grading-scale')
router.register(r'parent-accounts', ParentManagementViewSet, basename='parent-accounts')
router.register(r'staff-permissions', StaffPermissionViewSet, basename='staff-permissions')

# Register financial endpoints if available
if FINANCIAL_AVAILABLE:
    router.register(r'financial/staff', StaffViewSet, basename='financial-staff')
    router.register(r'financial/salaries', StaffSalaryViewSet, basename='financial-salary')
    router.register(r'financial/payroll', PayrollRecordViewSet, basename='financial-payroll')
    router.register(r'financial/income', IncomeViewSet, basename='financial-income')
    router.register(r'financial/expenses', ExpenseViewSet, basename='financial-expense')
    router.register(r'financial/budgets', BudgetViewSet, basename='financial-budget')
    router.register(r'financial/budget-items', BudgetItemViewSet, basename='financial-budget-item')
    router.register(r'financial/dashboard', FinancialDashboardView, basename='financial-dashboard')

router.register(r'', SchoolViewSet, basename='school')

urlpatterns = [
    path('dashboard/', SchoolDashboardView.as_view(), name='school_dashboard'),
    path('settings/', SchoolSettingsView.as_view(), name='school_settings'),
    path('parent-portal-settings/', ParentPortalSettingsView.as_view(), name='parent_portal_settings'),
    path('sms-settings/', SmsSettingsView.as_view(), name='sms_settings'),
    path('sms-purchase/', SmsPurchaseView.as_view(), name='sms_purchase'),
    path('sms-purchase/initiate/', SmsPurchaseInitiateView.as_view(), name='sms_purchase_initiate'),
    path('sms-purchase/verify/', SmsPurchaseVerifyView.as_view(), name='sms_purchase_verify'),
    path('paystack-webhook/', PaystackWebhookView.as_view(), name='paystack_webhook'),
] + router.urls

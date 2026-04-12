from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    FeeTypeViewSet, FeeStructureViewSet, StudentFeeViewSet,
    FeePaymentViewSet, FeeCollectionViewSet, StudentSearchForFeeViewSet,
    FeeReportViewSet, TermBillViewSet
)

router = DefaultRouter()
router.register(r'types', FeeTypeViewSet, basename='fee-type')
router.register(r'structures', FeeStructureViewSet, basename='fee-structure')
router.register(r'student-fees', StudentFeeViewSet, basename='student-fee')
router.register(r'payments', FeePaymentViewSet, basename='fee-payment')
router.register(r'collections', FeeCollectionViewSet, basename='fee-collection')
router.register(r'search', StudentSearchForFeeViewSet, basename='student-search-fee')
router.register(r'reports', FeeReportViewSet, basename='fee-report')
router.register(r'term-bills', TermBillViewSet, basename='term-bill')

urlpatterns = [
    path('', include(router.urls)),
]

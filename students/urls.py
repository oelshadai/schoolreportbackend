from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, AttendanceViewSet, BehaviourViewSet, StudentPromotionViewSet

router = DefaultRouter()
router.register(r'', StudentViewSet, basename='student')
router.register(r'attendance', AttendanceViewSet, basename='attendance')
router.register(r'behaviour', BehaviourViewSet, basename='behaviour')
router.register(r'promotions', StudentPromotionViewSet, basename='promotion')

urlpatterns = router.urls

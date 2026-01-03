from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, AttendanceViewSet, BehaviourViewSet, StudentPromotionViewSet, DailyAttendanceViewSet
from .auth_views import student_login, student_dashboard, student_logout
from accounts.password_views import change_password

router = DefaultRouter()
router.register(r'', StudentViewSet, basename='student')
router.register(r'attendance', DailyAttendanceViewSet, basename='attendance')  # Daily attendance
router.register(r'term-attendance', AttendanceViewSet, basename='term-attendance')  # Term-based attendance
router.register(r'behaviour', BehaviourViewSet, basename='behaviour')
router.register(r'promotions', StudentPromotionViewSet, basename='promotion')

urlpatterns = [
    path('auth/login/', student_login, name='student_login'),
    path('auth/logout/', student_logout, name='student_logout'),
    path('auth/dashboard/', student_dashboard, name='student_dashboard'),
    path('auth/change-password/', change_password, name='student_change_password'),
] + router.urls

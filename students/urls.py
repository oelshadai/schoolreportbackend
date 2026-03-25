from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, AttendanceViewSet, BehaviourViewSet, StudentPromotionViewSet, DailyAttendanceViewSet, create_behaviour_record
from .attendance_views import AttendanceAdminViewSet, StudentAttendanceViewSet
from .auth_views import student_login, student_dashboard, student_logout, student_refresh_token
from .portal_views import student_classes, student_subjects, student_announcements, student_profile, student_assignments_list, student_schedule, student_reports, student_published_reports, download_student_report, view_student_published_report
from .teacher_attendance_functions import teacher_attendance_my_classes, teacher_attendance_class_students, teacher_attendance_save
from accounts.password_views import change_password

router = DefaultRouter(trailing_slash=True)
router.register(r'my-attendance', StudentAttendanceViewSet, basename='my-attendance')
router.register(r'attendance/admin', AttendanceAdminViewSet, basename='attendance-admin')
router.register(r'attendance', DailyAttendanceViewSet, basename='attendance')
router.register(r'term-attendance', AttendanceViewSet, basename='term-attendance')
router.register(r'behaviour', BehaviourViewSet, basename='behaviour')
router.register(r'promotions', StudentPromotionViewSet, basename='promotion')
router.register(r'', StudentViewSet, basename='student')

urlpatterns = [
    # Teacher Attendance Function-based Views
    path('teacher-attendance/my-classes/', teacher_attendance_my_classes, name='teacher_attendance_my_classes'),
    path('teacher-attendance/class-students/', teacher_attendance_class_students, name='teacher_attendance_class_students'),
    path('teacher-attendance/save-attendance/', teacher_attendance_save, name='teacher_attendance_save'),
    
    # Student Authentication
    path('auth/login/', student_login, name='student_login'),
    path('auth/logout/', student_logout, name='student_logout'),
    path('auth/refresh/', student_refresh_token, name='student_refresh_token'),
    path('auth/dashboard/', student_dashboard, name='student_dashboard'),
    path('auth/change-password/', change_password, name='student_change_password'),
    
    # Student Profile
    path('profile/', student_profile, name='student_profile'),
    
    # Student Dashboard API (alternative endpoint)
    path('dashboard/', student_dashboard, name='student_dashboard_api'),
    
    # Student Portal APIs
    path('my-classes/', student_classes, name='student_classes'),
    path('my-schedule/', student_schedule, name='student_schedule'),
    path('assignments/', student_assignments_list, name='student_assignments'),
    path('reports/', student_reports, name='student_reports'),
    path('published-reports/', student_published_reports, name='student_published_reports'),
    path('reports/<int:report_id>/download/', download_student_report, name='download_student_report'),
    path('published-reports/<int:term_id>/view/', view_student_published_report, name='view_student_published_report'),
    
    # Behaviour
    path('behaviour/create/', create_behaviour_record, name='create_behaviour'),
] + router.urls
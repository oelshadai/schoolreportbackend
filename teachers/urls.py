from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet, teacher_assignments_view
from .assignment_views import teacher_class_assignments
from .simple_assignments import simple_teacher_assignments
from .cors_views import teachers_cors_endpoint
from .cors_test_views import cors_test, teacher_cors_test
from .debug_views import debug_user_info

router = DefaultRouter()
router.register(r'', TeacherViewSet, basename='teacher')

urlpatterns = [
    path('cors/', teachers_cors_endpoint, name='teachers_cors'),
    path('cors-test/', cors_test, name='cors_test'),
    path('cors-test/teacher/', teacher_cors_test, name='teacher_cors_test'),
    path('assignments/', simple_teacher_assignments, name='simple_teacher_assignments'),
    path('debug/', debug_user_info, name='debug_user_info'),
    path('', include(router.urls)),
]


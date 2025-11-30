from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet
from .cors_views import teachers_cors_endpoint
from .cors_test_views import cors_test, teacher_cors_test

router = DefaultRouter()
router.register(r'', TeacherViewSet, basename='teacher')

urlpatterns = [
    path('cors/', teachers_cors_endpoint, name='teachers_cors'),
    path('cors-test/', cors_test, name='cors_test'),
    path('cors-test/teacher/', teacher_cors_test, name='teacher_cors_test'),
    path('', include(router.urls)),
]


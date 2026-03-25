from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherTimetableViewSet, StudentTimetableViewSet

router = DefaultRouter()
router.register(r'teacher', TeacherTimetableViewSet, basename='timetable-teacher')
router.register(r'student', StudentTimetableViewSet, basename='timetable-student')

urlpatterns = [
    path('', include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SchoolViewSet, AcademicYearViewSet, TermViewSet,
    ClassViewSet, SubjectViewSet, ClassSubjectViewSet,
    GradingScaleViewSet, SchoolDashboardView, SchoolSettingsView
)

router = DefaultRouter()
# Register specific prefixes first to avoid the root ('') route capturing them
router.register(r'academic-years', AcademicYearViewSet, basename='academic-year')
router.register(r'terms', TermViewSet, basename='term')
router.register(r'classes', ClassViewSet, basename='class')
router.register(r'subjects', SubjectViewSet, basename='subject')
router.register(r'class-subjects', ClassSubjectViewSet, basename='class-subject')
router.register(r'grading-scales', GradingScaleViewSet, basename='grading-scale')
# Register the SchoolViewSet at the root last
router.register(r'', SchoolViewSet, basename='school')

urlpatterns = [
    path('dashboard/', SchoolDashboardView.as_view(), name='school_dashboard'),
    path('settings/', SchoolSettingsView.as_view(), name='school_settings'),
] + router.urls

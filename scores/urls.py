from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContinuousAssessmentViewSet, ExamScoreViewSet,
    SubjectResultViewSet, TermResultViewSet, ScoreManagementViewSet
)

router = DefaultRouter()
router.register(r'ca-scores', ContinuousAssessmentViewSet, basename='ca-score')
router.register(r'exam-scores', ExamScoreViewSet, basename='exam-score')
router.register(r'subject-results', SubjectResultViewSet, basename='subject-result')
router.register(r'term-results', TermResultViewSet, basename='term-result')
router.register(r'manage', ScoreManagementViewSet, basename='score-management')

urlpatterns = router.urls

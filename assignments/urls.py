from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import TeacherAssignmentViewSet, StudentAssignmentViewSet
from .workflow_api import AcademicWorkflowViewSet
from . import views

app_name = 'assignments'

# Create router for clean API
router = DefaultRouter()
router.register(r'teacher', TeacherAssignmentViewSet, basename='teacher-assignments')
router.register(r'student', StudentAssignmentViewSet, basename='student-assignments')
router.register(r'workflow', AcademicWorkflowViewSet, basename='assignment-workflow')

# COMPATIBILITY FIX: Add assignments router for frontend compatibility
router.register(r'assignments', TeacherAssignmentViewSet, basename='assignments')

urlpatterns = [
    # PRODUCTION FIX: Direct endpoint for student assignments (frontend compatibility)
    path('student/my-assignments/', StudentAssignmentViewSet.as_view({'get': 'my_assignments'}), name='student-my-assignments'),
    path('student/submission-stats/', StudentAssignmentViewSet.as_view({'get': 'submission_stats'}), name='student-submission-stats'),
    path('student/my-classes/', StudentAssignmentViewSet.as_view({'get': 'my_classes'}), name='student-my-classes'),
    
    # Teacher assignment management endpoints - FIXED ORDER
    path('teacher/<int:pk>/publish/', TeacherAssignmentViewSet.as_view({'post': 'publish'}), name='teacher-publish-assignment'),
    path('teacher/<int:pk>/publish_assignment/', TeacherAssignmentViewSet.as_view({'post': 'publish_assignment'}), name='teacher-publish-assignment-alt'),
    path('teacher/<int:pk>/submissions/', TeacherAssignmentViewSet.as_view({'get': 'get_submissions'}), name='teacher-assignment-submissions'),
    path('teacher/<int:pk>/reopen-submission/', TeacherAssignmentViewSet.as_view({'post': 'reopen_submission'}), name='teacher-reopen-submission'),
    path('teacher/<int:pk>/extend-deadline/', TeacherAssignmentViewSet.as_view({'post': 'extend_deadline'}), name='teacher-extend-deadline'),
    path('teacher/<int:pk>/bulk-reopen/', TeacherAssignmentViewSet.as_view({'post': 'bulk_reopen_submissions'}), name='teacher-bulk-reopen'),
    path('teacher/<int:pk>/extend-individual-deadline/', TeacherAssignmentViewSet.as_view({'post': 'extend_individual_deadline'}), name='teacher-extend-individual-deadline'),
    
    # Clean API routes - MUST BE LAST
    path('', include(router.urls)),
    
    # File upload endpoint
    path('quiz-answers/<int:quiz_answer_id>/upload-files/', 
         views.upload_quiz_answer_files, 
         name='upload_quiz_answer_files'),
]
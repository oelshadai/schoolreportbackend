from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AssignmentViewSet, StudentAssignmentViewSet, StudentPortalViewSet, 
    create_assignment, create_timed_task, activate_task, get_student_tasks,
    start_task, submit_answer, submit_task, get_task_results, test_endpoint,
    get_assignment_history, start_assignment_attempt, submit_assignment_attempt,
    get_student_assignments_with_attempts
)

router = DefaultRouter()
router.register(r'assignments', AssignmentViewSet, basename='assignment')
router.register(r'submissions', StudentAssignmentViewSet, basename='student-assignment')
router.register(r'portal', StudentPortalViewSet, basename='student-portal')

urlpatterns = [
    path('create/', create_assignment, name='create-assignment'),
    path('test/', test_endpoint, name='test-endpoint'),
    
    # Assignment History and Attempts
    path('history/', get_assignment_history, name='assignment-history'),
    path('current/', get_student_assignments_with_attempts, name='current-assignments'),
    path('<int:assignment_id>/start-attempt/', start_assignment_attempt, name='start-assignment-attempt'),
    path('attempts/<int:attempt_id>/submit/', submit_assignment_attempt, name='submit-assignment-attempt'),
    
    # Timed Tasks
    path('tasks/create/', create_timed_task, name='create-timed-task'),
    path('tasks/<int:task_id>/activate/', activate_task, name='activate-task'),
    path('tasks/<int:task_id>/results/', get_task_results, name='task-results'),
    path('tasks/available/', get_student_tasks, name='student-tasks'),
    path('tasks/<int:task_id>/start/', start_task, name='start-task'),
    path('attempts/<int:attempt_id>/answer/', submit_answer, name='submit-answer'),
    path('attempts/<int:attempt_id>/submit/', submit_task, name='submit-task'),
    
    path('', include(router.urls)),
]
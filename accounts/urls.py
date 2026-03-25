from django.urls import path
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    SecureTokenObtainPairView,
    RegisterView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    CreateTeacherView,
    RegisterSchoolView,
    LogoutView,
)
from .auth_views import (
    teacher_login, admin_login, superadmin_login,
    teacher_dashboard, admin_dashboard, superadmin_dashboard,
    change_password
)
from .password_views import forgot_password, reset_password_admin
from students.auth_views import student_login

@ensure_csrf_cookie
def csrf_token_view(request):
    """Provide CSRF token for frontend"""
    return JsonResponse({'csrf_token': request.META.get('CSRF_COOKIE')})

# Student-aware profile view
class StudentAwareProfileView(UserProfileView):
    """Profile view that handles both regular users and students"""
    def get_object(self):
        user = self.request.user
        # If user is a student, redirect to student dashboard endpoint
        if hasattr(user, 'role') and user.role == 'STUDENT':
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'detail': 'Students should use /api/students/auth/dashboard/ endpoint'}, 
                status=status.HTTP_302_FOUND
            )
        return user

urlpatterns = [
    path('csrf-token/', csrf_token_view, name='csrf_token'),
    path('login/', SecureTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('student-login/', student_login, name='student_login'),
    path('teacher-login/', teacher_login, name='teacher_login'),
    path('admin-login/', admin_login, name='admin_login'),
    path('superadmin-login/', superadmin_login, name='superadmin_login'),
    path('teacher-dashboard/', teacher_dashboard, name='teacher_dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('superadmin-dashboard/', superadmin_dashboard, name='superadmin_dashboard'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('register-school/', RegisterSchoolView.as_view(), name='register_school'),
    path('profile/', StudentAwareProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('auth/change-password/', change_password, name='auth_change_password'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('teachers/create/', CreateTeacherView.as_view(), name='create_teacher'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password_admin, name='reset_password_admin'),
]

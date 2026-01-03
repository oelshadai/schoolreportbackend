from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    RegisterView,
    UserProfileView,
    ChangePasswordView,
    UserListView,
    CreateTeacherView,
    RegisterSchoolView,
    LogoutView,
)
from .password_views import forgot_password, reset_password_admin
from students.auth_views import student_login

urlpatterns = [
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('student-login/', student_login, name='student_login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('register-school/', RegisterSchoolView.as_view(), name='register_school'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('users/', UserListView.as_view(), name='user_list'),
    path('teachers/create/', CreateTeacherView.as_view(), name='create_teacher'),
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password_admin, name='reset_password_admin'),
]

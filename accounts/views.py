from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    SchoolRegistrationSerializer
)

User = get_user_model()
from schools.models import Class as SchoolClass


class CORSMixin:
    """Mixin to add CORS headers to all responses"""
    
    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        
        # Add CORS headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
        response['Access-Control-Allow-Credentials'] = 'true'
        
        return response


class CustomTokenObtainPairView(CORSMixin, TokenObtainPairView):
    """Custom login view with user data"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(CORSMixin, generics.CreateAPIView):
    """User registration view"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer


class UserProfileView(CORSMixin, generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(CORSMixin, APIView):
    """Change user password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            if not user.check_password(serializer.data.get('old_password')):
                return Response(
                    {"old_password": "Wrong password"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.data.get('new_password'))
            user.save()
            
            return Response(
                {"message": "Password changed successfully"}, 
                status=status.HTTP_200_OK
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(CORSMixin, generics.ListAPIView):
    """List users (admin only)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_super_admin:
            return User.objects.all()
        elif user.is_school_admin or user.is_principal:
            return User.objects.filter(school=user.school)
        else:
            return User.objects.filter(id=user.id)


class CreateTeacherView(CORSMixin, generics.CreateAPIView):
    """Create teacher account (school admin only)"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Accept optional class_id for assigning class_teacher
        current_user = request.user
        if not (current_user.is_school_admin or current_user.is_principal):
            raise permissions.PermissionDenied("Only school admins can create teachers")

        # Copy request data and remove non-serializer fields
        data = request.data.copy()
        class_id = data.pop('class_id', None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        created_teacher = serializer.instance

        # Assign as class teacher if class_id provided
        if class_id:
            try:
                cls = SchoolClass.objects.get(id=class_id, school=current_user.school)
                cls.class_teacher = created_teacher
                cls.save(update_fields=['class_teacher'])
            except SchoolClass.DoesNotExist:
                pass  # Ignore invalid class_id silently

        headers = self.get_success_headers(serializer.data)
        return Response(UserSerializer(created_teacher).data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(school=user.school, role='TEACHER')


class RegisterSchoolView(CORSMixin, APIView):
    """Endpoint for a new school to self-register and obtain JWT tokens"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SchoolRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user, school = serializer.save()

        # Issue tokens
        token_serializer = CustomTokenObtainPairSerializer(data={'email': user.email, 'password': request.data['password']})
        token_serializer.is_valid(raise_exception=True)
        data = token_serializer.validated_data
        data['school'] = {
            'id': school.id,
            'name': school.name,
            'subscription_plan': school.subscription_plan,
        }
        return Response(data, status=status.HTTP_201_CREATED)

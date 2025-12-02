from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Teacher
from schools.serializers import SubjectSerializer
from schools.models import Class
from .email_utils import send_teacher_welcome_email
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class TeacherSerializer(serializers.ModelSerializer):
    """Serializer for Teacher model with full user information"""
    
    first_name = serializers.CharField(source='user.first_name', read_only=True)
    last_name = serializers.CharField(source='user.last_name', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)
    full_name = serializers.SerializerMethodField()
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    specializations_detail = SubjectSerializer(source='specializations', many=True, read_only=True)
    
    class Meta:
        model = Teacher
        fields = [
            'id', 'user_id', 'employee_id', 'first_name', 'last_name', 
            'email', 'phone_number', 'full_name', 'hire_date', 
            'qualification', 'experience_years', 'emergency_contact', 
            'address', 'is_class_teacher', 'is_active', 
            'specializations', 'specializations_detail', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_class_teacher', 'created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class TeacherCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new teacher with user account"""
    
    # User fields
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    
    # Optional class assignment
    class_id = serializers.IntegerField(required=False, allow_null=True)
    
    class Meta:
        model = Teacher
        fields = [
            'employee_id', 'first_name', 'last_name', 'email', 
            'phone_number', 'password', 'hire_date', 'qualification', 
            'experience_years', 'emergency_contact', 'address', 
            'specializations', 'class_id'
        ]
    
    def validate_email(self, value):
        """Ensure email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value
    
    def validate_employee_id(self, value):
        """Ensure employee_id is unique within school"""
        try:
            school = self.context.get('request').user.school if self.context.get('request') else None
            if school and Teacher.objects.filter(employee_id=value, school=school).exists():
                raise serializers.ValidationError("A teacher with this employee ID already exists in your school.")
        except Exception as e:
            logger.warning(f"Error validating employee_id: {str(e)}")
        return value
    
    def validate_class_id(self, value):
        """Validate class assignment belongs to the same school"""
        if value:
            try:
                request = self.context.get('request')
                if not request:
                    return value
                school = request.user.school
                class_instance = Class.objects.get(id=value, school=school)
                # Check if class already has a class teacher
                if class_instance.class_teacher:
                    raise serializers.ValidationError(f"Class {class_instance} already has a class teacher assigned.")
            except Class.DoesNotExist:
                raise serializers.ValidationError("Invalid class selection.")
            except Exception as e:
                logger.warning(f"Error validating class_id: {str(e)}")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        """Create user account and teacher profile with optional class assignment"""
        # Extract user fields
        class_id = validated_data.pop('class_id', None)
        password = validated_data['password']  # Store password for email
        
        user_data = {
            'first_name': validated_data.pop('first_name'),
            'last_name': validated_data.pop('last_name'),
            'email': validated_data.pop('email'),
            'phone_number': validated_data.pop('phone_number', ''),
            'password': validated_data.pop('password'),
            'role': 'TEACHER',
            'school': validated_data['school']
        }
        
        # Create user account
        user = User.objects.create_user(
            email=user_data['email'],
            password=user_data['password'],
            first_name=user_data['first_name'],
            last_name=user_data['last_name'],
            phone_number=user_data['phone_number'],
            role=user_data['role'],
            school=user_data['school']
        )
        
        # Create teacher profile
        specializations = validated_data.pop('specializations', [])
        teacher = Teacher.objects.create(user=user, **validated_data)
        teacher.specializations.set(specializations)
        
        # Assign class if provided
        assigned_class = None
        if class_id:
            try:
                assigned_class = Class.objects.get(id=class_id, school=user.school)
                assigned_class.class_teacher = user
                assigned_class.save()
                logger.info(f"Assigned teacher {user.email} as class teacher for {assigned_class}")
            except Class.DoesNotExist:
                logger.warning(f"Class with id {class_id} not found for teacher {user.email}")
        
        # Send welcome email with login credentials and assignments
        try:
            email_sent = send_teacher_welcome_email(
                teacher=teacher,
                password=password,
                assigned_class=assigned_class,
                subjects=list(specializations)
            )
            if email_sent:
                logger.info(f"Welcome email sent successfully to {user.email}")
            else:
                logger.warning(f"Failed to send welcome email to {user.email}")
        except Exception as e:
            logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
        
        return teacher
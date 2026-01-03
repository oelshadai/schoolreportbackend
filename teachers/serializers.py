from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from schools.models import Class, Subject, School
from .models import Teacher
from schools.serializers import SubjectSerializer
# from .email_utils import send_teacher_welcome_email   # ✅ Email function disabled
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
            'specializations_detail', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'is_class_teacher', 'created_at', 'updated_at']

    def get_full_name(self, obj):
        return obj.get_full_name()


class TeacherCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new teacher with user account"""

    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=15, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=6)
    class_id = serializers.IntegerField(required=False, allow_null=True)
    school = serializers.PrimaryKeyRelatedField(queryset=School.objects.all())

    specializations = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.all(),
        many=True,
        required=False,
        allow_empty=True
    )

    class Meta:
        model = Teacher
        fields = [
            'employee_id', 'first_name', 'last_name', 'email',
            'phone_number', 'password', 'hire_date', 'qualification',
            'experience_years', 'emergency_contact', 'address',
            'specializations', 'class_id', 'school'
        ]

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_employee_id(self, value):
        school = self.context.get('request').user.school if self.context.get('request') else None
        if school and Teacher.objects.filter(employee_id=value, school=school).exists():
            raise serializers.ValidationError("A teacher with this employee ID already exists in your school.")
        return value

    def validate_class_id(self, value):
        if value:
            request = self.context.get('request')
            if request:
                school = request.user.school
                try:
                    class_instance = Class.objects.get(id=value, school=school)
                    if class_instance.class_teacher:
                        raise serializers.ValidationError(f"Class {class_instance} already has a class teacher assigned.")
                except Class.DoesNotExist:
                    raise serializers.ValidationError("Invalid class selection.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        class_id = validated_data.pop('class_id', None)
        password = validated_data.pop('password')
        specializations = validated_data.pop('specializations', [])
        school = validated_data.pop('school')

        user = User.objects.create_user(
            email=validated_data.pop('email'),
            password=password,
            first_name=validated_data.pop('first_name'),
            last_name=validated_data.pop('last_name'),
            phone_number=validated_data.pop('phone_number', ''),
            role='TEACHER',
            school=school
        )

        teacher = Teacher.objects.create(user=user, school=school, **validated_data)
        teacher.specializations.set(specializations)

        assigned_class = None
        if class_id:
            try:
                assigned_class = Class.objects.get(id=class_id, school=school)
                assigned_class.class_teacher = user
                assigned_class.save()
                logger.info(f"Assigned teacher {user.email} as class teacher for {assigned_class}")
            except Class.DoesNotExist:
                logger.warning(f"Class with id {class_id} not found for teacher {user.email}")

        # ---------------------------------------------------------
        # ✅ EMAIL FUNCTION REMOVED (COMMENTED OUT)
        #
        # try:
        #     email_sent = send_teacher_welcome_email(
        #         teacher=teacher,
        #         password=password,
        #         assigned_class=assigned_class,
        #         subjects=list(specializations)
        #     )
        #     if email_sent:
        #         logger.info(f"Welcome email sent successfully to {user.email}")
        #     else:
        #         logger.warning(f"Failed to send welcome email to {user.email}")
        # except Exception as e:
        #     logger.error(f"Error sending welcome email to {user.email}: {str(e)}")
        # ---------------------------------------------------------

        # Store the plain password for display purposes
        teacher._plain_password = password
        teacher._assigned_class = assigned_class
        
        return teacher

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from schools.models import School, AcademicYear, Term, Subject, GradingScale
from datetime import date, timedelta
import re
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

PLAN_FREE = 'FREE'
PLAN_MONTHLY = 'MONTHLY'
PLAN_YEARLY = 'YEARLY'
PLAN_DURATIONS = {
    PLAN_FREE: 14,
    PLAN_MONTHLY: 30,
    PLAN_YEARLY: 366,
}


class SchoolBriefSerializer(serializers.ModelSerializer):
    """Brief school info for user profile"""
    class Meta:
        model = School
        fields = ['id', 'name']

class UserSerializer(serializers.ModelSerializer):
    """Serializer for the custom User model"""
    school = SchoolBriefSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id',
            'first_name',
            'last_name',
            'email',
            'phone_number',   # include if your User model has this field
            'role',           # include if your User model has this field
            'school'          # include if your User model links to School
        ]
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})

        # Enforce complexity: at least one uppercase, one digit
        password = attrs['password']
        if not re.search(r'[A-Z]', password):
            raise serializers.ValidationError({"password": "Password must contain at least one uppercase letter."})
        if not re.search(r'\d', password):
            raise serializers.ValidationError({"password": "Password must contain at least one digit."})

        # Run Django's built-in validators (common passwords, similarity, etc.)
        try:
            validate_password(password)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"password": list(e.messages)})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer that includes user data"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing password"""
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    new_password_confirm = serializers.CharField(required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "Passwords do not match"})
        return attrs


class SchoolRegistrationSerializer(serializers.Serializer):
    """Serializer for self-registration of a new school and initial admin user"""

    school_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    address = serializers.CharField(required=False, allow_blank=True, default='')
    location = serializers.CharField(required=False, allow_blank=True, default='')
    phone_number = serializers.CharField(required=False, allow_blank=True, default='')
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    levels = serializers.ListField(
        child=serializers.ChoiceField(choices=[('PRIMARY', 'PRIMARY'), ('JHS', 'JHS'), ('BOTH', 'BOTH')]),
        allow_empty=True,
        required=False
    )
    plan = serializers.ChoiceField(
        choices=[PLAN_FREE, PLAN_MONTHLY, PLAN_YEARLY],
        default=PLAN_FREE,
        required=False,
        help_text='Subscription plan: FREE (14-day trial), MONTHLY (KES 400), YEARLY (KES 4,400)',
    )

    first_name = serializers.CharField(max_length=100, required=False, default='Admin')
    last_name = serializers.CharField(max_length=100, required=False, default='User')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        if User.objects.filter(email=attrs['admin_email']).exists():
            raise serializers.ValidationError({"admin_email": "Email already in use"})
        if School.objects.filter(email=attrs['admin_email']).exists():
            raise serializers.ValidationError({"admin_email": "A school with this email already exists"})
        return attrs

    def create(self, validated_data):
        try:
            password = validated_data.pop('password')
            validated_data.pop('password_confirm')
            school_name = validated_data.pop('school_name')
            admin_email = validated_data.pop('admin_email')
            address = validated_data.pop('address', '').strip() or 'N/A'
            location = validated_data.pop('location', '').strip() or 'N/A'
            phone_number = validated_data.pop('phone_number', '').strip() or 'N/A'
            levels = validated_data.pop('levels', [])
            plan = validated_data.pop('plan', PLAN_FREE)

            today = date.today()
            duration = PLAN_DURATIONS.get(plan, PLAN_DURATIONS[PLAN_FREE])
            trial_expires = today + timedelta(days=duration)

            # Create School (CRITICAL - must succeed)
            school = School.objects.create(
                name=school_name,
                address=address,
                location=location,
                phone_number=phone_number,
                email=admin_email,
                subscription_plan=plan,
                subscription_expires=trial_expires,
                is_active=True,
            )
            logger.info(f"School created: {school.id} - {school_name}")

            # Subscription table writes were intentionally removed.

            # Academic year & term (NON-CRITICAL)
            try:
                with transaction.atomic():
                    year_span = f"{today.year}/{today.year+1}" if today.month >= 9 else f"{today.year-1}/{today.year}"
                    academic_year, _ = AcademicYear.objects.get_or_create(
                        school=school,
                        name=year_span,
                        defaults={
                            'start_date': date(today.year if today.month >= 9 else today.year - 1, 9, 1),
                            'end_date': date(today.year + 1 if today.month >= 9 else today.year, 7, 31),
                            'is_current': True
                        }
                    )
                    Term.objects.get_or_create(
                        academic_year=academic_year,
                        name='FIRST',
                        defaults={
                            'start_date': academic_year.start_date,
                            'end_date': date(academic_year.start_date.year, 12, 15),
                            'is_current': True,
                            'total_days': 0
                        }
                    )
                logger.info(f"Academic year/term created for school {school.id}")
            except Exception as year_err:
                logger.warning(f"Academic year/term creation failed (non-critical): {str(year_err)}")

            # Default grading scale (NON-CRITICAL)
            try:
                with transaction.atomic():
                    default_grades = [
                        GradingScale(school=school, grade='A', min_score=80, max_score=100, remark='Excellent'),
                        GradingScale(school=school, grade='B', min_score=70, max_score=79, remark='Very Good'),
                        GradingScale(school=school, grade='C', min_score=60, max_score=69, remark='Good'),
                        GradingScale(school=school, grade='D', min_score=50, max_score=59, remark='Average'),
                        GradingScale(school=school, grade='E', min_score=40, max_score=49, remark='Pass'),
                        GradingScale(school=school, grade='F', min_score=0, max_score=39, remark='Fail'),
                    ]
                    GradingScale.objects.bulk_create(default_grades, ignore_conflicts=True)
                logger.info(f"Grading scales created for school {school.id}")
            except Exception as grade_err:
                logger.warning(f"Grading scale creation failed (non-critical): {str(grade_err)}")

            # Default subjects (NON-CRITICAL)
            try:
                with transaction.atomic():
                    base_subjects = [
                        Subject(name='English Language', code='ENG', category='BOTH'),
                        Subject(name='Mathematics', code='MATH', category='BOTH'),
                        Subject(name='Integrated Science', code='SCI', category='BOTH'),
                        Subject(name='Creative Art', code='ART', category='BOTH'),
                        Subject(name='Computing', code='COMP', category='BOTH'),
                    ]
                    Subject.objects.bulk_create(base_subjects, ignore_conflicts=True)
                logger.info(f"Default subjects created")
            except Exception as subj_err:
                logger.warning(f"Subject creation failed (non-critical): {str(subj_err)}")

            # Create Admin User (CRITICAL)
            user = User.objects.create_user(
                email=admin_email,
                password=password,
                first_name=validated_data.get('first_name', 'Admin'),
                last_name=validated_data.get('last_name', 'User'),
                role='SCHOOL_ADMIN',
                school=school
            )
            logger.info(f"Admin user created: {user.id} - {admin_email}")

            return user
        except Exception as err:
            logger.error(f"Critical registration error: {str(err)}", exc_info=True)
            raise

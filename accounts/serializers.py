from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from schools.models import School, AcademicYear, Term, Subject, GradingScale
from datetime import date

User = get_user_model()


class SchoolRegistrationSerializer(serializers.Serializer):
    """Serializer for self-registration of a new school and initial admin user"""

    school_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    levels = serializers.ListField(
        child=serializers.ChoiceField(choices=[('PRIMARY', 'PRIMARY'), ('JHS', 'JHS'), ('BOTH', 'BOTH')]),
        allow_empty=True,
        required=False
    )

    first_name = serializers.CharField(max_length=100, required=False, default='Admin')
    last_name = serializers.CharField(max_length=100, required=False, default='User')

    def validate(self, attrs):
        # ✅ Ensure passwords match
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        # ✅ Ensure admin email is unique
        if User.objects.filter(email=attrs['admin_email']).exists():
            raise serializers.ValidationError({"admin_email": "Email already in use"})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        school_name = validated_data.pop('school_name')
        admin_email = validated_data.pop('admin_email')
        levels = validated_data.pop('levels', [])

        # ✅ Create School
        school = School.objects.create(
            name=school_name,
            email=admin_email,
            subscription_plan='FREE',
            # If your School model has a levels field, save it here
            # levels=levels
        )

        # ✅ Academic year & term setup
        today = date.today()
        year_span = f"{today.year}/{today.year+1}" if today.month >= 9 else f"{today.year-1}/{today.year}"
        academic_year = AcademicYear.objects.create(
            school=school,
            name=year_span,
            start_date=date(today.year if today.month >= 9 else today.year - 1, 9, 1),
            end_date=date(today.year + 1 if today.month >= 9 else today.year, 7, 31),
            is_current=True
        )
        Term.objects.create(
            academic_year=academic_year,
            name='FIRST',
            start_date=academic_year.start_date,
            end_date=date(academic_year.start_date.year, 12, 15),
            is_current=True,
            total_days=0
        )

        # ✅ Default grading scale
        default_grades = [
            GradingScale(school=school, grade='A', min_score=80, max_score=100, remark='Excellent'),
            GradingScale(school=school, grade='B', min_score=70, max_score=79, remark='Very Good'),
            GradingScale(school=school, grade='C', min_score=60, max_score=69, remark='Good'),
            GradingScale(school=school, grade='D', min_score=50, max_score=59, remark='Average'),
            GradingScale(school=school, grade='E', min_score=40, max_score=49, remark='Pass'),
            GradingScale(school=school, grade='F', min_score=0, max_score=39, remark='Fail'),
        ]
        GradingScale.objects.bulk_create(default_grades)

        # ✅ Default subjects
        base_subjects = [
            Subject(name='English Language', code='ENG', category='BOTH'),
            Subject(name='Mathematics', code='MATH', category='BOTH'),
            Subject(name='Integrated Science', code='SCI', category='BOTH'),
            Subject(name='Creative Art', code='ART', category='BOTH'),
            Subject(name='Computing', code='COMP', category='BOTH'),
        ]
        Subject.objects.bulk_create(base_subjects, ignore_conflicts=True)

        # ✅ Create Admin User
        user = User.objects.create_user(
            email=admin_email,
            password=password,
            first_name=validated_data.get('first_name', 'Admin'),
            last_name=validated_data.get('last_name', 'User'),
            role='SCHOOL_ADMIN',
            school=school
        )

        return user

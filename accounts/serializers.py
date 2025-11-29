from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from schools.models import School, AcademicYear, Term, Subject, GradingScale
from datetime import date

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""
    
    school_name = serializers.CharField(source='school.name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'phone_number', 
                  'school', 'school_name', 'profile_picture', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """User registration serializer"""
    
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 
                  'role', 'phone_number', 'school']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class SchoolRegistrationSerializer(serializers.Serializer):
    """Serializer for self-registration of a new school and initial admin user"""
    school_name = serializers.CharField(max_length=255)
    admin_email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    levels = serializers.ListField(child=serializers.ChoiceField(choices=[('PRIMARY','PRIMARY'),('JHS','JHS'),('BOTH','BOTH')]), allow_empty=True, required=False)

    first_name = serializers.CharField(max_length=100, required=False, default='Admin')
    last_name = serializers.CharField(max_length=100, required=False, default='User')

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match"})
        if User.objects.filter(email=attrs['admin_email']).exists():
            raise serializers.ValidationError({"admin_email": "Email already in use"})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')
        school_name = validated_data.pop('school_name')
        admin_email = validated_data.pop('admin_email')
        levels = validated_data.pop('levels', ['BOTH'])

        # Create School
        school = School.objects.create(
            name=school_name,
            address='',
            location='',
            phone_number='',
            email=admin_email,
            subscription_plan='FREE'
        )

        # Create initial academic year & term
        today = date.today()
        year_span = f"{today.year}/{today.year+1}" if today.month >= 9 else f"{today.year-1}/{today.year}"
        academic_year = AcademicYear.objects.create(
            school=school,
            name=year_span,
            start_date=date(today.year if today.month>=9 else today.year-1, 9, 1),
            end_date=date(today.year+1 if today.month>=9 else today.year, 7, 31),
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

        # Default grading scale (Ghana style)
        default_grades = [
            ('A', 80, 100, 'Excellent'),
            ('B', 70, 79, 'Very Good'),
            ('C', 60, 69, 'Good'),
            ('D', 50, 59, 'Average'),
            ('E', 40, 49, 'Pass'),
            ('F', 0, 39, 'Fail'),
        ]
        for grade, min_s, max_s, remark in default_grades:
            GradingScale.objects.create(school=school, grade=grade, min_score=min_s, max_score=max_s, remark=remark)

        # Default subjects minimal set
        base_subjects = [
            ('English Language','ENG','BOTH'),
            ('Mathematics','MATH','BOTH'),
            ('Integrated Science','SCI','BOTH'),
            ('Creative Art','ART','BOTH'),
            ('Computing','COMP','BOTH'),
        ]
        for name, code, cat in base_subjects:
            Subject.objects.get_or_create(name=name, code=code, defaults={'category': cat})

        # Create Admin User
        user = User.objects.create_user(
            email=admin_email,
            password=password,
            first_name=validated_data.get('first_name','Admin'),
            last_name=validated_data.get('last_name','User'),
            role='SCHOOL_ADMIN',
            school=school
        )

        return user, school


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer with user data"""
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add custom claims
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'school_id': self.user.school_id if self.user.school else None,
            'school_name': self.user.school.name if self.user.school else None,
        }
        
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer"""
    
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"new_password": "Passwords do not match"})
        return attrs

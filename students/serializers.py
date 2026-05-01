from rest_framework import serializers
from accounts.security_config import SecurityValidator
from .models import Student, Attendance, Behaviour, StudentPromotion, DailyAttendance
from assignments.models import Assignment, StudentAssignment


class StudentAssignmentSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_type = serializers.CharField(source='assignment.assignment_type', read_only=True)
    assignment_due_date = serializers.DateTimeField(source='assignment.due_date', read_only=True)
    assignment_max_score = serializers.IntegerField(source='assignment.max_score', read_only=True)
    subject_name = serializers.CharField(source='assignment.class_subject.subject.name', read_only=True)
    
    class Meta:
        model = StudentAssignment
        fields = ['id', 'assignment_title', 'assignment_type', 'assignment_due_date', 
                 'assignment_max_score', 'subject_name', 'status', 'score', 
                 'teacher_feedback', 'submitted_at', 'graded_at', 'attempts_count']
        read_only_fields = ['id', 'submitted_at', 'graded_at']


class StudentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='current_class.full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class StudentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating students with security validation"""
    generated_password = serializers.CharField(read_only=True)
    generated_username = serializers.CharField(read_only=True)
    parent_account_created = serializers.BooleanField(read_only=True, default=False)
    parent_generated_password = serializers.CharField(read_only=True, allow_null=True, default=None)
    
    class Meta:
        model = Student
        exclude = ['school']
    
    def validate_student_id(self, value):
        """Validate student ID using SecurityValidator"""
        validation = SecurityValidator.validate_student_id(value)
        if not validation['valid']:
            raise serializers.ValidationError(validation['error'])
        return value
    
    def validate_email(self, value):
        """Validate email using SecurityValidator"""
        if value:
            validation = SecurityValidator.validate_email(value)
            if not validation['valid']:
                raise serializers.ValidationError(validation['error'])
        return value
        
    def create(self, validated_data):
        # Check whether the admin wants to create a login account for this student
        request = self.context.get('request')
        create_account = True
        if request:
            raw = request.data.get('create_account', 'true')
            if isinstance(raw, str):
                create_account = raw.lower() not in ('false', '0', 'no')
            else:
                create_account = bool(raw)

        # Manually instantiate so we can set the skip flag before save()
        student = Student(**validated_data)
        if not create_account:
            student._skip_account_creation = True
        student.save()

        # Return the generated credentials in the response
        student.generated_password = student.password if create_account else None
        student.generated_username = student.username if create_account else None
        student.account_created = create_account

        if not create_account:
            student.parent_account_created = False
            student.parent_generated_password = None
            return student

        # ── Auto-create parent account from guardian info ──────────────────
        guardian_email = student.guardian_email
        if guardian_email:
            try:
                from django.contrib.auth import get_user_model
                from accounts.models import ParentStudent
                import secrets, string

                UserModel = get_user_model()

                # Parse guardian_name → first / last
                guardian_name = (student.guardian_name or '').strip()
                parts = guardian_name.split(' ', 1)
                g_first = parts[0] if parts else guardian_name
                g_last = parts[1] if len(parts) > 1 else ''

                existing = UserModel.objects.filter(email=guardian_email).first()
                if existing:
                    # User already exists — just ensure the link exists
                    parent = existing
                    student.parent_account_created = False
                    student.parent_generated_password = None
                else:
                    # Generate a secure random password
                    alphabet = string.ascii_letters + string.digits + '!@#$%'
                    raw_password = ''.join(secrets.choice(alphabet) for _ in range(12))

                    parent = UserModel.objects.create_user(
                        email=guardian_email,
                        password=raw_password,
                        first_name=g_first,
                        last_name=g_last,
                        role='PARENT',
                        school=student.school,
                        phone_number=student.guardian_phone or None,
                    )
                    student.parent_account_created = True
                    student.parent_generated_password = raw_password

                # Create or update the parent–student link
                ParentStudent.objects.get_or_create(
                    parent=parent,
                    student=student,
                    defaults={'relationship': 'Guardian', 'is_primary_guardian': True},
                )
            except Exception:
                # Never let parent creation failure block student creation
                pass

        return student


class BulkStudentUploadSerializer(serializers.Serializer):
    """Serializer for bulk student upload via Excel"""
    file = serializers.FileField()


class DailyAttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    class_name = serializers.CharField(source='class_instance.full_name', read_only=True)
    
    class Meta:
        model = DailyAttendance
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class BulkAttendanceSerializer(serializers.Serializer):
    """Serializer for bulk attendance creation"""
    records = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False
    )


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    term_name = serializers.CharField(source='term.__str__', read_only=True)
    attendance_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class BehaviourSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    term_name = serializers.CharField(source='term.__str__', read_only=True)
    teacher_remarks_templates = serializers.SerializerMethodField()
    
    class Meta:
        model = Behaviour
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_teacher_remarks_templates(self, obj):
        """Return predefined teacher remarks templates"""
        return Behaviour.get_teacher_remarks_templates()


class StudentPromotionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    from_class_name = serializers.CharField(source='from_class.full_name', read_only=True)
    to_class_name = serializers.CharField(source='to_class.full_name', read_only=True)
    
    class Meta:
        model = StudentPromotion
        fields = '__all__'
        read_only_fields = ['promoted_date']

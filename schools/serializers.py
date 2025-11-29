from rest_framework import serializers
from .models import School, AcademicYear, Term, Class, Subject, ClassSubject, GradingScale


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SchoolSettingsSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for school settings and configuration"""
    
    class Meta:
        model = School
        fields = [
            # Basic Information
            'id', 'name', 'address', 'location', 'phone_number', 'email', 
            'logo', 'motto', 'website', 'current_academic_year',
            
            # System Configuration
            'score_entry_mode', 'is_active',
            
            # Report Template Settings
            'report_template', 'report_header_text', 'report_footer_text',
            'show_class_average', 'show_position_in_class', 'show_attendance',
            'show_behavior_comments', 'principal_signature', 
            'class_teacher_signature_required', 'show_student_photos', 
            'show_headteacher_signature',
            
            # Grade Scale
            'grade_scale_a_min', 'grade_scale_b_min', 'grade_scale_c_min',
            'grade_scale_d_min', 'grade_scale_f_min',
            
            # Timestamps
            'updated_at'
        ]
        read_only_fields = ['id', 'updated_at']
        
    def validate_grade_scale(self, attrs):
        """Ensure grade scale values are in logical order"""
        grade_a = attrs.get('grade_scale_a_min', getattr(self.instance, 'grade_scale_a_min', 80))
        grade_b = attrs.get('grade_scale_b_min', getattr(self.instance, 'grade_scale_b_min', 70))
        grade_c = attrs.get('grade_scale_c_min', getattr(self.instance, 'grade_scale_c_min', 60))
        grade_d = attrs.get('grade_scale_d_min', getattr(self.instance, 'grade_scale_d_min', 50))
        grade_f = attrs.get('grade_scale_f_min', getattr(self.instance, 'grade_scale_f_min', 0))
        
        if not (grade_a > grade_b > grade_c > grade_d > grade_f >= 0):
            raise serializers.ValidationError(
                "Grade scale values must be in descending order: A > B > C > D > F >= 0"
            )
        return attrs
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self.validate_grade_scale(attrs)


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'
        read_only_fields = ['created_at']


class TermSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    
    class Meta:
        model = Term
        fields = '__all__'
        read_only_fields = ['created_at']


class ClassSerializer(serializers.ModelSerializer):
    class_teacher_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    level_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = '__all__'
        # 'school' is set from request.user.school in the view; don't require it from the client
        read_only_fields = ['created_at', 'school']
    
    def get_class_teacher_name(self, obj):
        if obj.class_teacher:
            return obj.class_teacher.get_full_name()
        return None
    
    def get_student_count(self, obj):
        return obj.students.filter(is_active=True).count()

    def get_level_display(self, obj):
        try:
            return obj.get_level_display()
        except Exception:
            return obj.level


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
        read_only_fields = ['created_at']


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='class_instance.full_name', read_only=True)
    
    class Meta:
        model = ClassSubject
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name()
        return None


class GradingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingScale
        fields = '__all__'
        read_only_fields = ['created_at']


class BulkAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk assignment operations"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of subject IDs to assign"
    )
    class_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of class IDs to assign subjects to"
    )


class BulkRemovalSerializer(serializers.Serializer):
    """Serializer for bulk removal operations"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of subject IDs to remove"
    )
    class_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of class IDs to remove subjects from"
    )

from rest_framework import serializers
from .models import Student, Attendance, Behaviour, StudentPromotion, DailyAttendance


class StudentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='current_class.full_name', read_only=True)
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = Student
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class StudentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating students"""
    generated_password = serializers.CharField(read_only=True)
    generated_username = serializers.CharField(read_only=True)
    
    class Meta:
        model = Student
        exclude = ['school']
        
    def create(self, validated_data):
        student = super().create(validated_data)
        # Return the generated credentials in the response
        student.generated_password = student.password
        student.generated_username = student.username
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

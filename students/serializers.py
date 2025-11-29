from rest_framework import serializers
from .models import Student, Attendance, Behaviour, StudentPromotion


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
    
    class Meta:
        model = Student
        exclude = ['school']


class BulkStudentUploadSerializer(serializers.Serializer):
    """Serializer for bulk student upload via Excel"""
    file = serializers.FileField()


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
    
    class Meta:
        model = Behaviour
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class StudentPromotionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    from_class_name = serializers.CharField(source='from_class.full_name', read_only=True)
    to_class_name = serializers.CharField(source='to_class.full_name', read_only=True)
    
    class Meta:
        model = StudentPromotion
        fields = '__all__'
        read_only_fields = ['promoted_date']

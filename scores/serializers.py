from rest_framework import serializers
from .models import ContinuousAssessment, ExamScore, SubjectResult, TermResult


class ContinuousAssessmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='class_subject.subject.name', read_only=True)
    total_ca_score = serializers.FloatField(read_only=True)
    
    class Meta:
        model = ContinuousAssessment
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ExamScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='class_subject.subject.name', read_only=True)
    
    class Meta:
        model = ExamScore
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class SubjectResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    subject_name = serializers.CharField(source='class_subject.subject.name', read_only=True)
    
    class Meta:
        model = SubjectResult
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TermResultSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    class_name = serializers.CharField(source='class_instance.full_name', read_only=True)
    term_name = serializers.CharField(source='term.__str__', read_only=True)
    
    class Meta:
        model = TermResult
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ScoreEntrySerializer(serializers.Serializer):
    """Serializer for entering all scores at once"""
    student_id = serializers.IntegerField()
    class_subject_id = serializers.IntegerField()
    term_id = serializers.IntegerField()
    
    # CA Scores
    task = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    homework = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    group_work = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    project_work = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    class_test = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0, max_value=10)
    
    # Exam Score
    exam_score = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=50)

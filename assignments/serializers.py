from rest_framework import serializers
from .models import QuizAnswerFile, QuizAnswer, StudentAssignment, Assignment


class QuizAnswerFileSerializer(serializers.ModelSerializer):
    """Serializer for professional file uploads"""
    
    class Meta:
        model = QuizAnswerFile
        fields = ['id', 'original_filename', 'file_size', 'mime_type', 'uploaded_at', 'file']
        read_only_fields = ['id', 'file_size', 'mime_type', 'uploaded_at']


class QuizAnswerSerializer(serializers.ModelSerializer):
    """Enhanced QuizAnswer serializer with file upload support"""
    uploaded_files = QuizAnswerFileSerializer(many=True, read_only=True)
    
    class Meta:
        model = QuizAnswer
        fields = ['id', 'attempt', 'question', 'selected_option', 'answer_text', 
                 'answer_files', 'is_correct', 'points_earned', 'answered_at', 'uploaded_files']
        read_only_fields = ['id', 'answered_at', 'uploaded_files']


class AssignmentSerializer(serializers.ModelSerializer):
    """Basic assignment serializer"""
    type = serializers.CharField(source='assignment_type', read_only=True)
    
    class Meta:
        model = Assignment
        fields = ['id', 'title', 'description', 'assignment_type', 'type', 'due_date', 'max_score', 'status', 'time_limit']


class StudentAssignmentSerializer(serializers.ModelSerializer):
    """Student assignment serializer"""
    assignment = AssignmentSerializer(read_only=True)
    # Add flattened fields for easier frontend access
    title = serializers.CharField(source='assignment.title', read_only=True)
    type = serializers.CharField(source='assignment.assignment_type', read_only=True)
    due_date = serializers.DateTimeField(source='assignment.due_date', read_only=True)
    time_limit = serializers.IntegerField(source='assignment.time_limit', read_only=True)
    points = serializers.IntegerField(source='assignment.max_score', read_only=True)
    
    class Meta:
        model = StudentAssignment
        fields = [
            'id', 'assignment', 'status', 'score', 'teacher_feedback', 
            'submitted_at', 'graded_at', 'attempts_count',
            # Flattened fields
            'title', 'type', 'due_date', 'time_limit', 'points'
        ]
        read_only_fields = ['id', 'submitted_at', 'graded_at']
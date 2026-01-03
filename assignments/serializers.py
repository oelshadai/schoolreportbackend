from rest_framework import serializers
from .models import Assignment, StudentAssignment, StudentPortalAccess, Question, QuestionOption, AssignmentAttempt
from students.serializers import StudentSerializer
from schools.serializers import ClassSerializer, ClassSubjectSerializer
from schools.models import Term


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ['id', 'option_text', 'is_correct', 'order']


class QuestionSerializer(serializers.ModelSerializer):
    options = QuestionOptionSerializer(many=True, required=False)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_type', 'points', 'order', 'expected_answer', 'case_sensitive', 'options']
    
    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        question = Question.objects.create(**validated_data)
        
        for option_data in options_data:
            QuestionOption.objects.create(question=question, **option_data)
        
        return question


class AssignmentSerializer(serializers.ModelSerializer):
    class_name = serializers.CharField(source='class_instance.full_name', read_only=True)
    subject_name = serializers.CharField(source='class_subject.subject.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    questions = QuestionSerializer(many=True, required=False)
    
    class Meta:
        model = Assignment
        fields = '__all__'
        read_only_fields = ['created_by']
    
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        
        # If no term is provided, use the current active term or first term
        if 'term' not in validated_data or not validated_data['term']:
            class_instance = validated_data.get('class_instance')
            if class_instance and class_instance.school:
                # Try to get current active term or first term
                term = Term.objects.filter(
                    school=class_instance.school,
                    is_current=True
                ).first()
                if not term:
                    term = Term.objects.filter(
                        school=class_instance.school
                    ).first()
                if term:
                    validated_data['term'] = term
        
        assignment = super().create(validated_data)
        
        # Create questions
        for question_data in questions_data:
            options_data = question_data.pop('options', [])
            question = Question.objects.create(assignment=assignment, **question_data)
            
            for option_data in options_data:
                QuestionOption.objects.create(question=question, **option_data)
        
        return assignment


class AssignmentAttemptSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='student_assignment.assignment.title', read_only=True)
    student_name = serializers.CharField(source='student_assignment.student.get_full_name', read_only=True)
    
    class Meta:
        model = AssignmentAttempt
        fields = '__all__'


class StudentAssignmentSerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    assignment_type = serializers.CharField(source='assignment.assignment_type', read_only=True)
    due_date = serializers.DateTimeField(source='assignment.due_date', read_only=True)
    max_score = serializers.IntegerField(source='assignment.max_score', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    assignment = AssignmentSerializer(read_only=True)  # Include full assignment data
    attempts = AssignmentAttemptSerializer(many=True, read_only=True)
    can_attempt = serializers.ReadOnlyField()
    attempts_remaining = serializers.ReadOnlyField()
    
    class Meta:
        model = StudentAssignment
        fields = '__all__'


class StudentPortalAccessSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    
    class Meta:
        model = StudentPortalAccess
        fields = ['id', 'student', 'username', 'is_active', 'last_login', 'student_name', 'student_id']
        read_only_fields = ['password_hash']
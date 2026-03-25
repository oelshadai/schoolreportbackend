"""
MINIMAL Academic Enforcement
Focus: Critical validation only, no over-engineering
"""
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import serializers
from .models import Assignment, StudentAssignment


class AcademicAssignmentSerializer(serializers.ModelSerializer):
    """SINGLE POINT of assignment validation"""
    
    class Meta:
        model = Assignment
        fields = '__all__'
    
    def validate(self, data):
        """Centralized academic validation"""
        assignment_type = data.get('assignment_type')
        class_subject = data.get('class_subject')
        created_by = data.get('created_by') or self.context['request'].user
        
        # CRITICAL: Subject ownership validation
        if class_subject and class_subject.teacher != created_by:
            raise serializers.ValidationError('You do not teach this subject')
        
        # CRITICAL: Type-specific rules
        if assignment_type == 'PROJECT':
            data['allow_file_submission'] = True
            data['max_file_size'] = max(data.get('max_file_size', 10), 10)
        
        if assignment_type in ['QUIZ', 'EXAM']:
            data['is_timed'] = True
            if not data.get('time_limit'):
                data['time_limit'] = 30 if assignment_type == 'QUIZ' else 60
        
        if assignment_type == 'EXAM':
            data['max_attempts'] = 1
        
        return data


class AtomicSubmissionService:
    """SINGLE POINT of submission enforcement"""
    
    @staticmethod
    @transaction.atomic
    def submit_assignment(assignment_id, student, submission_data):
        """Atomic submission with row-level locking"""
        
        # CRITICAL: Lock the row to prevent race conditions
        student_assignment = StudentAssignment.objects.select_for_update().get(
            assignment_id=assignment_id,
            student=student
        )
        
        # CRITICAL: Attempt validation
        if student_assignment.attempts_count >= student_assignment.assignment.max_attempts:
            raise ValidationError(f'Maximum attempts ({student_assignment.assignment.max_attempts}) exceeded')
        
        # CRITICAL: Time validation
        if student_assignment.assignment.is_timed and student_assignment.current_attempt_started_at:
            elapsed = timezone.now() - student_assignment.current_attempt_started_at
            if elapsed.total_seconds() > (student_assignment.assignment.time_limit * 60):
                raise ValidationError('Time limit exceeded')
        
        # CRITICAL: Type-specific validation
        assignment_type = student_assignment.assignment.assignment_type
        
        if assignment_type == 'PROJECT':
            if not submission_data.get('file'):
                raise ValidationError('Projects require file submission')
        
        if assignment_type in ['QUIZ', 'EXAM']:
            if not submission_data.get('answers'):
                raise ValidationError('Quiz/Exam requires answers')
        
        # CRITICAL: Atomic update
        student_assignment.attempts_count += 1
        student_assignment.status = 'SUBMITTED'
        student_assignment.submitted_at = timezone.now()
        
        if submission_data.get('text'):
            student_assignment.submission_text = submission_data['text']
        
        if submission_data.get('file'):
            student_assignment.submission_file = submission_data['file']
        
        student_assignment.save()
        
        return student_assignment


# MINIMAL database constraints (only what's actually enforceable)
MINIMAL_CONSTRAINTS = """
-- Only enforce what database CAN enforce
ALTER TABLE assignments 
ADD CONSTRAINT class_subject_required 
CHECK (class_subject_id IS NOT NULL);

ALTER TABLE assignments 
ADD CONSTRAINT valid_assignment_type 
CHECK (assignment_type IN ('HOMEWORK', 'PROJECT', 'QUIZ', 'EXAM'));

ALTER TABLE assignments 
ADD CONSTRAINT positive_max_score 
CHECK (max_score > 0);
"""
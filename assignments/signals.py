"""
Academic Enforcement Signals
Automatic validation and enforcement
"""
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Assignment, StudentAssignment, QuizAttempt


@receiver(pre_save, sender=Assignment)
def enforce_academic_assignment_rules(sender, instance, **kwargs):
    """Enforce academic rules before saving assignment"""
    
    # Validate teacher owns the subject
    if instance.class_subject and instance.created_by:
        if instance.class_subject.teacher != instance.created_by:
            raise ValidationError('Teacher does not own this subject')
    
    # Type-specific enforcement
    if instance.assignment_type == 'PROJECT':
        instance.allow_file_submission = True
        if instance.max_file_size < 10:
            instance.max_file_size = 50  # Projects need larger files
    
    if instance.assignment_type in ['QUIZ', 'EXAM']:
        instance.is_timed = True
        if not instance.time_limit:
            instance.time_limit = 30 if instance.assignment_type == 'QUIZ' else 60
    
    if instance.assignment_type == 'EXAM':
        instance.max_attempts = 1
        instance.show_results_immediately = False


@receiver(post_save, sender=Assignment)
def create_student_assignments(sender, instance, created, **kwargs):
    """Auto-create student assignments when published"""
    if instance.status == 'PUBLISHED' and created:
        students = instance.class_instance.students.all()
        for student in students:
            StudentAssignment.objects.get_or_create(
                assignment=instance,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )


@receiver(pre_save, sender=StudentAssignment)
def enforce_student_assignment_rules(sender, instance, **kwargs):
    """Enforce academic rules on student assignments"""
    
    # Prevent status changes if locked
    if instance.pk:  # Existing record
        old_instance = StudentAssignment.objects.get(pk=instance.pk)
        if old_instance.is_locked and instance.status != old_instance.status:
            if instance.status not in ['SUBMITTED', 'EXPIRED']:
                raise ValidationError('Cannot modify locked assignment')
    
    # Validate attempt limits
    if instance.attempts_count > instance.assignment.max_attempts:
        raise ValidationError('Attempt limit exceeded')
    
    # Auto-lock exams when started
    if (instance.assignment.assignment_type == 'EXAM' and 
        instance.status == 'IN_PROGRESS' and 
        instance.current_attempt_started_at):
        instance.is_locked = True


@receiver(post_save, sender=QuizAttempt)
def auto_grade_quiz(sender, instance, created, **kwargs):
    """Auto-grade quiz attempts"""
    if created and instance.assignment.auto_grade:
        instance.calculate_score()
        
        # Update student assignment
        student_assignment = StudentAssignment.objects.get(
            assignment=instance.assignment,
            student=instance.student
        )
        student_assignment.score = instance.score
        student_assignment.save()
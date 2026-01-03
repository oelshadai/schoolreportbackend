from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Assignment, StudentAssignment
from students.models import Student


@receiver(post_save, sender=Assignment)
def create_student_assignments(sender, instance, created, **kwargs):
    """
    Automatically create StudentAssignment records when an assignment is published
    """
    # Only create student assignments for published assignments
    if instance.status == 'PUBLISHED':
        # Get all active students in the assignment's class
        students = Student.objects.filter(
            current_class=instance.class_instance,
            is_active=True
        )
        
        print(f"Signal: Creating student assignments for '{instance.title}' - {students.count()} students")
        
        created_count = 0
        for student in students:
            student_assignment, was_created = StudentAssignment.objects.get_or_create(
                assignment=instance,
                student=student,
                defaults={'status': 'NOT_STARTED'}
            )
            if was_created:
                created_count += 1
        
        print(f"Signal: Created {created_count} new student assignments")


@receiver(pre_save, sender=Assignment)
def handle_assignment_status_change(sender, instance, **kwargs):
    """
    Handle when assignment status changes from DRAFT to PUBLISHED
    """
    if instance.pk:  # Only for existing assignments
        try:
            old_instance = Assignment.objects.get(pk=instance.pk)
            # If status changed from DRAFT to PUBLISHED, the post_save signal will handle student assignment creation
            if old_instance.status == 'DRAFT' and instance.status == 'PUBLISHED':
                print(f"Assignment '{instance.title}' is being published - student assignments will be created")
        except Assignment.DoesNotExist:
            pass
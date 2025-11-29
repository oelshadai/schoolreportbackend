from django.db import models
from django.contrib.auth import get_user_model
from schools.models import School, Subject, Class

User = get_user_model()


class Teacher(models.Model):
    """Teacher Profile Model - extends User model with teaching-specific fields"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='teacher_profile')
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='teachers')
    employee_id = models.CharField(max_length=50, unique=True)
    
    # Teaching Specializations
    specializations = models.ManyToManyField(
        Subject, 
        blank=True, 
        related_name='specialized_teachers',
        help_text='Subjects this teacher specializes in'
    )
    
    # Employment Details
    hire_date = models.DateField()
    qualification = models.CharField(max_length=200, blank=True)
    experience_years = models.PositiveIntegerField(default=0)
    
    # Contact and Personal
    emergency_contact = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    
    # Status
    is_class_teacher = models.BooleanField(
        default=False,
        help_text='True if this teacher is assigned as class teacher to any class'
    )
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teachers'
        ordering = ['user__last_name', 'user__first_name']
        unique_together = ['school', 'employee_id']
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_assigned_classes(self):
        """Get classes where this teacher is the class teacher"""
        return Class.objects.filter(class_teacher=self.user)
    
    def get_teaching_subjects(self):
        """Get subjects this teacher is assigned to teach"""
        from schools.models import ClassSubject
        return ClassSubject.objects.filter(teacher=self.user)
    
    def can_enter_scores_for_subject(self, class_subject):
        """Check if teacher can enter scores for a specific class-subject combination"""
        # Class teachers can enter scores for all subjects in their classes
        if class_subject.class_instance.class_teacher == self.user:
            return True
        
        # Subject teachers can enter scores for subjects they're assigned to teach
        if class_subject.teacher == self.user:
            return True
            
        return False
    
    def save(self, *args, **kwargs):
        # Ensure user role is set to TEACHER
        if self.user.role != 'TEACHER':
            self.user.role = 'TEACHER'
            self.user.save()
        
        # Update is_class_teacher flag
        self.is_class_teacher = self.get_assigned_classes().exists()
        
        super().save(*args, **kwargs)
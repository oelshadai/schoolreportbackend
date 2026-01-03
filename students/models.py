from django.db import models
from django.conf import settings
from schools.models import School, Class, Term
import secrets
import string


class Student(models.Model):
    """Student Model"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='students')
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='student_profile')
    student_id = models.CharField(max_length=50, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    current_class = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    
    # Login credentials
    username = models.CharField(max_length=50, unique=True, null=True, blank=True)
    password = models.CharField(max_length=20, null=True, blank=True)  # Store plain text for display
    
    # Parent/Guardian Information
    guardian_name = models.CharField(max_length=200)
    guardian_phone = models.CharField(max_length=15)
    guardian_email = models.EmailField(blank=True, null=True)
    guardian_address = models.TextField()
    
    # Student Photo
    photo = models.FileField(upload_to='student_photos/', null=True, blank=True)
    
    # Enrollment
    admission_date = models.DateField()
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'students'
        ordering = ['last_name', 'first_name']
        unique_together = ['school', 'student_id']
    
    def __str__(self):
        return f"{self.student_id} - {self.get_full_name()}"
    
    def get_full_name(self):
        if self.other_names:
            return f"{self.first_name} {self.other_names} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        # Auto-generate credentials on creation
        if not self.username:
            self.username = f"std_{self.student_id}"
        if not self.password:
            self.password = self.generate_password()
        
        # Create Django user for authentication only if user doesn't exist
        if not self.user and not self.pk:  # Only on creation
            from django.contrib.auth import get_user_model
            User = get_user_model()
            # Create email using student ID and school domain
            school_domain = self.school.name.lower().replace(' ', '').replace('-', '') if self.school else 'school'
            email = f"{self.username}@{school_domain}.edu"
            
            try:
                user = User.objects.create_user(
                    email=email,
                    password=self.password,
                    first_name=self.first_name,
                    last_name=self.last_name
                )
                # Set role and school if the User model supports it
                if hasattr(user, 'role'):
                    user.role = 'STUDENT'
                if hasattr(user, 'school') and self.school:
                    user.school = self.school
                user.save()
                self.user = user
            except Exception as e:
                # Log the error but don't fail the student creation
                print(f"Warning: Could not create user account for student {self.student_id}: {e}")
        
        super().save(*args, **kwargs)
    
    def generate_password(self):
        """Generate a simple 6-character password"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Attendance(models.Model):
    """Student Attendance Model (Term-based summary)"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='attendance_records')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='attendance_records')
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    times_late = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'attendance'
        unique_together = ['student', 'term']
        ordering = ['-term__start_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.term}"
    
    @property
    def total_days(self):
        return self.days_present + self.days_absent
    
    @property
    def attendance_percentage(self):
        total = self.total_days
        if total == 0:
            return 0
        return round((self.days_present / total) * 100, 2)


class DailyAttendance(models.Model):
    """Daily Attendance Model for tracking daily attendance"""
    
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='daily_attendance')
    class_instance = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='daily_attendance')
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='absent')
    marked_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'daily_attendance'
        unique_together = ['student', 'date']
        ordering = ['-date', 'student__last_name', 'student__first_name']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.date} - {self.get_status_display()}"


class Behaviour(models.Model):
    """Student Behaviour/Conduct Model"""
    
    RATING_CHOICES = [
        ('EXCELLENT', 'Excellent'),
        ('VERY_GOOD', 'Very Good'),
        ('GOOD', 'Good'),
        ('SATISFACTORY', 'Satisfactory'),
        ('NEEDS_IMPROVEMENT', 'Needs Improvement'),
    ]
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='behaviour_records')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='behaviour_records')
    
    # Conduct Ratings
    conduct = models.CharField(max_length=20, choices=RATING_CHOICES, default='GOOD')
    attitude = models.CharField(max_length=20, choices=RATING_CHOICES, default='GOOD')
    interest = models.CharField(max_length=20, choices=RATING_CHOICES, default='GOOD')
    punctuality = models.CharField(max_length=20, choices=RATING_CHOICES, default='GOOD')
    
    # Additional Notes
    remarks = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'behaviour'
        unique_together = ['student', 'term']
        ordering = ['-term__start_date']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.term}"


class StudentPromotion(models.Model):
    """Student Promotion/Graduation Model"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='promotions')
    from_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='promoted_from')
    to_class = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='promoted_to', null=True, blank=True)
    academic_year = models.ForeignKey('schools.AcademicYear', on_delete=models.CASCADE)
    is_graduated = models.BooleanField(default=False)
    promoted_date = models.DateField(auto_now_add=True)
    remarks = models.TextField(blank=True)
    
    class Meta:
        db_table = 'student_promotions'
        ordering = ['-promoted_date']
    
    def __str__(self):
        if self.is_graduated:
            return f"{self.student.get_full_name()} - Graduated from {self.from_class}"
        return f"{self.student.get_full_name()} - {self.from_class} to {self.to_class}"

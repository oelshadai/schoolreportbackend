from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from students.models import Student
from schools.models import ClassSubject, Term, GradingScale


class ContinuousAssessment(models.Model):
    """Continuous Assessment (CA) Scores - 50% of total"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='ca_scores')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='ca_scores')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='ca_scores')
    
    # 5 Components (Max 10 each = 50 total)
    task = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Task/Exercise (Max 10)"
    )
    homework = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Homework/Assignment (Max 10)"
    )
    group_work = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Group Work (Max 10)"
    )
    project_work = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Project Work (Max 10)"
    )
    class_test = models.DecimalField(
        max_digits=4, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Class Test (Max 10)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'continuous_assessments'
        unique_together = ['student', 'class_subject', 'term']
        ordering = ['student', 'class_subject']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_subject.subject.name} - {self.term}"
    
    @property
    def total_ca_score(self):
        """Calculate total CA score (max 50)"""
        return self.task + self.homework + self.group_work + self.project_work + self.class_test


class ExamScore(models.Model):
    """Exam Scores - 50% of total"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='exam_scores')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='exam_scores')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='exam_scores')
    
    score = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(50)],
        help_text="Exam Score (Max 50)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exam_scores'
        unique_together = ['student', 'class_subject', 'term']
        ordering = ['student', 'class_subject']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_subject.subject.name} - {self.term}"


class SubjectResult(models.Model):
    """Computed Subject Result (CA + Exam = Total)"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='subject_results')
    class_subject = models.ForeignKey(ClassSubject, on_delete=models.CASCADE, related_name='results')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='subject_results')
    
    ca_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    exam_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    grade = models.CharField(max_length=5, blank=True)
    remark = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'subject_results'
        unique_together = ['student', 'class_subject', 'term']
        ordering = ['student', 'class_subject']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.class_subject.subject.name} - {self.total_score}"
    
    def calculate_total(self):
        """Calculate total score and assign grade"""
        self.total_score = self.ca_score + self.exam_score
        self.assign_grade()
        self.save()
    
    def assign_grade(self):
        """Assign grade based on school's grading scale"""
        try:
            grading_scale = GradingScale.objects.filter(
                school=self.student.school,
                min_score__lte=self.total_score,
                max_score__gte=self.total_score
            ).first()
            
            if grading_scale:
                self.grade = grading_scale.grade
                self.remark = grading_scale.remark
            else:
                # Default grading if no scale found
                if self.total_score >= 80:
                    self.grade = 'A'
                    self.remark = 'Excellent'
                elif self.total_score >= 70:
                    self.grade = 'B'
                    self.remark = 'Very Good'
                elif self.total_score >= 60:
                    self.grade = 'C'
                    self.remark = 'Good'
                elif self.total_score >= 50:
                    self.grade = 'D'
                    self.remark = 'Satisfactory'
                elif self.total_score >= 40:
                    self.grade = 'E'
                    self.remark = 'Pass'
                else:
                    self.grade = 'F'
                    self.remark = 'Fail'
        except Exception as e:
            print(f"Error assigning grade: {e}")


class TermResult(models.Model):
    """Overall Term Result for a Student"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='term_results')
    term = models.ForeignKey(Term, on_delete=models.CASCADE, related_name='term_results')
    class_instance = models.ForeignKey('schools.Class', on_delete=models.CASCADE, related_name='term_results')
    
    # Aggregate Scores
    total_score = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    average_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subjects_count = models.IntegerField(default=0)
    
    # Class Position
    class_position = models.IntegerField(null=True, blank=True)
    total_students = models.IntegerField(default=0)
    
    # Teacher's Comments
    teacher_remarks = models.TextField(blank=True)
    principal_remarks = models.TextField(blank=True)
    
    # Promotion
    promoted = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'term_results'
        unique_together = ['student', 'term']
        ordering = ['-term__start_date', '-average_score']
    
    def __str__(self):
        return f"{self.student.get_full_name()} - {self.term} - Position: {self.class_position}"
    
    def calculate_aggregate(self):
        """Calculate total and average scores"""
        subject_results = SubjectResult.objects.filter(
            student=self.student,
            term=self.term
        )
        
        self.subjects_count = subject_results.count()
        if self.subjects_count > 0:
            self.total_score = sum([result.total_score for result in subject_results])
            self.average_score = self.total_score / self.subjects_count
        else:
            self.total_score = 0
            self.average_score = 0
        
        self.save()
    
    def generate_teacher_remarks(self):
        """Auto-generate teacher remarks based on performance"""
        avg = float(self.average_score)
        
        if avg >= 80:
            remarks = [
                "Excellent performance! Keep up the outstanding work.",
                "Outstanding achievement in all subjects.",
                "Exceptional student with excellent results.",
            ]
        elif avg >= 70:
            remarks = [
                "Very good performance. Well done!",
                "Commendable effort and good results.",
                "Good work. Keep striving for excellence.",
            ]
        elif avg >= 60:
            remarks = [
                "Good performance. There's room for improvement.",
                "Satisfactory work. Encourage more effort.",
                "Fair results. Can do better with more focus.",
            ]
        elif avg >= 50:
            remarks = [
                "Needs to put in more effort to improve.",
                "Average performance. Requires more dedication.",
                "Should work harder to achieve better results.",
            ]
        else:
            remarks = [
                "Needs significant improvement. Encourage extra classes.",
                "Weak performance. Requires urgent attention and support.",
                "Must work very hard to improve in all subjects.",
            ]
        
        import random
        self.teacher_remarks = random.choice(remarks)
        self.save()

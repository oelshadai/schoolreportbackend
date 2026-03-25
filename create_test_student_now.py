import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from students.models import Student
from schools.models import School, Class as SchoolClass
from django.contrib.auth import get_user_model

User = get_user_model()

# Get or create school
school, _ = School.objects.get_or_create(
    name='Test School',
    defaults={'subscription_plan': 'BASIC'}
)

# Get or create class
school_class, _ = SchoolClass.objects.get_or_create(
    level='Grade 9',
    school=school
)

# Create student
student, created = Student.objects.get_or_create(
    student_id='std_STD001',
    defaults={
        'first_name': 'John',
        'last_name': 'Doe',
        'password': 'password',
        'school': school,
        'current_class': school_class
    }
)

if created:
    print(f"✅ Created student: {student.student_id}")
else:
    student.password = 'password'
    student.save()
    print(f"✅ Updated student: {student.student_id}")

print(f"Login with: {student.student_id} / password")

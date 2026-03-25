from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix student user accounts with incorrect roles'

    def handle(self, *args, **options):
        self.stdout.write('Fixing student user accounts...')
        
        # Find all students with user accounts
        students_with_users = Student.objects.filter(user__isnull=False).select_related('user')
        
        fixed_count = 0
        for student in students_with_users:
            user = student.user
            if user.role != 'STUDENT':
                self.stdout.write(f'Fixing user {user.email} - changing role from {user.role} to STUDENT')
                user.role = 'STUDENT'
                user.save(update_fields=['role'])
                fixed_count += 1
        
        # Find students without user accounts and create them
        students_without_users = Student.objects.filter(user__isnull=True)
        created_count = 0
        
        for student in students_without_users:
            try:
                # Create email using student ID and school domain
                school_domain = student.school.name.lower().replace(' ', '').replace('-', '') if student.school else 'school'
                email = f"std_{student.student_id}@{school_domain}.edu"
                
                # Check if user with this email already exists
                if User.objects.filter(email=email).exists():
                    self.stdout.write(f'User with email {email} already exists, skipping...')
                    continue
                
                user = User.objects.create_user(
                    email=email,
                    password=student.password or 'temp123',
                    first_name=student.first_name,
                    last_name=student.last_name,
                    role='STUDENT',
                    school=student.school
                )
                student.user = user
                student.save(update_fields=['user'])
                created_count += 1
                self.stdout.write(f'Created user account for student {student.student_id}')
                
            except Exception as e:
                self.stdout.write(f'Failed to create user for student {student.student_id}: {e}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully fixed {fixed_count} student user roles and created {created_count} new user accounts'
            )
        )
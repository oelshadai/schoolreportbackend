from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from students.models import Student

User = get_user_model()

class Command(BaseCommand):
    help = 'Fix student user accounts - create missing accounts and fix roles'

    def handle(self, *args, **options):
        self.stdout.write('Fixing student user accounts...')
        
        # Find all students with user accounts and fix roles
        students_with_users = Student.objects.filter(user__isnull=False).select_related('user')
        
        fixed_count = 0
        for student in students_with_users:
            user = student.user
            changed = False
            if user.role != 'STUDENT':
                self.stdout.write(f'Fixing user {user.email} - changing role from {user.role} to STUDENT')
                user.role = 'STUDENT'
                changed = True
            if not user.is_active:
                user.is_active = True
                changed = True
            if student.school and user.school != student.school:
                user.school = student.school
                changed = True
            if changed:
                user.save()
                fixed_count += 1
        
        # Find students without user accounts and create them
        students_without_users = Student.objects.filter(user__isnull=True)
        created_count = 0
        
        for student in students_without_users:
            try:
                # Generate username/password if missing
                if not student.username:
                    student.username = f"std_{student.student_id}"
                if not student.password:
                    student.password = student.generate_password()
                    
                # Create email using student ID and school domain
                school_domain = student.school.name.lower().replace(' ', '').replace('-', '') if student.school else 'school'
                email = f"{student.username}@{school_domain}.edu"
                
                # Ensure email uniqueness
                counter = 1
                base_email = email
                while User.objects.filter(email=email).exists():
                    email = f"{student.username}_{counter}@{school_domain}.edu"
                    counter += 1
                
                user = User.objects.create_user(
                    email=email,
                    password=student.password,
                    first_name=student.first_name,
                    last_name=student.last_name,
                    role='STUDENT',
                    school=student.school,
                )
                student.user = user
                student.save(update_fields=['user', 'username', 'password'])
                created_count += 1
                self.stdout.write(self.style.SUCCESS(
                    f'Created user for {student.first_name} {student.last_name} (ID: {student.student_id}, login: {student.username})'
                ))
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to create user for {student.student_id}: {e}'))
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Done: fixed {fixed_count} existing users, created {created_count} new user accounts'
            )
        )
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import date, timedelta
from schools.models import School, AcademicYear, Term


class Command(BaseCommand):
    help = 'Setup default academic years and terms for schools'

    def add_arguments(self, parser):
        parser.add_argument(
            '--school-id',
            type=int,
            help='Setup for specific school ID (optional)',
        )

    def handle(self, *args, **options):
        school_id = options.get('school_id')
        
        if school_id:
            schools = School.objects.filter(id=school_id)
            if not schools.exists():
                self.stdout.write(
                    self.style.ERROR(f'School with ID {school_id} not found')
                )
                return
        else:
            schools = School.objects.all()

        current_year = timezone.now().year
        
        for school in schools:
            self.stdout.write(f'Setting up academic data for {school.name}...')
            
            # Create current academic year
            academic_year_name = f"{current_year}/{current_year + 1}"
            academic_year, created = AcademicYear.objects.get_or_create(
                school=school,
                name=academic_year_name,
                defaults={
                    'start_date': date(current_year, 9, 1),
                    'end_date': date(current_year + 1, 7, 31),
                    'is_current': True
                }
            )
            
            if created:
                self.stdout.write(f'  Created academic year: {academic_year_name}')
            else:
                self.stdout.write(f'  Academic year already exists: {academic_year_name}')
            
            # Create terms
            terms_data = [
                {
                    'name': 'FIRST',
                    'start_date': date(current_year, 9, 1),
                    'end_date': date(current_year, 12, 15),
                    'total_days': 90,
                    'is_current': True
                },
                {
                    'name': 'SECOND', 
                    'start_date': date(current_year + 1, 1, 8),
                    'end_date': date(current_year + 1, 4, 15),
                    'total_days': 85,
                    'is_current': False
                },
                {
                    'name': 'THIRD',
                    'start_date': date(current_year + 1, 4, 22),
                    'end_date': date(current_year + 1, 7, 31),
                    'total_days': 80,
                    'is_current': False
                }
            ]
            
            for term_data in terms_data:
                term, created = Term.objects.get_or_create(
                    academic_year=academic_year,
                    name=term_data['name'],
                    defaults=term_data
                )
                
                if created:
                    self.stdout.write(f'  Created term: {term_data["name"]}')
                else:
                    self.stdout.write(f'  Term already exists: {term_data["name"]}')
            
            # Update school's current academic year if not set
            if not school.current_academic_year:
                school.current_academic_year = academic_year_name
                school.save()
                self.stdout.write(f'  Updated school current academic year')
        
        self.stdout.write(
            self.style.SUCCESS('Successfully setup academic years and terms')
        )
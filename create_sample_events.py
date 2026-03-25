#!/usr/bin/env python
import os
import sys
import django
from datetime import datetime, date, time, timedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from events.models import Event
from schools.models import School
from accounts.models import User

def create_sample_events():
    try:
        # Get first school and user
        school = School.objects.first()
        user = User.objects.filter(is_staff=True).first()
        
        if not school or not user:
            print("No school or admin user found. Please create them first.")
            return
            
        print(f"Creating events for school: {school.name}")
        
        # Sample events data
        events_data = [
            {
                'title': 'Science Fair 2024',
                'description': 'Annual science fair showcasing student projects and innovations.',
                'date': date.today() + timedelta(days=7),
                'time': time(9, 0),
                'location': 'Main Hall',
                'type': 'academic',
                'attendees': 150,
                'status': 'confirmed'
            },
            {
                'title': 'Inter-House Sports Competition',
                'description': 'Annual sports competition between different houses.',
                'date': date.today() + timedelta(days=14),
                'time': time(8, 0),
                'location': 'Sports Complex',
                'type': 'sports',
                'attendees': 300,
                'status': 'confirmed'
            },
            {
                'title': 'Cultural Day Celebration',
                'description': 'Celebrating diverse cultures with performances and exhibitions.',
                'date': date.today() + timedelta(days=21),
                'time': time(10, 0),
                'location': 'School Auditorium',
                'type': 'cultural',
                'attendees': 200,
                'status': 'planned'
            },
            {
                'title': 'Parent-Teacher Meeting',
                'description': 'Quarterly meeting to discuss student progress.',
                'date': date.today() + timedelta(days=10),
                'time': time(14, 0),
                'location': 'Conference Room',
                'type': 'meeting',
                'attendees': 80,
                'status': 'confirmed'
            },
            {
                'title': 'Mid-Term Examinations',
                'description': 'Mid-term examinations for all classes.',
                'date': date.today() + timedelta(days=28),
                'time': time(8, 30),
                'location': 'Examination Hall',
                'type': 'exam',
                'attendees': 500,
                'status': 'planned'
            },
            {
                'title': 'Independence Day Holiday',
                'description': 'National holiday - School closed.',
                'date': date.today() + timedelta(days=35),
                'time': time(0, 0),
                'location': 'N/A',
                'type': 'holiday',
                'attendees': 0,
                'status': 'confirmed'
            }
        ]
        
        # Create events
        created_count = 0
        for event_data in events_data:
            event, created = Event.objects.get_or_create(
                title=event_data['title'],
                school=school,
                defaults={
                    **event_data,
                    'created_by': user
                }
            )
            if created:
                created_count += 1
                print(f"Created event: {event.title}")
            else:
                print(f"Event already exists: {event.title}")
        
        print(f"\nSample events creation completed!")
        print(f"Created {created_count} new events")
        print(f"Total events in database: {Event.objects.count()}")
        
    except Exception as e:
        print(f"Error creating sample events: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    create_sample_events()
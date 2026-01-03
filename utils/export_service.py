import json
import csv
from django.http import HttpResponse
from django.core import serializers
from django.apps import apps
from datetime import datetime
import zipfile
import io

class DataExportService:
    @staticmethod
    def export_students_csv(school):
        """Export students data as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="students_{school.name}_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Student ID', 'First Name', 'Last Name', 'Gender', 'Date of Birth',
            'Current Class', 'Guardian Name', 'Guardian Phone', 'Guardian Email',
            'Admission Date', 'Status'
        ])
        
        for student in school.students.all():
            writer.writerow([
                student.student_id,
                student.first_name,
                student.last_name,
                student.get_gender_display(),
                student.date_of_birth,
                student.current_class.level if student.current_class else 'N/A',
                student.guardian_name,
                student.guardian_phone,
                student.guardian_email or 'N/A',
                student.admission_date,
                'Active' if student.is_active else 'Inactive'
            ])
        
        return response
    
    @staticmethod
    def export_teachers_csv(school):
        """Export teachers data as CSV"""
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="teachers_{school.name}_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Employee ID', 'First Name', 'Last Name', 'Email', 'Phone',
            'Subjects', 'Classes', 'Hire Date', 'Status'
        ])
        
        for teacher in school.teachers.all():
            subjects = ', '.join([s.name for s in teacher.subjects.all()])
            classes = ', '.join([c.level for c in teacher.classes_taught.all()])
            
            writer.writerow([
                teacher.employee_id,
                teacher.user.first_name,
                teacher.user.last_name,
                teacher.user.email,
                teacher.phone_number,
                subjects,
                classes,
                teacher.hire_date,
                'Active' if teacher.is_active else 'Inactive'
            ])
        
        return response
    
    @staticmethod
    def export_school_backup(school):
        """Export complete school data as JSON backup"""
        backup_data = {
            'school_info': {
                'name': school.name,
                'address': school.address,
                'phone': school.phone_number,
                'email': school.email,
                'export_date': datetime.now().isoformat()
            },
            'students': [],
            'teachers': [],
            'classes': [],
            'subjects': [],
            'assignments': [],
            'scores': []
        }
        
        # Export students
        for student in school.students.all():
            backup_data['students'].append({
                'student_id': student.student_id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'gender': student.gender,
                'date_of_birth': student.date_of_birth.isoformat(),
                'current_class': student.current_class.level if student.current_class else None,
                'guardian_name': student.guardian_name,
                'guardian_phone': student.guardian_phone,
                'guardian_email': student.guardian_email,
                'admission_date': student.admission_date.isoformat(),
                'is_active': student.is_active
            })
        
        # Export teachers
        for teacher in school.teachers.all():
            backup_data['teachers'].append({
                'employee_id': teacher.employee_id,
                'first_name': teacher.user.first_name,
                'last_name': teacher.user.last_name,
                'email': teacher.user.email,
                'phone': teacher.phone_number,
                'hire_date': teacher.hire_date.isoformat(),
                'is_active': teacher.is_active
            })
        
        # Export classes
        for cls in school.classes.all():
            backup_data['classes'].append({
                'level': cls.level,
                'section': cls.section,
                'capacity': cls.capacity,
                'class_teacher': cls.class_teacher.employee_id if cls.class_teacher else None
            })
        
        response = HttpResponse(
            json.dumps(backup_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="school_backup_{school.name}_{datetime.now().strftime("%Y%m%d")}.json"'
        
        return response
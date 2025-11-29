from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def send_teacher_welcome_email(teacher, password, assigned_class=None, subjects=None):
    """
    Send welcome email to newly created teacher with login credentials and assignments
    
    Args:
        teacher: Teacher instance
        password: Plain text password for the teacher
        assigned_class: Class instance if teacher is assigned as form/class teacher
        subjects: List of Subject instances if teacher has subject specializations
    """
    try:
        # Prepare context for email template
        context = {
            'teacher': teacher,
            'school': teacher.school,
            'email': teacher.user.email,
            'password': password,
            'login_url': f"{settings.FRONTEND_URL}/login" if hasattr(settings, 'FRONTEND_URL') else "https://elitetechreport.netlify.app/login",
            'assigned_class': assigned_class,
            'subjects': subjects or [],
        }
        
        # Render email template
        subject = f'Welcome to {teacher.school.name} - Your Teaching Account Details'
        html_message = render_to_string('emails/teacher_welcome.html', context)
        plain_message = strip_tags(html_message)
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.user.email],
            fail_silently=False,
        )
        
        logger.info(f"Welcome email sent successfully to teacher: {teacher.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send welcome email to teacher {teacher.user.email}: {str(e)}")
        return False


def send_teacher_assignment_email(teacher, assignment_type, assignment_details):
    """
    Send email notification when teacher gets new assignments
    
    Args:
        teacher: Teacher instance
        assignment_type: 'class_teacher' or 'subject_teacher'
        assignment_details: Dict with assignment information
    """
    try:
        context = {
            'teacher': teacher,
            'school': teacher.school,
            'assignment_type': assignment_type,
            'assignment_details': assignment_details,
        }
        
        subject = f'New Teaching Assignment - {teacher.school.name}'
        html_message = render_to_string('emails/teacher_assignment.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher.user.email],
            fail_silently=False,
        )
        
        logger.info(f"Assignment email sent successfully to teacher: {teacher.user.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send assignment email to teacher {teacher.user.email}: {str(e)}")
        return False
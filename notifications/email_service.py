from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def send_password_reset(user, new_password):
        """Send password reset email"""
        try:
            subject = 'Password Reset - School Management System'
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4f46e5;">Password Reset</h2>
                <p>Hello {user.first_name},</p>
                <p>Your password has been reset. Your new temporary password is:</p>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin: 0; color: #1f2937; font-family: monospace;">{new_password}</h3>
                </div>
                <p><strong>Important:</strong> Please login and change your password immediately for security.</p>
                <p>If you didn't request this reset, please contact your administrator.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">School Management System</p>
            </div>
            """
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [user.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            return False
    
    @staticmethod
    def send_student_credentials(student, password):
        """Send student login credentials to guardian"""
        try:
            subject = 'Student Portal Access - School Management System'
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4f46e5;">Student Portal Access</h2>
                <p>Dear {student.guardian_name},</p>
                <p>Your child <strong>{student.get_full_name()}</strong> has been enrolled in our school management system.</p>
                
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">Login Credentials:</h3>
                    <p><strong>Username:</strong> {student.username}</p>
                    <p><strong>Password:</strong> {password}</p>
                    <p><strong>Portal URL:</strong> {settings.FRONTEND_URL}/student-portal</p>
                </div>
                
                <p>Your child can use these credentials to:</p>
                <ul>
                    <li>View and submit assignments</li>
                    <li>Join virtual classes</li>
                    <li>Take interactive quizzes</li>
                    <li>Check grades and progress</li>
                </ul>
                
                <p><strong>Note:</strong> Please help your child change the password on first login.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">School Management System</p>
            </div>
            """
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(
                subject, 
                text_content, 
                settings.DEFAULT_FROM_EMAIL, 
                [student.guardian_email] if student.guardian_email else []
            )
            email.attach_alternative(html_content, "text/html")
            email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send student credentials email: {e}")
            return False
    
    @staticmethod
    def send_assignment_notification(assignment, students):
        """Send assignment notification to students"""
        try:
            subject = f'New Assignment: {assignment.title}'
            
            for student in students:
                if student.guardian_email:
                    html_content = f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2 style="color: #4f46e5;">New Assignment</h2>
                        <p>Dear {student.guardian_name},</p>
                        <p>A new assignment has been posted for <strong>{student.get_full_name()}</strong>:</p>
                        
                        <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="margin: 0 0 10px 0;">{assignment.title}</h3>
                            <p><strong>Subject:</strong> {assignment.subject.name}</p>
                            <p><strong>Due Date:</strong> {assignment.due_date.strftime('%B %d, %Y at %I:%M %p')}</p>
                            <p><strong>Type:</strong> {assignment.assignment_type}</p>
                        </div>
                        
                        <p>Please remind your child to complete and submit the assignment on time.</p>
                        <p><strong>Student Portal:</strong> {settings.FRONTEND_URL}/student-portal</p>
                        
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                        <p style="color: #6b7280; font-size: 12px;">School Management System</p>
                    </div>
                    """
                    text_content = strip_tags(html_content)
                    
                    email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [student.guardian_email])
                    email.attach_alternative(html_content, "text/html")
                    email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send assignment notification: {e}")
            return False
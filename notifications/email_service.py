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
    
    @staticmethod
    def send_report_published(report_card):
        """Notify guardian/parent that a report card has been published."""
        try:
            student = report_card.student
            recipients = []
            if student.guardian_email:
                recipients.append(student.guardian_email)
            # Also notify linked parent user accounts
            from accounts.models import ParentStudent
            parent_emails = list(
                ParentStudent.objects.filter(student=student)
                .values_list('parent__email', flat=True)
            )
            for email in parent_emails:
                if email and email not in recipients:
                    recipients.append(email)
            if not recipients:
                return False
            term_name = str(report_card.term)
            subject = f'Report Card Available – {student.get_full_name()} | {term_name}'
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4f46e5;">Report Card Published</h2>
                <p>Dear {student.guardian_name},</p>
                <p>The report card for <strong>{student.get_full_name()}</strong> for <strong>{term_name}</strong> has been published and is now available to view.</p>
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>Student:</strong> {student.get_full_name()}</p>
                    <p style="margin: 8px 0 0;"><strong>Term:</strong> {term_name}</p>
                    <p style="margin: 8px 0 0;"><strong>Report Code:</strong> {report_card.report_code}</p>
                </div>
                <p>Log in to the student portal to view the full report card.</p>
                <p><a href="{settings.FRONTEND_URL}/student/reports" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 8px;">View Report Card</a></p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">School Management System</p>
            </div>
            """
            text_content = strip_tags(html_content)
            email_msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, recipients)
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send report published notification: {e}")
            return False

    @staticmethod
    def send_bills_generated(student, bills, term):
        """Notify guardian/parent that fee bills have been generated."""
        try:
            recipients = []
            if student.guardian_email:
                recipients.append(student.guardian_email)
            from accounts.models import ParentStudent
            parent_emails = list(
                ParentStudent.objects.filter(student=student)
                .values_list('parent__email', flat=True)
            )
            for email in parent_emails:
                if email and email not in recipients:
                    recipients.append(email)
            if not recipients:
                return False
            total_billed = sum(float(b.amount_billed) for b in bills)
            rows = ''.join(
                f'<tr><td style="padding: 6px 8px; border-bottom: 1px solid #e5e7eb;">{b.fee_type.name}</td>'
                f'<td style="padding: 6px 8px; border-bottom: 1px solid #e5e7eb; text-align: right;">GH₵ {float(b.amount_billed):,.2f}</td></tr>'
                for b in bills
            )
            subject = f'Fee Bills Generated – {student.get_full_name()} | {term}'
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #4f46e5;">Fee Bills Generated</h2>
                <p>Dear {student.guardian_name},</p>
                <p>Fee bills have been generated for <strong>{student.get_full_name()}</strong> for <strong>{term}</strong>.</p>
                <table style="width: 100%; border-collapse: collapse; margin: 16px 0;">
                    <thead>
                        <tr style="background: #f3f4f6;">
                            <th style="padding: 8px; text-align: left; border-bottom: 2px solid #e5e7eb;">Fee Type</th>
                            <th style="padding: 8px; text-align: right; border-bottom: 2px solid #e5e7eb;">Amount</th>
                        </tr>
                    </thead>
                    <tbody>{rows}</tbody>
                    <tfoot>
                        <tr>
                            <td style="padding: 8px; font-weight: bold;">Total</td>
                            <td style="padding: 8px; font-weight: bold; text-align: right;">GH₵ {total_billed:,.2f}</td>
                        </tr>
                    </tfoot>
                </table>
                <p>Please log in to the parent portal to view and pay your bills.</p>
                <p><a href="{settings.FRONTEND_URL}/student/bills" style="background: #4f46e5; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; display: inline-block; margin-top: 8px;">View Bills</a></p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">School Management System</p>
            </div>
            """
            text_content = strip_tags(html_content)
            email_msg = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, recipients)
            email_msg.attach_alternative(html_content, "text/html")
            email_msg.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send bills generated notification: {e}")
            return False

    @staticmethod
    def send_support_ticket_notification(superadmin, ticket):
        """Send support ticket notification to superadmin"""
        try:
            subject = f'Support Ticket: {ticket.subject}'
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #dc2626;">New Support Ticket</h2>
                <p>Hello {superadmin.first_name},</p>
                <p>A new support ticket has been submitted:</p>
                
                <div style="background: #f3f4f6; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin: 0 0 10px 0;">Ticket Details:</h3>
                    <p><strong>From:</strong> {ticket.user.get_full_name()} ({ticket.user.email})</p>
                    <p><strong>Role:</strong> {ticket.user.role}</p>
                    <p><strong>Subject:</strong> {ticket.subject}</p>
                    <p><strong>Message:</strong></p>
                    <div style="background: white; padding: 15px; border-left: 4px solid #dc2626; margin: 10px 0;">
                        {ticket.message}
                    </div>
                    <p><strong>Submitted:</strong> {ticket.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                </div>
                
                <p>Please respond to this ticket as soon as possible.</p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #e5e7eb;">
                <p style="color: #6b7280; font-size: 12px;">School Management System</p>
            </div>
            """
            text_content = strip_tags(html_content)
            
            email = EmailMultiAlternatives(subject, text_content, settings.DEFAULT_FROM_EMAIL, [superadmin.email])
            email.attach_alternative(html_content, "text/html")
            email.send()
            return True
        except Exception as e:
            logger.error(f"Failed to send support ticket notification: {e}")
            return False
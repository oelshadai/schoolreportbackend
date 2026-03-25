"""
Student-specific input validation using centralized SecurityValidator
"""

from accounts.security_config import SecurityValidator, SecuritySettings
from django.core.exceptions import ValidationError
import re


class StudentInputValidator:
    """Student-specific input validation using centralized security"""
    
    @staticmethod
    def validate_student_registration(data: dict) -> dict:
        """Validate student registration data"""
        errors = {}
        
        # Student ID validation
        if 'student_id' in data:
            validation = SecurityValidator.validate_student_id(data['student_id'])
            if not validation['valid']:
                errors['student_id'] = validation['error']
        
        # Email validation (if provided)
        if 'email' in data and data['email']:
            validation = SecurityValidator.validate_email(data['email'])
            if not validation['valid']:
                errors['email'] = validation['error']
        
        # Password validation (student mode)
        if 'password' in data:
            validation = SecurityValidator.validate_password(data['password'], is_student=True)
            if not validation['valid']:
                errors['password'] = validation['errors']
        
        # Name validation
        if 'first_name' in data:
            name_validation = StudentInputValidator._validate_name(data['first_name'], 'First name')
            if not name_validation['valid']:
                errors['first_name'] = name_validation['error']
        
        if 'last_name' in data:
            name_validation = StudentInputValidator._validate_name(data['last_name'], 'Last name')
            if not name_validation['valid']:
                errors['last_name'] = name_validation['error']
        
        # Phone number validation (if provided)
        if 'phone_number' in data and data['phone_number']:
            phone_validation = StudentInputValidator._validate_phone(data['phone_number'])
            if not phone_validation['valid']:
                errors['phone_number'] = phone_validation['error']
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_student_login(student_id: str, password: str) -> dict:
        """Validate student login credentials"""
        errors = []
        
        if not student_id or not password:
            errors.append('Student ID and password are required')
            return {'valid': False, 'errors': errors}
        
        # Use SecurityValidator for student ID
        student_id_validation = SecurityValidator.validate_student_id(student_id)
        if not student_id_validation['valid']:
            errors.append(student_id_validation['error'])
        
        # Use SecurityValidator for password (student mode)
        password_validation = SecurityValidator.validate_password(password, is_student=True)
        if not password_validation['valid']:
            errors.extend(password_validation['errors'])
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_assignment_submission(data: dict) -> dict:
        """Validate assignment submission data"""
        errors = {}
        
        # Text submission validation
        if 'submission_text' in data and data['submission_text']:
            text_validation = StudentInputValidator._validate_submission_text(data['submission_text'])
            if not text_validation['valid']:
                errors['submission_text'] = text_validation['error']
        
        # File validation handled by SecurityValidator in submission_validation_api.py
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def _validate_name(name: str, field_name: str) -> dict:
        """Validate student name fields"""
        if not name:
            return {'valid': False, 'error': f'{field_name} is required'}
        
        if len(name) < 2:
            return {'valid': False, 'error': f'{field_name} must be at least 2 characters'}
        
        if len(name) > 50:
            return {'valid': False, 'error': f'{field_name} must not exceed 50 characters'}
        
        # Only allow letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\-']+$", name):
            return {'valid': False, 'error': f'{field_name} contains invalid characters'}
        
        # Check for suspicious patterns
        suspicious_check = SecuritySettings.is_suspicious_pattern(name)
        if suspicious_check['is_suspicious']:
            return {'valid': False, 'error': f'{field_name} contains invalid characters'}
        
        return {'valid': True}
    
    @staticmethod
    def _validate_phone(phone: str) -> dict:
        """Validate phone number"""
        if not phone:
            return {'valid': True}  # Phone is optional
        
        # Remove common formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
        
        # Check if it's all digits and reasonable length
        if not re.match(r'^\d{10,15}$', cleaned_phone):
            return {'valid': False, 'error': 'Invalid phone number format'}
        
        return {'valid': True}
    
    @staticmethod
    def _validate_submission_text(text: str) -> dict:
        """Validate assignment submission text"""
        if not text:
            return {'valid': True}  # Text can be empty
        
        if len(text) > 10000:  # 10KB limit
            return {'valid': False, 'error': 'Text submission too long (max 10,000 characters)'}
        
        # Check for suspicious patterns
        suspicious_check = SecuritySettings.is_suspicious_pattern(text)
        if suspicious_check['is_suspicious']:
            return {'valid': False, 'error': 'Text contains invalid content'}
        
        return {'valid': True}
    
    @staticmethod
    def sanitize_student_input(data: dict) -> dict:
        """Sanitize student input data"""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                # Basic sanitization
                sanitized_value = value.strip()
                
                # Remove null bytes
                sanitized_value = sanitized_value.replace('\x00', '')
                
                # Limit length based on field type
                if key in ['first_name', 'last_name']:
                    sanitized_value = sanitized_value[:50]
                elif key == 'student_id':
                    sanitized_value = sanitized_value[:20]
                elif key == 'email':
                    sanitized_value = sanitized_value[:254]
                elif key == 'phone_number':
                    sanitized_value = sanitized_value[:20]
                elif key == 'submission_text':
                    sanitized_value = sanitized_value[:10000]
                else:
                    sanitized_value = sanitized_value[:255]  # Default limit
                
                sanitized[key] = sanitized_value
            else:
                sanitized[key] = value
        
        return sanitized


class StudentValidationMixin:
    """Mixin for Django models/views to add student validation"""
    
    def validate_student_data(self, data: dict) -> None:
        """Validate student data and raise ValidationError if invalid"""
        validation = StudentInputValidator.validate_student_registration(data)
        if not validation['valid']:
            raise ValidationError(validation['errors'])
    
    def clean_student_input(self, data: dict) -> dict:
        """Clean and sanitize student input"""
        return StudentInputValidator.sanitize_student_input(data)
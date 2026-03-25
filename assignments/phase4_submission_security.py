"""
Phase 4: Submission Security Service
Minimal security validation for submissions
"""
import hashlib
import mimetypes
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class SubmissionSecurityService:
    """Minimal submission security service"""
    
    ALLOWED_MIME_TYPES = {
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'text/plain',
        'image/jpeg',
        'image/png',
        'application/zip'
    }
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    @classmethod
    def validate_file_submission(cls, file):
        """Validate file submission security"""
        # Size check
        if file.size > cls.MAX_FILE_SIZE:
            raise ValidationError(f"File size exceeds {cls.MAX_FILE_SIZE // (1024*1024)}MB limit")
        
        # MIME type check
        mime_type, _ = mimetypes.guess_type(file.name)
        if mime_type not in cls.ALLOWED_MIME_TYPES:
            raise ValidationError(f"File type {mime_type} not allowed")
        
        # File name validation
        if not cls._is_safe_filename(file.name):
            raise ValidationError("Invalid file name")
        
        return True
    
    @staticmethod
    def _is_safe_filename(filename):
        """Check if filename is safe"""
        dangerous_chars = ['..', '/', '\\', '<', '>', ':', '"', '|', '?', '*']
        return not any(char in filename for char in dangerous_chars)
    
    @staticmethod
    def generate_submission_hash(content):
        """Generate hash for submission content"""
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()
    
    @staticmethod
    def validate_text_submission(text):
        """Validate text submission"""
        if len(text) > 10000:  # 10KB limit
            raise ValidationError("Text submission too long")
        
        # Basic XSS prevention
        dangerous_tags = ['<script', '<iframe', '<object', '<embed']
        text_lower = text.lower()
        if any(tag in text_lower for tag in dangerous_tags):
            raise ValidationError("Potentially dangerous content detected")
        
        return True
    
    @staticmethod
    def sanitize_submission_data(data):
        """Sanitize submission data"""
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if isinstance(value, str):
                    # Basic HTML escaping
                    value = value.replace('<', '&lt;').replace('>', '&gt;')
                sanitized[key] = value
            return sanitized
        
        return data
    
    @staticmethod
    def log_submission_attempt(student_id, assignment_id, success=True, error=None):
        """Log submission attempt for security audit"""
        status = "SUCCESS" if success else "FAILED"
        message = f"Submission {status}: Student {student_id}, Assignment {assignment_id}"
        
        if error:
            message += f", Error: {error}"
        
        if success:
            logger.info(message)
        else:
            logger.warning(message)
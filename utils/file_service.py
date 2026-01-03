import os
import uuid
from django.core.files.storage import default_storage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class FileUploadService:
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif']
    ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
    MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB
    
    @staticmethod
    def validate_file(file, file_type='image'):
        """Validate uploaded file"""
        if not file:
            return False, "No file provided"
        
        file_ext = os.path.splitext(file.name)[1].lower()
        
        if file_type == 'image':
            if file_ext not in FileUploadService.ALLOWED_IMAGE_EXTENSIONS:
                return False, f"Invalid image format"
            if file.size > FileUploadService.MAX_IMAGE_SIZE:
                return False, "Image size too large"
        
        elif file_type == 'document':
            if file_ext not in FileUploadService.ALLOWED_DOCUMENT_EXTENSIONS:
                return False, f"Invalid document format"
            if file.size > FileUploadService.MAX_DOCUMENT_SIZE:
                return False, "Document size too large"
        
        return True, "Valid file"
    
    @staticmethod
    def save_student_photo(file, student_id):
        """Save student photo"""
        try:
            is_valid, message = FileUploadService.validate_file(file, 'image')
            if not is_valid:
                return None, message
            
            file_ext = os.path.splitext(file.name)[1].lower()
            filename = f"student_{student_id}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = f"student_photos/{filename}"
            
            saved_path = default_storage.save(file_path, file)
            return saved_path, "Photo uploaded successfully"
        
        except Exception as e:
            logger.error(f"Failed to save student photo: {e}")
            return None, "Failed to upload photo"
    
    @staticmethod
    def save_assignment_file(file, assignment_id, student_id):
        """Save assignment file"""
        try:
            is_valid, message = FileUploadService.validate_file(file, 'document')
            if not is_valid:
                return None, message
            
            file_ext = os.path.splitext(file.name)[1].lower()
            filename = f"assignment_{assignment_id}_student_{student_id}_{uuid.uuid4().hex[:8]}{file_ext}"
            file_path = f"assignments/{filename}"
            
            saved_path = default_storage.save(file_path, file)
            return saved_path, "File uploaded successfully"
        
        except Exception as e:
            logger.error(f"Failed to save assignment file: {e}")
            return None, "Failed to upload file"
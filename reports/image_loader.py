import requests
from io import BytesIO
from django.conf import settings
from reportlab.lib.utils import ImageReader
import os
from PIL import Image as PILImage


class ReportImageLoader:
    """Professional image loader for report generation"""
    
    @staticmethod
    def get_image_reader(file_field, max_width=None, max_height=None, timeout=10):
        """
        Get image data for reportlab with comprehensive error handling
        
        Args:
            file_field: Django FileField, URL string, or file path
            max_width: Maximum width in inches
            max_height: Maximum height in inches  
            timeout: Request timeout in seconds
            
        Returns:
            tuple: (BytesIO object, width, height) or (None, 0, 0)
        """
        try:
            if not file_field:
                return ReportImageLoader._create_default_placeholder(max_width or 1, max_height or 1)
                
            # Get image data
            image_data = ReportImageLoader._get_image_data(file_field, timeout)
            if not image_data:
                return ReportImageLoader._create_default_placeholder(max_width or 1, max_height or 1)
                
            # Process and validate image
            processed_image = ReportImageLoader._process_image(image_data, max_width, max_height)
            if processed_image:
                return processed_image
                
            # Fallback to placeholder
            return ReportImageLoader._create_default_placeholder(max_width or 1, max_height or 1)
            
        except Exception as e:
            print(f"Image loading error: {e}")
            return ReportImageLoader._create_default_placeholder(max_width or 1, max_height or 1)
    
    @staticmethod
    def _get_image_data(file_field, timeout=10):
        """Get raw image data from various sources"""
        try:
            # Handle Django FileField
            if hasattr(file_field, 'url') and hasattr(file_field, 'path'):
                # Try local file first (faster)
                if os.path.exists(file_field.path):
                    with open(file_field.path, 'rb') as f:
                        return f.read()
                        
                # Fallback to URL
                url = file_field.url
                if not url.startswith('http'):
                    base_url = getattr(settings, 'MEDIA_URL_BASE', 'http://localhost:8000')
                    url = base_url.rstrip('/') + '/' + url.lstrip('/')
                    
                response = requests.get(url, timeout=timeout, stream=True)
                if response.status_code == 200:
                    return response.content
            
            # Handle URL string
            elif isinstance(file_field, str):
                if file_field.startswith('http'):
                    response = requests.get(file_field, timeout=timeout, stream=True)
                    if response.status_code == 200:
                        return response.content
                elif os.path.exists(file_field):
                    with open(file_field, 'rb') as f:
                        return f.read()
                        
        except Exception as e:
            print(f"Failed to fetch image data: {e}")
            
        return None
    
    @staticmethod
    def _process_image(image_data, max_width, max_height):
        """Process and validate image data"""
        try:
            # Open and validate image
            img = PILImage.open(BytesIO(image_data))
            
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = PILImage.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Get original dimensions
            orig_width, orig_height = img.size
            width_inches = orig_width / 72.0  # Convert pixels to inches
            height_inches = orig_height / 72.0
            
            # Apply size constraints
            if max_width and max_height:
                scale_w = max_width / width_inches
                scale_h = max_height / height_inches
                scale = min(scale_w, scale_h, 1.0)  # Don't upscale
                
                if scale < 1.0:
                    new_width = int(orig_width * scale)
                    new_height = int(orig_height * scale)
                    img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
                    width_inches = new_width / 72.0
                    height_inches = new_height / 72.0
            
            # Save processed image to buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85, optimize=True)
            buffer.seek(0)
            
            return buffer, width_inches, height_inches
            
        except Exception as e:
            print(f"Image processing error: {e}")
            return None
    
    @staticmethod
    def _create_default_placeholder(width_inches, height_inches):
        """Create a professional default placeholder"""
        try:
            # Create placeholder dimensions
            width_px = max(int(width_inches * 72), 50)
            height_px = max(int(height_inches * 72), 50)
            
            # Create professional placeholder
            img = PILImage.new('RGB', (width_px, height_px), color='#f8f9fa')
            
            # Save to buffer
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            buffer.seek(0)
            
            return buffer, width_inches, height_inches
            
        except Exception:
            return None, 0, 0
    
    @staticmethod
    def create_placeholder_image(width_inches, height_inches, text="IMAGE"):
        """Create a placeholder image with text"""
        return ReportImageLoader._create_default_placeholder(width_inches, height_inches)
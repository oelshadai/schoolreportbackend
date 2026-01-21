import requests
from io import BytesIO
from django.conf import settings
from reportlab.lib.utils import ImageReader


class ReportImageLoader:
    """Optimized image loader for report generation"""
    
    @staticmethod
    def get_image_reader(file_field, max_width=None, max_height=None, timeout=5):
        """
        Get ImageReader for reportlab with proper error handling
        
        Args:
            file_field: Django FileField or URL string
            max_width: Maximum width in inches
            max_height: Maximum height in inches  
            timeout: Request timeout in seconds
            
        Returns:
            tuple: (ImageReader object, width, height) or (None, 0, 0)
        """
        try:
            if not file_field:
                return None, 0, 0
                
            # Get image data
            image_data = ReportImageLoader._get_image_data(file_field, timeout)
            if not image_data:
                return None, 0, 0
                
            # Create ImageReader
            reader = ImageReader(BytesIO(image_data))
            width, height = reader.getSize()
            
            # Apply size constraints if specified
            if max_width and max_height:
                scale = min(max_width * 72 / width, max_height * 72 / height)  # Convert inches to points
                width = width * scale / 72  # Convert back to inches
                height = height * scale / 72
                
            return reader, width, height
            
        except Exception as e:
            print(f"Error loading image: {e}")
            return None, 0, 0
    
    @staticmethod
    def _get_image_data(file_field, timeout=5):
        """Get raw image data from file field or URL"""
        try:
            # Handle Django FileField
            if hasattr(file_field, 'url'):
                url = file_field.url
                if not url.startswith('http'):
                    # Build absolute URL
                    base_url = getattr(settings, 'MEDIA_URL_BASE', 'https://school-report-saas.onrender.com')
                    url = base_url + url
                    
                response = requests.get(url, timeout=timeout)
                if response.status_code == 200:
                    return response.content
                    
            # Handle direct URL string
            elif isinstance(file_field, str) and file_field.startswith('http'):
                response = requests.get(file_field, timeout=timeout)
                if response.status_code == 200:
                    return response.content
                    
            # Handle local file path
            elif isinstance(file_field, str):
                with open(file_field, 'rb') as f:
                    return f.read()
                    
        except Exception as e:
            print(f"Failed to fetch image data: {e}")
            
        return None
    
    @staticmethod
    def create_placeholder_image(width_inches, height_inches, text="IMAGE"):
        """Create a placeholder image when actual image fails to load"""
        try:
            from reportlab.graphics.shapes import Drawing, Rect, String
            from reportlab.graphics import renderPDF
            from reportlab.lib import colors
            
            width_points = width_inches * 72
            height_points = height_inches * 72
            
            drawing = Drawing(width_points, height_points)
            drawing.add(Rect(0, 0, width_points, height_points, 
                           fillColor=colors.lightgrey, strokeColor=colors.black))
            drawing.add(String(width_points/2, height_points/2, text, 
                             textAnchor='middle', fontSize=10))
            
            buffer = BytesIO()
            renderPDF.drawToFile(drawing, buffer)
            buffer.seek(0)
            
            return ImageReader(buffer), width_inches, height_inches
            
        except Exception:
            return None, 0, 0
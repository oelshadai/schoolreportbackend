from django.conf import settings
from django.contrib.sites.models import Site


def get_media_base_url(request=None):
    """
    Get the correct base URL for media files in both development and production.
    """
    # Try to get from request first
    if request:
        return request.build_absolute_uri('/').rstrip('/')
    
    # Check if we have a configured MEDIA_URL_BASE
    media_base = getattr(settings, 'MEDIA_URL_BASE', None)
    if media_base and not media_base.startswith('http://localhost'):
        return media_base
    
    # Fallback to production URL
    if not settings.DEBUG:
        return 'https://school-report-saas.onrender.com'
    
    # Development fallback
    return 'http://localhost:8000'


def get_absolute_media_url(file_field, request=None):
    """
    Get absolute URL for a file field, handling both development and production.
    """
    if not file_field:
        return None
    
    try:
        url = file_field.url
        if url.startswith('http'):
            return url
        
        # Always use production URL for deployed environment
        base_url = get_media_base_url(request)
        return base_url + url
    except (ValueError, AttributeError):
        # Handle cases where file_field.url might fail
        return None


def validate_image_url(url):
    """
    Validate if an image URL is accessible
    """
    if not url:
        return False
        
    try:
        import requests
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False
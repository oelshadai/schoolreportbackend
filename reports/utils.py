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
    
    url = file_field.url
    if url.startswith('http'):
        return url
    
    base_url = get_media_base_url(request)
    return base_url + url
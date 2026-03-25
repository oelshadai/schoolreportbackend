"""
Production-grade CORS security middleware
Handles CORS with enhanced security and proper header management
"""

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class CORSSecurityMiddleware(MiddlewareMixin):
    """
    Enhanced CORS middleware with security header filtering
    Prevents security headers from being processed as request headers
    """
    
    def process_request(self, request):
        """Process incoming request and clean invalid headers"""
        
        # Security headers that should never be request headers
        invalid_request_headers = [
            'x-content-type-options',
            'x-frame-options', 
            'x-xss-protection',
            'strict-transport-security',
            'content-security-policy',
            'referrer-policy',
            'permissions-policy'
        ]
        
        # Remove invalid headers from request META
        for header in invalid_request_headers:
            header_key = f'HTTP_{header.upper().replace("-", "_")}'
            if header_key in request.META:
                logger.warning(f"Removing invalid request header: {header}")
                del request.META[header_key]
        
        return None
    
    def process_response(self, request, response):
        """Add proper security headers to response"""
        
        # Only add CORS headers for API endpoints
        if request.path.startswith('/api/'):
            origin = request.META.get('HTTP_ORIGIN')
            
            # Check if origin is allowed
            allowed_origins = getattr(settings, 'CORS_ALLOWED_ORIGINS', [])
            
            if origin in allowed_origins:
                response['Access-Control-Allow-Origin'] = origin
                response['Access-Control-Allow-Credentials'] = 'true'
                response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS'
                response['Access-Control-Allow-Headers'] = ', '.join([
                    'accept', 'accept-encoding', 'accept-language', 'authorization',
                    'content-type', 'dnt', 'origin', 'user-agent', 'x-csrftoken',
                    'x-requested-with', 'cache-control', 'pragma', 'expires'
                ])
                response['Access-Control-Max-Age'] = '86400'
        
        # Add security headers (these should only be response headers)
        if not settings.DEBUG:
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-Frame-Options'] = 'DENY'
            response['X-XSS-Protection'] = '1; mode=block'
            response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
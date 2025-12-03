"""
Custom CORS middleware to ensure CORS headers are always added
"""

from django.http import HttpResponse
import logging

logger = logging.getLogger(__name__)

class ForceEveryCORSMiddleware:
    """
    Middleware to add CORS headers to every response, ensuring cross-origin requests work
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle preflight OPTIONS requests first
        if request.method == 'OPTIONS':
            logger.debug(f"OPTIONS request to {request.path} from origin {request.META.get('HTTP_ORIGIN')}")
            response = HttpResponse()
            self.add_cors_headers(response, request)
            return response
        
        # Process the actual request
        try:
            response = self.get_response(request)
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            response = HttpResponse(status=500)
        
        self.add_cors_headers(response, request)
        return response
    
    def add_cors_headers(self, response, request=None):
        """Add all necessary CORS headers to response"""
        # Always allow all origins - this is critical for cross-origin requests
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH, TRACE'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Encoding, Accept-Language, Authorization, '
            'Content-Type, Content-Length, Origin, User-Agent, X-CSRFToken, '
            'X-Requested-With, X-Request-ID, Cache-Control, DNT, '
            'X-Forwarded-For, X-Forwarded-Proto, X-Real-IP, X-Api-Key'
        )
        response['Access-Control-Expose-Headers'] = (
            'Content-Type, Content-Length, Authorization, X-Total-Count, '
            'X-Page-Count, X-Request-ID'
        )
        response['Access-Control-Max-Age'] = '86400'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Vary'] = 'Origin, Accept-Encoding'
        
        # Security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response
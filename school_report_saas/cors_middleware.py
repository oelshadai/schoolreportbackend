"""
Custom CORS middleware to force CORS headers on every response.
This must be the FIRST middleware in the MIDDLEWARE list in settings.py
"""

from django.http import HttpResponse


class ForceEveryCORSMiddleware:
    """
    Aggressive CORS middleware that ensures headers are added to EVERY response,
    including OPTIONS preflight requests.
    
    CRITICAL: This MUST be the first middleware in MIDDLEWARE list!
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ALWAYS handle OPTIONS requests - they need CORS headers to succeed
        if request.method == 'OPTIONS':
            # Create a simple response for preflight
            response = HttpResponse('')
            response.status_code = 200
        else:
            # For all other methods, get the normal response
            response = self.get_response(request)
        
        # Apply CORS headers to response
        self._apply_cors_headers(response)
        return response
    
    def _apply_cors_headers(self, response):
        """
        Apply CORS headers. These are the MINIMUM required headers for CORS to work.
        """
        # The origin header - MUST be present and match for browser to allow request
        response['Access-Control-Allow-Origin'] = '*'
        
        # Methods - list all HTTP methods that might be used
        response['Access-Control-Allow-Methods'] = (
            'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'
        )
        
        # Headers - list all headers that client might send
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Content-Language, Content-Type, '
            'Authorization, X-Requested-With, X-CSRFToken, Cache-Control, '
            'Origin, User-Agent, DNT, X-Request-ID, X-API-Key'
        )
        
        # Expose - headers that client can read from response
        response['Access-Control-Expose-Headers'] = 'Content-Type, Authorization'
        
        # Cache time for preflight
        response['Access-Control-Max-Age'] = '3600'
        
        return response
"""
Custom CORS middleware to ensure CORS headers are always added to every response
"""

from django.http import HttpResponse


class ForceEveryCORSMiddleware:
    """
    Middleware to forcefully add CORS headers to every response.
    This ensures cross-origin requests from Netlify frontend work properly.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle OPTIONS requests (CORS preflight)
        if request.method == 'OPTIONS':
            response = HttpResponse()
        else:
            response = self.get_response(request)
        
        # Force CORS headers on every response
        self._add_cors_headers(response)
        return response
    
    def _add_cors_headers(self, response):
        """
        Add CORS headers to response.
        Using * for origin since we want to allow all cross-origin requests.
        """
        # Always set these headers
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, PATCH, DELETE, OPTIONS, HEAD'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Content-Language, Content-Type, '
            'Authorization, X-Requested-With, X-CSRFToken, Cache-Control, '
            'Origin, User-Agent, DNT, X-Request-ID, X-API-Key'
        )
        response['Access-Control-Expose-Headers'] = (
            'Content-Type, Authorization, X-Total-Count, X-Page-Count'
        )
        response['Access-Control-Max-Age'] = '86400'
        response['X-Content-Type-Options'] = 'nosniff'
        
        return response
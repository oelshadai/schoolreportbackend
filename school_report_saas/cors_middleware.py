"""
CORS Middleware - Add CORS headers to ALL responses including error responses
This must be the FIRST middleware in Django's MIDDLEWARE list.
"""

from django.http import HttpResponse


class CORSMiddleware:
    """
    Add CORS headers to every single response, no exceptions.
    This handles:
    - Normal requests
    - OPTIONS preflight requests
    - Error responses (404, 500, etc)
    - All content types
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # For OPTIONS requests, return immediately with CORS headers
        if request.method == 'OPTIONS':
            response = self._build_cors_response()
            return response
        
        # Get the actual response from Django
        try:
            response = self.get_response(request)
        except Exception as e:
            # Even if there's an error, return a proper response with CORS headers
            response = HttpResponse(
                f'{{"error": "Internal Server Error", "detail": "{str(e)}"}}',
                status=500,
                content_type='application/json'
            )
        
        # Apply CORS headers to ALL responses
        self._add_cors_headers(response)
        return response
    
    def _build_cors_response(self):
        """Build a proper OPTIONS response"""
        response = HttpResponse('')
        response.status_code = 204  # No Content
        return response
    
    def _add_cors_headers(self, response):
        """Add CORS headers to response object"""
        # These are the CRITICAL headers that MUST be present
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Content-Language, Content-Type, '
            'Authorization, X-Requested-With, X-CSRFToken, Cache-Control, '
            'Origin, User-Agent, DNT, X-Request-ID'
        )
        response['Access-Control-Max-Age'] = '3600'
        
        # Return the modified response
        return response
"""
Custom CORS middleware to ensure CORS headers are always added
"""

from django.http import HttpResponse

class ForceEveryCORSMiddleware:
    """
    Middleware to add CORS headers to every response, bypassing django-cors-headers issues
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Handle preflight OPTIONS requests first
        if request.method == 'OPTIONS':
            response = HttpResponse()
            self.add_cors_headers(response)
            return response
            
        response = self.get_response(request)
        self.add_cors_headers(response)
        return response
    
    def add_cors_headers(self, response):
        """Add all necessary CORS headers to response"""
        # Always allow all origins for maximum compatibility
        origin = '*'
        response['Access-Control-Allow-Origin'] = origin
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Encoding, Accept-Language, Authorization, Content-Type, '
            'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With, Cache-Control, '
            'X-Forwarded-For, X-Forwarded-Proto, X-Real-IP'
        )
        response['Access-Control-Expose-Headers'] = 'Content-Type, Authorization, X-Total-Count'
        response['Access-Control-Max-Age'] = '86400'
        response['Vary'] = 'Origin'
        
        # Additional headers for better compatibility
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'SAMEORIGIN'
        
        return response
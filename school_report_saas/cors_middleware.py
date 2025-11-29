"""
Custom CORS middleware to ensure CORS headers are always added
"""

class ForceEveryCORSMiddleware:
    """
    Middleware to add CORS headers to every response, bypassing django-cors-headers issues
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Force CORS headers on every response
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
        response['Access-Control-Allow-Headers'] = (
            'Accept, Accept-Language, Authorization, Content-Type, '
            'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With'
        )
        response['Access-Control-Max-Age'] = '86400'
        
        return response

    def process_request(self, request):
        """Handle preflight OPTIONS requests"""
        if request.method == 'OPTIONS':
            from django.http import HttpResponse
            response = HttpResponse()
            response['Access-Control-Allow-Origin'] = '*'
            response['Access-Control-Allow-Credentials'] = 'true'
            response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
            response['Access-Control-Allow-Headers'] = (
                'Accept, Accept-Language, Authorization, Content-Type, '
                'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With'
            )
            response['Access-Control-Max-Age'] = '86400'
            return response
        return None
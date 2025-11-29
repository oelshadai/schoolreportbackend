"""
Ultra-simple CORS fix - add this to your Django project
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View

class SimpleCORSResponse:
    """Simple CORS response handler"""
    
    @staticmethod
    def add_cors_headers(response):
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-CSRFToken'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response

# Add this to your views.py files where needed
@csrf_exempt
@require_http_methods(["GET", "POST", "PUT", "DELETE", "OPTIONS"])
def cors_enabled_view(request):
    """View with CORS enabled"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'message': 'CORS preflight'})
        return SimpleCORSResponse.add_cors_headers(response)
    
    # Your actual view logic here
    data = {'message': 'CORS enabled', 'method': request.method}
    response = JsonResponse(data)
    return SimpleCORSResponse.add_cors_headers(response)
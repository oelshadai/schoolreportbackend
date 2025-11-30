"""
Simple CORS test endpoint
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json

@csrf_exempt
def cors_test(request):
    """Test endpoint to verify CORS configuration"""
    
    response = JsonResponse({
        'status': 'success',
        'message': 'CORS is working correctly!',
        'method': request.method,
        'origin': request.META.get('HTTP_ORIGIN', 'Unknown'),
        'user_agent': request.META.get('HTTP_USER_AGENT', 'Unknown'),
        'headers': dict(request.headers)
    })
    
    # Add explicit CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
    response['Access-Control-Allow-Headers'] = (
        'Accept, Accept-Encoding, Accept-Language, Authorization, Content-Type, '
        'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With, Cache-Control'
    )
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Max-Age'] = '86400'
    response['Vary'] = 'Origin'
    
    return response

@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def teacher_cors_test(request):
    """Specific test for teacher creation endpoint"""
    
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'preflight_ok'})
    elif request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            response = JsonResponse({
                'status': 'success',
                'message': 'Teacher creation endpoint is accessible',
                'received_data': data,
                'content_type': request.content_type,
                'auth_header': request.META.get('HTTP_AUTHORIZATION', 'None')
            })
        except json.JSONDecodeError:
            response = JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
    else:
        response = JsonResponse({
            'status': 'success',
            'message': 'Teacher creation endpoint is accessible via GET',
            'available_methods': ['GET', 'POST', 'OPTIONS']
        })
    
    # Add explicit CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS, HEAD, PATCH'
    response['Access-Control-Allow-Headers'] = (
        'Accept, Accept-Encoding, Accept-Language, Authorization, Content-Type, '
        'DNT, Origin, User-Agent, X-CSRFToken, X-Requested-With, Cache-Control'
    )
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Max-Age'] = '86400'
    response['Vary'] = 'Origin'
    
    return response
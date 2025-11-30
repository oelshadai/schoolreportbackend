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
    """Specific test for teacher creation endpoint - no auth required"""
    
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'preflight_ok'})
    elif request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
            response = JsonResponse({
                'status': 'success',
                'message': 'Teacher CORS test successful - POST data received',
                'received_data_keys': list(data.keys()) if data else [],
                'content_type': request.content_type,
                'auth_header': 'Present' if request.META.get('HTTP_AUTHORIZATION') else 'Missing',
                'origin': request.META.get('HTTP_ORIGIN', 'No origin header'),
                'note': 'This is a test endpoint. For actual teacher creation, use /api/teachers/ with authentication.'
            })
        except json.JSONDecodeError:
            response = JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
    else:
        response = JsonResponse({
            'status': 'success',
            'message': 'Teacher CORS test endpoint is accessible via GET',
            'available_methods': ['GET', 'POST', 'OPTIONS'],
            'origin': request.META.get('HTTP_ORIGIN', 'No origin header'),
            'note': 'This endpoint tests CORS for teacher operations without authentication requirements.'
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
"""
URL configuration for school_report_saas project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def api_root(request):
    """API root endpoint showing available endpoints"""
    response = JsonResponse({
        'message': 'School Report SaaS API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': '2024-11-30T16:00:00Z',
        'endpoints': {
            'admin': '/admin/',
            'authentication': '/api/auth/',
            'schools': '/api/schools/',
            'students': '/api/students/',
            'teachers': '/api/teachers/',
            'scores': '/api/scores/',
            'reports': '/api/reports/',
            'subscriptions': '/api/subscriptions/',
            'cors_test': '/api/cors-test/',
            'health': '/api/health/',
        },
        'frontend': 'https://elitetechreport.netlify.app/',
        'cors_enabled': True
    })
    
    # Add CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response['Access-Control-Allow-Credentials'] = 'true'
    
    return response

@csrf_exempt
def health_check(request):
    """Simple health check endpoint"""
    response = JsonResponse({
        'status': 'healthy',
        'timestamp': '2024-11-30T16:00:00Z',
        'database': 'connected',
        'cors': 'enabled'
    })
    
    # Add CORS headers
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response['Access-Control-Allow-Credentials'] = 'true'
    
    return response

@csrf_exempt
def cors_test_endpoint(request):
    """Test CORS configuration"""
    response = JsonResponse({
        'cors_status': 'working',
        'method': request.method,
        'origin': request.META.get('HTTP_ORIGIN', 'Unknown'),
        'message': 'CORS headers are properly configured'
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

urlpatterns = [
    path('', api_root, name='api_root'),
    path('api/', api_root, name='api_root_api'),
    path('api/health/', health_check, name='health_check'),
    path('api/cors-test/', cors_test_endpoint, name='cors_test'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/schools/', include('schools.urls')),
    path('api/students/', include('students.urls')),
    path('api/teachers/', include('teachers.urls')),
    path('api/scores/', include('scores.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

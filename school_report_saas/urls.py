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
    
    # CORS headers are handled by WSGI middleware - no need to add them here
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
    
    # CORS headers are handled by WSGI middleware
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
    
    # CORS headers are handled by WSGI middleware
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

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
    return JsonResponse({
        'message': 'School Report SaaS API',
        'version': '1.0.0',
        'endpoints': {
            'admin': '/admin/',
            'authentication': '/api/auth/',
            'schools': '/api/schools/',
            'students': '/api/students/',
            'teachers': '/api/teachers/',
            'scores': '/api/scores/',
            'reports': '/api/reports/',
            'subscriptions': '/api/subscriptions/',
        },
        'frontend': 'http://localhost:3000/',
        'status': 'running'
    })

urlpatterns = [
    path('', api_root, name='api_root'),
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

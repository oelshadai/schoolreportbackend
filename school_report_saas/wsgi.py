"""WSGI config for school_report_saas project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')

django_application = get_wsgi_application()


class CORSWSGIMiddleware:
    """
    WSGI middleware to add CORS headers at the application level.
    This runs at the outermost layer before anything else can interfere.
    """
    
    def __init__(self, application):
        self.application = application
    
    def __call__(self, environ, start_response):
        # For OPTIONS requests, return immediately with CORS headers
        if environ.get('REQUEST_METHOD') == 'OPTIONS':
            status = '204 No Content'
            headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-CSRFToken, Cache-Control, Origin, User-Agent, DNT, X-Request-ID'),
                ('Access-Control-Max-Age', '3600'),
                ('Content-Length', '0'),
            ]
            start_response(status, headers)
            return [b'']
        
        # For all other requests, wrap the start_response to inject CORS headers
        def cors_start_response(status, response_headers, exc_info=None):
            # Add CORS headers to every response
            cors_headers = [
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-CSRFToken, Cache-Control, Origin, User-Agent, DNT, X-Request-ID'),
                ('Access-Control-Max-Age', '3600'),
            ]
            response_headers.extend(cors_headers)
            return start_response(status, response_headers, exc_info)
        
        # Call the Django application with the wrapped start_response
        return self.application(environ, cors_start_response)


# Wrap the Django application with CORS middleware
application = CORSWSGIMiddleware(django_application)


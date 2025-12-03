"""WSGI config for school_report_saas project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')

django_app = get_wsgi_application()


def application(environ, start_response):
    """
    WSGI application wrapper that adds CORS headers to ALL responses.
    This is the simplest and most reliable way to add CORS at the application level.
    """
    
    # For OPTIONS requests, return immediately with CORS headers only
    if environ.get('REQUEST_METHOD') == 'OPTIONS':
        status = '200 OK'
        response_headers = [
            ('Content-Type', 'text/plain'),
            ('Content-Length', '0'),
            ('Access-Control-Allow-Origin', '*'),
            ('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'),
            ('Access-Control-Allow-Headers', 'Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-CSRFToken, Cache-Control, Origin, User-Agent, DNT'),
            ('Access-Control-Max-Age', '3600'),
        ]
        start_response(status, response_headers)
        return [b'']
    
    # For other methods, we need to intercept the response and add headers
    cors_headers_added = [False]  # Use list to make it mutable in nested function
    
    def cors_start_response(status, response_headers, exc_info=None):
        """Wrapper for start_response that adds CORS headers"""
        if not cors_headers_added[0]:
            # Check if CORS header already exists
            has_cors = any(h[0].lower() == 'access-control-allow-origin' for h in response_headers)
            
            if not has_cors:
                # Add CORS headers
                response_headers = list(response_headers) if response_headers else []
                response_headers.extend([
                    ('Access-Control-Allow-Origin', '*'),
                    ('Access-Control-Allow-Methods', 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'),
                    ('Access-Control-Allow-Headers', 'Accept, Accept-Language, Content-Language, Content-Type, Authorization, X-Requested-With, X-CSRFToken, Cache-Control, Origin, User-Agent, DNT'),
                    ('Access-Control-Max-Age', '3600'),
                ])
            
            cors_headers_added[0] = True
        
        return start_response(status, response_headers, exc_info)
    
    # Call Django application with our wrapped start_response
    return django_app(environ, cors_start_response)


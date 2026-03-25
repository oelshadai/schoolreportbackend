# This file has been disabled to prevent CORS conflicts
# The django-cors-headers package handles CORS properly
# Original content moved to cors_middleware_backup.py

# from django.http import HttpResponse

# class CORSMiddleware:
#     def __init__(self, get_response):
#         self.get_response = get_response

#     def __call__(self, request):
#         if request.method == 'OPTIONS':
#             response = self._build_cors_response()
#         else:
#             try:
#                 response = self.get_response(request)
#             except Exception as e:
#                 response = HttpResponse(
#                     f'{{"error": "Internal Server Error", "detail": "{str(e)}"}}',
#                     status=500,
#                     content_type='application/json'
#                 )
#         # Always add headers
#         self._add_cors_headers(request, response)
#         return response

#     def _build_cors_response(self):
#         response = HttpResponse('')
#         response.status_code = 204
#         # Add headers here too
#         return response

#     def _add_cors_headers(self, request, response):
#         origin = request.headers.get('Origin')
#         if origin:
#             response['Access-Control-Allow-Origin'] = origin
#         else:
#             response['Access-Control-Allow-Origin'] = '*'

#         response['Access-Control-Allow-Methods'] = 'GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS'
#         response['Access-Control-Allow-Headers'] = (
#             'Accept, Accept-Language, Content-Language, Content-Type, '
#             'Authorization, X-Requested-With, X-CSRFToken, Cache-Control, '
#             'Origin, User-Agent, DNT, X-Request-ID'
#         )
#         response['Access-Control-Max-Age'] = '3600'
#         return response
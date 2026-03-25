"""
Phase 4: Academic Enforcement Middleware
Minimal middleware for request-level enforcement
"""
from django.http import JsonResponse
from django.utils import timezone
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class AcademicEnforcementMiddleware:
    """Minimal middleware for academic enforcement"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Pre-process request
        if self._is_assignment_request(request):
            violation = self._check_request_violations(request)
            if violation:
                return JsonResponse({'error': violation}, status=403)
        
        response = self.get_response(request)
        
        # Post-process response
        if self._is_assignment_request(request):
            self._log_assignment_access(request, response)
        
        return response
    
    def _is_assignment_request(self, request):
        """Check if request is assignment-related"""
        return '/api/assignments/' in request.path
    
    def _check_request_violations(self, request):
        """Check for request-level violations"""
        if not request.user.is_authenticated:
            return None
        
        # Rate limiting check
        user_key = f"assignment_requests_{request.user.id}"
        request_count = cache.get(user_key, 0)
        
        if request_count > 100:  # 100 requests per minute
            logger.warning(f"Rate limit exceeded for user {request.user.id}")
            return "Too many requests"
        
        cache.set(user_key, request_count + 1, 60)  # 1 minute window
        return None
    
    def _log_assignment_access(self, request, response):
        """Log assignment access for audit"""
        if response.status_code >= 400:
            logger.warning(f"Assignment access failed: {request.user.id} - {request.path} - {response.status_code}")
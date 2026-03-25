"""
Production-grade security middleware for school SaaS system
Implements comprehensive security controls including rate limiting, 
session management, and threat detection.
"""

import time
import hashlib
import json
import logging
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timedelta
from django.core.cache import cache
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import jwt
from .security_config import SecuritySettings, SecurityMetrics, SecurityValidator

User = get_user_model()
logger = logging.getLogger(__name__)

class SecurityConfig:
    """Centralized security configuration - DEPRECATED: Use SecuritySettings instead"""
    
    # Backward compatibility - delegate to SecuritySettings
    RATE_LIMIT_REQUESTS = SecuritySettings.GENERAL_RATE_LIMIT
    RATE_LIMIT_WINDOW = 3600
    LOGIN_RATE_LIMIT = SecuritySettings.LOGIN_RATE_LIMIT
    LOGIN_RATE_WINDOW = 3600
    
    MAX_LOGIN_ATTEMPTS = SecuritySettings.MAX_LOGIN_ATTEMPTS
    LOCKOUT_DURATION = SecuritySettings.LOGIN_LOCKOUT_DURATION
    
    SESSION_TIMEOUT = SecuritySettings.SESSION_TIMEOUT
    IDLE_TIMEOUT = SecuritySettings.IDLE_TIMEOUT
    
    SECURITY_HEADERS = SecuritySettings.SECURITY_HEADERS

class ThreatDetector:
    """Advanced threat detection system"""
    
    @staticmethod
    def detect_suspicious_patterns(request: HttpRequest, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Detect suspicious request patterns using centralized security settings"""
        threats = []
        risk_score = 0
        
        # Get request data
        request_data = str(request.GET) + str(getattr(request, 'body', ''))
        
        # Check for suspicious patterns using centralized configuration
        pattern_check = SecuritySettings.is_suspicious_pattern(request_data)
        if pattern_check['is_suspicious']:
            threats.extend(pattern_check['threats'])
            risk_score += pattern_check['risk_score']
        
        # Check for unusual request frequency
        client_ip = ThreatDetector.get_client_ip(request)
        request_key = f"request_freq:{client_ip}"
        current_requests = cache.get(request_key, 0)
        
        if current_requests > 50:  # More than 50 requests in last minute
            threats.append("High request frequency detected")
            risk_score += 20
        
        cache.set(request_key, current_requests + 1, 60)
        
        # Check user agent patterns
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        for bot_pattern in SecuritySettings.BOT_PATTERNS:
            if bot_pattern in user_agent:
                threats.append(f"Bot pattern detected: {bot_pattern}")
                risk_score += 15
                break
        
        return {
            'threats': threats,
            'risk_score': risk_score,
            'action': 'block' if SecurityMetrics.should_block_request(risk_score) else 'monitor',
            'threat_level': SecurityMetrics.get_threat_level(risk_score)
        }
    
    @staticmethod
    def get_client_ip(request: HttpRequest) -> str:
        """Get real client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')

class SessionManager:
    """Secure session management"""
    
    @staticmethod
    def create_session(user_id: int, request: HttpRequest) -> str:
        """Create secure session with fingerprinting"""
        session_id = hashlib.sha256(
            f"{user_id}:{time.time()}:{ThreatDetector.get_client_ip(request)}".encode()
        ).hexdigest()
        
        session_data = {
            'user_id': user_id,
            'created_at': time.time(),
            'last_activity': time.time(),
            'ip_address': ThreatDetector.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'fingerprint': SessionManager.generate_fingerprint(request)
        }
        
        cache.set(f"session:{session_id}", session_data, SecurityConfig.SESSION_TIMEOUT)
        return session_id
    
    @staticmethod
    def validate_session(session_id: str, request: HttpRequest) -> Tuple[bool, Optional[Dict]]:
        """Validate session with security checks"""
        session_data = cache.get(f"session:{session_id}")
        if not session_data:
            return False, None
        
        current_time = time.time()
        
        # Check session timeout
        if current_time - session_data['created_at'] > SecurityConfig.SESSION_TIMEOUT:
            SessionManager.invalidate_session(session_id)
            return False, None
        
        # Check idle timeout
        if current_time - session_data['last_activity'] > SecurityConfig.IDLE_TIMEOUT:
            SessionManager.invalidate_session(session_id)
            return False, None
        
        # Validate fingerprint
        current_fingerprint = SessionManager.generate_fingerprint(request)
        if session_data['fingerprint'] != current_fingerprint:
            logger.warning(f"Session fingerprint mismatch for session {session_id}")
            SessionManager.invalidate_session(session_id)
            return False, None
        
        # Update last activity
        session_data['last_activity'] = current_time
        cache.set(f"session:{session_id}", session_data, SecurityConfig.SESSION_TIMEOUT)
        
        return True, session_data
    
    @staticmethod
    def generate_fingerprint(request: HttpRequest) -> str:
        """Generate browser fingerprint"""
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
        
        fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    @staticmethod
    def invalidate_session(session_id: str):
        """Invalidate session"""
        cache.delete(f"session:{session_id}")

class SecurityMiddleware(MiddlewareMixin):
    """Production-grade security middleware with enhanced protection"""
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        skip_paths = ['/admin/', '/static/', '/media/', '/health/']
        if any(request.path.startswith(path) for path in skip_paths):
            return None
        
        client_ip = ThreatDetector.get_client_ip(request)
        
        # Enhanced IP blocking with progressive penalties
        if self._is_blocked_ip(client_ip):
            AuditLogger.log_security_event('blocked_ip_access', None, request, {'ip': client_ip})
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        # Comprehensive rate limiting
        rate_check = self._comprehensive_rate_limit(client_ip, request.path)
        if not rate_check['allowed']:
            return JsonResponse({'error': rate_check['message']}, status=rate_check['status_code'])
        
        # Advanced threat detection
        threat_analysis = ThreatDetector.detect_suspicious_patterns(request)
        if threat_analysis['action'] == 'block':
            self._escalate_threat_response(client_ip, threat_analysis)
            incident_id = self._generate_incident_id()
            AuditLogger.log_security_event('threat_blocked', None, request, {
                'incident_id': incident_id,
                'threats': threat_analysis['threats'],
                'risk_score': threat_analysis['risk_score']
            })
            return JsonResponse({'error': 'Request blocked', 'incident_id': incident_id}, status=403)
        
        # Enhanced token validation for protected endpoints
        if request.path.startswith('/api/') and not self._is_public_endpoint(request.path):
            token_validation = self._enhanced_token_validation(request)
            if not token_validation['valid']:
                return JsonResponse({
                    'error': token_validation['error'],
                    'require_reauth': token_validation.get('require_reauth', False)
                }, status=401)
        
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to response"""
        
        # Add security headers
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response[header] = value
        
        # Add HSTS header for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    def _comprehensive_rate_limit(self, client_ip: str, path: str) -> Dict[str, Any]:
        """Comprehensive rate limiting with multiple tiers"""
        # General rate limiting
        general_key = f"rate_limit:{client_ip}"
        current_requests = cache.get(general_key, 0)
        if current_requests >= SecurityConfig.RATE_LIMIT_REQUESTS:
            return {'allowed': False, 'message': 'Rate limit exceeded', 'status_code': 429}
        cache.set(general_key, current_requests + 1, SecurityConfig.RATE_LIMIT_WINDOW)
        
        # Login-specific rate limiting
        if 'login' in path:
            login_key = f"login_attempts:{client_ip}"
            login_attempts = cache.get(login_key, 0)
            if login_attempts >= SecurityConfig.LOGIN_RATE_LIMIT:
                return {'allowed': False, 'message': 'Login rate limit exceeded', 'status_code': 429}
            cache.set(login_key, login_attempts + 1, SecurityConfig.LOGIN_RATE_WINDOW)
        
        # API endpoint specific limits
        if '/api/' in path:
            api_key = f"api_rate_limit:{client_ip}"
            api_requests = cache.get(api_key, 0)
            if api_requests >= 200:  # Higher limit for API
                return {'allowed': False, 'message': 'API rate limit exceeded', 'status_code': 429}
            cache.set(api_key, api_requests + 1, 3600)
        
        return {'allowed': True}
    
    def _validate_token(self, request: HttpRequest) -> bool:
        """Basic token validation for backward compatibility"""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return False
        
        token = auth_header.split(' ')[1]
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        # Check blacklist
        if cache.get(f"blacklisted_token:{token_hash}"):
            return False
        
        try:
            UntypedToken(token)
            return True
        except (InvalidToken, TokenError):
            return False
    
    def _enhanced_token_validation(self, request: HttpRequest) -> Dict[str, Any]:
        """Enhanced JWT token validation with session correlation"""
        
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return {'valid': False, 'error': 'Missing or invalid authorization header'}
        
        token = auth_header.split(' ')[1]
        
        # Check if token is blacklisted
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        if cache.get(f"blacklisted_token:{token_hash}"):
            return {'valid': False, 'error': 'Token has been revoked', 'require_reauth': True}
        
        try:
            # Validate token structure and signature
            UntypedToken(token)
            
            # Decode token to get user info
            decoded_token = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=['HS256'],
                options={"verify_signature": False}
            )
            
            user_id = decoded_token.get('user_id')
            if user_id:
                # Check if user account is locked or suspended
                if cache.get(f"account_suspended:{user_id}"):
                    return {'valid': False, 'error': 'Account suspended', 'require_reauth': True}
                
                # Check if user is forced to logout
                if cache.get(f"force_logout:{user_id}"):
                    return {'valid': False, 'error': 'Session invalidated', 'require_reauth': True}
                
                # Enhanced session validation with multiple factors
                session_validation = self._validate_session_security(decoded_token, request, user_id)
                if not session_validation['valid']:
                    return {
                        'valid': False, 
                        'error': session_validation['error'],
                        'require_reauth': session_validation.get('require_reauth', True)
                    }
                
                # Update token usage tracking
                self._track_token_usage(user_id, client_ip=ThreatDetector.get_client_ip(request))
            
            return {'valid': True, 'user_id': user_id}
            
        except (InvalidToken, TokenError, jwt.InvalidTokenError) as e:
            return {'valid': False, 'error': 'Invalid token format', 'require_reauth': True}
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return {'valid': False, 'error': 'Token validation failed', 'require_reauth': True}
    
    def _is_blocked_ip(self, client_ip: str) -> bool:
        """Check if IP is in blocked list"""
        return cache.get(f"blocked_ip:{client_ip}", False)
    
    def _escalate_threat_response(self, client_ip: str, threat_analysis: Dict[str, Any]):
        """Escalate threat response based on severity"""
        risk_score = threat_analysis['risk_score']
        
        if risk_score >= 80:
            # Block IP for 24 hours
            cache.set(f"blocked_ip:{client_ip}", True, 86400)
            logger.critical(f"IP {client_ip} blocked for 24h due to high-risk threats: {threat_analysis['threats']}")
        elif risk_score >= 60:
            # Temporary block for 1 hour
            cache.set(f"blocked_ip:{client_ip}", True, 3600)
            logger.error(f"IP {client_ip} temporarily blocked due to threats: {threat_analysis['threats']}")
    
    def _generate_incident_id(self) -> str:
        """Generate unique incident ID for tracking"""
        return f"INC-{int(time.time())}-{hashlib.md5(str(time.time()).encode()).hexdigest()[:8].upper()}"
    
    def _validate_session_security(self, decoded_token: Dict, request: HttpRequest, user_id: int) -> Dict[str, Any]:
        """Validate session security with multiple factors"""
        
        # Check token expiration with buffer
        exp = decoded_token.get('exp', 0)
        if exp < time.time() + 300:  # 5-minute buffer
            return {'valid': False, 'error': 'Token near expiration', 'require_reauth': True}
        
        # Validate session fingerprint
        token_fingerprint = decoded_token.get('fingerprint')
        if token_fingerprint:
            current_fingerprint = SessionManager.generate_fingerprint(request)
            if token_fingerprint != current_fingerprint:
                logger.warning(f"Session fingerprint mismatch for user {user_id}")
                return {'valid': False, 'error': 'Session security violation', 'require_reauth': True}
        
        # Check for concurrent session limits
        active_sessions = cache.get(f"active_sessions:{user_id}", 0)
        if active_sessions > 5:  # Max 5 concurrent sessions
            return {'valid': False, 'error': 'Too many active sessions', 'require_reauth': True}
        
        return {'valid': True}
    
    def _track_token_usage(self, user_id: int, client_ip: str):
        """Track token usage for analytics and security"""
        usage_key = f"token_usage:{user_id}:{client_ip}"
        current_usage = cache.get(usage_key, 0)
        cache.set(usage_key, current_usage + 1, 3600)  # Track for 1 hour
        
        # Update active sessions count
        sessions_key = f"active_sessions:{user_id}"
        cache.set(sessions_key, cache.get(sessions_key, 0) + 1, 300)  # 5-minute window
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public"""
        public_endpoints = [
            '/api/auth/login/',
            '/api/auth/student-login/',
            '/api/auth/register/',
            '/api/auth/token/refresh/',
            '/api/schools/register/',
            '/api/health/',
            '/api/schools/public/',
        ]
        return path in public_endpoints

class AuditLogger:
    """Enhanced security audit logging with structured data"""
    
    @staticmethod
    def log_security_event(event_type: str, user_id: Optional[int], 
                          request: HttpRequest, extra_data: Optional[Dict] = None):
        """Log security events for comprehensive audit trail"""
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ThreatDetector.get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'path': request.path,
            'method': request.method,
            'session_id': request.session.session_key if hasattr(request, 'session') else None,
            'extra_data': extra_data or {}
        }
        
        # Enhanced logging based on event criticality
        critical_events = ['account_locked', 'threat_detected', 'suspicious_activity', 'account_suspended']
        warning_events = ['failed_login', 'failed_student_login', 'invalid_token_access', 'rate_limit_exceeded']
        info_events = ['successful_login', 'successful_student_login', 'logout', 'student_logout']
        
        if event_type in critical_events:
            logger.critical(f"CRITICAL_SECURITY_EVENT: {json.dumps(log_data)}")
        elif event_type in warning_events:
            logger.warning(f"SECURITY_WARNING: {json.dumps(log_data)}")
        elif event_type in info_events:
            logger.info(f"SECURITY_INFO: {json.dumps(log_data)}")
        else:
            logger.debug(f"SECURITY_DEBUG: {json.dumps(log_data)}")
        
        # Store in cache for real-time monitoring (last 100 events)
        recent_events_key = "recent_security_events"
        recent_events = cache.get(recent_events_key, [])
        recent_events.append(log_data)
        recent_events = recent_events[-100:]  # Keep last 100 events
        cache.set(recent_events_key, recent_events, 3600)  # Store for 1 hour
    
    @staticmethod
    def get_recent_security_events(limit: int = 50) -> List[Dict]:
        """Get recent security events for monitoring"""
        recent_events = cache.get("recent_security_events", [])
        return recent_events[-limit:]
    
    @staticmethod
    def get_security_metrics() -> Dict[str, Any]:
        """Get security metrics for dashboard"""
        recent_events = AuditLogger.get_recent_security_events(100)
        
        metrics = {
            'total_events': len(recent_events),
            'failed_logins': len([e for e in recent_events if 'failed_login' in e['event_type']]),
            'successful_logins': len([e for e in recent_events if 'successful_login' in e['event_type']]),
            'blocked_attempts': len([e for e in recent_events if 'blocked' in e['event_type']]),
            'unique_ips': len(set([e['ip_address'] for e in recent_events])),
            'last_hour_events': len([e for e in recent_events if 
                                   datetime.fromisoformat(e['timestamp']) > datetime.now() - timedelta(hours=1)])
        }
        
        return metrics
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model, authenticate
from django.http import HttpRequest
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from datetime import datetime, timedelta
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
import logging
import hashlib
import time
import re
import secrets
import string
from .security_middleware import SecurityConfig, ThreatDetector, SessionManager, AuditLogger
from .security_config import SecuritySettings, SecurityValidator

from .serializers import (
    UserSerializer, 
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer,
    ChangePasswordSerializer,
    SchoolRegistrationSerializer
)

User = get_user_model()
from schools.models import Class as SchoolClass
from students.models import Student

logger = logging.getLogger(__name__)

class SecureTokenObtainPairView(TokenObtainPairView):
    """Production-grade login with comprehensive security"""
    permission_classes = [permissions.AllowAny]
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').lower().strip()
        password = request.data.get('password', '')
        client_ip = ThreatDetector.get_client_ip(request)
        
        # Enhanced input validation
        input_validation = self._validate_login_input(email, password, request)
        if not input_validation['valid']:
            return Response({'error': input_validation['errors'][0]}, status=400)
        
        # Comprehensive security check
        security_check = self._comprehensive_security_check(email, client_ip, request)
        if not security_check['allowed']:
            return Response({'error': security_check['message']}, status=security_check['status_code'])
        
        # Account lockout check
        lockout_check = self._check_account_lockout(email)
        if not lockout_check['allowed']:
            return Response({'error': lockout_check['message']}, status=423)
        
        try:
            user = User.objects.get(email=email, is_active=True)
            
            # Enhanced password verification
            password_check = self._enhanced_password_check(user, password, request)
            if not password_check['valid']:
                self._handle_failed_login(email, client_ip, request, password_check['reason'])
                return Response({'error': 'Invalid credentials'}, status=401)
            
            # Generate secure tokens
            tokens = self._generate_secure_tokens(user, request)
            
            # Handle successful login
            self._handle_successful_login(email, client_ip, user, request)
            
            response_data = {
                'access': tokens['access'],
                'refresh': tokens['refresh'],
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'role': user.role,
                    'school': user.school.name if user.school else None,
                    'permissions': self._get_user_permissions(user),
                    'security_level': self._determine_security_level(user)
                }
            }
            
            response = Response(response_data)
            return self._add_security_headers(response, user)
            
        except User.DoesNotExist:
            # Timing attack protection
            self._secure_password_check(None, password)
            self._handle_failed_login(email, client_ip, request, 'user_not_found')
            return Response({'error': 'Invalid credentials'}, status=401)
        except Exception as e:
            logger.error(f"Login error for {email}: {str(e)}")
            return Response({'error': 'Authentication failed'}, status=500)
    
    def _validate_login_input(self, email: str, password: str, request: HttpRequest) -> Dict[str, Any]:
        """Enhanced input validation using centralized security validator"""
        errors = []
        
        # Validate email
        email_validation = SecurityValidator.validate_email(email)
        if not email_validation['valid']:
            errors.append(email_validation['error'])
        
        # Validate password
        password_validation = SecurityValidator.validate_password(password, is_student=False)
        if not password_validation['valid']:
            errors.extend(password_validation['errors'])
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    def _comprehensive_security_check(self, email: str, client_ip: str, request: HttpRequest) -> Dict[str, Any]:
        """Comprehensive security check combining multiple factors"""
        
        # Check if IP is temporarily blocked
        if cache.get(f"temp_blocked_ip:{client_ip}"):
            return {
                'allowed': False,
                'message': 'IP temporarily blocked due to suspicious activity',
                'status_code': status.HTTP_429_TOO_MANY_REQUESTS
            }
        
        # Enhanced rate limiting checks
        rate_checks = [
            self._check_ip_rate_limit(client_ip),
            self._check_email_rate_limit(email),
            self._check_global_rate_limit()
        ]
        
        for check in rate_checks:
            if not check['allowed']:
                return check
        
        # Behavioral analysis
        behavior_score = self._analyze_login_behavior(email, client_ip, request)
        if behavior_score > 70:
            return {
                'allowed': False,
                'message': 'Login attempt flagged for review',
                'status_code': status.HTTP_403_FORBIDDEN
            }
        
        return {'allowed': True}
    
    def _check_ip_rate_limit(self, client_ip: str) -> Dict[str, Any]:
        """Check IP-based rate limiting"""
        ip_key = f"login_ip_attempts:{client_ip}"
        ip_attempts = cache.get(ip_key, 0)
        
        if ip_attempts >= 15:  # 15 attempts per IP per hour
            cache.set(f"temp_blocked_ip:{client_ip}", True, 3600)  # Block for 1 hour
            return {
                'allowed': False,
                'message': 'Too many login attempts from this IP',
                'status_code': status.HTTP_429_TOO_MANY_REQUESTS
            }
        
        cache.set(ip_key, ip_attempts + 1, 3600)
        return {'allowed': True}
    
    def _check_email_rate_limit(self, email: str) -> Dict[str, Any]:
        """Check email-based rate limiting"""
        email_key = f"login_email_attempts:{email}"
        email_attempts = cache.get(email_key, 0)
        
        if email_attempts >= 8:  # 8 attempts per email per 30 minutes
            return {
                'allowed': False,
                'message': 'Too many login attempts for this account',
                'status_code': status.HTTP_429_TOO_MANY_REQUESTS
            }
        
        cache.set(email_key, email_attempts + 1, 1800)
        return {'allowed': True}
    
    def _check_global_rate_limit(self) -> Dict[str, Any]:
        """Check global system rate limiting"""
        global_key = "global_login_attempts"
        global_attempts = cache.get(global_key, 0)
        
        if global_attempts >= 1000:  # 1000 global attempts per minute
            return {
                'allowed': False,
                'message': 'System temporarily overloaded',
                'status_code': status.HTTP_503_SERVICE_UNAVAILABLE
            }
        
        cache.set(global_key, global_attempts + 1, 60)
        return {'allowed': True}
    
    def _analyze_login_behavior(self, email: str, client_ip: str, request: HttpRequest) -> int:
        """Analyze login behavior for suspicious patterns"""
        score = 0
        
        # Check for rapid successive attempts
        last_attempt_key = f"last_login_attempt:{email}"
        last_attempt = cache.get(last_attempt_key, 0)
        current_time = time.time()
        
        if last_attempt and (current_time - last_attempt) < 5:  # Less than 5 seconds
            score += 30
        
        cache.set(last_attempt_key, current_time, 300)
        
        # Check for unusual user agent patterns
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        if not user_agent or len(user_agent) < 10:
            score += 25
        
        # Check for known bot patterns
        bot_patterns = ['bot', 'crawler', 'spider', 'scraper']
        if any(pattern in user_agent.lower() for pattern in bot_patterns):
            score += 40
        
        # Check for geographic anomalies (simplified)
        previous_ip_key = f"previous_login_ip:{email}"
        previous_ip = cache.get(previous_ip_key)
        if previous_ip and previous_ip != client_ip:
            # Different IP - could be legitimate or suspicious
            score += 15
        
        cache.set(previous_ip_key, client_ip, 86400)  # Store for 24 hours
        
        return score
    
    def _enhanced_password_check(self, user: User, password: str, request: HttpRequest) -> Dict[str, Any]:
        """Enhanced password verification with security measures"""
        
        # Timing attack protection - always perform hash operation
        password_valid = check_password(password, user.password)
        
        if not password_valid:
            return {
                'valid': False,
                'reason': 'invalid_password'
            }
        
        # Check if password needs to be updated (weak hash)
        if user.password.startswith('pbkdf2_sha256$') and '$260000$' not in user.password:
            # Old hash algorithm, should be updated
            logger.info(f"Updating password hash for user {user.email}")
            user.set_password(password)
            user.save(update_fields=['password'])
        
        # Check for password expiration (if implemented)
        password_age_key = f"password_age:{user.id}"
        password_set_time = cache.get(password_age_key, time.time())
        
        # If password is older than 90 days, flag for update
        if time.time() - password_set_time > 7776000:  # 90 days
            logger.warning(f"Password expired for user {user.email}")
            # Don't block login, but flag for password change
        
        return {'valid': True, 'reason': 'success'}
    
    def _generate_secure_tokens(self, user: User, request: HttpRequest) -> Dict[str, str]:
        """Generate secure tokens with enhanced claims"""
        
        # Generate refresh token
        refresh = RefreshToken.for_user(user)
        
        # Add custom claims to access token
        access_token = refresh.access_token
        
        # Add security fingerprint
        fingerprint = SessionManager.generate_fingerprint(request)
        access_token['fingerprint'] = fingerprint
        
        # Add session metadata
        access_token['login_time'] = int(time.time())
        access_token['client_ip'] = ThreatDetector.get_client_ip(request)
        access_token['user_agent_hash'] = hashlib.sha256(
            request.META.get('HTTP_USER_AGENT', '').encode()
        ).hexdigest()[:16]
        
        # Add role-based permissions
        access_token['permissions'] = self._get_user_permissions(user)
        access_token['security_level'] = self._determine_security_level(user)
        
        return {
            'access': str(access_token),
            'refresh': str(refresh)
        }
    
    def _handle_failed_login(self, email: str, client_ip: str, request: HttpRequest, reason: str):
        """Enhanced failed login handling with progressive lockout"""
        
        # Track failed attempts with detailed metadata
        failed_attempts_key = f"failed_attempts:{email}"
        failed_attempts = cache.get(failed_attempts_key, [])
        
        # Add current attempt
        attempt_data = {
            'timestamp': time.time(),
            'ip': client_ip,
            'reason': reason,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100]
        }
        failed_attempts.append(attempt_data)
        
        # Keep only last 10 attempts
        failed_attempts = failed_attempts[-10:]
        cache.set(failed_attempts_key, failed_attempts, 3600)
        
        # Calculate lockout duration based on attempt count
        recent_attempts = [a for a in failed_attempts if time.time() - a['timestamp'] < 1800]  # Last 30 minutes
        attempt_count = len(recent_attempts)
        
        if attempt_count >= 5:
            # Progressive lockout: 5 min, 15 min, 30 min, 1 hour, 2 hours
            lockout_durations = [300, 900, 1800, 3600, 7200]
            lockout_index = min(attempt_count - 5, len(lockout_durations) - 1)
            lockout_duration = lockout_durations[lockout_index]
            
            lockout_data = {
                'until': time.time() + lockout_duration,
                'attempts': attempt_count,
                'reason': 'too_many_failed_attempts'
            }
            
            cache.set(f"account_locked:{email}", lockout_data, lockout_duration)
            
            AuditLogger.log_security_event('account_locked', None, request, {
                'email': email,
                'attempt_count': attempt_count,
                'lockout_duration': lockout_duration,
                'reason': reason
            })
        
        # Log failed attempt
        AuditLogger.log_security_event('failed_login', None, request, {
            'email': email,
            'reason': reason,
            'attempt_count': attempt_count
        })
    
    def _handle_successful_login(self, email: str, client_ip: str, user: User, request: HttpRequest):
        """Handle successful login with security updates"""
        
        # Clear failed attempts
        cache.delete(f"failed_attempts:{email}")
        cache.delete(f"login_ip_attempts:{client_ip}")
        cache.delete(f"login_email_attempts:{email}")
        cache.delete(f"account_locked:{email}")
        
        # Update user login metadata
        user.last_login = datetime.now()
        user.save(update_fields=['last_login'])
        
        # Track successful login
        login_history_key = f"login_history:{user.id}"
        login_history = cache.get(login_history_key, [])
        
        login_data = {
            'timestamp': time.time(),
            'ip': client_ip,
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100],
            'success': True
        }
        
        login_history.append(login_data)
        login_history = login_history[-20:]  # Keep last 20 logins
        cache.set(login_history_key, login_history, 86400 * 7)  # Store for 7 days
        
        # Log successful login
        AuditLogger.log_security_event('successful_login', user.id, request, {
            'email': email,
            'login_method': 'standard'
        })
    
    def _check_account_lockout(self, email: str) -> Dict[str, Any]:
        """Enhanced account lockout with progressive delays"""
        lockout_key = f"account_locked:{email}"
        lockout_data = cache.get(lockout_key)
        
        if lockout_data:
            if isinstance(lockout_data, dict):
                lockout_until = lockout_data.get('until', 0)
                attempt_count = lockout_data.get('attempts', 0)
                
                if time.time() < lockout_until:
                    remaining_time = int(lockout_until - time.time())
                    return {
                        'allowed': False,
                        'message': f'Account locked. Try again in {remaining_time} seconds.',
                        'remaining_time': remaining_time,
                        'attempt_count': attempt_count
                    }
            else:
                # Legacy boolean lockout
                return {
                    'allowed': False,
                    'message': 'Account temporarily locked due to failed login attempts'
                }
        
        return {'allowed': True}
    
    def _secure_password_check(self, user, password: str):
        """Secure password check with timing attack protection"""
        if user:
            return check_password(password, user.password)
        else:
            # Perform dummy hash to prevent timing attacks
            check_password(password, 'pbkdf2_sha256$260000$dummy$dummy')
            return False
    
    def _log_security_event(self, event_type, email, client_ip, extra_data=None):
        """Log security events for audit"""
        log_data = {
            'event': event_type,
            'email': email,
            'ip': client_ip,
            'timestamp': time.time(),
            'extra': extra_data or {}
        }
        
        if event_type in ['failed_login', 'account_locked', 'account_locked_attempt']:
            logger.warning(f"Security Event: {log_data}")
        else:
            logger.info(f"Security Event: {log_data}")
    
    def _get_user_permissions(self, user: User) -> list:
        """Get user permissions based on role"""
        role_permissions = {
            'SUPER_ADMIN': ['all'],
            'SCHOOL_ADMIN': ['school_manage', 'user_manage', 'report_view'],
            'PRINCIPAL': ['school_manage', 'user_manage', 'report_view'],
            'TEACHER': ['class_manage', 'assignment_manage', 'grade_manage'],
            'STUDENT': ['assignment_view', 'grade_view', 'profile_view']
        }
        return role_permissions.get(user.role, ['profile_view'])
    
    def _determine_security_level(self, user: User) -> str:
        """Determine user security level"""
        if user.role in ['SUPER_ADMIN', 'SCHOOL_ADMIN']:
            return 'high'
        elif user.role in ['PRINCIPAL', 'TEACHER']:
            return 'medium'
        else:
            return 'standard'
    
    def _add_security_headers(self, response: Response, user: User):
        """Add security headers to response"""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        
        # Add user-specific security headers
        if user.role in ['SUPER_ADMIN', 'SCHOOL_ADMIN']:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response


class RegisterView(generics.CreateAPIView):
    """User registration view"""
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = UserRegistrationSerializer


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update user profile"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    """Secure password change with enhanced validation"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        old_password = serializer.validated_data.get('old_password')
        new_password = serializer.validated_data.get('new_password')
        
        # Verify current password
        if not user.check_password(old_password):
            # Log failed password change attempt
            client_ip = self._get_client_ip(request)
            logger.warning(f"Failed password change attempt for {user.email} from {client_ip}")
            return Response(
                {"old_password": "Current password is incorrect"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Additional password strength validation
        password_validation = self._validate_password_strength(new_password)
        if not password_validation['valid']:
            return Response(
                {"new_password": password_validation['errors']}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if new password is different from old
        if user.check_password(new_password):
            return Response(
                {"new_password": "New password must be different from current password"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            with transaction.atomic():
                # Change password
                user.set_password(new_password)
                user.save(update_fields=['password'])
                
                # Invalidate all existing sessions for this user
                self._invalidate_user_sessions(user)
                
                # Log successful password change
                client_ip = self._get_client_ip(request)
                logger.info(f"Password changed successfully for {user.email} from {client_ip}")
                
                return Response({
                    "message": "Password changed successfully. Please log in again.",
                    "require_reauth": True
                }, status=status.HTTP_200_OK)
                
        except Exception as e:
            logger.error(f"Password change error for {user.email}: {str(e)}")
            return Response(
                {"error": "Failed to change password. Please try again."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _validate_password_strength(self, password):
        """Validate password strength"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = ['password', '123456', 'password123', 'admin', 'qwerty']
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _invalidate_user_sessions(self, user):
        """Invalidate all sessions for user after password change"""
        # This would require implementing a user session tracking system
        # For now, we'll use cache-based approach
        cache.set(f"force_logout:{user.id}", True, 86400)  # 24 hours
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')


class UserListView(generics.ListAPIView):
    """List users (admin only)"""
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_super_admin:
            return User.objects.all()
        elif user.is_school_admin or user.is_principal:
            return User.objects.filter(school=user.school)
        else:
            return User.objects.filter(id=user.id)


class CreateTeacherView(generics.CreateAPIView):
    """Create teacher account (school admin only)"""
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # Accept optional class_id for assigning class_teacher
        current_user = request.user
        if not (current_user.is_school_admin or current_user.is_principal):
            raise permissions.PermissionDenied("Only school admins can create teachers")

        # Copy request data and remove non-serializer fields
        data = request.data.copy()
        class_id = data.pop('class_id', None)

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        created_teacher = serializer.instance

        # Assign as class teacher if class_id provided
        if class_id:
            try:
                cls = SchoolClass.objects.get(id=class_id, school=current_user.school)
                cls.class_teacher = created_teacher
                cls.save(update_fields=['class_teacher'])
            except SchoolClass.DoesNotExist:
                pass  # Ignore invalid class_id silently

        headers = self.get_success_headers(serializer.data)
        return Response(UserSerializer(created_teacher).data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(school=user.school, role='TEACHER')


class LogoutView(APIView):
    """Secure logout with token blacklisting and session cleanup"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            # Get tokens from request
            refresh_token = request.data.get('refresh_token')
            access_token = request.META.get('HTTP_AUTHORIZATION', '').replace('Bearer ', '')
            
            # Blacklist refresh token
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.warning(f"Failed to blacklist refresh token: {str(e)}")
            
            # Blacklist access token
            if access_token:
                token_hash = hashlib.sha256(access_token.encode()).hexdigest()
                cache.set(f"blacklisted_token:{token_hash}", True, 86400)  # 24 hours
            
            # Log logout event
            client_ip = self._get_client_ip(request)
            logger.info(f"User logout: {request.user.email} from IP: {client_ip}")
            
            return Response({
                'message': 'Successfully logged out',
                'timestamp': time.time()
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({
                'message': 'Logout completed',
                'timestamp': time.time()
            }, status=status.HTTP_200_OK)
    
    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')


class RegisterSchoolView(APIView):
    """Endpoint for a new school to self-register and obtain JWT tokens"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SchoolRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()
        school = user.school

        # Issue tokens
        token_serializer = CustomTokenObtainPairSerializer(data={'email': user.email, 'password': request.data['password']})
        token_serializer.is_valid(raise_exception=True)
        data = token_serializer.validated_data
        data['school'] = {
            'id': school.id,
            'name': school.name,
            'subscription_plan': school.subscription_plan,
        }
        return Response(data, status=status.HTTP_201_CREATED)

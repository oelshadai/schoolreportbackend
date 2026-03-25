"""
Centralized security configuration for the school SaaS system.
This module contains all security-related constants and configurations.
"""

from typing import Dict, List, Any
from datetime import timedelta

class SecuritySettings:
    """Centralized security settings"""
    
    # Authentication Security
    MAX_LOGIN_ATTEMPTS = 5
    LOGIN_LOCKOUT_DURATION = 3600  # 1 hour in seconds
    PASSWORD_MIN_LENGTH = 8
    PASSWORD_MAX_LENGTH = 128
    
    # Student Authentication (more lenient)
    MAX_STUDENT_LOGIN_ATTEMPTS = 10
    STUDENT_LOCKOUT_DURATION = 1800  # 30 minutes
    STUDENT_PASSWORD_MIN_LENGTH = 3
    
    # Rate Limiting
    GENERAL_RATE_LIMIT = 100  # requests per hour
    LOGIN_RATE_LIMIT = 15     # login attempts per hour per IP
    API_RATE_LIMIT = 200      # API requests per hour
    STUDENT_LOGIN_RATE_LIMIT = 20  # student login attempts per hour per IP
    
    # Session Management
    SESSION_TIMEOUT = 28800   # 8 hours
    IDLE_TIMEOUT = 1800       # 30 minutes
    MAX_CONCURRENT_SESSIONS = 5
    
    # Token Security
    TOKEN_BLACKLIST_DURATION = 86400  # 24 hours
    TOKEN_REFRESH_THRESHOLD = 300     # 5 minutes before expiry
    
    # Threat Detection
    THREAT_SCORE_THRESHOLD = 50
    HIGH_RISK_THRESHOLD = 80
    CRITICAL_RISK_THRESHOLD = 90
    
    # IP Blocking
    TEMP_BLOCK_DURATION = 1800    # 30 minutes
    PERMANENT_BLOCK_DURATION = 86400  # 24 hours
    
    # Security Headers
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Referrer-Policy': 'strict-origin-when-cross-origin',
        'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        'Pragma': 'no-cache'
    }
    
    # Suspicious Patterns
    SQL_INJECTION_PATTERNS = [
        'union', 'select', 'drop', 'delete', 'insert', 'update', 
        '--', ';', 'exec', 'execute', 'sp_', 'xp_'
    ]
    
    XSS_PATTERNS = [
        '<script', 'javascript:', 'onerror=', 'onload=', 'onclick=',
        'onmouseover=', 'onfocus=', 'onblur=', 'eval(', 'alert('
    ]
    
    # User Agent Patterns (bots/crawlers)
    BOT_PATTERNS = [
        'bot', 'crawler', 'spider', 'scraper', 'curl', 'wget',
        'python-requests', 'postman', 'insomnia'
    ]
    
    # Public Endpoints (no authentication required)
    PUBLIC_ENDPOINTS = [
        '/api/auth/login/',
        '/api/auth/student-login/',
        '/api/auth/register/',
        '/api/auth/token/refresh/',
        '/api/schools/register/',
        '/api/health/',
        '/api/schools/public/',
    ]
    
    # Role-based Permissions
    ROLE_PERMISSIONS = {
        'SUPER_ADMIN': ['all'],
        'SCHOOL_ADMIN': ['school_manage', 'user_manage', 'report_view', 'student_manage'],
        'PRINCIPAL': ['school_manage', 'user_manage', 'report_view', 'student_manage'],
        'TEACHER': ['class_manage', 'assignment_manage', 'grade_manage', 'attendance_manage'],
        'STUDENT': ['assignment_view', 'grade_view', 'profile_view', 'attendance_view']
    }
    
    # Security Levels
    SECURITY_LEVELS = {
        'SUPER_ADMIN': 'critical',
        'SCHOOL_ADMIN': 'high',
        'PRINCIPAL': 'high',
        'TEACHER': 'medium',
        'STUDENT': 'standard'
    }
    
    # Lockout Durations (progressive)
    PROGRESSIVE_LOCKOUT_DURATIONS = [300, 900, 1800, 3600, 7200]  # 5min, 15min, 30min, 1h, 2h
    STUDENT_LOCKOUT_DURATIONS = [300, 600, 1200]  # 5min, 10min, 20min
    
    # Audit Log Settings
    AUDIT_LOG_RETENTION = 2592000  # 30 days
    SECURITY_EVENT_CACHE_SIZE = 100
    SECURITY_EVENT_CACHE_DURATION = 3600  # 1 hour
    
    @classmethod
    def get_lockout_duration(cls, attempt_count: int, is_student: bool = False) -> int:
        """Get progressive lockout duration based on attempt count"""
        durations = cls.STUDENT_LOCKOUT_DURATIONS if is_student else cls.PROGRESSIVE_LOCKOUT_DURATIONS
        index = min(attempt_count - cls.MAX_LOGIN_ATTEMPTS, len(durations) - 1)
        return durations[max(0, index)]
    
    @classmethod
    def get_user_permissions(cls, role: str) -> List[str]:
        """Get permissions for user role"""
        return cls.ROLE_PERMISSIONS.get(role, ['profile_view'])
    
    @classmethod
    def get_security_level(cls, role: str) -> str:
        """Get security level for user role"""
        return cls.SECURITY_LEVELS.get(role, 'standard')
    
    @classmethod
    def is_public_endpoint(cls, path: str) -> bool:
        """Check if endpoint is public"""
        return path in cls.PUBLIC_ENDPOINTS
    
    @classmethod
    def is_suspicious_pattern(cls, text: str) -> Dict[str, Any]:
        """Check for suspicious patterns in text"""
        text_lower = text.lower()
        threats = []
        risk_score = 0
        
        # Check SQL injection patterns
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if pattern in text_lower:
                threats.append(f"SQL injection pattern: {pattern}")
                risk_score += 30
        
        # Check XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if pattern in text_lower:
                threats.append(f"XSS pattern: {pattern}")
                risk_score += 25
        
        return {
            'threats': threats,
            'risk_score': risk_score,
            'is_suspicious': risk_score > 0
        }

class SecurityMetrics:
    """Security metrics and monitoring"""
    
    @staticmethod
    def get_threat_level(risk_score: int) -> str:
        """Get threat level based on risk score"""
        if risk_score >= SecuritySettings.CRITICAL_RISK_THRESHOLD:
            return 'CRITICAL'
        elif risk_score >= SecuritySettings.HIGH_RISK_THRESHOLD:
            return 'HIGH'
        elif risk_score >= SecuritySettings.THREAT_SCORE_THRESHOLD:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    @staticmethod
    def should_block_request(risk_score: int) -> bool:
        """Determine if request should be blocked"""
        return risk_score >= SecuritySettings.THREAT_SCORE_THRESHOLD
    
    @staticmethod
    def get_block_duration(risk_score: int) -> int:
        """Get block duration based on risk score"""
        if risk_score >= SecuritySettings.CRITICAL_RISK_THRESHOLD:
            return SecuritySettings.PERMANENT_BLOCK_DURATION
        elif risk_score >= SecuritySettings.HIGH_RISK_THRESHOLD:
            return SecuritySettings.PERMANENT_BLOCK_DURATION // 2  # 12 hours
        else:
            return SecuritySettings.TEMP_BLOCK_DURATION

class SecurityValidator:
    """Security validation utilities"""
    
    @staticmethod
    def validate_email(email: str) -> Dict[str, Any]:
        """Validate email format and security"""
        import re
        
        if not email:
            return {'valid': False, 'error': 'Email is required'}
        
        # Basic email format validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return {'valid': False, 'error': 'Invalid email format'}
        
        # Check for suspicious patterns
        suspicious_check = SecuritySettings.is_suspicious_pattern(email)
        if suspicious_check['is_suspicious']:
            return {'valid': False, 'error': 'Invalid characters in email'}
        
        return {'valid': True}
    
    @staticmethod
    def validate_password(password: str, is_student: bool = False) -> Dict[str, Any]:
        """Validate password strength"""
        import re
        
        errors = []
        min_length = SecuritySettings.STUDENT_PASSWORD_MIN_LENGTH if is_student else SecuritySettings.PASSWORD_MIN_LENGTH
        
        if not password:
            return {'valid': False, 'errors': ['Password is required']}
        
        if len(password) < min_length:
            errors.append(f'Password must be at least {min_length} characters long')
        
        if len(password) > SecuritySettings.PASSWORD_MAX_LENGTH:
            errors.append('Password is too long')
        
        # For non-student users, enforce stronger password requirements
        if not is_student:
            if not re.search(r'[A-Z]', password):
                errors.append('Password must contain at least one uppercase letter')
            
            if not re.search(r'[a-z]', password):
                errors.append('Password must contain at least one lowercase letter')
            
            if not re.search(r'\d', password):
                errors.append('Password must contain at least one number')
            
            if not re.search(r'[!@#$%^&*(),.?\":{}|<>]', password):
                errors.append('Password must contain at least one special character')
        
        # Check for common passwords
        common_passwords = ['password', '123456', 'password123', 'admin', 'qwerty', 'letmein']
        if password.lower() in common_passwords:
            errors.append('Password is too common')
        
        # Check for suspicious patterns
        suspicious_check = SecuritySettings.is_suspicious_pattern(password)
        if suspicious_check['is_suspicious']:
            errors.append('Password contains invalid characters')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    @staticmethod
    def validate_student_id(student_id: str) -> Dict[str, Any]:
        """Validate student ID format"""
        import re
        
        if not student_id:
            return {'valid': False, 'error': 'Student ID is required'}
        
        # Student ID format validation (alphanumeric, underscore, hyphen)
        if not re.match(r'^[A-Za-z0-9_-]{3,20}$', student_id):
            return {'valid': False, 'error': 'Invalid student ID format'}
        
        # Check for suspicious patterns
        suspicious_check = SecuritySettings.is_suspicious_pattern(student_id)
        if suspicious_check['is_suspicious']:
            return {'valid': False, 'error': 'Invalid characters in student ID'}
        
        return {'valid': True}
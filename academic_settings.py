# Academic Enforcement Settings
# Add to Django settings.py

# Middleware for academic enforcement
MIDDLEWARE = [
    # ... existing middleware ...
    'assignments.middleware.AcademicTimeEnforcementMiddleware',
    'assignments.middleware.ExamLockingMiddleware',
]

# Academic enforcement settings
ACADEMIC_ENFORCEMENT = {
    'STRICT_TIME_LIMITS': True,
    'AUTO_SUBMIT_EXPIRED': True,
    'EXAM_LOCKING': True,
    'ATTEMPT_LIMIT_ENFORCEMENT': True,
    'FILE_SIZE_LIMITS': {
        'HOMEWORK': 10 * 1024 * 1024,  # 10MB
        'PROJECT': 50 * 1024 * 1024,   # 50MB
        'QUIZ': 0,                      # No files
        'EXAM': 0,                      # No files
    },
    'DEFAULT_TIME_LIMITS': {
        'QUIZ': 30,   # 30 minutes
        'EXAM': 60,   # 60 minutes
    },
    'MAX_ATTEMPTS': {
        'HOMEWORK': 3,
        'PROJECT': 2,
        'QUIZ': 2,
        'EXAM': 1,
    }
}

# Celery tasks for time enforcement (optional)
CELERY_BEAT_SCHEDULE = {
    'handle-expired-assignments': {
        'task': 'assignments.tasks.handle_expired_assignments',
        'schedule': 60.0,  # Every minute
    },
}

# File upload validation
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# Academic logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'academic_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'academic_enforcement.log',
        },
    },
    'loggers': {
        'assignments.academic': {
            'handlers': ['academic_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
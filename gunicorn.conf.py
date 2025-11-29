"""
Gunicorn configuration to prevent worker timeouts and memory issues
"""
import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120  # Increase timeout from default 30s
keepalive = 30
max_requests = 1000
max_requests_jitter = 50

# Memory management
preload_app = True
reload = False

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "school_report_saas"

# Server mechanics
daemon = False
pidfile = None
tmp_upload_dir = None
user = None
group = None
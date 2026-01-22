# Gunicorn configuration for memory optimization
import multiprocessing
import os

# Worker processes - reduced for memory efficiency
workers = min(2, multiprocessing.cpu_count())
worker_class = "sync"
worker_connections = 1000

# Memory management
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Timeouts
timeout = 30
keepalive = 2

# Binding
bind = "0.0.0.0:10000"

# Logging
loglevel = "warning"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "school_report_saas"

# Memory limits per worker
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
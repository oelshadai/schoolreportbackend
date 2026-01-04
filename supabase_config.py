"""
Supabase configuration for Django
"""
from supabase import create_client, Client
from decouple import config
import os

# Supabase configuration
SUPABASE_URL = config('SUPABASE_URL', default='')
SUPABASE_KEY = config('SUPABASE_ANON_KEY', default='')
SUPABASE_SERVICE_KEY = config('SUPABASE_SERVICE_KEY', default='')

# Create Supabase client
def get_supabase_client() -> Client:
    """Get Supabase client instance"""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase URL and Key must be provided")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase_admin_client() -> Client:
    """Get Supabase admin client with service key"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase URL and Service Key must be provided")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Database configuration for Supabase
def get_supabase_database_config():
    """Get database configuration for Supabase PostgreSQL"""
    supabase_url = config('SUPABASE_URL', default='')
    supabase_db_password = config('SUPABASE_DB_PASSWORD', default='')
    
    if not supabase_url or not supabase_db_password:
        return None
    
    # Extract database details from Supabase URL
    # Format: https://your-project.supabase.co
    project_id = supabase_url.replace('https://', '').replace('.supabase.co', '')
    
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': supabase_db_password,
        'HOST': f'db.{project_id}.supabase.co',
        'PORT': '5432',
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
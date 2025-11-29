"""
Direct CORS-enabled teacher endpoint as a backup solution
"""
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_user_model
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json

from .models import Teacher
from .serializers import TeacherSerializer

User = get_user_model()

def add_cors_headers(response):
    """Add CORS headers to any response"""
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Origin'
    response['Access-Control-Allow-Credentials'] = 'true'
    response['Access-Control-Max-Age'] = '3600'
    return response

@csrf_exempt
def teachers_cors_endpoint(request):
    """Teacher endpoint with explicit CORS handling"""
    
    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        return add_cors_headers(response)
    
    # Handle GET request (list teachers)
    if request.method == 'GET':
        try:
            teachers = Teacher.objects.all()
            serializer = TeacherSerializer(teachers, many=True)
            response = JsonResponse({'results': serializer.data})
            return add_cors_headers(response)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=500)
            return add_cors_headers(response)
    
    # Handle POST request (create teacher)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Create user first
            user_data = {
                'email': data.get('email'),
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'password': data.get('password', 'defaultpass123'),
                'role': 'TEACHER'
            }
            
            # Check if user exists
            if User.objects.filter(email=user_data['email']).exists():
                response = JsonResponse({'error': 'User with this email already exists'}, status=400)
                return add_cors_headers(response)
            
            # Create user
            user = User.objects.create_user(**user_data)
            
            # Create teacher
            teacher_data = {
                'user': user,
                'employee_id': data.get('employee_id'),
                'qualification': data.get('qualification'),
                'experience_years': data.get('experience_years', 0),
                'emergency_contact': data.get('emergency_contact'),
                'address': data.get('address')
            }
            
            teacher = Teacher.objects.create(**teacher_data)
            serializer = TeacherSerializer(teacher)
            
            response = JsonResponse(serializer.data, status=201)
            return add_cors_headers(response)
            
        except json.JSONDecodeError:
            response = JsonResponse({'error': 'Invalid JSON'}, status=400)
            return add_cors_headers(response)
        except Exception as e:
            response = JsonResponse({'error': str(e)}, status=500)
            return add_cors_headers(response)
    
    # Method not allowed
    response = JsonResponse({'error': 'Method not allowed'}, status=405)
    return add_cors_headers(response)
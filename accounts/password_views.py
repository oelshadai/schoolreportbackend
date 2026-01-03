from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """Change student password"""
    current_password = request.data.get('current_password')
    new_password = request.data.get('new_password')
    
    if not current_password or not new_password:
        return Response({'error': 'Current and new password required'}, status=400)
    
    user = request.user
    if not user.check_password(current_password):
        return Response({'error': 'Current password is incorrect'}, status=400)
    
    if len(new_password) < 6:
        return Response({'error': 'Password must be at least 6 characters'}, status=400)
    
    user.set_password(new_password)
    user.save()
    
    # Update student model password field for display
    if hasattr(user, 'student_profile'):
        user.student_profile.password = new_password
        user.student_profile.save()
    
    return Response({'message': 'Password changed successfully'})

@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    """Send password reset for any user type"""
    username = request.data.get('username')
    email = request.data.get('email')
    
    if not username and not email:
        return Response({'error': 'Username or email required'}, status=400)
    
    try:
        if username:
            user = User.objects.get(username=username)
        else:
            user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    # Generate new temporary password
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    user.set_password(temp_password)
    user.save()
    
    # Update student password field if student
    if hasattr(user, 'student_profile'):
        user.student_profile.password = temp_password
        user.student_profile.save()
    
    # Send email with new password
    try:
        send_mail(
            'Password Reset - School Management System',
            f'Your new temporary password is: {temp_password}\n\nPlease login and change your password immediately.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email or 'admin@school.com'],
            fail_silently=False,
        )
        return Response({'message': 'New password sent to your email'})
    except:
        return Response({
            'message': 'Password reset successful',
            'temp_password': temp_password  # Fallback if email fails
        })

@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_admin(request):
    """Admin reset password for any user"""
    username = request.data.get('username')
    
    if not username:
        return Response({'error': 'Username required'}, status=400)
    
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=404)
    
    # Generate new password
    new_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(6))
    user.set_password(new_password)
    user.save()
    
    # Update student password field if student
    if hasattr(user, 'student_profile'):
        user.student_profile.password = new_password
        user.student_profile.save()
    
    return Response({
        'message': 'Password reset successfully',
        'new_password': new_password,
        'username': username
    })
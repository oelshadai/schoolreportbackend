from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import authenticate, get_user_model
from django.core.mail import send_mail
from django.conf import settings
import secrets
import string


def _require_superadmin(request):
    """Return error Response if caller is not an authenticated SUPER_ADMIN."""
    if not request.user or not request.user.is_authenticated:
        return Response({'error': 'Authentication required'}, status=401)
    if getattr(request.user, 'role', None) != 'SUPER_ADMIN':
        return Response({'error': 'Super admin access required'}, status=403)
    return None


def _emergency_disabled():
    """Return 403 in production so emergency endpoints are never reachable publicly."""
    if not getattr(settings, 'DEBUG', False):
        return Response({'error': 'Not available'}, status=403)
    return None

User = get_user_model()

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
    """Send password reset email for any user type"""
    email = request.data.get('email') or request.data.get('username')

    if not email:
        return Response({'error': 'Email is required'}, status=400)

    try:
        user = User.objects.get(email__iexact=str(email).strip())
    except User.DoesNotExist:
        # Return success anyway to prevent email enumeration
        return Response({'message': 'If that email exists, a reset link has been sent.'})

    # Generate a secure token and store it in the session via cache
    token = secrets.token_urlsafe(32)

    # Store token in user's password field temporarily using Django cache
    from django.core.cache import cache
    cache.set(f'pwd_reset_{token}', user.pk, timeout=3600)  # 1 hour

    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://schoolreportfrontend.onrender.com')
    reset_url = f'{frontend_url}/reset-password?token={token}'

    try:
        send_mail(
            'Password Reset - School Report System',
            f'Hello {user.first_name or user.email},\n\n'
            f'Click the link below to reset your password (valid for 1 hour):\n\n'
            f'{reset_url}\n\n'
            f'If you did not request this, ignore this email.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    except Exception:
        pass  # Email sending failures are silent to avoid leaking info

    return Response({'message': 'If that email exists, a reset link has been sent.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def confirm_reset_password(request):
    """Confirm password reset using token from email link"""
    token = request.data.get('token')
    new_password = request.data.get('password')

    if not token or not new_password:
        return Response({'error': 'Token and new password are required.'}, status=400)

    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters.'}, status=400)

    from django.core.cache import cache
    user_pk = cache.get(f'pwd_reset_{token}')
    if not user_pk:
        return Response({'error': 'Reset link is invalid or has expired.'}, status=400)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return Response({'error': 'User not found.'}, status=400)

    user.set_password(new_password)
    user.save()
    cache.delete(f'pwd_reset_{token}')

    return Response({'message': 'Password reset successfully. You can now log in.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reset_password_admin(request):
    """Admin reset password for any user — requires SUPER_ADMIN role."""
    err = _require_superadmin(request)
    if err:
        return err

    username = request.data.get('username') or request.data.get('email', '').strip()

    if not username:
        return Response({'error': 'Username or email required'}, status=400)

    try:
        if '@' in username:
            user = User.objects.get(email__iexact=username)
        else:
            user = User.objects.get(username=username)
    except User.DoesNotExist:
        # Avoid leaking whether the user exists
        return Response({'error': 'User not found or reset failed'}, status=404)

    # Generate new 12-char password with mixed characters
    alphabet = string.ascii_letters + string.digits + '!@#$'
    new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
    user.set_password(new_password)
    user.save()

    # Update student password display field if applicable
    if hasattr(user, 'student_profile'):
        user.student_profile.password = new_password
        user.student_profile.save()

    return Response({
        'message': 'Password reset successfully',
        'new_password': new_password,
        'username': user.email
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def emergency_reset(request):
    """Emergency password reset — DEBUG only, requires SECRET_KEY.
    Disabled entirely in production — use the admin panel or shell instead.
    """
    guard = _emergency_disabled()
    if guard:
        return guard
    from django.conf import settings as django_settings
    token = request.data.get('token', '')
    email = request.data.get('email', '').strip().lower()
    new_password = request.data.get('password', '')

    # Must supply the server SECRET_KEY as auth — safe because SECRET_KEY is never public
    if not token or token != django_settings.SECRET_KEY:
        return Response({'error': 'Unauthorized'}, status=401)

    if not email or not new_password:
        return Response({'error': 'email and password required'}, status=400)

    if len(new_password) < 8:
        return Response({'error': 'Password must be at least 8 characters'}, status=400)

    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        return Response({'error': f'No user found with email {email}'}, status=404)

    user.set_password(new_password)
    user.is_active = True
    user.save()

    return Response({'message': f'Password reset for {user.email} ({user.role}). Active: {user.is_active}'})


@api_view(['POST'])
@permission_classes([AllowAny])
def emergency_list_users(request):
    """List all users — DEBUG only, requires SECRET_KEY.
    Disabled entirely in production.
    """
    guard = _emergency_disabled()
    if guard:
        return guard
    from django.conf import settings as django_settings
    token = request.data.get('token', '')
    if not token or token != django_settings.SECRET_KEY:
        return Response({'error': 'Unauthorized'}, status=401)

    users = User.objects.all().values('id', 'email', 'first_name', 'last_name', 'role', 'is_active')
    return Response({'count': len(users), 'users': list(users)})


@api_view(['POST'])
@permission_classes([AllowAny])
def emergency_wipe_users(request):
    """Delete ALL users and schools — DEBUG only, requires SECRET_KEY + confirm.
    Disabled entirely in production.
    """
    guard = _emergency_disabled()
    if guard:
        return guard
    from django.conf import settings as django_settings
    token = request.data.get('token', '')
    confirm = request.data.get('confirm', '')

    if not token or token != django_settings.SECRET_KEY:
        return Response({'error': 'Unauthorized'}, status=401)

    if confirm != 'WIPE_EVERYTHING':
        return Response({'error': 'Pass confirm="WIPE_EVERYTHING" to proceed'}, status=400)

    user_count = User.objects.count()
    User.objects.all().delete()

    # Also wipe schools so school name/email isn't blocked either
    try:
        from schools.models import School
        school_count = School.objects.count()
        School.objects.all().delete()
    except Exception:
        school_count = 0

    return Response({
        'message': f'Wiped {user_count} users and {school_count} schools. Database is now empty — go register your school.'
    })
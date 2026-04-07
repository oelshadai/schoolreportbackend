"""
Views for student/teacher profile change requests that require admin approval.
Password changes are handled separately and do NOT go through this flow.
"""
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import ProfileChangeRequest, Student


# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────

STUDENT_ALLOWED_FIELDS = {
    'guardian_name', 'guardian_phone', 'guardian_email', 'guardian_address',
}

TEACHER_ALLOWED_FIELDS = {
    'first_name', 'last_name', 'phone_number', 'emergency_contact', 'address', 'qualification',
}


# ─────────────────────────────────────────────
# Student: submit change request
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def student_request_profile_change(request):
    """Student submits a profile change request. Only guardian/contact fields allowed."""
    user = request.user
    try:
        student = user.student_profile
    except Student.DoesNotExist:
        return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)

    changes = {
        k: v for k, v in request.data.items()
        if k in STUDENT_ALLOWED_FIELDS and v is not None and str(v).strip() != ''
    }
    if not changes:
        return Response(
            {'error': 'No valid fields to change. Allowed: ' + ', '.join(STUDENT_ALLOWED_FIELDS)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Cancel any previous PENDING request from this student and create a fresh one
    ProfileChangeRequest.objects.filter(
        requested_by=user,
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_STUDENT,
        status=ProfileChangeRequest.STATUS_PENDING,
    ).update(status=ProfileChangeRequest.STATUS_REJECTED, rejection_reason='Superseded by newer request')

    req = ProfileChangeRequest.objects.create(
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_STUDENT,
        requested_by=user,
        requester_name=student.get_full_name(),
        requested_changes=changes,
    )
    return Response({
        'id': req.id,
        'status': req.status,
        'message': 'Change request submitted. It will take effect once approved by admin.',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_get_pending_request(request):
    """Return the student's latest pending profile change request (if any)."""
    user = request.user
    req = ProfileChangeRequest.objects.filter(
        requested_by=user,
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_STUDENT,
        status=ProfileChangeRequest.STATUS_PENDING,
    ).first()
    if req:
        return Response({
            'id': req.id,
            'status': req.status,
            'requested_changes': req.requested_changes,
            'created_at': req.created_at,
        })
    return Response(None)


# ─────────────────────────────────────────────
# Teacher: submit change request
# ─────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_request_profile_change(request):
    """Teacher submits a profile change request."""
    user = request.user
    if user.role not in ('TEACHER', 'PRINCIPAL', 'SCHOOL_ADMIN'):
        return Response({'error': 'Not a teacher account'}, status=status.HTTP_403_FORBIDDEN)

    changes = {
        k: v for k, v in request.data.items()
        if k in TEACHER_ALLOWED_FIELDS and v is not None and str(v).strip() != ''
    }
    if not changes:
        return Response(
            {'error': 'No valid fields to change. Allowed: ' + ', '.join(TEACHER_ALLOWED_FIELDS)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Cancel previous pending
    ProfileChangeRequest.objects.filter(
        requested_by=user,
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_TEACHER,
        status=ProfileChangeRequest.STATUS_PENDING,
    ).update(status=ProfileChangeRequest.STATUS_REJECTED, rejection_reason='Superseded by newer request')

    req = ProfileChangeRequest.objects.create(
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_TEACHER,
        requested_by=user,
        requester_name=f"{user.first_name} {user.last_name}".strip() or user.email,
        requested_changes=changes,
    )
    return Response({
        'id': req.id,
        'status': req.status,
        'message': 'Change request submitted. It will take effect once approved by admin.',
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_get_pending_request(request):
    """Return the teacher's latest pending profile change request (if any)."""
    user = request.user
    req = ProfileChangeRequest.objects.filter(
        requested_by=user,
        requester_type=ProfileChangeRequest.REQUESTER_TYPE_TEACHER,
        status=ProfileChangeRequest.STATUS_PENDING,
    ).first()
    if req:
        return Response({
            'id': req.id,
            'status': req.status,
            'requested_changes': req.requested_changes,
            'created_at': req.created_at,
        })
    return Response(None)


# ─────────────────────────────────────────────
# Admin: list + approve/reject
# ─────────────────────────────────────────────

def _require_admin(user):
    return user.role in ('SCHOOL_ADMIN', 'SUPER_ADMIN', 'PRINCIPAL')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def admin_list_profile_change_requests(request):
    """Admin: list all pending (or filtered by status) profile change requests for this school."""
    user = request.user
    if not _require_admin(user):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    qs = ProfileChangeRequest.objects.filter(requested_by__school=user.school)
    req_status = request.query_params.get('status', 'PENDING')
    if req_status != 'ALL':
        qs = qs.filter(status=req_status)

    data = []
    for r in qs:
        data.append({
            'id': r.id,
            'requester_type': r.requester_type,
            'requester_name': r.requester_name,
            'requester_user_id': r.requested_by_id,
            'requested_changes': r.requested_changes,
            'status': r.status,
            'rejection_reason': r.rejection_reason,
            'reviewed_at': r.reviewed_at,
            'created_at': r.created_at,
        })
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_approve_profile_change(request, pk):
    """Admin: approve a profile change request and apply the changes."""
    user = request.user
    if not _require_admin(user):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    try:
        req = ProfileChangeRequest.objects.get(pk=pk, status=ProfileChangeRequest.STATUS_PENDING)
    except ProfileChangeRequest.DoesNotExist:
        return Response({'error': 'Request not found or already processed'}, status=status.HTTP_404_NOT_FOUND)

    # Apply changes
    changes = req.requested_changes
    if req.requester_type == ProfileChangeRequest.REQUESTER_TYPE_STUDENT:
        try:
            student = req.requested_by.student_profile
            for field, value in changes.items():
                if field in STUDENT_ALLOWED_FIELDS:
                    setattr(student, field, value)
            student.save()
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=status.HTTP_404_NOT_FOUND)
    elif req.requester_type == ProfileChangeRequest.REQUESTER_TYPE_TEACHER:
        teacher_user = req.requested_by
        for field, value in changes.items():
            if field in ('first_name', 'last_name'):
                setattr(teacher_user, field, value)
        teacher_user.save(update_fields=[f for f in ('first_name', 'last_name') if f in changes])

        # Also update the teacher profile object if it exists
        try:
            teacher_profile = teacher_user.teacher_profile
            for field, value in changes.items():
                if field in TEACHER_ALLOWED_FIELDS and hasattr(teacher_profile, field):
                    setattr(teacher_profile, field, value)
            teacher_profile.save()
        except Exception:
            pass  # teacher profile model may not exist — user fields already updated above

    req.status = ProfileChangeRequest.STATUS_APPROVED
    req.reviewed_by = user
    req.reviewed_at = timezone.now()
    req.save()

    return Response({'message': 'Profile change approved and applied.'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_reject_profile_change(request, pk):
    """Admin: reject a profile change request."""
    user = request.user
    if not _require_admin(user):
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    try:
        req = ProfileChangeRequest.objects.get(pk=pk, status=ProfileChangeRequest.STATUS_PENDING)
    except ProfileChangeRequest.DoesNotExist:
        return Response({'error': 'Request not found or already processed'}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get('reason', '')
    req.status = ProfileChangeRequest.STATUS_REJECTED
    req.rejection_reason = reason
    req.reviewed_by = user
    req.reviewed_at = timezone.now()
    req.save()

    return Response({'message': 'Profile change request rejected.'})

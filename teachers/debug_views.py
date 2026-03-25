from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from schools.models import Class, ClassSubject
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def debug_user_info(request):
    """Debug endpoint to check current user info and assignments"""
    try:
        user = request.user
        
        # Get user info
        user_info = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': getattr(user, 'role', 'Unknown'),
            'school': str(user.school) if hasattr(user, 'school') and user.school else None,
            'school_id': user.school.id if hasattr(user, 'school') and user.school else None,
            'is_authenticated': user.is_authenticated,
            'is_active': user.is_active,
        }
        
        # Get class assignments
        class_assignments = []
        if hasattr(user, 'school') and user.school:
            classes = Class.objects.filter(school=user.school, class_teacher=user)
            for cls in classes:
                class_assignments.append({
                    'id': cls.id,
                    'name': str(cls),
                    'level': cls.level,
                    'section': cls.section
                })
        
        # Get subject assignments
        subject_assignments = []
        if hasattr(user, 'school') and user.school:
            subjects = ClassSubject.objects.filter(teacher=user, class_instance__school=user.school)
            for subj in subjects:
                subject_assignments.append({
                    'id': subj.id,
                    'class_name': str(subj.class_instance),
                    'subject_name': subj.subject.name
                })
        
        return Response({
            'user_info': user_info,
            'class_assignments': class_assignments,
            'subject_assignments': subject_assignments,
            'total_assignments': len(class_assignments) + len(subject_assignments)
        })
        
    except Exception as e:
        logger.error(f"Error in debug_user_info: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)
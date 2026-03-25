from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from schools.models import Class, ClassSubject
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_class_assignments(request):
    """Get teacher's class and subject assignments"""
    try:
        user = request.user
        results = []
        
        # Check if user has school
        if not hasattr(user, 'school') or not user.school:
            return Response([])
        
        # Get classes where user is class teacher
        try:
            class_assignments = Class.objects.filter(
                school=user.school,
                class_teacher=user
            )
            
            for cls in class_assignments:
                results.append({
                    'id': f'class_{cls.id}',
                    'type': 'form_class',
                    'class': {
                        'id': cls.id,
                        'name': str(cls),
                        'level': cls.level,
                        'section': cls.section or ''
                    },
                    'subject': None,
                    'assignment_count': 0
                })
        except Exception as e:
            logger.error(f"Error getting class assignments: {e}")
        
        # Get subject assignments
        try:
            subject_assignments = ClassSubject.objects.filter(
                teacher=user,
                class_instance__school=user.school
            ).select_related('class_instance', 'subject')
            
            for assignment in subject_assignments:
                results.append({
                    'id': assignment.id,
                    'type': 'subject_class',
                    'class': {
                        'id': assignment.class_instance.id,
                        'name': str(assignment.class_instance),
                        'level': assignment.class_instance.level,
                        'section': assignment.class_instance.section or ''
                    },
                    'subject': {
                        'id': assignment.subject.id,
                        'name': assignment.subject.name
                    },
                    'assignment_count': 0
                })
        except Exception as e:
            logger.error(f"Error getting subject assignments: {e}")
        
        return Response(results)
        
    except Exception as e:
        logger.error(f"Error in teacher_class_assignments: {str(e)}")
        return Response([], status=200)
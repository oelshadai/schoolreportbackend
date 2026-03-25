from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def simple_teacher_assignments(request):
    """Simple endpoint to get teacher assignments without complex queries"""
    try:
        user = request.user
        logger.info(f"Teacher assignments request from user: {user.email}, role: {user.role}")
        assignments = []
        
        # Check if user has school
        if not hasattr(user, 'school') or not user.school:
            logger.warning(f"User {user.email} has no school assigned")
            return Response([])
        
        logger.info(f"User school: {user.school.name}")
        
        # Try to get class assignments safely
        try:
            from schools.models import Class
            classes = Class.objects.filter(school=user.school, class_teacher=user)
            logger.info(f"Found {classes.count()} classes for teacher {user.email}")
            for cls in classes:
                assignments.append({
                    'id': f'class_{cls.id}',
                    'type': 'form_class',
                    'class': {
                        'id': cls.id,
                        'name': f"{cls.get_level_display()} {cls.section}" if cls.section else cls.get_level_display(),
                        'level': cls.level,
                        'section': cls.section or ''
                    },
                    'subject': None,
                    'assignment_count': 0
                })
        except Exception as e:
            logger.error(f"Error getting class assignments: {str(e)}")
        
        # Try to get subject assignments safely
        try:
            from schools.models import ClassSubject
            subjects = ClassSubject.objects.filter(teacher=user, class_instance__school=user.school)
            logger.info(f"Found {subjects.count()} subject assignments for teacher {user.email}")
            for subj in subjects:
                assignments.append({
                    'id': f'subject_{subj.id}',
                    'type': 'subject_class',
                    'class': {
                        'id': subj.class_instance.id,
                        'name': f"{subj.class_instance.get_level_display()} {subj.class_instance.section}" if subj.class_instance.section else subj.class_instance.get_level_display(),
                        'level': subj.class_instance.level,
                        'section': subj.class_instance.section or ''
                    },
                    'subject': {
                        'id': subj.subject.id,
                        'name': subj.subject.name
                    },
                    'assignment_count': 0
                })
        except Exception as e:
            logger.error(f"Error getting subject assignments: {str(e)}")
        
        logger.info(f"Returning {len(assignments)} assignments for teacher {user.email}")
        return Response(assignments)
        
    except Exception as e:
        logger.error(f"Error in simple_teacher_assignments: {str(e)}")
        return Response([])
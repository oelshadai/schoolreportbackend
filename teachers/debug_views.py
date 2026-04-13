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

        # Get Teacher profile info (separate model from User)
        teacher_profile_info = None
        try:
            from teachers.models import Teacher
            tp = Teacher.objects.get(user=user)
            teacher_profile_info = {
                'teacher_model_id': tp.id,
                'user_id': tp.user_id,
                'ids_match': tp.id == tp.user_id,
                'school_id': tp.school_id,
            }
        except Exception as e:
            teacher_profile_info = {'error': str(e)}

        # Get user info
        user_school_id = getattr(user, 'school_id', None)
        user_info = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': getattr(user, 'role', 'Unknown'),
            'school_id': user_school_id,
            'school': str(user.school) if user_school_id and hasattr(user, 'school') else None,
            'is_authenticated': user.is_authenticated,
            'is_active': user.is_active,
            'teacher_profile': teacher_profile_info,
        }

        # Get ALL classes in the school (to see their class_teacher_id values)
        all_school_classes = []
        if user_school_id:
            for cls in Class.objects.filter(school_id=user_school_id):
                all_school_classes.append({
                    'id': cls.id,
                    'name': str(cls),
                    'class_teacher_id_stored': cls.class_teacher_id,
                    'is_assigned_to_me': cls.class_teacher_id == user.id,
                })

        # Get class assignments (filtered by user.id)
        class_assignments = []
        if user_school_id:
            for cls in Class.objects.filter(school_id=user_school_id, class_teacher=user):
                class_assignments.append({
                    'id': cls.id,
                    'name': str(cls),
                    'level': cls.level,
                    'section': cls.section,
                })

        # Get subject assignments
        subject_assignments = []
        if user_school_id:
            for subj in ClassSubject.objects.filter(teacher=user, class_instance__school_id=user_school_id):
                subject_assignments.append({
                    'id': subj.id,
                    'class_name': str(subj.class_instance),
                    'subject_name': subj.subject.name,
                })

        return Response({
            'user_info': user_info,
            'all_school_classes': all_school_classes,
            'class_assignments': class_assignments,
            'subject_assignments': subject_assignments,
            'total_assignments': len(class_assignments) + len(subject_assignments),
            'diagnosis': (
                'class_teacher_id mismatch detected — re-assign the class teacher via Classes Management'
                if all_school_classes and not class_assignments
                else 'OK'
            ),
        })

    except Exception as e:
        logger.error(f"Error in debug_user_info: {str(e)}")
        import traceback
        traceback.print_exc()
        return Response({'error': str(e)}, status=500)
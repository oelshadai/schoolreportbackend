from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import QuizAnswer, QuizAnswerFile
from .serializers import QuizAnswerFileSerializer
from .api_views import TeacherAssignmentViewSet, StudentAssignmentViewSet


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_quiz_answer_files(request, quiz_answer_id):
    """
    Upload files for a quiz answer (project questions).
    Accepts multipart/form-data with multiple files.
    """
    quiz_answer = get_object_or_404(QuizAnswer, id=quiz_answer_id)
    
    # Verify this is a project question
    if quiz_answer.question.question_type != 'project':
        return Response(
            {'error': 'File uploads only allowed for project questions'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Verify student owns this answer
    if quiz_answer.attempt.student.user != request.user:
        return Response(
            {'error': 'Permission denied'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    files = request.FILES.getlist('files')
    if not files:
        return Response(
            {'error': 'No files provided'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check file count limit
    current_count = quiz_answer.uploaded_files.count()
    max_files = quiz_answer.question.max_files
    if current_count + len(files) > max_files:
        return Response(
            {'error': f'Maximum {max_files} files allowed. Current: {current_count}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_files = []
    errors = []
    
    for file in files:
        # Validate file
        is_valid, message = quiz_answer.question.validate_file_upload(file)
        if not is_valid:
            errors.append(f'{file.name}: {message}')
            continue
        
        # Create QuizAnswerFile record
        quiz_answer_file = QuizAnswerFile(
            quiz_answer=quiz_answer,
            file=file,
            original_filename=file.name
        )
        quiz_answer_file.save()
        uploaded_files.append(quiz_answer_file)
    
    if errors and not uploaded_files:
        return Response(
            {'errors': errors}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    serializer = QuizAnswerFileSerializer(uploaded_files, many=True)
    response_data = {
        'uploaded_files': serializer.data,
        'total_files': quiz_answer.uploaded_files.count()
    }
    
    if errors:
        response_data['warnings'] = errors
    
    return Response(response_data, status=status.HTTP_201_CREATED)
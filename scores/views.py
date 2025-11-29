from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum, Avg, Count
from .models import ContinuousAssessment, ExamScore, SubjectResult, TermResult
from .serializers import (
    ContinuousAssessmentSerializer, ExamScoreSerializer,
    SubjectResultSerializer, TermResultSerializer, ScoreEntrySerializer
)
from students.models import Student
from schools.models import ClassSubject, Term


class ContinuousAssessmentViewSet(viewsets.ModelViewSet):
    """CA Score management"""
    queryset = ContinuousAssessment.objects.all()
    serializer_class = ContinuousAssessmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = ContinuousAssessment.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            class_subject_id = self.request.query_params.get('class_subject_id')
            if class_subject_id:
                queryset = queryset.filter(class_subject_id=class_subject_id)
            
            return queryset
        return ContinuousAssessment.objects.none()


class ExamScoreViewSet(viewsets.ModelViewSet):
    """Exam Score management"""
    queryset = ExamScore.objects.all()
    serializer_class = ExamScoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = ExamScore.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            class_subject_id = self.request.query_params.get('class_subject_id')
            if class_subject_id:
                queryset = queryset.filter(class_subject_id=class_subject_id)
            
            return queryset
        return ExamScore.objects.none()


class SubjectResultViewSet(viewsets.ModelViewSet):
    """Subject Result management"""
    queryset = SubjectResult.objects.all()
    serializer_class = SubjectResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = SubjectResult.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            student_id = self.request.query_params.get('student_id')
            if student_id:
                queryset = queryset.filter(student_id=student_id)
            
            return queryset
        return SubjectResult.objects.none()


class TermResultViewSet(viewsets.ModelViewSet):
    """Term Result management"""
    queryset = TermResult.objects.all()
    serializer_class = TermResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.school:
            queryset = TermResult.objects.filter(student__school=user.school)
            
            term_id = self.request.query_params.get('term_id')
            if term_id:
                queryset = queryset.filter(term_id=term_id)
            
            class_id = self.request.query_params.get('class_id')
            if class_id:
                queryset = queryset.filter(class_instance_id=class_id)
            
            return queryset
        return TermResult.objects.none()
    
    @action(detail=False, methods=['post'])
    def calculate_positions(self, request):
        """Calculate class positions for all students in a term"""
        term_id = request.data.get('term_id')
        class_id = request.data.get('class_id')
        
        if not term_id or not class_id:
            return Response(
                {"error": "term_id and class_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get all term results for this class and term, ordered by total score
        term_results = TermResult.objects.filter(
            term_id=term_id,
            class_instance_id=class_id
        ).order_by('-total_score', '-average_score')
        
        total_students = term_results.count()
        
        # Assign positions
        for position, result in enumerate(term_results, start=1):
            result.class_position = position
            result.total_students = total_students
            result.save()
        
        return Response({
            "message": f"Positions calculated for {total_students} students"
        })


class ScoreManagementViewSet(viewsets.ViewSet):
    """Combined score entry and computation"""
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def enter_scores(self, request):
        """Enter CA and exam scores together"""
        serializer = ScoreEntrySerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data

        # Only teachers can enter scores
        user = request.user
        if getattr(user, 'role', None) != 'TEACHER':
            return Response({"error": "Only teachers can enter scores"}, status=status.HTTP_403_FORBIDDEN)

        # Permission checks for teachers
        if getattr(user, 'role', None) == 'TEACHER':
            try:
                student = Student.objects.get(id=data['student_id'], school=user.school)
            except Student.DoesNotExist:
                return Response({"error": "Invalid student"}, status=status.HTTP_400_BAD_REQUEST)
            
            try:
                cs = ClassSubject.objects.get(id=data['class_subject_id'])
            except ClassSubject.DoesNotExist:
                return Response({"error": "Invalid class subject"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if teacher has permission to enter scores for this student/subject combination
            is_class_teacher = student.current_class and student.current_class.class_teacher_id == user.id
            is_subject_teacher = cs.teacher_id == user.id if cs.teacher_id else False
            
            # Allow access if teacher is either the class teacher OR the subject teacher
            if not (is_class_teacher or is_subject_teacher):
                return Response({
                    "error": "You can only enter scores for students in your class or subjects you teach"
                }, status=status.HTTP_403_FORBIDDEN)
        
        try:
            with transaction.atomic():
                # Create or update CA scores
                ca_score, ca_created = ContinuousAssessment.objects.update_or_create(
                    student_id=data['student_id'],
                    class_subject_id=data['class_subject_id'],
                    term_id=data['term_id'],
                    defaults={
                        'task': data['task'],
                        'homework': data['homework'],
                        'group_work': data['group_work'],
                        'project_work': data['project_work'],
                        'class_test': data['class_test'],
                    }
                )
                
                # Create or update exam score
                exam_score, exam_created = ExamScore.objects.update_or_create(
                    student_id=data['student_id'],
                    class_subject_id=data['class_subject_id'],
                    term_id=data['term_id'],
                    defaults={'score': data['exam_score']}
                )
                
                # Create or update subject result
                subject_result, result_created = SubjectResult.objects.update_or_create(
                    student_id=data['student_id'],
                    class_subject_id=data['class_subject_id'],
                    term_id=data['term_id'],
                    defaults={
                        'ca_score': ca_score.total_ca_score,
                        'exam_score': exam_score.score,
                    }
                )
                
                # Calculate total and assign grade
                subject_result.calculate_total()
            
            return Response({
                "message": "Scores entered successfully",
                "total_score": float(subject_result.total_score),
                "grade": subject_result.grade,
                "ca_score": float(subject_result.ca_score),
                "exam_score": float(subject_result.exam_score)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"Error in enter_scores: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return Response({
                "error": f"Failed to save scores: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def compute_term_results(self, request):
        """Compute overall term results for students"""
        term_id = request.data.get('term_id')
        class_id = request.data.get('class_id')
        
        if not term_id:
            return Response(
                {"error": "term_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get students
        students = Student.objects.filter(school=request.user.school, is_active=True)
        if class_id:
            students = students.filter(current_class_id=class_id)
        
        computed_count = 0
        
        with transaction.atomic():
            for student in students:
                # Create or update term result
                term_result, _ = TermResult.objects.update_or_create(
                    student=student,
                    term_id=term_id,
                    defaults={'class_instance': student.current_class}
                )
                
                # Calculate aggregate
                term_result.calculate_aggregate()
                
                # Generate teacher remarks
                term_result.generate_teacher_remarks()
                
                computed_count += 1
        
        return Response({
            "message": f"Term results computed for {computed_count} students"
        })
    
    @action(detail=False, methods=['get'])
    def class_analytics(self, request):
        """Get class performance analytics"""
        term_id = request.query_params.get('term_id')
        class_id = request.query_params.get('class_id')
        
        if not term_id or not class_id:
            return Response(
                {"error": "term_id and class_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get term results for the class
        term_results = TermResult.objects.filter(
            term_id=term_id,
            class_instance_id=class_id
        )
        
        analytics = {
            'total_students': term_results.count(),
            'average_score': term_results.aggregate(Avg('average_score'))['average_score__avg'] or 0,
            'highest_score': term_results.aggregate(Sum('total_score'))['total_score__sum'] or 0,
            'top_performers': TermResultSerializer(
                term_results.order_by('-average_score')[:5], many=True
            ).data
        }
        
        return Response(analytics)

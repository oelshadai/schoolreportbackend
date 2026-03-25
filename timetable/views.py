from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from schools.models import Class, ClassSubject
from students.models import Student
from .models import LessonSlot


# ── helpers ──────────────────────────────────────────────────────────────────

def _slot_data(slot):
    return {
        'id':         slot.id,
        'day':        slot.day,
        'day_label':  slot.get_day_display(),
        'start_time': slot.start_time.strftime('%H:%M'),
        'end_time':   slot.end_time.strftime('%H:%M'),
        'subject':    slot.class_subject.subject.name,
        'subject_id': slot.class_subject.subject.id,
        'teacher':    slot.class_subject.teacher.get_full_name() if slot.class_subject.teacher else None,
        'room':       slot.room,
        'notes':      slot.notes,
    }


DAY_ORDER = ['MON', 'TUE', 'WED', 'THU', 'FRI']


def _group_by_day(slots_qs):
    grouped = {d: [] for d in DAY_ORDER}
    for slot in slots_qs.select_related('class_subject__subject', 'class_subject__teacher'):
        grouped[slot.day].append(_slot_data(slot))
    return [{'day': d, 'day_label': dict(LessonSlot.DAY_CHOICES)[d], 'slots': grouped[d]}
            for d in DAY_ORDER]


# ── Teacher ViewSet ───────────────────────────────────────────────────────────

class TeacherTimetableViewSet(viewsets.ViewSet):
    """Teacher manages timetable for their class(es)."""
    permission_classes = [IsAuthenticated]

    def _get_class(self, request, class_id):
        try:
            return Class.objects.get(id=class_id, class_teacher=request.user, school=request.user.school)
        except Class.DoesNotExist:
            return None

    def list(self, request):
        """GET /api/timetable/teacher/?class_id=<id>"""
        class_id = request.query_params.get('class_id')
        if not class_id:
            # Return all classes the teacher manages
            classes = Class.objects.filter(class_teacher=request.user, school=request.user.school)
            return Response([{'id': c.id, 'name': str(c)} for c in classes])

        cls = self._get_class(request, class_id)
        if not cls:
            return Response({'error': 'Class not found or not assigned to you'}, status=404)

        slots = LessonSlot.objects.filter(class_instance=cls)
        return Response({
            'class': {'id': cls.id, 'name': str(cls)},
            'timetable': _group_by_day(slots),
        })

    def create(self, request):
        """POST /api/timetable/teacher/ — add a lesson slot"""
        class_id       = request.data.get('class_id')
        class_subject_id = request.data.get('class_subject_id')
        day            = request.data.get('day')
        start_time     = request.data.get('start_time')
        end_time       = request.data.get('end_time')
        room           = request.data.get('room', '')
        notes          = request.data.get('notes', '')

        if not all([class_id, class_subject_id, day, start_time, end_time]):
            return Response({'error': 'class_id, class_subject_id, day, start_time, end_time are required'}, status=400)

        cls = self._get_class(request, class_id)
        if not cls:
            return Response({'error': 'Class not found or not assigned to you'}, status=404)

        try:
            cs = ClassSubject.objects.get(id=class_subject_id, class_instance=cls)
        except ClassSubject.DoesNotExist:
            return Response({'error': 'Subject not found in this class'}, status=404)

        slot = LessonSlot.objects.create(
            class_instance=cls,
            class_subject=cs,
            day=day,
            start_time=start_time,
            end_time=end_time,
            room=room,
            notes=notes,
            created_by=request.user,
        )
        return Response(_slot_data(slot), status=201)

    def update(self, request, pk=None):
        """PUT /api/timetable/teacher/<id>/"""
        try:
            slot = LessonSlot.objects.select_related('class_instance').get(pk=pk)
        except LessonSlot.DoesNotExist:
            return Response({'error': 'Slot not found'}, status=404)

        if slot.class_instance.class_teacher != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        for field in ('day', 'start_time', 'end_time', 'room', 'notes'):
            if field in request.data:
                setattr(slot, field, request.data[field])

        if 'class_subject_id' in request.data:
            try:
                cs = ClassSubject.objects.get(id=request.data['class_subject_id'], class_instance=slot.class_instance)
                slot.class_subject = cs
            except ClassSubject.DoesNotExist:
                return Response({'error': 'Subject not found in this class'}, status=404)

        slot.save()
        return Response(_slot_data(slot))

    def destroy(self, request, pk=None):
        """DELETE /api/timetable/teacher/<id>/"""
        try:
            slot = LessonSlot.objects.select_related('class_instance').get(pk=pk)
        except LessonSlot.DoesNotExist:
            return Response({'error': 'Slot not found'}, status=404)

        if slot.class_instance.class_teacher != request.user:
            return Response({'error': 'Permission denied'}, status=403)

        slot.delete()
        return Response(status=204)


# ── Student ViewSet ───────────────────────────────────────────────────────────

class StudentTimetableViewSet(viewsets.ViewSet):
    """Student reads their class timetable."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """GET /api/timetable/student/"""
        try:
            student = Student.objects.select_related('current_class').get(user=request.user)
        except Student.DoesNotExist:
            return Response({'error': 'Student profile not found'}, status=404)

        if not student.current_class:
            return Response({'class': None, 'timetable': [], 'subjects': []})

        cls = student.current_class
        slots = LessonSlot.objects.filter(class_instance=cls)

        # Also return subjects list for the "My Subjects" section
        from schools.models import ClassSubject
        class_subjects = ClassSubject.objects.filter(
            class_instance=cls
        ).select_related('subject', 'teacher').order_by('subject__name')

        subjects = [{
            'id':       cs.id,
            'subject':  cs.subject.name,
            'code':     cs.subject.code,
            'teacher':  cs.teacher.get_full_name() if cs.teacher else None,
        } for cs in class_subjects]

        return Response({
            'class': {
                'name':         str(cls),
                'level':        cls.get_level_display(),
                'class_teacher': cls.class_teacher.get_full_name() if cls.class_teacher else None,
            },
            'timetable': _group_by_day(slots),
            'subjects':  subjects,
        })

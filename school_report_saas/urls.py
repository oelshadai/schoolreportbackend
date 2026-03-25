from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from students.portal_views import student_subjects, student_announcements
from students.auth_views import student_dashboard

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/schools/', include('schools.urls')),
    path('api/students/', include('students.urls')),
    path('api/teachers/', include('teachers.urls')),
    path('api/scores/', include('scores.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/assignments/', include('assignments.urls')),
    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/events/', include('events.urls')),
    path('api/fees/', include('fees.urls')),
    path('api/announcements/', include('announcements.urls')),
    path('api/timetable/', include('timetable.urls')),
    
    # Student portal API endpoints
    path('api/classes/<int:class_id>/subjects/', student_subjects, name='class_subjects'),
    path('api/classes/<int:class_id>/announcements/', student_announcements, name='class_announcements'),
    path('api/student/dashboard/', student_dashboard, name='student_dashboard_main'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
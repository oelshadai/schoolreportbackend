from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

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
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

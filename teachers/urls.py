from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TeacherViewSet
from .cors_views import teachers_cors_endpoint

router = DefaultRouter()
router.register(r'', TeacherViewSet, basename='teacher')

urlpatterns = [
    path('cors/', teachers_cors_endpoint, name='teachers_cors'),
    path('', include(router.urls)),
]


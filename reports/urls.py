from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReportCardViewSet, template_preview_pdf

router = DefaultRouter()
# Use explicit prefix to avoid action name collision with detail routes
router.register(r'report-cards', ReportCardViewSet, basename='report-card')

template_preview = ReportCardViewSet.as_view({'get': 'template_preview'})
preview_data = ReportCardViewSet.as_view({'get': 'preview_data'})

urlpatterns = [
	path('template_preview/', template_preview, name='template-preview'),
	path('preview_data/', preview_data, name='preview-data'),
	path('template-preview-standalone/', template_preview_pdf, name='template-preview-standalone'),
]

urlpatterns += router.urls

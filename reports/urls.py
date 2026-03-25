from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ReportCardViewSet, report_preview_iframe, template_preview_public

router = DefaultRouter()
# Use explicit prefix to avoid action name collision with detail routes
router.register(r'report-cards', ReportCardViewSet, basename='report-card')

from .views import template_preview_public
template_preview = template_preview_public
preview_data = ReportCardViewSet.as_view({'get': 'preview_data'})

urlpatterns = [
	path('template_preview/', template_preview, name='template-preview'),
	path('preview_data/', preview_data, name='preview-data'),
	path('template-preview-standalone/', template_preview, name='template-preview-standalone'),
	path('template-preview-public/', template_preview_public, name='template-preview-public'),
	path('preview-iframe/', report_preview_iframe, name='report-preview-iframe'),
]

urlpatterns += router.urls

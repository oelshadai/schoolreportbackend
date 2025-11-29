from rest_framework import serializers
from .models import ReportCard


class ReportCardSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    term_name = serializers.CharField(source='term.__str__', read_only=True)
    
    class Meta:
        model = ReportCard
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'generated_at', 'published_at']

from rest_framework import serializers
from .models import FeeType, FeeStructure, StudentFee, FeePayment, FeeCollection
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()


class FeeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeType
        fields = ['id', 'name', 'description', 'is_active']


class FeeStructureSerializer(serializers.ModelSerializer):
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    
    class Meta:
        model = FeeStructure
        fields = ['id', 'fee_type', 'fee_type_name', 'level', 'amount', 'collection_period', 'due_date']


class StudentFeeSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    student_name = serializers.SerializerMethodField()
    class_level = serializers.CharField(source='student.current_class.level', read_only=True)
    
    class Meta:
        model = StudentFee
        fields = [
            'id', 'student_id', 'student_name', 'class_level',
            'total_amount', 'amount_paid', 'balance', 'status',
            'last_payment_date', 'created_at', 'updated_at'
        ]
    
    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"


class FeePaymentSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    student_name = serializers.SerializerMethodField(read_only=True)
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    collected_by_name = serializers.CharField(source='collected_by.get_full_name', read_only=True)
    
    class Meta:
        model = FeePayment
        fields = [
            'id', 'student_id', 'student_name', 'fee_type', 'fee_type_name',
            'amount_paid', 'payment_method', 'reference_number', 'notes',
            'payment_date', 'collected_by_name', 'is_verified', 'created_at'
        ]
        read_only_fields = ['payment_date', 'created_at', 'updated_at']
    
    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"


class FeePaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating fee payments"""
    
    class Meta:
        model = FeePayment
        fields = ['student', 'fee_type', 'amount_paid', 'payment_method', 'reference_number', 'notes']
    
    def create(self, validated_data):
        from django.utils import timezone
        
        # Get current user (collector)
        request = self.context.get('request')
        validated_data['school'] = request.user.school
        validated_data['collected_by'] = request.user
        
        # Create payment
        payment = FeePayment.objects.create(**validated_data)
        
        # Update StudentFee record
        student_fee, created = StudentFee.objects.get_or_create(
            student=validated_data['student'],
            school=validated_data['school'],
            defaults={'total_amount': 0, 'amount_paid': 0}
        )
        
        # Update amounts
        student_fee.amount_paid += validated_data['amount_paid']
        student_fee.balance = student_fee.total_amount - student_fee.amount_paid
        student_fee.last_payment_date = timezone.now()
        
        # Update status
        if student_fee.balance <= 0:
            student_fee.status = 'PAID'
        elif student_fee.amount_paid > 0:
            student_fee.status = 'PARTIAL'
        
        student_fee.save()
        
        return payment


class FeeCollectionSerializer(serializers.ModelSerializer):
    collected_by_name = serializers.CharField(source='collected_by.get_full_name', read_only=True)
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    class_name = serializers.CharField(source='class_assigned', read_only=True)
    
    class Meta:
        model = FeeCollection
        fields = [
            'id', 'collected_by_name', 'class_name', 'fee_type', 'fee_type_name',
            'total_amount_collected', 'total_students_paid', 'collection_date',
            'notes', 'is_submitted', 'submitted_date'
        ]
        read_only_fields = ['collection_date', 'submitted_date']


class StudentSearchSerializer(serializers.Serializer):
    """Serializer for student search results"""
    id = serializers.IntegerField()
    student_id = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    class_level = serializers.CharField()
    section = serializers.CharField()
    email = serializers.EmailField()
    phone_number = serializers.CharField()
    current_balance = serializers.DecimalField(max_digits=10, decimal_places=2)
    payment_status = serializers.CharField()


class FeeCollectionReportSerializer(serializers.Serializer):
    """Serializer for fee collection reports"""
    fee_type = serializers.CharField()
    total_students = serializers.IntegerField()
    students_paid = serializers.IntegerField()
    total_amount_due = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_amount_collected = serializers.DecimalField(max_digits=12, decimal_places=2)
    outstanding_balance = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_percentage = serializers.FloatField()

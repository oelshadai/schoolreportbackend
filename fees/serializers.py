from rest_framework import serializers
from .models import FeeType, FeeStructure, StudentFee, FeePayment, FeeCollection, TermBill, StudentFeeSubType
from students.models import Student
from django.contrib.auth import get_user_model

User = get_user_model()


class SubFeeTypeSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sub-fee types (nested inside FeeTypeSerializer)."""
    class Meta:
        model = FeeType
        fields = ['id', 'name', 'description', 'is_active', 'collection_frequency']


class FeeTypeSerializer(serializers.ModelSerializer):
    sub_types = SubFeeTypeSerializer(many=True, read_only=True)
    has_sub_types = serializers.SerializerMethodField()

    class Meta:
        model = FeeType
        fields = [
            'id', 'name', 'description', 'is_active',
            'collection_frequency', 'collection_day',
            'allow_class_teacher_collection', 'allow_any_teacher_collection',
            'require_payment_approval',
            'parent_fee_type',
            'sub_types',
            'has_sub_types',
        ]

    def get_has_sub_types(self, obj):
        return obj.sub_types.exists()


class StudentFeeSubTypeSerializer(serializers.ModelSerializer):
    main_fee_type_name = serializers.CharField(source='main_fee_type.name', read_only=True)
    sub_fee_type_name = serializers.CharField(source='sub_fee_type.name', read_only=True, allow_null=True)
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentFeeSubType
        fields = [
            'id', 'student', 'student_name',
            'main_fee_type', 'main_fee_type_name',
            'sub_fee_type', 'sub_fee_type_name',
        ]

    def get_student_name(self, obj):
        return f"{obj.student.first_name} {obj.student.last_name}"

    def create(self, validated_data):
        validated_data['school'] = self.context['request'].user.school
        # upsert: update if already exists
        obj, _ = StudentFeeSubType.objects.update_or_create(
            student=validated_data['student'],
            main_fee_type=validated_data['main_fee_type'],
            defaults={
                'sub_fee_type': validated_data.get('sub_fee_type'),
                'school': validated_data['school'],
            },
        )
        return obj


class FeeStructureSerializer(serializers.ModelSerializer):
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    
    class Meta:
        model = FeeStructure
        fields = ['id', 'fee_type', 'fee_type_name', 'level', 'tier_label', 'amount', 'collection_period', 'due_date']


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

        request = self.context.get('request')
        validated_data['school'] = request.user.school
        validated_data['collected_by'] = request.user

        payment = FeePayment.objects.create(**validated_data)

        # ------------------------------------------------------------------
        # Update the running StudentFee balance
        # ------------------------------------------------------------------
        student_fee, _ = StudentFee.objects.get_or_create(
            student=validated_data['student'],
            school=validated_data['school'],
            defaults={'total_amount': 0, 'amount_paid': 0, 'balance': 0}
        )
        student_fee.amount_paid += validated_data['amount_paid']
        student_fee.balance = student_fee.total_amount - student_fee.amount_paid
        student_fee.last_payment_date = timezone.now()
        if student_fee.balance <= 0:
            student_fee.status = 'PAID'
        elif student_fee.amount_paid > 0:
            student_fee.status = 'PARTIAL'
        student_fee.save()

        # ------------------------------------------------------------------
        # If the fee type has a TermBill for the current term, update it too
        # ------------------------------------------------------------------
        try:
            from schools.models import Term
            current_term = Term.objects.filter(
                academic_year__school=validated_data['school'],
                is_current=True
            ).first()
            if current_term:
                term_bill = TermBill.objects.filter(
                    student=validated_data['student'],
                    term=current_term,
                    fee_type=validated_data['fee_type']
                ).first()
                if term_bill:
                    term_bill.amount_paid += validated_data['amount_paid']
                    term_bill.save()  # balance + status updated in TermBill.save()
        except Exception:
            pass  # Never block payment recording due to bill update failures

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


class TermBillSerializer(serializers.ModelSerializer):
    student_id = serializers.CharField(source='student.student_id', read_only=True)
    student_name = serializers.SerializerMethodField()
    class_level = serializers.CharField(source='student.current_class.level', read_only=True)
    class_section = serializers.CharField(source='student.current_class.section', read_only=True)
    fee_type_name = serializers.CharField(source='fee_type.name', read_only=True)
    term_name = serializers.CharField(source='term.name', read_only=True)
    academic_year_name = serializers.CharField(source='term.academic_year.name', read_only=True)

    class Meta:
        model = TermBill
        fields = [
            'id', 'student_id', 'student_name', 'class_level', 'class_section',
            'fee_type', 'fee_type_name', 'term', 'term_name', 'academic_year_name',
            'amount_billed', 'amount_paid', 'balance', 'status',
            'due_date', 'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['amount_paid', 'balance', 'status', 'created_at', 'updated_at']

    def get_student_name(self, obj):
        return f"{obj.student.user.first_name} {obj.student.user.last_name}"


class GenerateBillsSerializer(serializers.Serializer):
    """Input for bulk bill generation"""
    term = serializers.IntegerField(help_text='Term ID to generate bills for')
    fee_type = serializers.IntegerField(required=False, allow_null=True,
                                        help_text='Specific fee type; omit to generate for all TERM/YEAR fee types')
    overwrite = serializers.BooleanField(
        default=False,
        help_text='If True, update existing bills with new amounts; otherwise skip students already billed'
    )

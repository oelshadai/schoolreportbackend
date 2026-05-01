from rest_framework import serializers
from .models import School, AcademicYear, Term, Class, Subject, ClassSubject, GradingScale, StaffPermission, SmsPurchaseOrder
from django.contrib.auth import get_user_model

User = get_user_model()


class SchoolSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class ParentPortalSettingsSerializer(serializers.ModelSerializer):
    """Read/write only the parent-portal-related fields of a school."""

    class Meta:
        model = School
        fields = [
            'parent_portal_enabled',
            'parent_can_view_grades',
            'parent_can_view_attendance',
            'parent_can_view_fees',
            'parent_can_view_reports',
            'parent_can_pay_fees_online',
            'parent_can_message_teachers',
            'parent_support_email',
            'paystack_public_key',
            # NOTE: paystack_secret_key is intentionally excluded from read output
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Tell the frontend whether a secret key is saved, without exposing it
        data['paystack_secret_key_saved'] = bool(instance.paystack_secret_key)
        return data

    def validate(self, attrs):
        # If online payments are being enabled, a secret key must be present
        enabling = attrs.get('parent_can_pay_fees_online', False)
        if enabling:
            incoming_secret = attrs.get('paystack_secret_key', '')
            existing_secret = getattr(self.instance, 'paystack_secret_key', '') if self.instance else ''
            if not incoming_secret and not existing_secret:
                raise serializers.ValidationError(
                    {'paystack_secret_key': 'Paystack secret key is required to enable online payments.'}
                )
        return attrs


class ParentPortalWriteSerializer(ParentPortalSettingsSerializer):
    """Same as above but also accepts (optional) secret key write."""

    paystack_secret_key = serializers.CharField(
        max_length=100, required=False, allow_blank=True,
        write_only=True,
        help_text='Leave blank to keep existing key',
    )

    class Meta(ParentPortalSettingsSerializer.Meta):
        fields = ParentPortalSettingsSerializer.Meta.fields + ['paystack_secret_key']

    def update(self, instance, validated_data):
        # Only overwrite secret key if a new non-blank value was provided
        new_secret = validated_data.pop('paystack_secret_key', '').strip()
        if new_secret:
            validated_data['paystack_secret_key'] = new_secret
        return super().update(instance, validated_data)


class SmsSettingsSerializer(serializers.ModelSerializer):
    """Read/write SMS notification settings for a school."""

    class Meta:
        model = School
        fields = [
            'sms_enabled',
            'arkesel_api_key',
            'sms_sender_name',
            'sms_attendance_enabled',
            'sms_fee_reminder_enabled',
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Mask the API key — only show whether it is set
        data['arkesel_api_key_saved'] = bool(instance.arkesel_api_key)
        data['arkesel_api_key'] = ''  # never expose the raw key on GET
        return data

    def update(self, instance, validated_data):
        # Only overwrite the API key if a new non-blank value is provided
        new_key = validated_data.pop('arkesel_api_key', '').strip()
        if new_key:
            validated_data['arkesel_api_key'] = new_key
        return super().update(instance, validated_data)


class SchoolSettingsSerializer(serializers.ModelSerializer):
    """Comprehensive serializer for school settings and configuration"""

    class Meta:
        model = School
        fields = [
            # Basic Information
            'id', 'name', 'address', 'location', 'phone_number', 'email',
            'logo', 'motto', 'website', 'current_academic_year', 'current_term',
            
            # System Configuration
            'score_entry_mode', 'is_active',
            
            # Terminal Report Settings
            'term_closing_date', 'term_reopening_date', 'show_promotion_on_terminal',
            
            # Report Template Settings
            'report_template',
            'show_class_average', 'show_position_in_class', 'show_attendance',
            'show_behavior_comments', 'principal_signature', 
            'class_teacher_signature_required', 'show_student_photos', 
            'show_headteacher_signature',
            
            # Grade Scale
            'grade_scale_a_min', 'grade_scale_b_min', 'grade_scale_c_min',
            'grade_scale_d_min', 'grade_scale_f_min',
            
            # Timestamps
            'updated_at',

            # Staff permissions
            'special_fee_collection_enabled',
            'teachers_can_add_students',
        ]
        read_only_fields = ['id', 'updated_at']
        
    def validate_grade_scale(self, attrs):
        """Ensure grade scale values are in logical order"""
        grade_a = attrs.get('grade_scale_a_min', getattr(self.instance, 'grade_scale_a_min', 80))
        grade_b = attrs.get('grade_scale_b_min', getattr(self.instance, 'grade_scale_b_min', 70))
        grade_c = attrs.get('grade_scale_c_min', getattr(self.instance, 'grade_scale_c_min', 60))
        grade_d = attrs.get('grade_scale_d_min', getattr(self.instance, 'grade_scale_d_min', 50))
        grade_f = attrs.get('grade_scale_f_min', getattr(self.instance, 'grade_scale_f_min', 0))
        
        if not (grade_a > grade_b > grade_c > grade_d > grade_f >= 0):
            raise serializers.ValidationError(
                "Grade scale values must be in descending order: A > B > C > D > F >= 0"
            )
        return attrs
    
    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self.validate_grade_scale(attrs)


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'
        read_only_fields = ['created_at']


class TermSerializer(serializers.ModelSerializer):
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    display_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Term
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_display_name(self, obj):
        """Return formatted display name like '2024/2025 - 1st Term'"""
        term_names = {
            'FIRST': '1st Term',
            'SECOND': '2nd Term', 
            'THIRD': '3rd Term'
        }
        term_display = term_names.get(obj.name, obj.get_name_display())
        return f"{obj.academic_year.name} - {term_display}"


class ClassSerializer(serializers.ModelSerializer):
    class_teacher_name = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    level_display = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Class
        fields = '__all__'
        read_only_fields = ['created_at', 'school']
    
    def get_class_teacher_name(self, obj):
        if obj.class_teacher:
            return obj.class_teacher.get_full_name()
        return None
    
    def get_student_count(self, obj):
        return obj.students.filter(is_active=True).count()

    def get_level_display(self, obj):
        try:
            return obj.get_level_display()
        except Exception:
            return obj.level
    
    def get_full_name(self, obj):
        return obj.full_name


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
        read_only_fields = ['created_at']


class ClassSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    class_name = serializers.CharField(source='class_instance.full_name', read_only=True)
    
    class Meta:
        model = ClassSubject
        fields = '__all__'
        read_only_fields = ['created_at']
    
    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name()
        return None


class GradingScaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradingScale
        fields = '__all__'
        read_only_fields = ['created_at']


class BulkAssignmentSerializer(serializers.Serializer):
    """Serializer for bulk assignment operations"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of subject IDs to assign"
    )
    class_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of class IDs to assign subjects to"
    )


class BulkRemovalSerializer(serializers.Serializer):
    """Serializer for bulk removal operations"""
    subject_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of subject IDs to remove"
    )
    class_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        help_text="List of class IDs to remove subjects from"
    )


class StaffPermissionSerializer(serializers.ModelSerializer):
    teacher_name = serializers.SerializerMethodField()
    teacher_email = serializers.SerializerMethodField()
    collect_fee_type_ids = serializers.PrimaryKeyRelatedField(
        source='collect_fee_types',
        many=True,
        queryset=__import__('fees.models', fromlist=['FeeType']).FeeType.objects.all(),
        required=False,
    )
    cover_class_ids = serializers.PrimaryKeyRelatedField(
        source='cover_classes',
        many=True,
        queryset=Class.objects.all(),
        required=False,
    )

    class Meta:
        model = StaffPermission
        fields = [
            'id', 'teacher', 'teacher_name', 'teacher_email',
            'can_collect_fees', 'fee_collection_enabled',
            'collect_fee_type_ids',
            'can_cover_attendance', 'cover_class_ids',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'teacher_name', 'teacher_email']

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.username

    def get_teacher_email(self, obj):
        return obj.teacher.email


# SMS purchase price per unit in GHS
SMS_PRICE_GHS = '0.10'

SMS_BUNDLES = [
    {'id': 1, 'name': '50 SMS',    'sms_units': 50,   'amount_ghs': '5.00'},
    {'id': 2, 'name': '100 SMS',   'sms_units': 100,  'amount_ghs': '10.00'},
    {'id': 3, 'name': '500 SMS',   'sms_units': 500,  'amount_ghs': '50.00'},
    {'id': 4, 'name': '1000 SMS',  'sms_units': 1000, 'amount_ghs': '100.00'},
    {'id': 5, 'name': '2000 SMS',  'sms_units': 2000, 'amount_ghs': '200.00'},
]


class SmsPurchaseOrderSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SmsPurchaseOrder
        fields = [
            'id', 'sms_units', 'amount_ghs', 'status',
            'paystack_reference', 'requested_by_name',
            'credited_at', 'created_at',
        ]
        read_only_fields = fields

    def get_requested_by_name(self, obj):
        if obj.requested_by:
            return obj.requested_by.get_full_name() or obj.requested_by.username
        return ''


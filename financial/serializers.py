from rest_framework import serializers
# Import models from schools app
from schools.models import (
    Staff, StaffSalary, PayrollRecord, Income, Expense,
    Budget, BudgetItem, ExpenseApproval, PaymentReminder
)

from schools.models import FinancialAuditLog


class StaffSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Staff
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class StaffSalarySerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.first_name', read_only=True)
    gross_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = StaffSalary
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PayrollRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.first_name', read_only=True)
    staff_id = serializers.CharField(source='staff.staff_id', read_only=True)
    
    class Meta:
        model = PayrollRecord
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'approved_by']


class IncomeSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source='recorded_by.get_full_name', read_only=True)
    
    class Meta:
        model = Income
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'recorded_by']


class ExpenseSerializer(serializers.ModelSerializer):
    requested_by_name = serializers.CharField(source='requested_by.get_full_name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = Expense
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'requested_by', 'approved_by']


class BudgetItemSerializer(serializers.ModelSerializer):
    remaining_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    utilization_percentage = serializers.FloatField(read_only=True)
    
    class Meta:
        model = BudgetItem
        fields = '__all__'


class BudgetSerializer(serializers.ModelSerializer):
    items = BudgetItemSerializer(many=True, read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Budget
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'created_by']


class ExpenseApprovalSerializer(serializers.ModelSerializer):
    approver_name = serializers.CharField(source='approver.get_full_name', read_only=True)
    
    class Meta:
        model = ExpenseApproval
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class PaymentReminderSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.first_name', read_only=True)
    
    class Meta:
        model = PaymentReminder
        fields = '__all__'
        read_only_fields = ['created_at', 'sent_at']


class FinancialAuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    class Meta:
        model = FinancialAuditLog
        fields = '__all__'
        read_only_fields = ['timestamp']

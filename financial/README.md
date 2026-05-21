# Financial Management System

Complete financial management system for schools including payroll, expenses, income tracking, and budgeting.

## Features

### 1. Staff & Payroll Management
- **Staff Records**: Manage employee information with status tracking
- **Salary Structures**: Define salary components (basic, allowances, deductions)
- **Monthly Payroll**: Automated payroll generation and tracking
- **Payment Processing**: Mark salaries as paid with payment details
- **Payment Reminders**: Automated reminders for pending payments

### 2. Income Tracking
- Track all school income by category:
  - Tuition Fees
  - Registration Fees
  - Examination Fees
  - Transport Fees
  - Canteen Fees
  - Donations
  - Grants
  - Other Income
- Payment method tracking
- Reference number management

### 3. Expense Management
- Expense categories:
  - Salaries
  - Utilities
  - Maintenance
  - Supplies
  - Transport
  - Equipment
  - Training
  - Marketing
  - Other Expenses
- Approval workflow (Pending → Approved → Paid)
- Receipt upload support
- Multi-level approval tracking

### 4. Budget Planning
- Create annual/term budgets
- Budget line items by category
- Real-time spending tracking
- Budget utilization monitoring
- Alerts when budget exceeds 80%

### 5. Financial Dashboard
- Total income vs expenses
- Monthly financial summary
- Net balance tracking
- Payroll summary
- Pending approvals count
- Budget utilization
- Income/Expense breakdown by category

### 6. Notifications
- Payroll generation alerts
- Payment reminders (in-app + SMS)
- Salary payment confirmations
- Expense approval requests
- Budget alerts

## API Endpoints

### Staff Management
```
GET    /api/financial/staff/              - List all staff
POST   /api/financial/staff/              - Create staff member
GET    /api/financial/staff/{id}/         - Get staff details
PUT    /api/financial/staff/{id}/         - Update staff
DELETE /api/financial/staff/{id}/         - Delete staff
```

### Salary Management
```
GET    /api/financial/salaries/           - List salaries
POST   /api/financial/salaries/           - Create salary structure
GET    /api/financial/salaries/{id}/      - Get salary details
PUT    /api/financial/salaries/{id}/      - Update salary
DELETE /api/financial/salaries/{id}/      - Delete salary
```

### Payroll Management
```
GET    /api/financial/payroll/                    - List payroll records
POST   /api/financial/payroll/                    - Create payroll
POST   /api/financial/payroll/generate_monthly/   - Generate monthly payroll
POST   /api/financial/payroll/{id}/mark_paid/     - Mark as paid
POST   /api/financial/payroll/{id}/approve/       - Approve payroll
```

### Income Management
```
GET    /api/financial/income/             - List income records
POST   /api/financial/income/             - Record income
GET    /api/financial/income/{id}/        - Get income details
PUT    /api/financial/income/{id}/        - Update income
DELETE /api/financial/income/{id}/        - Delete income
```

### Expense Management
```
GET    /api/financial/expenses/           - List expenses
POST   /api/financial/expenses/           - Create expense
POST   /api/financial/expenses/{id}/approve/  - Approve expense
POST   /api/financial/expenses/{id}/reject/   - Reject expense
```

### Budget Management
```
GET    /api/financial/budgets/            - List budgets
POST   /api/financial/budgets/            - Create budget
GET    /api/financial/budget-items/       - List budget items
POST   /api/financial/budget-items/       - Create budget item
```

### Financial Dashboard
```
GET    /api/financial/dashboard/          - Get financial analytics
```

## Models

### Staff
- Basic information (name, email, phone, position)
- Employment details (hire date, status, department)
- Bank account information
- Status: ACTIVE, ON_LEAVE, SUSPENDED, TERMINATED

### StaffSalary
- Basic salary
- Allowances (housing, transport, other)
- Deductions (tax, pension, other)
- Effective date
- Calculated: gross_salary(), net_salary()

### PayrollRecord
- Monthly payroll tracking
- Status: DRAFT, APPROVED, PAID, CANCELLED
- Payment details (date, method, reference)
- Approval tracking

### Income
- Category-based income tracking
- Payment method and reference
- Recorded by user tracking

### Expense
- Category-based expense tracking
- Approval workflow
- Receipt file upload
- Status: PENDING, APPROVED, PAID, REJECTED

### Budget
- Budget period (start/end dates)
- Total allocated amount
- Active status

### BudgetItem
- Budget line items
- Allocated vs spent tracking
- Utilization percentage calculation

## Usage Examples

### Generate Monthly Payroll
```python
POST /api/financial/payroll/generate_monthly/
{
    "month": 12,
    "year": 2024
}
```

### Mark Payroll as Paid
```python
POST /api/financial/payroll/{id}/mark_paid/
{
    "payment_date": "2024-12-31",
    "payment_method": "Bank Transfer",
    "payment_reference": "TXN123456"
}
```

### Approve Expense
```python
POST /api/financial/expenses/{id}/approve/
{
    "comments": "Approved for payment"
}
```

### Create Budget
```python
POST /api/financial/budgets/
{
    "name": "2024 Annual Budget",
    "description": "School budget for 2024",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "total_amount": 500000.00
}
```

## Management Commands

### Send Payment Reminders
```bash
python manage.py send_payment_reminders --days=3
```
Sends reminders for payroll due within 3 days.

## Notifications

The system automatically sends notifications for:

1. **Payroll Generated**: Notifies admins when monthly payroll is created
2. **Payment Reminder**: Reminds staff about pending salary payments
3. **Salary Paid**: Confirms payment to staff (in-app + SMS)
4. **Expense Approval**: Alerts admins about pending expense approvals
5. **Expense Status**: Notifies requester when expense is approved/rejected
6. **Budget Alert**: Warns when budget utilization exceeds 80%

## Permissions

- **School Admin/Principal**: Full access to all financial features
- **Teachers**: Can view their own salary information
- **Staff**: Can view their own payroll records

## Installation

1. Add 'financial' to INSTALLED_APPS in settings.py
2. Add financial URLs to main urls.py:
   ```python
   path('api/financial/', include('financial.urls')),
   ```
3. Run migrations:
   ```bash
   python manage.py makemigrations financial
   python manage.py migrate
   ```

## Database Schema

All models are properly indexed and optimized:
- Foreign keys to School for multi-tenancy
- Unique constraints on staff_id per school
- Unique payroll records per staff/month/year
- Proper ordering and filtering

## Security Features

- School-level data isolation
- Permission-based access control
- Audit trail (created_by, approved_by tracking)
- Secure file upload for receipts
- Input validation on all endpoints

## Future Enhancements

- [ ] Payslip PDF generation
- [ ] Tax calculation automation
- [ ] Bank integration for payments
- [ ] Financial reports export (Excel/PDF)
- [ ] Multi-currency support
- [ ] Recurring expense automation
- [ ] Budget forecasting
- [ ] Financial analytics dashboard

## Support

For issues or questions about the Financial Management System, contact the development team.

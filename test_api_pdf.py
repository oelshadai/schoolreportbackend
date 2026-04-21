import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from students.models import Student
from scores.models import SubjectResult
from schools.models import Term
import requests

User = get_user_model()

# Find a student that has subject results
sr = SubjectResult.objects.select_related('student', 'term').first()
if not sr:
    print("No subject results in the database at all!")
    exit(1)

test_student = sr.student
test_term = sr.term
school_id = test_student.school_id
print(f"Student: id={test_student.id} name={test_student.get_full_name()} school={school_id}")
print(f"Term: id={test_term.id} name={test_term.name}")

# Find an admin/teacher user in the same school
user = User.objects.filter(is_active=True, school_id=school_id, role__in=['TEACHER', 'SCHOOL_ADMIN']).first()
if not user:
    # Try SUPER_ADMIN
    user = User.objects.filter(is_active=True, role='SUPER_ADMIN').first()
if not user:
    print("No staff user found!")
    exit(1)

print(f"User: {user.email} role={user.role} school={user.school_id}")

token = RefreshToken.for_user(user)
access = str(token.access_token)

url = 'http://127.0.0.1:8000/api/reports/report-cards/generate_pdf_report/'
headers = {
    'Authorization': f'Bearer {access}',
    'Content-Type': 'application/json',
}
data = {'student_id': test_student.id, 'term_id': test_term.id}

print(f"\nPOST {url}")
print(f"Data: {data}")
resp = requests.post(url, json=data, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp.headers.get('Content-Type', 'N/A')}")
print(f"Content-Length: {len(resp.content)}")
if resp.status_code != 200:
    print(f"Response body: {resp.text[:500]}")
else:
    print("PDF generated successfully via HTTP!")

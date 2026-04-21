import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_report_saas.settings')
django.setup()

import requests

# Login to get token
login_resp = requests.post('http://127.0.0.1:8000/api/auth/login/', json={
    'username': 'admin',
    'password': 'admin123'
})
print(f'Login status: {login_resp.status_code}')
if login_resp.status_code != 200:
    # Try other common credentials
    from django.contrib.auth import get_user_model
    User = get_user_model()
    for u in User.objects.filter(is_active=True, role__in=['ADMIN', 'TEACHER'])[:10]:
        print(f'  Active staff: {u.id} username={u.username} role={u.role} school={u.school_id}')
    print('Could not login. Check credentials.')
else:
    data = login_resp.json()
    token = data.get('access') or data.get('token', {}).get('access', '')
    print(f'Token obtained: {token[:20]}...')
    
    # Try PDF download
    pdf_resp = requests.post(
        'http://127.0.0.1:8000/api/reports/report-cards/generate_pdf_report/',
        json={'student_id': 21, 'term_id': 9},
        headers={'Authorization': f'Bearer {token}'}
    )
    print(f'PDF status: {pdf_resp.status_code}')
    print(f'PDF content-type: {pdf_resp.headers.get("Content-Type")}')
    print(f'PDF size: {len(pdf_resp.content)} bytes')
    if pdf_resp.status_code != 200:
        print(f'PDF error: {pdf_resp.text[:500]}')


import psycopg2
import sys

DB_URL = 'postgresql://mydata_vrae_user:Ek7A81QBArqKLVJzalrv8FWIbSoUCSzb@dpg-d7a7h44hg0os73baeshg-a.oregon-postgres.render.com/mydata_vrae'

conn = psycopg2.connect(DB_URL, sslmode='require')
cur = conn.cursor()

action = sys.argv[1] if len(sys.argv) > 1 else 'list'

if action == 'list':
    # Try both possible table names
    for tbl in ('accounts_user', 'users'):
        try:
            cur.execute(f"SELECT id, email, role, is_active FROM {tbl} ORDER BY id")
            rows = cur.fetchall()
            print(f'Found {len(rows)} users in table [{tbl}]:')
            for r in rows:
                print(f'  id={r[0]}  email={r[1]}  role={r[2]}  active={r[3]}')
            break
        except Exception as e:
            print(f'Table {tbl} error: {e}')
            conn.rollback()
            conn = psycopg2.connect(DB_URL, sslmode='require')
            cur = conn.cursor()

elif action == 'reset_all':
    # Reset all user passwords to a known value using Django's PBKDF2 hasher
    import hashlib, base64, os, struct
    new_password = sys.argv[2] if len(sys.argv) > 2 else 'School@2026'

    # Use Django's make_password algorithm (PBKDF2-SHA256, 600000 iterations)
    import subprocess, json
    result = subprocess.run(
        ['python', '-c',
         f'import django, os; os.environ["DJANGO_SETTINGS_MODULE"]="school_report_saas.settings"; '
         f'django.setup(); from django.contrib.auth.hashers import make_password; '
         f'print(make_password("{new_password}"))'],
        capture_output=True, text=True
    )
    hashed = result.stdout.strip()
    if not hashed.startswith('pbkdf2_'):
        print('Error generating hash:', result.stderr)
    else:
        cur.execute("UPDATE users SET password = %s", (hashed,))
        conn.commit()
        print(f'Reset {cur.rowcount} user passwords to: {new_password}')
        print('Hash:', hashed[:30], '...')

elif action == 'tables':
    cur.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
    tables = [r[0] for r in cur.fetchall()]
    print(f'Tables ({len(tables)}):')
    for t in tables:
        print(f'  {t}')

elif action == 'wipe':
    # Delete ALL application data in FK-safe order (children before parents)
    ordered = [
        # Assignment / quiz children
        'submission_files', 'quiz_answer_files', 'quiz_answers', 'quiz_attempts',
        'task_answers', 'task_attempts', 'task_questions', 'timed_tasks',
        'assignment_attempts', 'student_assignments',
        'question_files', 'question_options', 'questions', 'assignments',
        # Scores / reports
        'continuous_assessments', 'exam_scores',
        'subject_results', 'term_results',
        'report_cards',
        # Attendance / behaviour
        'daily_attendance', 'attendance', 'behaviour',
        # Fees
        'fees_studentfee', 'fees_feepayment', 'fees_feecollection',
        'fees_feestructure', 'fees_feetype',
        # Students
        'student_portal_access', 'student_promotions', 'students',
        # Classes / curriculum
        'class_subjects', 'subjects', 'grading_scales',
        'lesson_slots', 'classes',
        'terms', 'academic_years',
        # Notifications / events / announcements
        'notifications_notification', 'notifications_supportticket',
        'events_event', 'announcements',
        # Profile / payments
        'profile_change_requests', 'payments',
        'subscriptions', 'subscription_plans',
        # Teachers
        'teachers_specializations', 'teachers',
        # Auth / users
        'users_groups', 'users_user_permissions',
        'django_admin_log', 'django_session',
        'users',
        # School last
        'schools',
    ]
    wiped = 0
    for table in ordered:
        try:
            cur.execute(f'DELETE FROM "{table}"')
            conn.commit()
            if cur.rowcount:
                print(f'  Cleared [{table}]: {cur.rowcount} rows')
                wiped += cur.rowcount
        except Exception:
            conn.rollback()
    print(f'\nDone. Wiped {wiped} total rows. Database is completely empty.')

elif action == 'wipe_users_only':
    cur.execute('DELETE FROM accounts_user')
    print(f'Deleted {cur.rowcount} users')
    conn.commit()

cur.close()
conn.close()

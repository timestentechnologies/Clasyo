import os
import sys
import django
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')
django.setup()

from django.test import Client
from accounts.models import User

client = Client(SERVER_NAME='127.0.0.1', SERVER_PORT='8000')
superadmin = User.objects.using('default').filter(role='superadmin').first()
client.force_login(superadmin, backend='django.contrib.auth.backends.ModelBackend')

# 1. Dashboard
res = client.get('/school/demo-school/')
content = res.content.decode('utf-8')

m_students = re.search(r'<div class="hero-stat-primary-value">\s*(\d+)\s*</div>', content)
if m_students:
    print('Rendered Students on Dashboard:', m_students.group(1))
else:
    print('Students not matched')

side_stats = re.findall(r'<span class="side-stat-val[^"]*">\s*(\d+)\s*</span>\s*<span class="side-stat-lbl">\s*([^<]+)\s*</span>', content)
print('Side Stats:', side_stats)

events = re.findall(r'<h6 class="mb-1">\s*([^<]+)\s*</h6>', content)
print('Events rendered on Dashboard:', events)

# 2. Students List
res_stu = client.get('/school/demo-school/students/')
content_stu = res_stu.content.decode('utf-8')
m_enrolled = re.search(r'(\d+)\s*students enrolled', content_stu, re.IGNORECASE)
print('Students page enrolled count:', m_enrolled.group(0) if m_enrolled else 'Not found')

# 3. Parents List
res_par = client.get('/school/demo-school/students/parents/')
content_par = res_par.content.decode('utf-8')
parent_rows = re.findall(r'<tr[^>]*>\s*<td>\s*([^<]+)\s*</td>', content_par)
print('Parents rendered on Parents page:', parent_rows[:10])

# 4. Check if demo school badge is in header
print('Header has demo-school badge:', 'Official Demo School Environment' in content or 'badge bg-info-subtle' in content)

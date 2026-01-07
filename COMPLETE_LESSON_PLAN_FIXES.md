# Complete Lesson Plan Fixes - Deployment Guide

## Issues Fixed

### 1. ✅ Lesson Plan Update Issue
**Problem**: Lesson plans were not updating due to form validation logic
**Root Cause**: `form_valid()` method only saved if resource_formset was valid
**Fix**: Modified to always save main lesson plan, handle resources separately

### 2. ✅ Dashboard Cards Showing Zeros
**Problem**: All dashboard cards showed "0" despite having data
**Root Cause**: Missing count calculations in dashboard view
**Fix**: Added proper count logic for admin vs teacher roles

### 3. ✅ CKEditor Security Warning
**Problem**: Persistent security warning about CKEditor version
**Root Cause**: Version check not properly disabled and outdated static files
**Fix**: Enhanced configuration and created cache clearing command

## Files Modified

### 1. `lesson_plan/views.py`
- **Lines 277-303**: Fixed `form_valid()` method in `LessonPlanUpdateView`
- **Lines 21-78**: Added dashboard card count calculations

### 2. `school_saas/settings.py`
- **Lines 248-273**: Enhanced CKEditor configuration with security settings
- **Lines 272-273**: Added CKEditor cache settings

### 3. `lesson_plan/management/commands/clear_ckeditor_cache.py` (NEW)
- Management command to clear CKEditor cache and static files

## Deployment Instructions

### Step 1: Deploy Code Changes
```bash
# On production server
cd /home3/opulentl/schoolsaas
git pull origin main
```

### Step 2: Update Dependencies
```bash
source /home3/opulentl/virtualenv/schoolsaas/3.13/bin/activate
pip install -r requirements.txt
```

### Step 3: Clear CKEditor Cache
```bash
python manage.py clear_ckeditor_cache
```

### Step 4: Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### Step 5: Restart Application
```bash
# Restart your web server
# For cPanel: Restart Python app through cPanel interface
# For systemd:
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

## Testing Checklist

### Lesson Plan Update Test
- [ ] Go to existing lesson plan
- [ ] Click "Edit"
- [ ] Make changes to title/content
- [ ] Click "Save"
- [ ] Verify success message appears
- [ ] Verify changes are saved
- [ ] Verify redirect to detail page works

### Dashboard Cards Test
- [ ] Total Lesson Plans shows correct count
- [ ] My Lesson Plans shows correct count
- [ ] Subjects shows correct count
- [ ] Today's Plans shows correct count
- [ ] Recent Lesson Plans list displays correctly

### CKEditor Test
- [ ] No security warning appears
- [ ] Editor loads properly
- [ ] Unicode characters (⅓, ⅔, ±, ×, ÷) work
- [ ] Rich text formatting works
- [ ] File uploads work

## Troubleshooting

### If Lesson Plan Update Still Fails:
1. Check browser console for JavaScript errors
2. Check Django logs: `tail -f debug.log`
3. Verify form submission data in network tab
4. Check if user has proper permissions

### If Dashboard Cards Still Show Zero:
1. Verify user role (admin vs teacher)
2. Check database connection
3. Verify lesson plans exist in database
4. Check query filters in dashboard view

### If CKEditor Warning Persists:
1. Clear browser cache (Ctrl+F5)
2. Clear server static files: `rm -rf staticfiles/ckeditor/*`
3. Restart web server
4. Check if CDN is loading old version

## Database Queries for Verification

### Check Lesson Plan Counts:
```sql
-- Total lesson plans
SELECT COUNT(*) FROM lesson_plan_lessonplan;

-- Your lesson plans
SELECT COUNT(*) FROM lesson_plan_lessonplan WHERE created_by_id = [user_id];

-- Today's plans
SELECT COUNT(*) FROM lesson_plan_lessonplan 
WHERE planned_date = CURDATE() AND status = 'approved';
```

### Check CKEditor Version:
```sql
-- Check if static files were updated
SELECT * FROM django_admin_log 
WHERE action_flag = 'CHANGE' AND object_repr LIKE '%ckeditor%';
```

## Expected Results

After deployment:
1. **Lesson plan updates** should work immediately with success messages
2. **Dashboard cards** should show accurate counts based on user role
3. **CKEditor** should load without security warnings
4. **Unicode characters** should save properly in all text fields

## Monitoring

Monitor these logs for 24 hours after deployment:
- Django application logs: `debug.log`
- Web server error logs
- Browser console for JavaScript errors
- User feedback on functionality

## Rollback Plan

If critical issues occur:
```bash
# Revert to previous commit
git checkout HEAD~1 -- .

# Downgrade CKEditor if needed
pip install django-ckeditor==6.7.0

# Restart application
```

These fixes should resolve all three issues simultaneously while maintaining full functionality.

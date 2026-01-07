# Fix for Lesson Plan Unicode Character Issue

## Problem
When saving lesson plans containing Unicode characters (like fractions ⅓, ⅔, ¼, etc.), the following error occurs:
```
DataError: (1366, "Incorrect string value: '\\xE2\\x85\\x93 + ...' for column `lesson_plan_lessonplan`.`main_content` at row 1")
```

## Root Cause
The MySQL database columns were created with a charset that doesn't support Unicode characters beyond basic ASCII.

## Solution
I've created a comprehensive fix that includes:

### 1. Database Migrations
- `0004_fix_textfield_charset.py` - Converts all text fields to utf8mb4 charset
- `0005_convert_tables_to_utf8mb4.py` - Converts all lesson_plan tables to utf8mb4

### 2. Enhanced Database Configuration
Updated `school_saas/settings.py` to include `use_unicode: True` for better Unicode support.

### 3. Production Fix Script
`fix_lesson_plan_charset.py` - A standalone script to apply the charset fixes directly on production.

## Deployment Instructions

### Option 1: Using Migrations (Recommended)
1. Deploy the code changes to production
2. Run the migrations:
   ```bash
   python manage.py migrate lesson_plan
   ```

### Option 2: Using the Fix Script (Immediate Fix)
1. Upload `fix_lesson_plan_charset.py` to the production server
2. Run the script:
   ```bash
   cd /home3/opulentl/schoolsaas
   python fix_lesson_plan_charset.py
   ```

### Option 3: Manual SQL Execution
Run these SQL commands directly on the database:

```sql
-- Convert text fields in lesson_plan_lessonplan table
ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN description LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN learning_objectives LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN materials_resources LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN introduction LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN main_content LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN activities LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN assessment LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN differentiation LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN conclusion LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN homework LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN notes LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

ALTER TABLE lesson_plan_lessonplan 
MODIFY COLUMN execution_notes LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Convert all lesson_plan tables to utf8mb4
ALTER TABLE lesson_plan_lessonplan CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE lesson_plan_lessonplantemplate CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE lesson_plan_lessonplanstandard CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE lesson_plan_lessonplanfeedback CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE lesson_plan_lessonplanresource CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Verification
After applying the fix, test by creating a lesson plan with Unicode characters like:
- Fractions: ⅓, ⅔, ¼, ¾
- Mathematical symbols: ±, ×, ÷
- Special characters: ©, ®, ™

## Prevention
The enhanced database configuration in `settings.py` will ensure that:
1. All new database connections use utf8mb4 charset
2. Unicode characters are properly handled
3. Future migrations will create columns with the correct charset

## Files Modified/Created
1. `lesson_plan/migrations/0004_fix_textfield_charset.py` (new)
2. `lesson_plan/migrations/0005_convert_tables_to_utf8mb4.py` (new)
3. `school_saas/settings.py` (modified)
4. `fix_lesson_plan_charset.py` (new)
5. `LESSON_PLAN_CHARSET_FIX.md` (this file)

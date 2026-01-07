#!/usr/bin/env python3
"""
Fix for MySQL charset issue in lesson_plan app.
This script fixes the Unicode character encoding issue that prevents saving
lesson plans with special characters like fractions (⅓, ⅔, ¼, etc.).

Run this script on the production server after deploying the migrations.
"""

import os
import sys
import django
from django.db import connection

# Add the project directory to Python path
sys.path.append('/home3/opulentl/schoolsaas')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'school_saas.settings')

# Setup Django
django.setup()

def fix_lesson_plan_charset():
    """
    Fix charset issues in lesson_plan tables and columns
    """
    print("Starting charset fix for lesson_plan tables...")
    
    with connection.cursor() as cursor:
        try:
            # 1. Convert all text fields in lesson_plan_lessonplan table
            text_fields = [
                'description', 'learning_objectives', 'materials_resources',
                'introduction', 'main_content', 'activities', 'assessment',
                'differentiation', 'conclusion', 'homework', 'notes', 'execution_notes'
            ]
            
            print("Converting text fields to utf8mb4...")
            for field in text_fields:
                cursor.execute(f"""
                    ALTER TABLE lesson_plan_lessonplan 
                    MODIFY COLUMN {field} LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """)
                print(f"✓ Fixed field: {field}")
            
            # 2. Convert all lesson_plan tables to utf8mb4
            tables = [
                'lesson_plan_lessonplan',
                'lesson_plan_lessonplantemplate', 
                'lesson_plan_lessonplanstandard',
                'lesson_plan_lessonplanfeedback',
                'lesson_plan_lessonplanresource'
            ]
            
            print("\nConverting tables to utf8mb4...")
            for table in tables:
                cursor.execute(f"""
                    ALTER TABLE {table} 
                    CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
                """)
                print(f"✓ Fixed table: {table}")
            
            # 3. Verify the changes
            print("\nVerifying charset changes...")
            cursor.execute("""
                SELECT table_name, table_collation 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name LIKE 'lesson_plan_%'
            """)
            
            results = cursor.fetchall()
            for table, collation in results:
                print(f"✓ {table}: {collation}")
            
            print("\n✅ Charset fix completed successfully!")
            print("You can now save lesson plans with Unicode characters like ⅓, ⅔, ¼, etc.")
            
        except Exception as e:
            print(f"❌ Error during charset fix: {e}")
            raise

if __name__ == "__main__":
    fix_lesson_plan_charset()

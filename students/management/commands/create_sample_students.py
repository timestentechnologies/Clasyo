from django.core.management.base import BaseCommand
from students.models import Student
from accounts.models import User
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Create sample students for testing'

    def handle(self, *args, **kwargs):
        # Sample data
        first_names_male = ['John', 'Michael', 'David', 'James', 'Robert', 'William', 'Joseph', 'Thomas', 'Daniel', 'Matthew']
        first_names_female = ['Mary', 'Emma', 'Olivia', 'Sophia', 'Isabella', 'Ava', 'Mia', 'Emily', 'Abigail', 'Madison']
        last_names = ['Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis', 'Rodriguez', 'Martinez']
        blood_groups = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
        religions = ['Christian', 'Muslim', 'Hindu', 'Buddhist', 'Jewish', 'Other']
        cities = ['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']
        states = ['NY', 'CA', 'IL', 'TX', 'AZ']
        
        students_created = 0
        
        for i in range(1, 21):  # Create 20 students
            gender = random.choice(['male', 'female'])
            if gender == 'male':
                first_name = random.choice(first_names_male)
            else:
                first_name = random.choice(first_names_female)
            
            last_name = random.choice(last_names)
            email = f'{first_name.lower()}.{last_name.lower()}{i}@student.school.com'
            
            # Create user account first
            user = User.objects.create_user(
                email=email,
                password='student123',
                first_name=first_name,
                last_name=last_name,
                role='student',
                is_active=True
            )
            
            # Random date of birth (age between 10 and 18)
            days_old = random.randint(10*365, 18*365)
            date_of_birth = date.today() - timedelta(days=days_old)
            city_idx = random.randint(0, 4)
            
            # Create student profile
            student = Student.objects.create(
                user=user,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                gender=gender,
                blood_group=random.choice(blood_groups),
                religion=random.choice(religions),
                admission_number=f'STU{2024}{i:04d}',
                admission_date=date(2024, random.randint(1, 12), random.randint(1, 28)),
                roll_number=f'R{i:03d}',
                email=email,
                current_address=f'{random.randint(100, 999)} Main Street, {cities[city_idx]}, {states[city_idx]} {random.randint(10000, 99999)}',
                city=cities[city_idx],
                state=states[city_idx],
                country='US',
                postal_code=str(random.randint(10000, 99999))
            )
            
            students_created += 1
            self.stdout.write(self.style.SUCCESS(f'Created student: {student.first_name} {student.last_name}'))
        
        self.stdout.write(self.style.SUCCESS(f'\nSuccessfully created {students_created} sample students!'))
        self.stdout.write(self.style.SUCCESS('Login with: student email / password: student123'))

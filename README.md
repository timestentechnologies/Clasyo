# Multi-Tenant School Management System (SaaS)

A comprehensive, multi-tenant School Management System built with Django, designed to manage multiple schools from a single installation.

## Features

### 🎯 Core Features

#### Multi-Tenancy & Subscriptions
- **Multi-tenant Architecture**: Each school operates independently with its own database schema
- **Subscription Plans**: Flexible subscription plans (Free Trial, Basic, Standard, Premium, Enterprise)
- **Online Payment Integration**: Stripe, Razorpay, PayPal support
- **Free Trial System**: Configurable trial periods
- **Auto-renewal**: Automatic subscription renewal with notifications

#### User Management
- **Multiple User Roles**:
  - Super Admin (Platform owner)
  - School Admin
  - Teacher
  - Accountant
  - Librarian
  - Receptionist
  - Parent
  - Student
- **Role-based Access Control (RBAC)**
- **Fine-grained Permissions**
- **User Activity Logs**

#### Student Management
- **Complete Student Profiles**: Personal, academic, medical information
- **Admission Management**: Online admissions, admission queries
- **Student Categories**: Organize students by categories
- **Student Groups**: Custom student groupings
- **Student Promotion**: Bulk and individual promotion
- **Disable/Enable Students**
- **Student Timeline**: Complete history tracking
- **Sibling Management**: Link siblings
- **Document Management**: Upload and manage student documents
- **Multi-class Support**: Single student can enroll in multiple classes

#### Academic Management
- **Classes & Sections**: Unlimited classes and sections
- **Subjects**: Subject management with optional subjects
- **Class Teacher Assignment**
- **Subject Teacher Assignment**
- **Class Routines**: Automated timetable generation
- **Academic Year Management**
- **Semester/Term Management**
- **House System**: House allocation and management

#### Fees Management
- **Fees Groups & Types**
- **Fees Master**: Define fee structures
- **Fees Collection**: Online and offline collection
- **Fees Discount**: Category-based and individual discounts
- **Fees Carry Forward**: Carry fees to next session
- **Bank Payment**: Bank transfer integration
- **Payment History**
- **Fee Reminders**: Automated SMS/Email reminders
- **Collection Reports**: Daily, monthly, yearly reports
- **Wallet System**: Student wallet for payments

#### Examination System
- **Marks Grading System**
- **Exam Types**: Mid-term, Final, Unit tests
- **Exam Schedule**: Automated scheduling
- **Exam Attendance**: Track student presence
- **Marks Entry**: Teacher marks entry
- **Mark Register**: Complete marks records
- **Final Mark Calculation**: Multiple exam aggregation
- **Report Cards**: Auto-generated report cards
- **Progress Cards**: Student progress tracking
- **Tabulation Sheets**
- **Merit Lists**

#### Online Examination
- **Question Bank**: Centralized question repository
- **Multiple Question Types**:
  - Multiple Choice Questions (MCQ)
  - True/False
  - Fill in the Blanks
  - Descriptive
- **Online Test Creation**
- **Automated Grading**
- **Time-bound Exams**
- **Result Analysis**

#### Homework Management
- **Homework Assignment**: Create and assign homework
- **Subject-wise Homework**
- **Homework Submission**: Students can submit online
- **Evaluation System**: Grade and provide feedback
- **Homework Reports**
- **Reminder System**

#### Human Resource (HR)
- **Staff Directory**: Complete staff database
- **Staff Attendance**: Daily attendance tracking
- **Department Management**
- **Designation Management**
- **Payroll System**: Automated salary calculation
- **Payroll Reports**
- **Staff ID Cards**: Auto-generate ID cards

#### Leave Management
- **Leave Types**: Sick, casual, earned, etc.
- **Leave Application**: Staff leave requests
- **Leave Approval**: Multi-level approval
- **Leave Balance**: Track remaining leaves
- **Leave Calendar**
- **Leave Reports**

#### Communication System
- **Notice Board**: School-wide announcements
- **SMS Notifications**: Bulk SMS sending
- **Email Notifications**: Automated emails
- **Push Notifications**
- **Event Management**: School events calendar
- **Holiday Management**
- **Parent-Teacher Messaging**
- **Event Logs**

#### Chat Module
- **Real-time Chat**: WebSocket-based chat
- **User-to-User Chat**
- **Group Chat**: Class/section groups
- **Teacher-Parent Chat**
- **Admin Chat Control**
- **File Sharing**: Images, documents
- **Chat History**
- **Block/Unblock Users**
- **Pinned Messages**

#### Library Management
- **Book Catalog**: Complete book database
- **Book Categories**
- **Member Management**
- **Book Issue/Return**
- **Fine Management**: Overdue fines
- **Library Cards**: Generate library cards
- **Book Reservation**
- **Library Reports**

#### Inventory Management
- **Item Categories**
- **Item Management**
- **Store Management**
- **Supplier Management**
- **Item Purchase/Receive**
- **Item Issue**: Issue to departments
- **Item Sell**
- **Stock Reports**

#### Transport Management
- **Route Management**: Define transport routes
- **Vehicle Management**: Vehicle database
- **Vehicle Assignment**: Assign vehicles to routes
- **Student Transport**: Assign students to routes
- **Transport Fees**
- **Driver Management**
- **Transport Schedule**
- **GPS Tracking** (Integration ready)

#### Dormitory/Hostel Management
- **Dormitory Management**: Multiple hostels
- **Room Types**: Different room categories
- **Room Management**: Room allocation
- **Student Allocation**: Assign students to rooms
- **Hostel Fees**
- **Room Monitoring**
- **Hostel Reports**

#### Reports & Analytics
- **Student Reports**: Comprehensive student data
- **Guardian Reports**
- **Attendance Reports**: Class-wise, student-wise
- **Fee Reports**: Collection, dues, statements
- **Exam Reports**: Subject-wise, class-wise
- **Staff Reports**: Attendance, payroll
- **Transport Reports**
- **Library Reports**
- **Custom Report Builder**

#### Lesson Plan
- **Lesson Management**: Create lesson plans
- **Topic Management**: Organize by topics
- **Topic Overview**
- **Lesson Plan Calendar**
- **Subject-wise Lessons**

#### Certificates & ID Cards
- **Certificate Templates**: Customizable templates
- **Certificate Generation**: Bulk generation
- **ID Card Templates**
- **ID Card Generation**: Student & staff
- **QR Code Integration**
- **Barcode Support**

#### Attendance System
- **Student Attendance**: Daily attendance
- **Subject-wise Attendance**
- **Attendance Reports**
- **Attendance Percentage**
- **Biometric Integration** (Ready)
- **SMS Notifications**: Absent alerts

#### Front Office
- **Admission Enquiry**: Track prospective students
- **Follow-up System**
- **Visitor Book**: Visitor management
- **Phone Call Log**: Track all calls
- **Postal Dispatch/Receive**
- **Complaint Management**
- **Front Office Reports**

#### Website Management (CMS)
- **Homepage Builder**
- **Menu Manager**: Dynamic menu creation
- **Pages**: Unlimited custom pages
- **News/Blogs**: News management
- **Events**: Event listing
- **Gallery**: Photo galleries
- **Courses**: Course showcase
- **Testimonials**
- **Contact Form**
- **Banner Management**
- **Footer Widgets**
- **SEO Friendly**

### 🛠️ Technical Features

- **Modern Tech Stack**: Django 4.2, Python 3.10+
- **Database**: PostgreSQL with multi-tenant support
- **Real-time Updates**: WebSockets (Channels)
- **Task Queue**: Celery with Redis
- **RESTful API**: Django REST Framework
- **Responsive Design**: Mobile-friendly UI
- **Security**: CSRF protection, SQL injection prevention
- **Multi-language Support**: i18n ready
- **RTL Support**: Right-to-left languages
- **Dark Mode**: Theme switching
- **Export Data**: PDF, Excel, CSV
- **Import Data**: Bulk data import
- **Automated Backups**: Scheduled backups
- **One-click Updates**
- **Debug Toolbar**: Development tools
- **Email Templates**: Customizable email templates
- **SMS Gateway Integration**
- **Cloud Storage**: AWS S3, Google Cloud ready

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 12 or higher
- Redis Server
- Virtual Environment (recommended)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd SAASSCHHOLERP
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create a `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` and configure your settings:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=school_saas
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=localhost
DB_PORT=5432

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Payment Gateways
STRIPE_PUBLIC_KEY=your-stripe-public-key
STRIPE_SECRET_KEY=your-stripe-secret-key
RAZORPAY_KEY_ID=your-razorpay-key
RAZORPAY_KEY_SECRET=your-razorpay-secret

# Redis
REDIS_URL=redis://localhost:6379/0
```

### Step 5: Create PostgreSQL Database

```bash
psql -U postgres
CREATE DATABASE school_saas;
\q
```

### Step 6: Run Migrations

```bash
# Migrate shared schema
python manage.py migrate_schemas --shared

# Create public tenant
python manage.py create_tenant_superuser
```

### Step 7: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 8: Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### Step 9: Run Development Server

```bash
python manage.py runserver
```

Visit `http://localhost:8000` in your browser.

### Step 10: Start Celery (Optional, for background tasks)

In a new terminal:

```bash
# Windows
celery -A school_saas worker -l info -P solo

# Linux/Mac
celery -A school_saas worker -l info
```

Start Celery Beat for scheduled tasks:

```bash
celery -A school_saas beat -l info
```

### Step 11: Start Redis Server

Make sure Redis is running:

```bash
# Windows (if installed via installer)
redis-server

# Linux
sudo service redis-server start

# Mac
brew services start redis
```

## Usage

### Creating a New School (Tenant)

1. Login to Super Admin panel
2. Go to Subscriptions → Create School
3. Fill in school details
4. Select subscription plan
5. School domain will be created automatically

### Accessing School Dashboard

Each school can be accessed via subdomain:
- `http://school-slug.localhost:8000`
- Or use domain mapping

### Default Logins

After installation:
- **Super Admin**: superadmin@example.com
- **Password**: (set during superuser creation)

## Project Structure

```
SAASSCHHOLERP/
├── school_saas/          # Main project settings
├── tenants/              # Multi-tenant models
├── subscriptions/        # Subscription management
├── superadmin/           # Super admin panel
├── accounts/             # User authentication
├── students/             # Student management
├── academics/            # Academic management
├── fees/                 # Fee management
├── examinations/         # Examination system
├── online_exam/          # Online examination
├── homework/             # Homework management
├── human_resource/       # HR management
├── leave_management/     # Leave system
├── communication/        # Communication module
├── chat/                 # Chat system
├── library/              # Library management
├── inventory/            # Inventory management
├── transport/            # Transport management
├── dormitory/            # Hostel management
├── attendance/           # Attendance system
├── lesson_plan/          # Lesson planning
├── certificates/         # Certificates & ID cards
├── reports/              # Reports module
├── frontend/             # Public website
├── core/                 # Core utilities
├── templates/            # HTML templates
├── static/               # Static files (CSS, JS)
├── media/                # User uploaded files
└── requirements.txt      # Python dependencies
```

## Technology Stack

- **Backend**: Django 4.2
- **Database**: PostgreSQL (Multi-tenant)
- **Cache**: Redis
- **Task Queue**: Celery
- **WebSockets**: Django Channels
- **Frontend**: Bootstrap 5, jQuery
- **Charts**: Chart.js
- **Icons**: Font Awesome, Lucide
- **PDF Generation**: ReportLab, WeasyPrint
- **Excel**: openpyxl, pandas
- **Payment**: Stripe, Razorpay

## API Documentation

API endpoints are available at `/api/docs/` (when enabled)

## Contributing

Contributions are welcome! Please read CONTRIBUTING.md for details.

## License

This project is licensed under the MIT License - see LICENSE file for details.

## Support

For support, email support@schoolsaas.com or visit our documentation at docs.schoolsaas.com

## Credits

Developed by Yugesh Verma
Version: 1.0.0
Release Date: May 8, 2025

## Changelog

### Version 1.0.0 (May 8, 2025)
- Initial release
- Multi-tenant architecture
- All core modules implemented
- Payment gateway integration
- Real-time chat system
- Comprehensive reporting

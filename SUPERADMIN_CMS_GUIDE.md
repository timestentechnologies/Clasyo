# Super Admin CMS Guide

## Overview
The frontend content (Pricing Plans, FAQs, Page Content, Contact Messages) is now managed through the **Super Admin** panel with full CRUD functionality.

## Accessing Super Admin CMS

### Login
1. Navigate to: `http://127.0.0.1:8000/superadmin/`
2. Login with your superadmin credentials
3. You must have `role='superadmin'` in the database

### CMS Menu
Look for the **"Website Content"** section in the left sidebar:
- **Pricing Plans** - Manage pricing tiers
- **FAQs** - Manage frequently asked questions
- **Page Content** - Manage About/Contact page content
- **Contact Messages** - View form submissions

---

## Managing Content

### 1. Pricing Plans (`/superadmin/content/pricing/`)

**Features:**
- Create, Edit, Delete pricing plans
- Set popular plan (shows "Most Popular" badge)
- Set display order
- Activate/deactivate plans
- Add unlimited features per plan

**Fields:**
- **Name**: Plan name (e.g., "Basic", "Professional", "Enterprise")
- **Price**: Monthly/yearly price (e.g., 29.99)
- **Duration**: "Monthly", "Yearly", etc.
- **Max Students**: Number allowed (blank for unlimited)
- **Max Teachers**: Number allowed (blank for unlimited)
- **Max Staff**: Number allowed (blank for unlimited)
- **Features**: One per line:
  ```
  Online Attendance
  Real-time Notifications
  Exam Management
  Fee Collection
  ```
- **Is Popular**: Check for recommended plan
- **Is Active**: Must be checked to show on website
- **Order**: Display order (1, 2, 3...)

**How to Use:**
1. Click "Pricing Plans" in sidebar
2. View existing plans in table
3. Use Django Admin link to add/edit (opens in new tab)
4. Or use direct CRUD forms (if custom templates implemented)

---

### 2. FAQs (`/superadmin/content/faq/`)

**Features:**
- Create, Edit, Delete FAQs
- Organize by category
- Filter by category
- Set display order
- Activate/deactivate

**Fields:**
- **Question**: The FAQ question
- **Answer**: Detailed answer (supports multiple paragraphs)
- **Category**: Choose category:
  - `General` - Shows on FAQ page
  - `About` - Shows on About page  
  - `Pricing` - Shows on Pricing page
  - `Contact` - Shows on Contact page
  - `Technical` - For technical FAQs
- **Order**: Display order within category
- **Is Active**: Must be checked to appear

**How to Use:**
1. Click "FAQs" in sidebar
2. Filter by category if needed
3. Add/Edit FAQs
4. Set proper category and order

**Example FAQs:**

**General:**
- Q: "What is Clasyo?"
- A: "Clasyo is a comprehensive school management system..."

**Pricing:**
- Q: "Can I change my plan anytime?"
- A: "Yes, you can upgrade or downgrade..."

**About:**
- Q: "How long have you been in business?"
- A: "Since 2020..."

---

### 3. Page Content (`/superadmin/content/pages/`)

**Features:**
- Manage static page content
- Edit About page content
- Edit Contact information
- Add JSON data for structured content

**Available Pages:**
- `about` - About Us page
- `home_hero` - Home page hero section
- `home_features` - Home features section
- `contact` - Contact page information

**Fields:**
- **Page**: Select the page
- **Title**: Main heading
- **Subtitle**: Subheading (optional)
- **Content**: Main text content
- **Extra Data**: JSON format for additional data
  
  Example for contact page:
  ```json
  {
    "email": "support@yourschool.com",
    "phone": "+254 xxx xxx xxx",
    "address": "123 Main St, City, Country"
  }
  ```
- **Is Active**: Must be checked to show

**How to Use:**
1. Click "Page Content" in sidebar
2. Edit existing content or create new
3. Use proper JSON format for extra_data
4. Save and view on frontend

---

### 4. Contact Messages (`/superadmin/content/messages/`)

**Features:**
- View all contact form submissions
- Mark as read/unread
- Mark as replied
- Delete messages
- Filter by status

**Available Filters:**
- All Messages
- Unread
- Replied

**Actions:**
- **Mark as Read**: Track which messages you've seen
- **Mark as Replied**: After responding to user
- **Delete**: Remove message

**Message Details:**
- Name
- Email
- Phone (if provided)
- Subject
- Message
- Date submitted

**How to Use:**
1. Click "Contact Messages" in sidebar
2. View list of submissions
3. Click on message to view details
4. Use action buttons to mark status
5. Reply via email, then mark as "Replied"

---

## Implementation Details

### Backend (Already Implemented)
✅ Models: `PricingPlan`, `FAQ`, `PageContent`, `ContactMessage`
✅ Views: Full CRUD operations in `superadmin/views.py`
✅ Forms: ModelForms for all content types
✅ URLs: Routes configured in `superadmin/urls.py`

### Frontend Pages (Database-Driven)
✅ **About** (`/about/`) - Fetches from PageContent & FAQs
✅ **Pricing** (`/pricing/`) - Fetches from PricingPlan & FAQs  
✅ **Contact** (`/contact/`) - Fetches from PageContent & FAQs, saves to ContactMessage
✅ **FAQ** (`/faq/`) - Displays all FAQs grouped by category

### Current CMS Interface
The superadmin templates currently link to Django Admin for add/edit operations. This provides:
- Full model admin interface
- Inline editing
- Search and filters
- Bulk actions

### Custom CMS Interface (Optional Future Enhancement)
To create inline forms in superadmin (without Django Admin):
1. Update templates with modal forms
2. Add JavaScript for dynamic interactions
3. Style with Bootstrap 5
4. Add AJAX for seamless updates

---

## Quick Start Workflow

### Initial Setup:

1. **Create Superadmin User** (if not exists):
   ```python
   python manage.py shell
   from accounts.models import User
   User.objects.create_superuser(
       email='admin@school.com',
       password='yourpassword',
       first_name='Super',
       last_name='Admin',
       role='superadmin'
   )
   ```

2. **Login to Super Admin**:
   - Go to: http://127.0.0.1:8000/superadmin/
   - Login with superadmin credentials

3. **Add Content**:
   - Add 3-4 Pricing Plans
   - Add 5-10 FAQs across categories
   - Update About page content
   - Set Contact information

4. **Test Frontend**:
   - Visit http://127.0.0.1:8000/about/
   - Visit http://127.0.0.1:8000/pricing/
   - Visit http://127.0.0.1:8000/faq/
   - Visit http://127.0.0.1:8000/contact/
   - Submit a test contact form

---

## Tips

1. **Pricing Plans**:
   - Keep feature lists concise
   - Mark your best value plan as "Popular"
   - Use proper ordering (1=first, 2=second...)

2. **FAQs**:
   - Answer common questions
   - Use appropriate categories
   - Keep answers helpful but brief

3. **Page Content**:
   - Update regularly
   - Use JSON format carefully for extra_data
   - Preview changes on frontend

4. **Contact Messages**:
   - Check daily for new submissions
   - Mark as read when viewed
   - Mark as replied after responding

---

## Troubleshooting

**Q: Can't access superadmin panel**
- Ensure your user has `role='superadmin'`
- Check you're logged in
- Verify URL: `/superadmin/` not `/admin/`

**Q: Changes don't appear on frontend**
- Check "Is Active" is checked
- Clear browser cache (Ctrl+F5)
- Verify correct category/page selection

**Q: Content not showing on specific page**
- Check category matches page (FAQ)
- Ensure page field is correct (PageContent)
- Verify "Is Active" is true

**Q: JSON parse error in extra_data**
- Use valid JSON format
- Use double quotes, not single quotes
- Validate JSON syntax

---

## File Locations

**Models**: `frontend/models.py`
**Views**: `superadmin/views.py` + `frontend/views.py`
**Templates (Superadmin)**: `templates/superadmin/`
**Templates (Frontend)**: `templates/frontend/`
**URLs**: `superadmin/urls.py` + `frontend/urls.py`

---

**Last Updated:** November 2025
**Version:** 1.0

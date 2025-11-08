# Frontend Content Management Guide

## Overview
The frontend pages (About, Pricing, Contact) are now database-driven and can be managed through the Django admin panel.

## Accessing the Admin Panel

1. Navigate to: `http://127.0.0.1:8000/admin/`
2. Login with superadmin credentials
3. Look for the **Frontend** section in the admin dashboard

## Managing Content

### 1. Pricing Plans

**Location:** `Frontend > Pricing Plans`

**How to Add/Edit:**
1. Click "Add Pricing Plan" or select an existing plan
2. Fill in the following fields:
   - **Name**: e.g., "Basic Plan", "Professional Plan", "Enterprise Plan"
   - **Price**: Monthly or yearly price (e.g., 29.99)
   - **Duration**: e.g., "Monthly", "Yearly", "Lifetime"
   - **Max Students**: Number of students allowed (leave blank for unlimited)
   - **Max Teachers**: Number of teachers allowed (leave blank for unlimited)
   - **Max Staff**: Number of staff allowed (leave blank for unlimited)
   - **Features**: Enter each feature on a new line:
     ```
     Online Attendance Tracking
     Real-time SMS Notifications
     Complete Exam Management
     Fee Collection & Reports
     ```
   - **Is Popular**: Check this for the recommended plan (displays "Most Popular" badge)
   - **Is Active**: Must be checked for the plan to appear on the website
   - **Order**: Display order (lower numbers appear first)

**Example Plans:**
- **Starter**: $19/month, 100 students, 10 teachers
- **Professional**: $49/month, 500 students, 50 teachers (mark as popular)
- **Enterprise**: $99/month, unlimited students and teachers

---

### 2. FAQs (Frequently Asked Questions)

**Location:** `Frontend > FAQs`

**How to Add/Edit:**
1. Click "Add FAQ" or select an existing FAQ
2. Fill in the following fields:
   - **Question**: The question text (e.g., "What payment methods do you accept?")
   - **Answer**: The detailed answer (can be multiple paragraphs)
   - **Category**: Choose from:
     - `About` - Shows on About page
     - `Pricing` - Shows on Pricing page
     - `Contact` - Shows on Contact page
     - `General` - For general FAQs
   - **Order**: Display order (lower numbers appear first)
   - **Is Active**: Must be checked for the FAQ to appear

**Example FAQs:**

**For About Page:**
- Q: "How long has Clasyo been in business?"
- A: "Clasyo has been serving educational institutions since 2020..."

**For Pricing Page:**
- Q: "Can I upgrade or downgrade my plan anytime?"
- A: "Yes, you can change your subscription plan at any time..."

**For Contact Page:**
- Q: "What is your support hours?"
- A: "Our support team is available 24/7..."

---

### 3. Page Content

**Location:** `Frontend > Page Contents`

**How to Add/Edit:**
1. Click "Add Page Content" or select an existing page
2. Fill in the following fields:
   - **Page**: Select the page:
     - `about` - About Us page header content
     - `home_hero` - Home page hero section
     - `home_features` - Home page features
     - `contact` - Contact page information
   - **Title**: Main heading for the section
   - **Subtitle**: Subheading (optional)
   - **Content**: Main text content
   - **Extra Data**: JSON format for additional structured data
     For contact page example:
     ```json
     {
       "email": "support@yourschool.com",
       "phone": "+1 (555) 123-4567",
       "address": "123 Main St, City, Country"
     }
     ```
   - **Is Active**: Must be checked for content to appear

**Example for About Page:**
- **Page**: About Us
- **Title**: "About Clasyo"
- **Subtitle**: "Leading the Future of School Management"
- **Content**: "We are committed to providing..."

---

### 4. Contact Messages

**Location:** `Frontend > Contact Messages`

**Purpose:** View messages submitted through the contact form

**Features:**
- Mark as read/unread
- Mark as replied
- View all details: name, email, phone, subject, message
- Search by name, email, or subject
- Filter by read/replied status

**To Respond:**
1. Open the message
2. Copy the email address
3. Send response via your email client
4. Mark as "Replied" in the admin

---

## Quick Start Checklist

### Initial Setup:

1. **Create Pricing Plans:**
   - [ ] Add at least 3 pricing tiers
   - [ ] Mark one as "Popular"
   - [ ] Set proper order for display

2. **Add FAQs:**
   - [ ] Add 3-5 FAQs for About page
   - [ ] Add 3-5 FAQs for Pricing page
   - [ ] Add 2-3 FAQs for Contact page

3. **Configure Page Content:**
   - [ ] Set About page content
   - [ ] Set Contact information with email/phone/address

4. **Test the Pages:**
   - [ ] Visit `/about/` to see About page
   - [ ] Visit `/pricing/` to see Pricing plans
   - [ ] Visit `/contact/` to test contact form

---

## Tips

1. **Keep Features Short**: Use clear, benefit-focused bullet points for pricing features
2. **FAQ Best Practices**: 
   - Answer the most common questions first (use Order field)
   - Keep answers concise but helpful
   - Use categories to organize FAQs by page
3. **Regular Updates**: Update pricing plans seasonally or as your offering changes
4. **Monitor Contact Messages**: Check regularly for new inquiries

---

## Troubleshooting

**Q: Changes don't appear on the website**
- Ensure "Is Active" is checked
- Clear browser cache (Ctrl+F5)
- Check if you're viewing the correct page

**Q: FAQs not showing**
- Verify the Category matches the page
- Ensure "Is Active" is checked
- Check the Order field (start with 1, 2, 3...)

**Q: Contact form not working**
- Check browser console for errors
- Verify CSRF token is present
- Ensure all required fields are filled

---

## Need Help?

If you encounter any issues managing the content:
1. Check this guide first
2. Review the Django admin documentation
3. Contact your development team

---

**Last Updated:** November 2025
**Version:** 1.0

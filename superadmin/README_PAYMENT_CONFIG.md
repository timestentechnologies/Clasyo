# School Admin Payment Configuration System

## Overview
This system allows school administrators to configure payment gateways for their schools, enabling parents to make fee payments using various methods including M-Pesa, PayPal, bank transfers, cash, and cheques.

## Features

### Supported Payment Gateways
- **M-Pesa**: Business shortcode and paybill number configuration
- **PayPal**: Business email setup
- **Bank Transfer**: Account details configuration
- **Cash**: Payment instructions setup
- **Cheque**: Payment instructions setup

### Key Features
- ✅ School-specific payment configurations
- ✅ Sandbox/Live environment switching
- ✅ Active/Inactive status management
- ✅ Complete CRUD operations
- ✅ Modern responsive UI
- ✅ Real-time status updates
- ✅ Copy-to-clipboard functionality
- ✅ Setup guides for each gateway

## Installation & Setup

### 1. Run Migrations
```bash
python manage.py migrate superadmin
```

### 2. Create Sample Data (Optional)
```bash
python manage.py create_sample_payment_configs
```

### 3. Access the System
- **URL**: `/school/{school_slug}/payment-config/`
- **Sidebar**: Finance → Payment Configurations

## URL Structure

### School Admin Payment Configurations
- **List**: `/school/{school_slug}/payment-config/`
- **Create**: `/school/{school_slug}/payment-config/create/`
- **Detail**: `/school/{school_slug}/payment-config/{id}/`
- **Edit**: `/school/{school_slug}/payment-config/{id}/edit/`
- **Delete**: `/school/{school_slug}/payment-config/{id}/delete/`
- **Toggle Status**: `/school/{school_slug}/payment-config/{id}/edit/?toggle_status=true`

### Super Admin Payment Configurations
- **List**: `/superadmin/payment-config/`
- **Create**: `/superadmin/payment-config/create/`
- **Detail**: `/superadmin/payment-config/{id}/`
- **Edit**: `/superadmin/payment-config/{id}/edit/`
- **Delete**: `/superadmin/payment-config/{id}/delete/`

## Models

### SchoolPaymentConfiguration
School-specific payment gateway configurations.

**Fields:**
- `school`: ForeignKey to School
- `gateway`: Payment gateway type (mpesa, paypal, stripe, bank, cash, cheque)
- `environment`: sandbox or live
- `is_active`: Boolean status
- Gateway-specific fields (mpesa_shortcode, paypal_email, bank_name, etc.)
- `payment_instructions`: For cash/cheque payments

### PaymentConfiguration
Global payment gateway configurations (Super Admin only).

## Templates

### School Admin Templates
- `school_payment_config_list.html`: List all configurations
- `school_payment_config_form.html`: Create/Edit configuration
- `school_payment_config_detail.html`: View configuration details
- `school_payment_config_confirm_delete.html`: Delete confirmation

### Super Admin Templates
- `payment_config_list.html`: List global configurations
- `payment_config_form.html`: Create/Edit global configuration
- `payment_config_detail.html`: View global configuration details
- `payment_config_confirm_delete.html`: Delete confirmation

## Forms

### SchoolPaymentConfigurationForm
Form for creating/editing school payment configurations with validation.

### PaymentConfigurationForm
Form for creating/editing global payment configurations.

## Views

### School Admin Views
- `SchoolPaymentConfigurationListView`: List configurations
- `SchoolPaymentConfigurationCreateView`: Create new configuration
- `SchoolPaymentConfigurationUpdateView`: Update configuration (with toggle status)
- `SchoolPaymentConfigurationDetailView`: View configuration details
- `SchoolPaymentConfigurationDeleteView`: Delete configuration

### Super Admin Views
- `PaymentConfigurationListView`: List global configurations
- `PaymentConfigurationCreateView`: Create global configuration
- `PaymentConfigurationUpdateView`: Update global configuration
- `PaymentConfigurationDetailView`: View global configuration details
- `PaymentConfigurationDeleteView`: Delete global configuration

## Template Filters

### Payment Gateway Filters
- `payment_gateway_icon`: Returns Font Awesome icon for gateway
- `payment_gateway_color`: Returns Bootstrap color class for gateway

Usage:
```django
{% load payment_filters %}
<i class="fas {{ gateway|payment_gateway_icon }}"></i>
<span class="badge bg-{{ gateway|payment_gateway_color }}">
```

## Security & Permissions

### Access Control
- **School Admin**: Can only manage their own school's configurations
- **Super Admin**: Can manage global configurations and all school configurations
- **Authentication**: Required for all views
- **Authorization**: Role-based access control

### Data Isolation
- Each school has isolated configurations
- Schools cannot access other schools' configurations
- Unique constraint on (school, gateway) prevents duplicates

## API Integration

### M-Pesa Integration
```python
# Get active M-Pesa configuration for a school
config = SchoolPaymentConfiguration.objects.get(
    school=school, 
    gateway='mpesa', 
    is_active=True
)
mpesa_data = config.get_config_data()
# mpesa_data = {'shortcode': '174379', 'paybill_number': '123456'}
```

### PayPal Integration
```python
# Get PayPal configuration
config = SchoolPaymentConfiguration.objects.get(
    school=school, 
    gateway='paypal', 
    is_active=True
)
paypal_data = config.get_config_data()
# paypal_data = {'email': 'school@domain.com'}
```

## Testing

### Create Test Data
```bash
python manage.py create_sample_payment_configs
```

### Manual Testing
1. Login as a school admin
2. Navigate to Finance → Payment Configurations
3. Test creating, editing, and deleting configurations
4. Test toggle status functionality
5. Test copy-to-clipboard feature

## Troubleshooting

### Common Issues

#### 1. Template Not Found
Ensure all templates are in the correct directory:
```
templates/superadmin/school_payment_config_*.html
```

#### 2. Permission Denied
Check user role and school association:
```python
# User must be school admin
user.role == 'admin'

# School must exist
School.objects.filter(slug=school_slug).exists()
```

#### 3. JavaScript Errors
Ensure template filters are loaded:
```django
{% load payment_filters %}
```

#### 4. Migration Issues
Run migrations:
```bash
python manage.py migrate superadmin
```

## Future Enhancements

### Planned Features
- [ ] Webhook integration for payment status updates
- [ ] Transaction history per payment method
- [ ] Payment method analytics
- [ ] Bulk configuration updates
- [ ] API endpoints for mobile app integration
- [ ] Multi-currency support
- [ ] Payment method prioritization

### Integration Points
- **Fee Collection System**: Use configured payment methods
- **Parent Portal**: Display available payment options
- **Notification System**: Send payment confirmations
- **Reporting System**: Payment method usage analytics

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Verify all migrations have been run
3. Ensure proper user permissions
4. Check template syntax and JavaScript console errors

## License
This module is part of the SchoolSaaS system and follows the same license terms.

from django import template

register = template.Library()

@register.filter
def payment_gateway_icon(gateway):
    """Return the Font Awesome icon for a payment gateway"""
    icons = {
        'mpesa': 'fa-mobile-alt',
        'paypal': 'fab fa-paypal',
        'stripe': 'fab fa-stripe',
        'bank': 'fa-university',
        'cash': 'fa-money-bill-wave',
        'cheque': 'fa-money-check',
    }
    return icons.get(gateway, 'fa-credit-card')

@register.filter
def payment_gateway_color(gateway):
    """Return the Bootstrap color class for a payment gateway"""
    colors = {
        'mpesa': 'success',
        'paypal': 'info',
        'stripe': 'purple',
        'bank': 'primary',
        'cash': 'warning',
        'cheque': 'secondary',
    }
    return colors.get(gateway, 'secondary')

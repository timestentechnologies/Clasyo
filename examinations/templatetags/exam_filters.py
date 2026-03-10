from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key"""
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def percentage_of(value, total):
    """Calculate percentage of value out of total"""
    try:
        if total and float(total) > 0:
            return (float(value) / float(total)) * 100
        return 0
    except (ValueError, TypeError):
        return 0

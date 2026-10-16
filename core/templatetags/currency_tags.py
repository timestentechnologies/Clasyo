from decimal import Decimal
from django import template
from django.contrib.humanize.templatetags.humanize import intcomma

register = template.Library()


@register.simple_tag(takes_context=True)
def currency_symbol(context, default='$'):
    """Return the dynamic active school currency symbol from context"""
    sym = context.get('currency_symbol')
    if not sym:
        school = context.get('school')
        if school:
            sym = getattr(school, 'clean_currency_symbol', getattr(school, 'currency_symbol', default))
    return (sym or default).strip()


@register.simple_tag(takes_context=True)
def currency_code(context, default='USD'):
    """Return the dynamic active school currency code from context"""
    code = context.get('currency_code') or context.get('currency')
    if not code:
        school = context.get('school')
        if school:
            code = getattr(school, 'clean_currency', getattr(school, 'currency', default))
    return (code or default).strip().upper()


@register.simple_tag(takes_context=True)
def school_language(context, default='en'):
    """Return the active school language code"""
    lang = context.get('school_language') or context.get('language')
    if not lang:
        school = context.get('school')
        if school:
            lang = getattr(school, 'clean_language', getattr(school, 'language', default))
    return (lang or default).strip().lower()


@register.filter(name='currency')
@register.filter(name='money')
def money_format(value, custom_symbol=None):
    """
    Format a number as currency using the given or dynamic symbol.
    Usage: {{ fee.amount|money }} or {{ fee.amount|currency:currency_symbol }}
    """
    if value is None or value == '':
        return ''
    try:
        num = Decimal(str(value))
    except Exception:
        try:
            num = float(value)
        except Exception:
            return value

    if num % 1 == 0:
        formatted_num = intcomma(int(num))
    else:
        formatted_num = f"{num:,.2f}"

    sym = (custom_symbol or '').strip()
    if sym:
        return f"{sym} {formatted_num}"
    return formatted_num

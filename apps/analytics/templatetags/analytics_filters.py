from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the arg and the value."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            return int(value) * int(arg)
        except (ValueError, TypeError):
            return ''

@register.filter
def subtract(value, arg):
    """Subtract the arg from the value."""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        try:
            return int(value) - int(arg)
        except (ValueError, TypeError):
            return ''

@register.filter
def divide(value, arg):
    """Divide the value by the arg."""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return ''
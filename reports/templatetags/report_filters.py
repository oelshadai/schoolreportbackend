from django import template

register = template.Library()


@register.filter
def ordinal(value):
    """Convert an integer to its ordinal string: 1 -> '1st', 2 -> '2nd', etc."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return value
    if 11 <= (n % 100) <= 13:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

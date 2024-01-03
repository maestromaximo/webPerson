from django import template

register = template.Library()

@register.filter(name='percentage_of')
def percentage_of(value, total):
    try:
        return (float(value) / float(total)) * 100
    except (ValueError, ZeroDivisionError):
        return 0

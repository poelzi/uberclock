from django.template.defaultfilters import stringfilter
from django import template

register = template.Library()

@register.filter
def timelengh(value):
    return "%s:%0.2d" %(value[0], value[1])
"""Custom template tags for the Skyeman project."""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Look up a key in a dict inside a template.

    Usage: {{ mydict|get_item:key }}
    """
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    return None

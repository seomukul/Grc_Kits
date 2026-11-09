import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def gold(text):
    """Escape text, then render *words* in gold: 'Toolkits, *written by auditors*'."""
    html = re.sub(r"\*(.+?)\*", r'<span class="text-brand-300">\1</span>', escape(text or ""))
    return mark_safe(html)


@register.filter
def strip_stars(text):
    return (text or "").replace("*", "")

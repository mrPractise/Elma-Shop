

from django import template
from django.urls import reverse

register = template.Library()

@register.simple_tag
def category_url(category):
    url_names = {
        'beauty-products': 'beauty-products',
        'dresses': 'dresses',
        'jewelry': 'jewelry',
        'home-decor': 'home-decor'
    }
    url_name = url_names.get(category.slug, 'category_detail')
    return reverse(url_name, kwargs={'category_slug': category.slug})
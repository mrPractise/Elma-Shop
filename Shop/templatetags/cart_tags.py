from django import template
from Shop.models import Cart, CartItem

register = template.Library()

@register.filter
def cart_item_count(session):
    cart_id = session.get('cart_id')
    if cart_id:
        return CartItem.objects.filter(cart_id=cart_id).count()
    return 0
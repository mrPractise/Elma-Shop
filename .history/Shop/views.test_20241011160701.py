from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from .models import Category, Product, Cart, CartItem, ShippingLocation
from .views import get_or_create_cart, add_to_cart, remove_from_cart, update_cart

class ShopViewsTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.category = Category.objects.create(name='Test Category', slug='test-category')
        self.product = Product.objects.create(
            name='Test Product',
            price=Decimal('10.00'),
            category=self.category
        )
        self.shipping_location = ShippingLocation.objects.create(
            name='Test Location',
            shipping_cost=Decimal('5.00')
        )

if __name__ == '__main__':
    unittest.main()

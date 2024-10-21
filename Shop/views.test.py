from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.conf import settings
from unittest.mock import patch, MagicMock
from Shop.views import thank_you
from Shop.models import PurchaseOrder

class ThankYouViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.pending_order = {
            'order_number': 'ORD123',
            'name': 'John Doe',
            'address': '123 Test St',
            'subtotal': '100.00',
            'shipping_cost': '10.00',
            'total_amount': '110.00',
            'items': [
                {
                    'product_id': 1,
                    'product_name': 'Test Product',
                    'quantity': 2,
                    'price': '50.00',
                    'image_url': 'http://example.com/image.jpg'
                }
            ]
        }

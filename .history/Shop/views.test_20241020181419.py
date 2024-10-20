from decimal import Decimal
from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.db.models import Sum, F
from unittest.mock import patch, MagicMock

from .models import Cart, CartItem, Product, ShippingLocation, PurchaseOrder, PurchaseOrderItem
from .forms import ShippingForm
from .views import checkout, get_or_create_cart

class CheckoutViewTestCase(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.product = Product.objects.create(name="Test Product", price=Decimal('10.00'))
        self.shipping_location = ShippingLocation.objects.create(name="Test Location", shipping_cost=Decimal('5.00'))

    def _add_session_to_request(self, request):
        middleware = SessionMiddleware(lambda x: None)
        middleware.process_request(request)
        request.session.save()

class YourTestCase(TestCase):
    def test_apply_correct_shipping_cost(self):
        # Create a product and add it to the cart
        product = Product.objects.create(name="Test Product", price=Decimal('10.00'))
        cart = Cart.objects.create(session=self.client.session)
        CartItem.objects.create(cart=cart, product=product, quantity=1)

        # Create shipping locations
        location1 = ShippingLocation.objects.create(name="Location 1", shipping_cost=Decimal('5.00'))
        location2 = ShippingLocation.objects.create(name="Location 2", shipping_cost=Decimal('7.50'))

        # Prepare POST data
        post_data = {
            'name': 'Test User',
            'location': location1.id,
            'custom_address': False,
            'address': ''
        }

        # Make a POST request to the checkout view
        response = self.client.post(reverse('checkout'), data=post_data)

        # Check if the order was created with the correct shipping cost
        order = PurchaseOrder.objects.latest('id')
        self.assertEqual(order.total_amount, Decimal('15.00'))  # 10.00 (product) + 5.00 (shipping)

        # Change the location and make another request
        post_data['location'] = location2.id
        response = self.client.post(reverse('checkout'), data=post_data)

        # Check if the new order was created with the updated shipping cost
        new_order = PurchaseOrder.objects.latest('id')
        self.assertEqual(new_order.total_amount, Decimal('17.50'))  # 10.00 (product) + 7.50 (shipping)
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse,HttpResponseRedirect
from django.views.decorators.http import require_POST
from Shop.models import Cart, CartItem, Product, Category, Subcategory, HeroImage,PurchaseOrder, PurchaseOrderItem,ShippingLocation
from django.db.models import F, Sum
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .forms import ShippingForm
import urllib.parse
import uuid
from decimal import Decimal






CATEGORY_DRESSES = 'Dresses'
CATEGORY_BEAUTY = 'Beauty-Products'
CATEGORY_HOMEDECOR = 'Homedecor'
CATEGORY_JEWELRY = 'Jewelry'

def get_category_context(request, category_identifier):
    category = get_object_or_404(Category, name=category_identifier)
    subcategories = Subcategory.objects.filter(category=category).prefetch_related('products')
    products = Product.objects.filter(category=category).select_related('subcategory')
    
    featured_products = get_featured_products(category)  # Use caching for featured products

    cart = get_or_create_cart(request)
    cart_items = CartItem.objects.filter(cart=cart)
    cart_quantities = {item.product_id: item.quantity for item in cart_items}
    
    context = {
        'page': category.get_name_display().lower(),
        'category': category,
        'subcategories': subcategories,
        'products': products,
        'current_category_slug': category.slug,
        'cart_quantities': cart_quantities,
        'featured_products': featured_products
    }
    return context

def get_featured_products(category):
    key = f'featured_products_{category.id}'
    products = cache.get(key)
    if not products:
        products = category.get_featured_products()
        cache.set(key, products, timeout=60*15)  # Cache for 15 minutes
    return products





def home(request):
    featured_categories = Category.objects.filter(is_featured=True)
    hero_images = HeroImage.objects.select_related('category', 'product').all()
    
    context = {
        'featured_categories': featured_categories,
        'hero_images': hero_images,
    }
    return render(request, 'home.html', context)


def dress(request):
    context = get_category_context(request, CATEGORY_DRESSES)
    return render(request, 'dress.html', context)


def beauty(request):
    context = get_category_context(request, CATEGORY_BEAUTY)
    return render(request, 'beauty.html', context)

def homedecor(request):
    context = get_category_context(request, CATEGORY_HOMEDECOR)
    return render(request, 'homedecor.html', context)

def jewelry(request):    
    context = get_category_context(request, CATEGORY_JEWELRY)
    return render(request, 'jewelry.html', context)

def category_products(request, category_slug):
    category = get_object_or_404(Category, slug=category_slug)
    context = get_category_context(request, category.name)
    return render(request, f'{category_slug}.html', context)



def get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_id=request.session.session_key)
    return cart



def cartpage(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    subtotal = cart.get_total_price()
    
    context = {
        'page': 'cartpage',
        'cart_items': cart_items,
        'subtotal': subtotal,
        'cart': cart,
    }
    return render(request, 'cartpage.html', context)








def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    
    # Recalculate subtotal server-side
    subtotal = cart_items.aggregate(
        total=Sum(F('product__price') * F('quantity'))
    )['total'] or Decimal('0')

    initial_shipping_cost = Decimal('0')
    initial_total = subtotal

    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            location = form.cleaned_data['location']
            custom_address = form.cleaned_data['custom_address']
            address = form.cleaned_data['address'] if custom_address else location.name

            # Verify shipping cost
            if location and not custom_address:
                shipping_cost = location.shipping_cost
                # Ensure the location still exists and cost matches
                try:
                    verified_location = ShippingLocation.objects.get(id=location.id, shipping_cost=shipping_cost)
                except ShippingLocation.DoesNotExist:
                    form.add_error('location', 'Invalid shipping location selected.')
                    return render(request, 'checkout.html', {
                        'form': form,
                        'cart_items': cart_items,
                        'subtotal': subtotal,
                        'initial_shipping_cost': initial_shipping_cost,
                        'initial_total': initial_total,
                        'order_number': PurchaseOrder.generate_order_number()
                    })
            else:
                shipping_cost = Decimal('0')

            total = subtotal + shipping_cost

            # Verify cart integrity
            for item in cart_items:
                if item.total_price != item.product.price * item.quantity:
                    # Cart item total price doesn't match current product price * quantity
                    return render(request, 'checkout.html', {
                        'form': form,
                        'cart_items': cart_items,
                        'subtotal': subtotal,
                        'initial_shipping_cost': initial_shipping_cost,
                        'initial_total': initial_total,
                        'order_number': PurchaseOrder.generate_order_number(),
                        'error': 'Product prices have changed. Please review your cart.'
                    })

            # Create PurchaseOrder
            order = PurchaseOrder.objects.create(
                name=name,
                address=address,
                total_amount=total,
                status='PENDING'
            )

            # Create PurchaseOrderItems
            for item in cart_items:
                PurchaseOrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            order_details = f"New Order: {order.order_number}\n\nCustomer Details:\nName: {name}\nAddress: {address}\n\nOrder Summary:\n"
            
            for item in cart_items:
                order_details += f"\nItem: {item.product.name}\n"
                order_details += f"Quantity: {item.quantity}\n"
                order_details += f"Price: Ksh.{item.product.price}\n"
                order_details += f"Total: Ksh.{item.total_price}\n"
                order_details += f"Image: {request.build_absolute_uri(item.product.get_image_url())}\n"
            
            order_details += f"\nSubtotal: Ksh.{subtotal}"
            order_details += f"\nShipping Cost: Ksh.{shipping_cost}"
            order_details += f"\nTotal Order Amount: Ksh.{total}"
            
            # Replace with your actual WhatsApp number
            whatsapp_number = "+254735151721"
            whatsapp_url = f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(order_details)}"
            
            # Clear the cart
            cart.items.all().delete()
            
            return HttpResponseRedirect(whatsapp_url)
   else:
        form = ShippingForm()
        # Get the first shipping location (if any exist)
        default_location = ShippingLocation.objects.first()
        if default_location:
            form.fields['location'].initial = default_location.id
            initial_shipping_cost = default_location.shipping_cost
            initial_total = subtotal + initial_shipping_cost

    context = {
        'page': 'checkout',
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'initial_shipping_cost': initial_shipping_cost,
        'initial_total': initial_total,
        'cart': cart,
        'order_number': PurchaseOrder.generate_order_number()
    }
    return render(request, 'checkout.html', context)

@require_POST
def add_to_cart(request, product_id):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity = F('quantity') + 1
        cart_item.save()
    
    cart_item.refresh_from_db()
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity,
        'total_price': str(cart_item.total_price),
        'cart_total': str(cart.items.aggregate(total=Sum(F('product__price') * F('quantity')))['total'] or 0)
    })

@require_POST
def remove_from_cart(request, product_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    if cart_item.quantity > 1:
        cart_item.quantity = F('quantity') - 1
        cart_item.save()
        cart_item.refresh_from_db()
    else:
        cart_item.delete()
        cart_item = None
    
    cart_total = cart.items.aggregate(total=Sum(F('product__price') * F('quantity')))['total'] or 0
    
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity if cart_item else 0,
        'total_price': str(cart_item.total_price) if cart_item else '0',
        'cart_total': str(cart_total)
    })

@require_POST
def update_cart(request, product_id):
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    quantity = int(request.POST.get('quantity', 0))
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
        cart_item = None
    
    cart_total = cart.items.aggregate(total=Sum(F('product__price') * F('quantity')))['total'] or 0
    
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity if cart_item else 0,
        'total_price': str(cart_item.total_price) if cart_item else '0',
        'cart_total': str(cart_total)
    })

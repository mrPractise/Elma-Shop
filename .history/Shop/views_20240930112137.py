# Standard library imports
import os
import uuid
from decimal import Decimal
from io import BytesIO

# Third-party imports
import requests
from PIL import Image, ImageDraw, ImageFont

# Django imports
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import F, Sum, Q
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie

# Local imports
from .models import Cart, CartItem, Product, Category, Subcategory, HeroImage, PurchaseOrder,PurchaseOrderItem,ShippingLocation
from .forms import ShippingForm
from .utils import get_cart_quantities, generate_order_pdf

# Constants
CATEGORY_DRESSES = 'Dresses'
CATEGORY_BEAUTY = 'Beauty-Products'
CATEGORY_HOMEDECOR = 'Homedecor'
CATEGORY_JEWELRY = 'Jewelry'

def get_category_context(request, category_identifier):
    """
    Retrieve context data for a specific category.
    """
    category = get_object_or_404(Category, name=category_identifier)
    subcategories = Subcategory.objects.filter(category=category).prefetch_related('products')
    products = Product.objects.filter(category=category).select_related('subcategory')
    
    featured_products = get_featured_products(category)

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
    """
    Get featured products for a category, using cache to improve performance.
    """
    key = f'featured_products_{category.id}'
    products = cache.get(key)
    if not products:
        products = category.get_featured_products()
        cache.set(key, products, timeout=60*15)  # Cache for 15 minutes
    return products

def home(request):
    """
    Render the home page with featured categories and hero images.
    """
    featured_categories = Category.objects.filter(is_featured=True)
    hero_images = HeroImage.objects.select_related('category', 'product').all()
    
    context = {
        'featured_categories': featured_categories,
        'hero_images': hero_images,
    }
    # Check if in production (DEBUG = False) and use minified template if true
    if not settings.DEBUG:
        return render(request, 'home.min.html', context)
    else:
        return render(request, 'home.html', context)

def dress(request):
    """Render the dresses category page."""
    context = get_category_context(request, CATEGORY_DRESSES)
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'dress.min.html', context)
    else:
        return render(request, 'dress.html', context)

def beauty(request):
    """Render the beauty products category page."""
    context = get_category_context(request, CATEGORY_BEAUTY)
     # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'beauty.min.html', context)
    else:
        return render(request, 'beauty.html', context)

def homedecor(request):
    """Render the home decor category page."""
    context = get_category_context(request, CATEGORY_HOMEDECOR)
     # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'homedecor.min.html', context)
    else:
        return render(request, 'homedecor.html', context)

def jewelry(request):
    """Render the jewelry category page."""
    context = get_category_context(request, CATEGORY_JEWELRY)
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'jewelry.min.html', context)
    else:
        return render(request, 'jewelry.html', context)

def category_products(request, category_slug):
    """Render a category page based on the category slug."""
    category = get_object_or_404(Category, slug=category_slug)
    context = get_category_context(request, category.name)
     # Dynamically load the minified or normal template based on environment
    if not settings.DEBUG:
        return render(request, f'{category_slug}.min.html', context)
    else:
        return render(request, f'{category_slug}.html', context)

def get_or_create_cart(request):
    """
    Get the existing cart for the session or create a new one if it doesn't exist.
    """
    if not request.session.session_key:
        request.session.create()
    
    cart_id = request.session.get('cart_id')
    
    if cart_id:
        try:
            return Cart.objects.get(id=cart_id, is_active=True, session__session_key=request.session.session_key)
        except Cart.DoesNotExist:
            pass
    
    session = Session.objects.get(session_key=request.session.session_key)
    cart = Cart.objects.create(
        session=session,
        is_active=True,
        created_at=timezone.now()
    )
    request.session['cart_id'] = cart.id
    return cart

@ensure_csrf_cookie
def search_products(request):
    """
    Search for products based on name or short description.
    """
    query = request.GET.get('q', '')
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | 
            Q(short_description__icontains=query)
        ).order_by('name')
    else:
        products = Product.objects.none()
    
    paginator = Paginator(products, 12)  # Show 12 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    cart_quantities = get_cart_quantities(request)
    cart = get_or_create_cart(request)
    cart_total_items = cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
    context = {
        'query': query,
        'products': page_obj,
        'cart_quantities': cart_quantities,
        'cart_total_items': cart_total_items,
    }
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'search_results.min.html', context)
    else:
        return render(request, 'search_results.html', context)



@ensure_csrf_cookie
def cartpage(request):
    """
    Render the cart page with current and completed cart items.
    """
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    subtotal = cart.get_total_price()
    
    # Check for completed cart
    completed_cart_id = request.session.get('completed_cart_id')
    completed_cart_items = None
    if completed_cart_id:
        try:
            completed_cart = Cart.objects.get(id=completed_cart_id, is_active=False)
            completed_cart_items = completed_cart.items.all().select_related('product')
        except Cart.DoesNotExist:
            del request.session['completed_cart_id']
    
    cart_total_items = cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
    
    context = {
        'page': 'cartpage',
        'cart_items': cart_items,
        'completed_cart_items': completed_cart_items,
        'subtotal': subtotal,
        'cart': cart,
        'cart_total_items': cart_total_items,
    }
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'cartpage.min.html', context)
    else:
        return render(request, 'cartpage.html', context)



def checkout(request):
    cart = get_or_create_cart(request)
    cart_items = cart.items.all().select_related('product')
    
    subtotal = cart_items.aggregate(
        total=Sum(F('product__price') * F('quantity'))
    )['total'] or Decimal('0')

    initial_shipping_cost = Decimal('0')
    initial_total = subtotal

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'cancel':
            clear_cart(request)
            return redirect('home')
        
        form = ShippingForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            location = form.cleaned_data['location']
            custom_address = form.cleaned_data['custom_address']
            address = form.cleaned_data['address'] if custom_address else location.name

            shipping_cost = location.shipping_cost if location and not custom_address else Decimal('0')
            total = subtotal + shipping_cost

            with transaction.atomic():
                # Create a PurchaseOrder instance
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

                # Store order details in session
                request.session['pending_order'] = {
                    'order_number': order.order_number,
                    'name': name,
                    'address': address,
                    'total_amount': str(total),
                    'items': [{
                        'product_id': item.product.id,
                        'product_name': item.product.name,
                        'quantity': item.quantity,
                        'price': str(item.product.price),
                        'image_url': request.build_absolute_uri(item.product.get_image_url())
                    } for item in cart_items],
                    'subtotal': str(subtotal),
                    'shipping_cost': str(shipping_cost)
                }

                # Clear the cart
                cart.items.all().delete()
                cart.is_active = False
                cart.save()

            return redirect('thank_you')
    else:
        form = ShippingForm()
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
    }
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'checkout.min.html', context)
    else:
        return render(request, 'checkout.html', context)

def thank_you(request):
    """
    Render the thank you page after a successful order placement.
    """
    pending_order = request.session.get('pending_order')
    if not pending_order:
        return redirect('checkout')

    def format_price(price):
        return intcomma(f"{Decimal(price):.2f}")

    order_details = f"New Order: {pending_order['order_number']}\n"
    order_details += f"Customer Details:\nName: {pending_order['name']}\nAddress: {pending_order['address']}\n"
    order_details += f"Subtotal: Ksh.{format_price(pending_order['subtotal'])}\n"
    order_details += f"Shipping Cost: Ksh.{format_price(pending_order['shipping_cost'])}\n"
    order_details += f"Total Order Amount: Ksh.{format_price(pending_order['total_amount'])}"

    # Humanize prices in items
    for item in pending_order['items']:
        item['price'] = format_price(item['price'])
        item['total'] = format_price(Decimal(item['price'].replace(',', '')) * int(item['quantity']))

    # Generate the order PDF
    pdf_filename = generate_order_pdf(order_details, pending_order['items'])
    
    # Get the full URL for the PDF
    pdf_url = request.build_absolute_uri(settings.MEDIA_URL + 'order_pdfs/' + pdf_filename)

    # Prepare the WhatsApp message with the PDF link
    whatsapp_message = f"New order placed.\nView order details: \n{pdf_url}"


    context = {
        'order': pending_order,
        'whatsapp_message': whatsapp_message,
        'whatsapp_number': settings.WHATSAPP_NUMBER
    }
    # Use minified template in production
    if not settings.DEBUG:
        return render(request, 'thankyou.min.html', context)
    else:
        return render(request, 'thankyou.html', context)

def clear_cart(request):
    """Clear all items from the cart."""
    cart = get_or_create_cart(request)
    cart.items.all().delete()
    if 'pending_order' in request.session:
        del request.session['pending_order']

def cancel_order(request):
    """Cancel the current order and redirect to home."""
    clear_cart(request)
    return redirect('home')

@require_POST
def add_to_cart(request, product_id):
    """Add a product to the cart or increase its quantity if already present."""
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity = F('quantity') + 1
        cart_item.save()
    
    cart_item.refresh_from_db()
    
    cart_total = cart.get_total_price()
    cart_total_items = cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
    
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity,
        'total_price': str(cart_item.total_price),
        'cart_total': str(cart_total),
        'cart_total_items': cart_total_items
    })

@require_POST
def remove_from_cart(request, product_id):
    """Remove a product from the cart or decrease its quantity."""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    
    if cart_item.quantity > 1:
        cart_item.quantity = F('quantity') - 1
        cart_item.save()
        cart_item.refresh_from_db()
    else:
        cart_item.delete()
        cart_item = None
    
    cart_total = cart.get_total_price()
    cart_total_items = cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
    
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity if cart_item else 0,
        'total_price': str(cart_item.total_price) if cart_item else '0',
        'cart_total': str(cart_total),
        'cart_total_items': cart_total_items
    })

@require_POST
def update_cart(request, product_id):
    """Update the quantity of a product in the cart."""
    cart = get_or_create_cart(request)
    cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
    quantity = int(request.POST.get('quantity', 0))
    
    if quantity > 0:
        cart_item.quantity = quantity
        cart_item.save()
    else:
        cart_item.delete()
        cart_item = None
    
    cart_total = cart.get_total_price()
    cart_total_items = cart.items.aggregate(total_items=Sum('quantity'))['total_items'] or 0
    
    return JsonResponse({
        'success': True,
        'quantity': cart_item.quantity if cart_item else 0,
        'total_price': str(cart_item.total_price) if cart_item else '0',
        'cart_total': str(cart_total),
        'cart_total_items': cart_total_items
    })
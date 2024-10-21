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
from django.core.files.storage import default_storage
from django.core.cache import cache
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db import transaction
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseServerError
from django.core.exceptions import ObjectDoesNotExist
import logging
from django.urls import reverse


# Local imports
from .models import Cart, CartItem, Product, Category, Subcategory, HeroImage, PurchaseOrder,PurchaseOrderItem,ShippingLocation
from .forms import ShippingForm
from .utils import get_cart_quantities, generate_order_pdf


logger = logging.getLogger(__name__)

# Constants
CATEGORY_DRESSES = 'Dresses'
CATEGORY_BEAUTY = 'Beauty-Products'
CATEGORY_HOMEDECOR = 'Homedecor'
CATEGORY_JEWELRY = 'Jewelry'

def get_category_context(request, category_identifier):
    try:
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
    except ObjectDoesNotExist:
        return None

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
    try:
        featured_categories = Category.objects.filter(is_featured=True)
        hero_images = HeroImage.objects.select_related('category', 'product').all()
        
        context = {
            'featured_categories': featured_categories,
            'hero_images': hero_images,
        }
        return render(request, 'home.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)}, status=500)

def dress(request):
    """Render the dresses category page."""
    context = get_category_context(request, CATEGORY_DRESSES)
    return render(request, 'dress.html', context)

def beauty(request):
    """Render the beauty products category page."""
    context = get_category_context(request, CATEGORY_BEAUTY)
    return render(request, 'beauty.html', context)

def homedecor(request):
    """Render the home decor category page."""
    context = get_category_context(request, CATEGORY_HOMEDECOR)
    return render(request, 'homedecor.html', context)

def jewelry(request):
    """Render the jewelry category page."""
    context = get_category_context(request, CATEGORY_JEWELRY)
    return render(request, 'jewelry.html', context)

def category_products(request, category_slug):
    try:
        category = get_object_or_404(Category, slug=category_slug)
        context = get_category_context(request, category.name)
        if context is None:
            return render(request, 'error.html', {'error_message': 'Category not found'}, status=404)
        return render(request, f'{category_slug}.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)}, status=500)

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
    try:
        query = request.GET.get('q', '')
        if query:
            products = Product.objects.filter(
                Q(name__icontains=query) | 
                Q(short_description__icontains=query)
            ).order_by('name')
        else:
            products = Product.objects.none()
        
        paginator = Paginator(products, 12)
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
        return render(request, 'search_results.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)}, status=500)



@ensure_csrf_cookie
def cartpage(request):
    try:
        cart = get_or_create_cart(request)
        cart_items = cart.items.all().select_related('product')
        subtotal = cart.get_total_price()
        
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
        return render(request, 'cartpage.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)}, status=500)


def checkout(request):
    try:
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
        return render(request, 'checkout.html', context)
    except Exception as e:
        return render(request, 'error.html', {'error_message': str(e)}, status=500)





def thank_you(request):
    try:
        pending_order = request.session.get('pending_order')
        if not pending_order:
            logger.warning("Attempted to access thank you page without pending order")
            return redirect('checkout')

        order_number = pending_order['order_number']
        logger.info(f"Processing thank you page for order: {order_number}")

        # Ensure all necessary fields are present and correctly formatted
        order_details = (
            f"New Order: {order_number}\n"
            f"Customer Details:\nName: {pending_order.get('name', 'N/A')}\n"
            f"Address: {pending_order.get('address', 'N/A')}\n"
            f"Subtotal: Ksh.{pending_order.get('subtotal', '0')}\n"
            f"Shipping Cost: Ksh.{pending_order.get('shipping_cost', '0')}\n"
            f"Total Order Amount: Ksh.{pending_order.get('total_amount', '0')}"
        )

        # Ensure items are properly formatted
        for item in pending_order.get('items', []):
            item['price'] = str(Decimal(item.get('price', '0')))
            item['quantity'] = int(item.get('quantity', 1))

        try:
            pdf_filename = generate_order_pdf(order_details, pending_order.get('items', []), order_number)
            logger.info(f"PDF generated: {pdf_filename}")
            
            pdf_directory = 'order_pdfs'
            os.makedirs(pdf_directory, exist_ok=True)

            pdf_path = f'{pdf_directory}/{pdf_filename}'
            with open(pdf_filename, 'rb') as pdf_file:
                default_storage.save(pdf_path, pdf_file)
            
            pdf_url = request.build_absolute_uri(default_storage.url(pdf_path))
            logger.info(f"PDF URL generated: {pdf_url}")
            
            try:
                os.remove(pdf_filename)
                logger.debug(f"Local PDF file deleted: {pdf_filename}")
            except OSError as e:
                logger.warning(f"Could not delete local PDF file {pdf_filename}: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating PDF for order {order_number}: {str(e)}", exc_info=True)
            pdf_url = request.build_absolute_uri(reverse('error_order', kwargs={'order_number': order_number}))

        whatsapp_message = f"New order placed: {order_number}. \nView order details: \n{pdf_url}"

        context = {
            'order': pending_order,
            'whatsapp_message': whatsapp_message,
            'whatsapp_number': settings.WHATSAPP_NUMBER,
            'pdf_url': pdf_url,
        }
       
        del request.session['pending_order']
        request.session.modified = True
        logger.info(f"Order {order_number} processed successfully")

        return render(request, 'thankyou.html', context)
    except Exception as e:
        logger.error(f"Error in thank you view: {str(e)}", exc_info=True)
        return render(request, 'error.html', {'error_message': "An error occurred processing your order. Please contact support."}, status=500)






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
    try:
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
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
  

@require_POST
def remove_from_cart(request, product_id):
    """Remove a product from the cart or decrease its quantity."""
    
    try:
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
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@require_POST
def update_cart(request, product_id):
    """Update the quantity of a product in the cart."""
    
    try:
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
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    
    
def custom_404(request, exception):
    return render(request, '404.html', status=404)

def custom_500(request):
    return render(request, '500.html', status=500)



def error_order(request, order_number):
    return render(request, 'error_order.html', {'order_number': order_number})

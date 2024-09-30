from django.shortcuts import render, get_object_or_404,redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from Shop.models import Cart, CartItem, Product, Category, Subcategory, HeroImage,PurchaseOrder,ShippingLocation
from django.db.models import F, Sum
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from .forms import ShippingForm
import urllib.parse
from django.contrib import messages
from decimal import Decimal
from django.utils import timezone
from django.contrib.sessions.models import Session 
from datetime import timedelta  
from django.db.models import Q
from django.core.paginator import Paginator
from .utils import get_cart_quantities 







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
    
    cart_id = request.session.get('cart_id')
    
    if cart_id:
        try:
            cart = Cart.objects.get(id=cart_id, is_active=True, session__session_key=request.session.session_key)
            return cart
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


def search_products(request):
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
    
    context = {
        'query': query,
        'products': page_obj,
        'cart_quantities': cart_quantities,
    }
    return render(request, 'search_results.html', context)



def cartpage(request):
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
    
    context = {
        'page': 'cartpage',
        'cart_items': cart_items,
        'completed_cart_items': completed_cart_items,
        'subtotal': subtotal,
        'cart': cart,
    }
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
        form = ShippingForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            location = form.cleaned_data['location']
            custom_address = form.cleaned_data['custom_address']
            address = form.cleaned_data['address'] if custom_address else location.name

            if location and not custom_address:
                shipping_cost = location.shipping_cost
            else:
                shipping_cost = Decimal('0')

            total = subtotal + shipping_cost

            # Store order details in session instead of creating PurchaseOrder
            request.session['pending_order'] = {
                'order_number': PurchaseOrder.generate_order_number(),
                'name': name,
                'address': address,
                'total_amount': str(total),
                'items': [{
                    'product_id': item.product.id,
                    'product_name': item.product.name,  # Add this line
                    'quantity': item.quantity,
                    'price': str(item.product.price),
                    'image_url': request.build_absolute_uri(item.product.get_image_url())
                } for item in cart_items],
                'subtotal': str(subtotal),
                'shipping_cost': str(shipping_cost)
            }

            # Redirect to thank you page
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
        'order_number': PurchaseOrder.generate_order_number()
    }
    return render(request, 'checkout.html', context)


def thank_you(request):
    pending_order = request.session.get('pending_order')
    if not pending_order:
        return redirect('checkout')

    order_details = f"New Order: {pending_order['order_number']}\n\n"
    order_details += f"Customer Details:\nName: {pending_order['name']}\nAddress: {pending_order['address']}\n\n"
    order_details += "Order Summary:\n"

    for item in pending_order['items']:
        order_details += f"\nItem: {item['product_name']}\n"
        order_details += f"Quantity: {item['quantity']}\n"
        order_details += f"Price: Ksh.{item['price']}\n"
        order_details += f"Total: Ksh.{Decimal(item['price']) * item['quantity']}\n"

    order_details += f"\nSubtotal: Ksh.{pending_order['subtotal']}"
    order_details += f"\nShipping Cost: Ksh.{pending_order['shipping_cost']}"
    order_details += f"\nTotal Order Amount: Ksh.{pending_order['total_amount']}"

    context = {
        'order': pending_order,
        'order_details': order_details
    }
    return render(request, 'thank_you.html', context)

def cancel_order(request):
    if 'pending_order' in request.session:
        del request.session['pending_order']
    
    # Clear the cart
    cart = get_or_create_cart(request)
    cart.items.all().delete()

    messages.success(request, "Your order has been cancelled successfully.")
    return redirect('home')

# def generate_whatsapp_url(order):
#     order_details = f"New Order: {order['order_number']}\n\n"
#     order_details += f"Customer Details:\nName: {order['name']}\nAddress: {order['address']}\n\n"
#     order_details += "Order Summary:\n"

#     for item in order['items']:
#         order_details += f"\nItem: {item['product_name']}\n"
#         order_details += f"Quantity: {item['quantity']}\n"
#         order_details += f"Price: Ksh.{item['price']}\n"
#         order_details += f"Total: Ksh.{Decimal(item['price']) * item['quantity']}\n"
#         order_details += f"Image: {item['image_url']}\n"

#     order_details += f"\nSubtotal: Ksh.{order['subtotal']}"
#     order_details += f"\nShipping Cost: Ksh.{order['shipping_cost']}"
#     order_details += f"\nTotal Order Amount: Ksh.{order['total_amount']}"

#     whatsapp_number = "+254735151721"
#     return f"https://wa.me/{whatsapp_number}?text={urllib.parse.quote(order_details)}"

@require_POST
def add_to_cart(request, product_id):
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


# Add this function to clear old completed carts
def clear_old_completed_carts():
    threshold = timezone.now() - timedelta(hours=24)  # Adjust time as needed
    Cart.objects.filter(is_active=False, completed_at__lt=threshold).delete()
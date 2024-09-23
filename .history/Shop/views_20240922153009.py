from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from Shop.models import Cart, CartItem, Product, Category, Subcategory, HeroImage
from django.db.models import F, Sum
from django.views.decorators.cache import cache_page
from django.core.cache import cache

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




@cache_page(60 * 15)  # Cache for 15 minutes
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

def product_list(request):
    products = Product.objects.all()
    categories = Category.objects.all()
    context = {
        'products': products,
        'categories': categories
    }
    return render(request, 'product_list.html', context)

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

def get_or_create_cart(request):
    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(session_id=request.session.session_key)
    return cart

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

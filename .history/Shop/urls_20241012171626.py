from django.urls import path
from Shop import views
from django.contrib.sitemaps.views import sitemap
from Shop.sitemaps import StaticViewSitemap, CategorySitemap, ProductSitemap

sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}

urlpatterns = [
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('', views.home, name='home'),
    path('beauty/', views.beauty, name='Beauty-Products'),
    path('dress/', views.dress, name='Dresses'),
    path('jewelry/', views.jewelry, name='Jewelry'),
    path('homedecor/', views.homedecor, name='Homedecor'),
    path('checkout/', views.checkout, name='checkout'),
    path('products/<slug:category_slug>/', views.category_products, name='category_products'),
    path('cart/', views.cartpage, name='cartpage'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('search/', views.search_products, name='search_products'),
    path('thank-you/', views.thank_you, name='thank_you'),
    path('cancel-order/', views.cancel_order, name='cancel_order'),
]

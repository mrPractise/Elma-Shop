from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Category, Product

class StaticViewSitemap(Sitemap):
    priority = 0.5
    changefreq = 'daily'

    def items(self):
        # Return list of url names for static pages
        return ['home', 'Beauty-Products', 'Dresses', 'Jewelry', 'Homedecor']

    def location(self, item):
        # Reverse the URL names to their corresponding URL paths
        return reverse(item)

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # Return all category objects
        return Category.objects.all()

    def location(self, obj):
        # Generate the URL for each category
        return reverse('category_products', args=[obj.slug])

class ProductSitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        # Return all product objects
        return Product.objects.all()

    def location(self, obj):
        # Generate the URL for each product
        # Note: This assumes products are displayed on their category page with an anchor
        return reverse('category_products', args=[obj.category.slug]) + f'#{obj.id}'

# Dictionary of sitemap classes to be used in urls.py
sitemaps = {
    'static': StaticViewSitemap,
    'categories': CategorySitemap,
    'products': ProductSitemap,
}
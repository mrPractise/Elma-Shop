from django.db import models
from django.contrib.sessions.models import Session
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.conf import settings
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.db.models import F, Sum
from django.utils import timezone
from django.utils.html import mark_safe
from decimal import Decimal

class Category(models.Model):
    CATEGORY_CHOICES = [
        ('Homedecor', 'Homedecor'),
        ('Beauty-Products', 'Beauty-Products'),
        ('Jewelry', 'Jewelry'),
        ('Dresses', 'Dresses'),
    ]

    name = models.CharField(max_length=100, choices=CATEGORY_CHOICES, unique=True)
    slug = models.SlugField(unique=True, editable=False)
    description = models.TextField(blank=True, null=True)
    featured_image = models.ImageField(upload_to='category_featured_images/', blank=True, null=True)
    is_featured = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.get_name_display()

    def get_featured_products(self, count=4):
        return self.featured_products.select_related('product')[:count]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_subcategories(self):
        return self.subcategories.all()

class Subcategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, editable=False)

    class Meta:
        verbose_name_plural = "Subcategories"
        unique_together = ('category', 'name')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.category.name}-{self.name}")
        super().save(*args, **kwargs)

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='product_images/', null=True, blank=True)
    category = models.ForeignKey(Category, related_name='products', on_delete=models.PROTECT)
    subcategory = models.ForeignKey(Subcategory, related_name='products', on_delete=models.SET_NULL, null=True, blank=True)
    short_description = models.CharField(max_length=100, blank=True, help_text="A brief description of the product (max 200 characters)")
    is_hero_image = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def get_image_url(self):
        if self.image and hasattr(self.image, 'url'):
            return self.image.url
        return f"{settings.STATIC_URL}images/default-product-image.jpg"

    def clean(self):
        if self.is_hero_image:
            existing_hero = Product.objects.filter(category=self.category, is_hero_image=True).exclude(pk=self.pk)
            if existing_hero.exists():
                raise ValidationError('There can only be one hero image per category.')

        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError("The subcategory must belong to the selected category.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

        if self.is_featured:
            FeaturedProduct.objects.get_or_create(category=self.category, product=self)
        else:
            FeaturedProduct.objects.filter(category=self.category, product=self).delete()

        if self.subcategory:
            OrderedProduct.objects.get_or_create(subcategory=self.subcategory, product=self)
        else:
            OrderedProduct.objects.filter(product=self).delete()

    def delete(self, *args, **kwargs):
        HeroImage.objects.filter(product=self).delete()
        super().delete(*args, **kwargs)

@receiver(pre_delete, sender=Product)
def remove_product_references(sender, instance, **kwargs):
    FeaturedProduct.objects.filter(product=instance).delete()
    HeroImage.objects.filter(product=instance).delete()
    OrderedProduct.objects.filter(product=instance).delete()

class OrderedProduct(models.Model):
    subcategory = models.ForeignKey(Subcategory, on_delete=models.CASCADE, related_name='ordered_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('subcategory', 'product')

    def __str__(self):
        return f"{self.subcategory.name} - {self.product.name} (Order: {self.order})"

class FeaturedProduct(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='featured_products')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)
    order = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ['order']
        unique_together = ('category', 'product')

    def __str__(self):
        return f"{self.category.name} - {self.product.name if self.product else 'No Product'}"

class HeroImage(models.Model):
    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name='hero_image')
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='hero_for')

    def __str__(self):
        return f"Hero Image for {self.category.name}"

    def clean(self):
        if self.product.category != self.category:
            raise ValidationError("The product must belong to the same category as the hero image.")
        if not self.product.is_hero_image:
            raise ValidationError("The selected product is not marked as a hero image.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        product = self.product
        super().delete(*args, **kwargs)
        product.is_hero_image = False
        product.save()

class Cart(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def get_total_price(self):
        return self.items.aggregate(
            total=Sum(F('product__price') * F('quantity'))
        )['total'] or Decimal('0')

    @classmethod
    def remove_expired_carts(cls):
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        cls.objects.filter(session__in=expired_sessions).delete()

    def __str__(self):
        return f"Cart {self.id} - {'Active' if self.is_active else 'Inactive'}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Cart {self.cart.id}"

class OrderSequence(models.Model):
    date = models.DateField(unique=True)
    last_sequence = models.PositiveIntegerField(default=0)

    @classmethod
    def get_next_sequence(cls, date):
        sequence, created = cls.objects.get_or_create(date=date)
        sequence.last_sequence += 1
        sequence.save()
        return sequence.last_sequence

class PurchaseOrder(models.Model):
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SUCCESSFUL', 'Successful'),
        ('UNSUCCESSFUL', 'Unsuccessful'),
    ]

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    name = models.CharField(max_length=100)
    address = models.TextField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='PENDING')

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    @classmethod
    def generate_order_number(cls):
        now = timezone.now()
        day_abbr = now.strftime("%a")
        date_string = now.strftime("%d/%m/%Y")

        new_sequence = OrderSequence.get_next_sequence(now.date())
        sequence_str = f"{new_sequence:05d}"

        order_number = f"{day_abbr}-{sequence_str}-{date_string}"

        while cls.objects.filter(order_number=order_number).exists():
            new_sequence = OrderSequence.get_next_sequence(now.date())
            sequence_str = f"{new_sequence:05d}"
            order_number = f"{day_abbr}-{sequence_str}-{date_string}"

        return order_number

    def __str__(self):
        return f"Order {self.order_number}"

class PurchaseOrderItem(models.Model):
    order = models.ForeignKey(PurchaseOrder, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order {self.order.order_number}"
   
class ShippingLocation(models.Model):
    name = models.CharField(max_length=100)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"
        
    def save(self, *args, **kwargs):
        if self.is_default:
            # If this is being set as default, unset any existing default
            ShippingLocation.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)
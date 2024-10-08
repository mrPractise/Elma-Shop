from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Cart,Product, Category, FeaturedProduct, HeroImage, Subcategory, OrderedProduct,PurchaseOrder, PurchaseOrderItem,ShippingLocation
from django.utils import timezone
from datetime import timedelta
from django.contrib.humanize.templatetags.humanize import intcomma

@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug']
    list_filter = ['category']
    search_fields = ['name', 'category__name']
    readonly_fields = ['slug']

class SubcategoryInline(admin.TabularInline):
    model = Subcategory
    extra = 1

class OrderedProductInline(admin.TabularInline):
    model = OrderedProduct
    extra = 1
    ordering = ['order']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'subcategory', 'price', 'is_featured', 'is_hero_image', 'display_image']
    list_filter = ['category', 'subcategory', 'is_featured', 'is_hero_image']
    search_fields = ['name', 'short_description', 'category__name', 'subcategory__name']
    list_editable = ['is_featured', 'is_hero_image', 'subcategory']
    actions = ['make_hero', 'remove_hero']

    def display_image(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.image.url)
        return "No Image"
    display_image.short_description = 'Image'

    def save_model(self, request, obj, form, change):
        is_new = not obj.pk
        original_hero_status = None if is_new else Product.objects.get(pk=obj.pk).is_hero_image
        original_subcategory = None if is_new else Product.objects.get(pk=obj.pk).subcategory

        # Save the product first
        super().save_model(request, obj, form, change)

        try:
            if obj.is_hero_image and (is_new or not original_hero_status):
                # If this product is being set as hero, unset any existing hero for this category
                Product.objects.filter(category=obj.category, is_hero_image=True).exclude(pk=obj.pk).update(is_hero_image=False)
                
                # Update or create HeroImage
                HeroImage.objects.update_or_create(
                    category=obj.category,
                    defaults={'product': obj}
                )
            elif not obj.is_hero_image and not is_new and original_hero_status:
                # If this product is being unset as hero, remove it from HeroImage if it exists
                HeroImage.objects.filter(category=obj.category, product=obj).delete()

            # Handle OrderedProduct creation/update
            if obj.subcategory:
                if obj.subcategory != original_subcategory:
                    # Remove from old subcategory if changed
                    OrderedProduct.objects.filter(product=obj, subcategory=original_subcategory).delete()
                OrderedProduct.objects.get_or_create(subcategory=obj.subcategory, product=obj)
            else:
                OrderedProduct.objects.filter(product=obj).delete()

        except ValidationError as e:
            messages.error(request, str(e))
            # If there's an error, revert the hero status and subcategory
            obj.is_hero_image = original_hero_status
            obj.subcategory = original_subcategory
            obj.save()

    def make_hero(self, request, queryset):
        for product in queryset:
            product.is_hero_image = True
            self.save_model(request, product, None, change=True)
        self.message_user(request, f"Selected products have been set as hero images.")
    make_hero.short_description = "Set selected products as hero images"

    def remove_hero(self, request, queryset):
        queryset.update(is_hero_image=False)
        HeroImage.objects.filter(product__in=queryset).delete()
        self.message_user(request, f"Hero status removed from selected products.")
    remove_hero.short_description = "Remove hero status from selected products"
    
    
    
    def delete_queryset(self, request, queryset):
        # Custom delete_queryset to ensure proper cleanup
        for obj in queryset:
            obj.delete()

    def delete_model(self, request, obj):
        # Custom delete_model to ensure proper cleanup
        obj.delete()

class HeroImageInline(admin.StackedInline):
    model = HeroImage
    can_delete = False
    verbose_name_plural = 'Hero Image'

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['get_name_display', 'slug', 'description', 'is_featured', 'display_hero_image']
    readonly_fields = ['slug']
    fields = ['name', 'description', 'is_featured']
    inlines = [SubcategoryInline, HeroImageInline]

    def get_name_display(self, obj):
        return obj.get_name_display()
    get_name_display.short_description = 'Name'

    def display_hero_image(self, obj):
        if hasattr(obj, 'hero_image') and obj.hero_image and obj.hero_image.product:
            return format_html('<img src="{}" width="50" height="50" />', obj.hero_image.product.get_image_url())
        return "No Hero Image"
    display_hero_image.short_description = 'Hero Image'

    def has_add_permission(self, request):
        return False  # Prevent adding new categories

    def has_delete_permission(self, request, obj=None):
        return False  # Prevent deleting categories

@admin.register(FeaturedProduct)
class FeaturedProductAdmin(admin.ModelAdmin):
    list_display = ('category', 'product', 'order', 'display_image')
    list_filter = ('category',)
    ordering = ('category', 'order')

    def display_image(self, obj):
        if obj.product and obj.product.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.product.image.url)
        return "No Image"
    display_image.short_description = 'Image'

    def has_add_permission(self, request):
        return False  # Prevent manually adding featured products

    def has_delete_permission(self, request, obj=None):
        return True  # Allow deleting featured products

@admin.register(OrderedProduct)
class OrderedProductAdmin(admin.ModelAdmin):
    list_display = ['product', 'subcategory', 'order']
    list_filter = ['subcategory__category', 'subcategory']
    ordering = ['subcategory', 'order']
    search_fields = ['product__name', 'subcategory__name']



class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'quantity', 'price', 'total_price', 'image_preview')
    fields = ('product', 'product_name', 'quantity', 'price', 'total_price', 'image_preview')
    can_delete = False
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def product_name(self, obj):
        return obj.product.name
    product_name.short_description = 'Product Name'

    def total_price(self, obj):
        return intcomma(obj.quantity * obj.price)  # Using intcomma for formatting
    total_price.short_description = 'Total Price'

    def image_preview(self, obj):
        if obj.product.image:
            return format_html('<img src="{}" width="50" height="50" />', obj.product.image.url)
        return "No Image"
    image_preview.short_description = 'Image'

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'name', 'formatted_total_amount', 'created_at', 'status', 'item_count')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'name')
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ('order_number', 'name', 'address', 'formatted_total_amount', 'created_at', 'item_count', 'items_display')
    
    fieldsets = (
        (None, {
            'fields': ('order_number', 'name', 'address', 'formatted_total_amount', 'created_at', 'status', 'item_count', 'items_display')
        }),
    )

    def item_count(self, obj):
        return obj.items.count()
    item_count.short_description = 'Number of Items'

    def items_display(self, obj):
        items = obj.items.all()
        return "\n".join([f"{item.quantity} x {item.product.name} - Ksh.{intcomma(item.price)}" for item in items])
    items_display.short_description = 'Order Items'

    def formatted_total_amount(self, obj):
        return f"Ksh.{intcomma(obj.total_amount)}"
    formatted_total_amount.short_description = 'Total Amount'







@admin.register(ShippingLocation)
class ShippingLocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'shipping_cost')
    search_fields = ('name',)



# Unregister the Group model if you don't need it
from django.contrib.auth.models import Group
admin.site.unregister(Group)
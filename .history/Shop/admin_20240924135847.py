from django.contrib import admin
from django.utils.html import format_html
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import Product, Category, FeaturedProduct, HeroImage, Subcategory, OrderedProduct,PurchaseOrder, PurchaseOrderItem


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
    readonly_fields = ('product', 'quantity', 'price', 'image_tag')
    fields = ('product', 'quantity', 'price', 'image_tag')
    can_delete = True
    max_num = 0

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'name', 'total_amount', 'created_at', 'status')
    list_filter = ('status', 'created_at')
    search_fields = ('order_number', 'name')
    inlines = [PurchaseOrderItemInline]
    readonly_fields = ('order_number', 'name', 'address', 'total_amount', 'created_at')
    
    fieldsets = (
        (None, {
            'fields': ('order_number', 'name', 'address', 'total_amount', 'created_at', 'status')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    def has_change_permission(self, request, obj=None):
        # Allow changing only the status field
        return True

    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('order_number', 'name', 'address', 'total_amount', 'created_at')
        return self.readonly_fields


# Unregister the Group model if you don't need it
from django.contrib.auth.models import Group
admin.site.unregister(Group)
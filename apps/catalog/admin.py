from django.contrib import admin
from .models import (
    ProductCategory, Product,
    ProductImage, ProductVariantOption,
    ProductVariant, ProductAddon,
    ProductTag, ProductAttribute,
    ProductVariantValue, ProductAddonGroup,
    ProductAddonItem, InventoryMovement,
    ProductCollection, CollectionProduct,
)


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'business', 'parent',
        'is_active', 'is_featured', 'order'
    )
    list_filter  = ('is_active', 'is_featured')
    search_fields = ('name', 'business__name')
    ordering = ('business', 'order', 'name')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'business', 'category',
        'price', 'status', 'is_featured',
        'total_sold', 'rating'
    )
    list_filter  = ('status', 'product_type', 'is_featured')
    search_fields = ('name', 'business__name')
    ordering = ('-created_at',)


@admin.register(ProductTag)
class ProductTagAdmin(admin.ModelAdmin):
    list_display  = ('name', 'business', 'color', 'is_active')
    list_filter   = ('is_active',)
    search_fields = ('name',)


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'product', 'value',
        'attribute_type', 'is_filterable'
    )
    list_filter  = ('attribute_type', 'is_filterable')
    search_fields = ('name', 'product__name')


@admin.register(ProductVariantOption)
class ProductVariantOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'product', 'is_required', 'order')
    search_fields = ('name', 'product__name')


@admin.register(ProductVariantValue)
class ProductVariantValueAdmin(admin.ModelAdmin):
    list_display = (
        'value', 'option', 'price_modifier',
        'is_active', 'is_default'
    )
    list_filter  = ('is_active', 'is_default')
    search_fields = ('value', 'option__name')


@admin.register(ProductVariant)
class ProductVariantAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'product', 'price',
        'stock_quantity', 'is_active'
    )
    list_filter  = ('is_active',)
    search_fields = ('name', 'product__name', 'sku')
    ordering = ('product', 'order')


@admin.register(ProductAddonGroup)
class ProductAddonGroupAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'product', 'is_required',
        'min_selections', 'max_selections',
        'is_active'
    )
    list_filter  = ('is_required', 'is_active')
    search_fields = ('name', 'product__name')


@admin.register(ProductAddonItem)
class ProductAddonItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'group', 'price',
        'is_active', 'is_default'
    )
    list_filter  = ('is_active', 'is_default')
    search_fields = ('name', 'group__name')


@admin.register(ProductAddon)
class ProductAddonAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'product', 'price',
        'is_required', 'is_active'
    )
    list_filter  = ('is_required', 'is_active')
    ordering = ('product', 'order')


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'movement_type', 'quantity',
        'quantity_before', 'quantity_after',
        'performed_by', 'created_at'
    )
    list_filter  = ('movement_type',)
    search_fields = ('product__name', 'reference')
    ordering = ('-created_at',)


@admin.register(ProductCollection)
class ProductCollectionAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'business', 'is_active',
        'is_featured', 'is_automated',
        'product_count', 'order'
    )
    list_filter  = ('is_active', 'is_featured', 'is_automated')
    search_fields = ('name', 'business__name')
    ordering = ('order', '-created_at')

    def product_count(self, obj):
        return obj.product_count
    product_count.short_description = 'Products'


@admin.register(CollectionProduct)
class CollectionProductAdmin(admin.ModelAdmin):
    list_display = ('collection', 'product', 'order')
    ordering = ('collection', 'order')
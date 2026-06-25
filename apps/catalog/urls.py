from django.urls import path
from .views import (
    CategoryListCreateView,
    CategoryDetailView,
    CategoryTreeView,
    CategoryProductsView,
    ProductListCreateView,
    ProductDetailView,
    ProductImageView,
    ProductVariantOptionView,
    ProductVariantView,
    ProductVariantValueView,
    ProductAddonView,
    ProductAddonGroupView,
    ProductAddonGroupDetailView,
    AddonItemView,
    ProductTagListCreateView,
    ProductAttributeView,
    InventoryMovementView,
    ProductCollectionListCreateView,
    ProductCollectionDetailView,
    CollectionProductView,
    BusinessCatalogView,
)

urlpatterns = [
    # Full catalog
    path('<int:business_id>/catalog/', BusinessCatalogView.as_view(), name='business_catalog'),

    # Category tree
    path('<int:business_id>/categories/tree/', CategoryTreeView.as_view(), name='category_tree'),

    # Categories
    path('<int:business_id>/categories/', CategoryListCreateView.as_view(), name='categories'),
    path('<int:business_id>/categories/<int:pk>/', CategoryDetailView.as_view(), name='category_detail'),
    path('<int:business_id>/categories/<int:pk>/products/', CategoryProductsView.as_view(), name='category_products'),

    # Products
    path('<int:business_id>/products/', ProductListCreateView.as_view(), name='products'),
    path('<int:business_id>/products/<int:pk>/', ProductDetailView.as_view(), name='product_detail'),

    # Product images
    path('<int:business_id>/products/<int:pk>/images/', ProductImageView.as_view(), name='product_images'),
    path('<int:business_id>/products/<int:pk>/images/<int:image_id>/', ProductImageView.as_view(), name='product_image_delete'),

    # Variant options + values
    path('<int:business_id>/products/<int:pk>/variant-options/', ProductVariantOptionView.as_view(), name='variant_options'),
    path('<int:business_id>/products/<int:pk>/variant-options/<int:option_id>/values/', ProductVariantValueView.as_view(), name='variant_values'),

    # Variants
    path('<int:business_id>/products/<int:pk>/variants/', ProductVariantView.as_view(), name='variants'),

    # Addon groups + items
    path('<int:business_id>/products/<int:pk>/addon-groups/', ProductAddonGroupView.as_view(), name='addon_groups'),
    path('<int:business_id>/products/<int:pk>/addon-groups/<int:group_id>/', ProductAddonGroupDetailView.as_view(), name='addon_group_detail'),
    path('<int:business_id>/products/<int:pk>/addon-groups/<int:group_id>/items/', AddonItemView.as_view(), name='addon_items'),
    path('<int:business_id>/products/<int:pk>/addon-groups/<int:group_id>/items/<int:item_id>/', AddonItemView.as_view(), name='addon_item_delete'),

    # Addons (simple)
    path('<int:business_id>/products/<int:pk>/addons/', ProductAddonView.as_view(), name='addons'),

    # Attributes
    path('<int:business_id>/products/<int:pk>/attributes/', ProductAttributeView.as_view(), name='product_attributes'),

    # Inventory
    path('<int:business_id>/products/<int:pk>/inventory/', InventoryMovementView.as_view(), name='inventory'),

    # Tags
    path('<int:business_id>/tags/', ProductTagListCreateView.as_view(), name='product_tags'),

    # Collections
    path('<int:business_id>/collections/', ProductCollectionListCreateView.as_view(), name='collections'),
    path('<int:business_id>/collections/<int:pk>/', ProductCollectionDetailView.as_view(), name='collection_detail'),
    path('<int:business_id>/collections/<int:pk>/products/', CollectionProductView.as_view(), name='collection_products'),
    path('<int:business_id>/collections/<int:pk>/products/<int:product_id>/', CollectionProductView.as_view(), name='collection_product_remove'),
]
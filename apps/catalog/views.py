from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from apps.common.views import api_response
from apps.common.permissions import IsAdmin, IsVendor
from apps.marketplace.models import Business, BusinessStaff
from .models import (
    ProductCategory, Product,
    ProductImage, ProductVariantOption,
    ProductVariant, ProductAddon, ProductTag,
    ProductAttribute, ProductVariantValue, ProductAddonItem, 
    ProductAddonGroup, InventoryMovement, CollectionProduct,
    ProductCollection
)
from .serializers import (
    ProductCategorySerializer,
    FlatCategorySerializer,
    ProductSerializer,
    CreateProductSerializer,
    ProductImageSerializer,
    ProductVariantOptionSerializer,
    ProductVariantSerializer,
    ProductAddonSerializer,
    ProductCollectionSerializer,
    CollectionProductSerializer,
    InventoryMovementSerializer,
    ProductAddonGroupSerializer,
    ProductAddonItemSerializer,
    ProductVariantValueSerializer,
    ProductAttributeSerializer,
    ProductTagSerializer,
)


def get_business_or_error(pk, user=None, owner_only=False):
    """Helper to get business and check permissions"""
    try:
        business = Business.objects.get(pk=pk)
        if owner_only and user and business.owner != user:
            return None, api_response(
                'error',
                'Only the business owner can perform this action',
                http_status=status.HTTP_403_FORBIDDEN
            )
        return business, None
    except Business.DoesNotExist:
        return None, api_response(
            'error', 'Business not found',
            http_status=status.HTTP_404_NOT_FOUND
        )


def can_manage_menu(user, business):
    """Check if user can manage menu"""
    if business.owner == user:
        return True
    return BusinessStaff.objects.filter(
        business=business,
        user=user,
        status='active'
    ).filter(
        role__permissions__codename='can_manage_menu'
    ).exists()


# ─── Category Views ──────────────────────────────

class CategoryListCreateView(APIView):
    """List categories for a business"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        # Query params
        flat = request.query_params.get('flat', 'false').lower() == 'true'
        parent_id = request.query_params.get('parent')
        root_only = request.query_params.get('root', 'false').lower() == 'true'

        categories = ProductCategory.objects.filter(
            business=business,
            is_active=True
        )

        if root_only:
            # Only root categories (no parent)
            categories = categories.filter(parent=None)
        elif parent_id:
            # Children of a specific category
            categories = categories.filter(parent__id=parent_id)

        if flat:
            # Return flat list
            serializer = FlatCategorySerializer(
                categories, many=True,
                context={'request': request}
            )
        else:
            # Return nested tree (root categories with children)
            if not parent_id and not root_only:
                categories = categories.filter(parent=None)
            serializer = ProductCategorySerializer(
                categories, many=True,
                context={'request': request}
            )

        return api_response(
            'success',
            'Categories retrieved successfully',
            data={
                'count': categories.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        data['business'] = business.id

        # Validate parent belongs to same business
        parent_id = data.get('parent')
        if parent_id:
            try:
                parent = ProductCategory.objects.get(
                    pk=parent_id,
                    business=business
                )
            except ProductCategory.DoesNotExist:
                return api_response(
                    'error',
                    'Parent category not found or does not belong to this business',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

        serializer = FlatCategorySerializer(
            data=data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response(
                'success',
                'Category created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CategoryDetailView(APIView):
    """Get, update, delete a category"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAuthenticated()]
        return []

    def get_object(self, pk, business_id):
        try:
            return ProductCategory.objects.get(
                pk=pk, business__id=business_id
            )
        except ProductCategory.DoesNotExist:
            return None

    def get(self, request, business_id, pk):
        category = self.get_object(pk, business_id)
        if not category:
            return api_response(
                'error', 'Category not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductCategorySerializer(
            category, context={'request': request}
        )
        return api_response(
            'success',
            'Category retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        category = self.get_object(pk, business_id)
        if not category:
            return api_response(
                'error', 'Category not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Prevent circular reference
        new_parent_id = request.data.get('parent')
        if new_parent_id:
            if str(new_parent_id) == str(pk):
                return api_response(
                    'error',
                    'A category cannot be its own parent',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            # Check not setting a descendant as parent
            descendant_ids = [d.id for d in category.descendants]
            if int(new_parent_id) in descendant_ids:
                return api_response(
                    'error',
                    'Cannot set a descendant as parent',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

        serializer = FlatCategorySerializer(
            category, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Category updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        category = self.get_object(pk, business_id)
        if not category:
            return api_response(
                'error', 'Category not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check has children
        if category.children.filter(is_active=True).exists():
            return api_response(
                'error',
                'Cannot delete a category with subcategories. Delete or move subcategories first.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        category.is_active = False
        category.save()
        return api_response(
            'success', 'Category deleted successfully'
        )


class CategoryTreeView(APIView):
    """
    Get full category tree for a business
    Returns hierarchical structure from root
    """
    permission_classes = []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        # Get root categories only (parent=None)
        roots = ProductCategory.objects.filter(
            business=business,
            parent=None,
            is_active=True
        ).order_by('order', 'name')

        serializer = ProductCategorySerializer(
            roots, many=True,
            context={'request': request}
        )

        return api_response(
            'success',
            'Category tree retrieved successfully',
            data={
                'count': roots.count(),
                'tree': serializer.data
            }
        )


class CategoryProductsView(APIView):
    """
    Get all products in a category
    including products from subcategories
    """
    permission_classes = []

    def get(self, request, business_id, pk):
        try:
            category = ProductCategory.objects.get(
                pk=pk, business__id=business_id
            )
        except ProductCategory.DoesNotExist:
            return api_response(
                'error', 'Category not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        include_subcategories = request.query_params.get(
            'include_subcategories', 'true'
        ).lower() == 'true'

        if include_subcategories:
            products = category.get_all_products()
        else:
            products = Product.objects.filter(
                category=category,
                is_active=True,
                status='active'
            )

        serializer = ProductSerializer(
            products, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            f'Products in {category.name} retrieved successfully',
            data={
                'category': {
                    'id': category.id,
                    'name': category.name,
                    'full_path': category.full_path,
                    'level': category.level,
                },
                'include_subcategories': include_subcategories,
                'count': products.count(),
                'results': serializer.data
            }
        )


# ─── Product Views ───────────────────────────────

class ProductListCreateView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        products = Product.objects.filter(
            business=business,
            is_active=True,
            status='active'
        )

        # Filters
        category_id  = request.query_params.get('category')
        search       = request.query_params.get('search')
        is_featured  = request.query_params.get('featured')
        product_type = request.query_params.get('type')
        min_price    = request.query_params.get('min_price')
        max_price    = request.query_params.get('max_price')
        in_stock     = request.query_params.get('in_stock')

        if category_id:
            try:
                category = ProductCategory.objects.get(
                    pk=category_id
                )
                # Include subcategories
                cat_ids = (
                    [category.id] +
                    [d.id for d in category.descendants]
                )
                products = products.filter(
                    category__id__in=cat_ids
                )
            except ProductCategory.DoesNotExist:
                pass

        if search:
            products = products.filter(
                name__icontains=search
            ) | products.filter(
                description__icontains=search
            ) | products.filter(
                tags__icontains=search
            )
        if is_featured:
            products = products.filter(is_featured=True)
        if product_type:
            products = products.filter(product_type=product_type)
        if min_price:
            products = products.filter(price__gte=min_price)
        if max_price:
            products = products.filter(price__lte=max_price)

        serializer = ProductSerializer(
            products, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Products retrieved successfully',
            data={
                'count': products.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = CreateProductSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Check slug unique for business
            if Product.objects.filter(
                business=business,
                slug=data['slug']
            ).exists():
                return api_response(
                    'error',
                    'Product slug already exists in this business',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get category
            category = None
            if data.get('category_id'):
                try:
                    category = ProductCategory.objects.get(
                        pk=data['category_id'],
                        business=business
                    )
                except ProductCategory.DoesNotExist:
                    return api_response(
                        'error',
                        'Category not found',
                        http_status=status.HTTP_404_NOT_FOUND
                    )

            product = Product.objects.create(
                business=business,
                category=category,
                name=data['name'],
                slug=data['slug'],
                description=data.get('description', ''),
                short_description=data.get('short_description', ''),
                product_type=data.get('product_type', 'simple'),
                price=data['price'],
                compare_price=data.get('compare_price'),
                cost_price=data.get('cost_price'),
                track_stock=data.get('track_stock', False),
                stock_quantity=data.get('stock_quantity', 0),
                weight=data.get('weight'),
                preparation_time=data.get('preparation_time', 0),
                is_featured=data.get('is_featured', False),
                tags=data.get('tags', []),
                order=data.get('order', 0),
            )

            return api_response(
                'success',
                'Product created successfully',
                data=ProductSerializer(
                    product, context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAuthenticated()]
        return []

    def get_object(self, pk, business_id):
        try:
            return Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return None

    def get(self, request, business_id, pk):
        product = self.get_object(pk, business_id)
        if not product:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductSerializer(
            product, context={'request': request}
        )
        return api_response(
            'success',
            'Product retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        product = self.get_object(pk, business_id)
        if not product:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductSerializer(
            product, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Product updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission to manage menu',
                http_status=status.HTTP_403_FORBIDDEN
            )

        product = self.get_object(pk, business_id)
        if not product:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        product.is_active = False
        product.status = 'inactive'
        product.save()
        return api_response(
            'success', 'Product deleted successfully'
        )


class ProductImageView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        image = request.FILES.get('image')
        if not image:
            return api_response(
                'error', 'No image provided',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        product_image = ProductImage.objects.create(
            product=product,
            image=image,
            alt_text=request.data.get('alt_text', ''),
            is_primary=request.data.get('is_primary', False),
        )

        return api_response(
            'success', 'Image uploaded successfully',
            data=ProductImageSerializer(
                product_image, context={'request': request}
            ).data,
            http_status=status.HTTP_201_CREATED
        )

    def delete(self, request, business_id, pk, image_id):
        try:
            image = ProductImage.objects.get(
                pk=image_id, product__id=pk
            )
            image.delete()
            return api_response(
                'success', 'Image deleted successfully'
            )
        except ProductImage.DoesNotExist:
            return api_response(
                'error', 'Image not found',
                http_status=status.HTTP_404_NOT_FOUND
            )


class ProductVariantOptionView(APIView):
    """Manage variant options (e.g Size, Color)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            product = Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        options = ProductVariantOption.objects.filter(
            product=product
        )
        serializer = ProductVariantOptionSerializer(
            options, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Variant options retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductVariantOptionSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(product=product)
            return api_response(
                'success',
                'Variant option created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductVariantView(APIView):
    """Manage product variants"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            product = Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        variants = ProductVariant.objects.filter(
            product=product, is_active=True
        )
        serializer = ProductVariantSerializer(
            variants, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Variants retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductVariantSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return api_response(
                'success',
                'Variant created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductAddonView(APIView):
    """Manage product add-ons"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            product = Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        addons = ProductAddon.objects.filter(
            product=product, is_active=True
        )
        serializer = ProductAddonSerializer(addons, many=True)
        return api_response(
            'success',
            'Add-ons retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductAddonSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product)
            return api_response(
                'success',
                'Add-on created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BusinessCatalogView(APIView):
    """
    Get full catalog for a business
    Categories with products nested
    """
    permission_classes = []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        # Get root categories with all children + products
        roots = ProductCategory.objects.filter(
            business=business,
            parent=None,
            is_active=True
        ).order_by('order', 'name')

        catalog = []
        for root in roots:
            category_data = ProductCategorySerializer(
                root, context={'request': request}
            ).data
            # Add products for this category
            category_data['products'] = ProductSerializer(
                Product.objects.filter(
                    category=root,
                    is_active=True,
                    status='active'
                ).order_by('order', 'name'),
                many=True,
                context={'request': request}
            ).data
            catalog.append(category_data)

        return api_response(
            'success',
            'Business catalog retrieved successfully',
            data={
                'business': {
                    'id': business.id,
                    'name': business.name,
                    'logo': request.build_absolute_uri(
                        business.logo.url
                    ) if business.logo else None,
                    'delivery_fee': str(business.delivery_fee),
                    'delivery_time_minutes': business.delivery_time_minutes,
                    'min_order_amount': str(business.min_order_amount),
                    'rating': str(business.rating),
                    'is_open_now': business.is_open_now,
                },
                'total_categories': roots.count(),
                'catalog': catalog,
            }
        )

class ProductTagListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        tags = ProductTag.objects.filter(
            business=business,
            is_active=True
        )
        serializer = ProductTagSerializer(
            tags, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Tags retrieved successfully',
            data={
                'count': tags.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductTagSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(business=business)
            return api_response(
                'success',
                'Tag created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductAttributeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            product = Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        attributes = ProductAttribute.objects.filter(
            product=product, is_visible=True
        )
        serializer = ProductAttributeSerializer(
            attributes, many=True
        )
        return api_response(
            'success',
            'Attributes retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductAttributeSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(
                product=product,
                business=business
            )
            return api_response(
                'success',
                'Attribute added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductVariantValueView(APIView):
    """Manage values for a variant option"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk, option_id):
        try:
            option = ProductVariantOption.objects.get(
                pk=option_id, product__id=pk
            )
        except ProductVariantOption.DoesNotExist:
            return api_response(
                'error', 'Variant option not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        values = ProductVariantValue.objects.filter(
            option=option, is_active=True
        )
        serializer = ProductVariantValueSerializer(
            values, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Variant values retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk, option_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            option = ProductVariantOption.objects.get(
                pk=option_id, product__id=pk
            )
        except ProductVariantOption.DoesNotExist:
            return api_response(
                'error', 'Variant option not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductVariantValueSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(option=option)
            return api_response(
                'success',
                'Variant value added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductAddonGroupView(APIView):
    """Manage addon groups for a product"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        try:
            product = Product.objects.get(
                pk=pk, business__id=business_id
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        groups = ProductAddonGroup.objects.filter(
            product=product, is_active=True
        )
        serializer = ProductAddonGroupSerializer(
            groups, many=True, context={'request': request}
        )
        return api_response(
            'success',
            'Addon groups retrieved successfully',
            data=serializer.data
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductAddonGroupSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(product=product)
            return api_response(
                'success',
                'Addon group created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductAddonGroupDetailView(APIView):
    """Add items to an addon group"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, product_id):
        try:
            return ProductAddonGroup.objects.get(
                pk=pk, product__id=product_id
            )
        except ProductAddonGroup.DoesNotExist:
            return None

    def patch(self, request, business_id, pk, group_id):
        group = self.get_object(group_id, pk)
        if not group:
            return api_response(
                'error', 'Addon group not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductAddonGroupSerializer(
            group, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Addon group updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, business_id, pk, group_id):
        group = self.get_object(group_id, pk)
        if not group:
            return api_response(
                'error', 'Addon group not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        group.is_active = False
        group.save()
        return api_response(
            'success', 'Addon group deleted successfully'
        )


class AddonItemView(APIView):
    """Manage items in an addon group"""
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, pk, group_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            group = ProductAddonGroup.objects.get(
                pk=group_id, product__id=pk
            )
        except ProductAddonGroup.DoesNotExist:
            return api_response(
                'error', 'Addon group not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductAddonItemSerializer(
            data=request.data
        )
        if serializer.is_valid():
            serializer.save(group=group)
            return api_response(
                'success',
                'Addon item added successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, business_id, pk, group_id, item_id):
        try:
            item = ProductAddonItem.objects.get(
                pk=item_id, group__id=group_id
            )
            item.is_active = False
            item.save()
            return api_response(
                'success', 'Addon item deleted successfully'
            )
        except ProductAddonItem.DoesNotExist:
            return api_response(
                'error', 'Addon item not found',
                http_status=status.HTTP_404_NOT_FOUND
            )


class InventoryMovementView(APIView):
    """Track inventory movements"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        movements = InventoryMovement.objects.filter(
            product=product
        )

        movement_type = request.query_params.get('type')
        if movement_type:
            movements = movements.filter(
                movement_type=movement_type
            )

        # Summary
        total_in = sum(
            m.quantity for m in movements
            if m.quantity > 0
        )
        total_out = sum(
            abs(m.quantity) for m in movements
            if m.quantity < 0
        )

        serializer = InventoryMovementSerializer(
            movements, many=True
        )
        return api_response(
            'success',
            'Inventory movements retrieved successfully',
            data={
                'current_stock': product.stock_quantity,
                'total_in': total_in,
                'total_out': total_out,
                'count': movements.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        try:
            product = Product.objects.get(
                pk=pk, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        movement_type = request.data.get('movement_type')
        quantity      = int(request.data.get('quantity', 0))
        notes         = request.data.get('notes', '')
        reference     = request.data.get('reference', '')
        unit_cost     = request.data.get('unit_cost')
        variant_id    = request.data.get('variant_id')

        variant = None
        if variant_id:
            variant = ProductVariant.objects.filter(
                pk=variant_id, product=product
            ).first()

        # Get current stock
        if variant:
            quantity_before = variant.stock_quantity
        else:
            quantity_before = product.stock_quantity

        quantity_after = quantity_before + quantity

        if quantity_after < 0:
            return api_response(
                'error',
                f'Insufficient stock. Current: {quantity_before}',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        movement = InventoryMovement.objects.create(
            product=product,
            variant=variant,
            movement_type=movement_type,
            quantity=quantity,
            quantity_before=quantity_before,
            quantity_after=quantity_after,
            notes=notes,
            reference=reference,
            unit_cost=unit_cost,
            performed_by=request.user,
        )

        return api_response(
            'success',
            'Inventory movement recorded successfully',
            data=InventoryMovementSerializer(movement).data,
            http_status=status.HTTP_201_CREATED
        )


class ProductCollectionListCreateView(APIView):
    """Manage product collections"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated()]
        return []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        collections = ProductCollection.objects.filter(
            business=business,
            is_active=True
        )
        featured = request.query_params.get('featured')
        if featured:
            collections = collections.filter(is_featured=True)

        serializer = ProductCollectionSerializer(
            collections, many=True,
            context={'request': request}
        )
        return api_response(
            'success',
            'Collections retrieved successfully',
            data={
                'count': collections.count(),
                'results': serializer.data
            }
        )

    def post(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        if not can_manage_menu(request.user, business):
            return api_response(
                'error',
                'You do not have permission',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = ProductCollectionSerializer(
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            collection = serializer.save(business=business)
            return api_response(
                'success',
                'Collection created successfully',
                data=ProductCollectionSerializer(
                    collection,
                    context={'request': request}
                ).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error', 'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ProductCollectionDetailView(APIView):
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE', 'POST']:
            return [IsAuthenticated()]
        return []

    def get_object(self, pk, business_id):
        try:
            return ProductCollection.objects.get(
                pk=pk, business__id=business_id
            )
        except ProductCollection.DoesNotExist:
            return None

    def get(self, request, business_id, pk):
        collection = self.get_object(pk, business_id)
        if not collection:
            return api_response(
                'error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = ProductCollectionSerializer(
            collection, context={'request': request}
        )
        return api_response(
            'success',
            'Collection retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        collection = self.get_object(pk, business_id)
        if not collection:
            return api_response(
                'error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = ProductCollectionSerializer(
            collection, data=request.data,
            partial=True, context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Collection updated successfully',
                data=serializer.data
            )
        return api_response(
            'error', 'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, business_id, pk):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        collection = self.get_object(pk, business_id)
        if not collection:
            return api_response(
                'error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        collection.is_active = False
        collection.save()
        return api_response(
            'success', 'Collection deleted successfully'
        )


class CollectionProductView(APIView):
    """Add/remove products from collection"""
    permission_classes = [IsAuthenticated]

    def post(self, request, business_id, pk):
        """Add product to collection"""
        business, error = get_business_or_error(business_id)
        if error:
            return error

        collection = ProductCollection.objects.filter(
            pk=pk, business=business
        ).first()
        if not collection:
            return api_response(
                'error', 'Collection not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        product_id = request.data.get('product_id')
        order      = request.data.get('order', 0)
        notes      = request.data.get('notes', '')

        try:
            product = Product.objects.get(
                pk=product_id, business=business
            )
        except Product.DoesNotExist:
            return api_response(
                'error', 'Product not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        cp, created = CollectionProduct.objects.get_or_create(
            collection=collection,
            product=product,
            defaults={'order': order, 'notes': notes}
        )

        if not created:
            return api_response(
                'error',
                'Product already in collection',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        return api_response(
            'success',
            f'{product.name} added to {collection.name}',
            data=CollectionProductSerializer(
                cp, context={'request': request}
            ).data,
            http_status=status.HTTP_201_CREATED
        )

    def delete(self, request, business_id, pk, product_id):
        """Remove product from collection"""
        try:
            cp = CollectionProduct.objects.get(
                collection__id=pk,
                product__id=product_id
            )
            cp.delete()
            return api_response(
                'success',
                'Product removed from collection'
            )
        except CollectionProduct.DoesNotExist:
            return api_response(
                'error', 'Product not in collection',
                http_status=status.HTTP_404_NOT_FOUND
            )

class BusinessCatalogView(APIView):
    permission_classes = []

    def get(self, request, business_id):
        business, error = get_business_or_error(business_id)
        if error:
            return error

        roots = ProductCategory.objects.filter(
            business=business,
            parent=None,
            is_active=True
        ).order_by('order', 'name')

        catalog = []
        for root in roots:
            category_data = ProductCategorySerializer(
                root, context={'request': request}
            ).data

            # Get ALL products from this root
            # and all its descendants
            all_category_ids = (
                [root.id] +
                [d.id for d in root.descendants]
            )
            category_data['products'] = ProductSerializer(
                Product.objects.filter(
                    category__id__in=all_category_ids,
                    is_active=True,
                    status='active'
                ).order_by('order', 'name'),
                many=True,
                context={'request': request}
            ).data

            catalog.append(category_data)

        return api_response(
            'success',
            'Business catalog retrieved successfully',
            data={
                'business': {
                    'id': business.id,
                    'name': business.name,
                    'logo': request.build_absolute_uri(
                        business.logo.url
                    ) if business.logo else None,
                    'delivery_fee': str(business.delivery_fee),
                    'delivery_time_minutes': business.delivery_time_minutes,
                    'min_order_amount': str(business.min_order_amount),
                    'rating': str(business.rating),
                    'is_open_now': business.is_open_now,
                },
                'total_categories': roots.count(),
                'catalog': catalog,
            }
        )

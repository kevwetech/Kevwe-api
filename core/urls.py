"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/products/', include('apps.products.urls')),
    path('api/v1/reviews/', include('apps.reviews.urls')),
    path('api/v1/wishlist/', include('apps.wishlist.urls')),
    path('api/v1/orders/', include('apps.orders.urls')),
    path('api/v1/bookings/', include('apps.bookings.urls')),
    path('api/v1/admin/', include('apps.dashboard.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/drivers/', include('apps.drivers.urls')),
    path('api/v1/shipments/', include('apps.shipments.urls')),
    path('api/v1/rides/', include('apps.rides.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/deliveries/', include('apps.deliveries.urls')),
    path('api/v1/subscriptions/', include('apps.subscriptions.urls')),
    path('api/v1/wallet/', include('apps.wallet.urls')),
    path('api/v1/locations/', include('apps.locations.urls')),
    path('api/v1/operations/', include('apps.operations.urls')),
    path('api/v1/cms/', include('apps.cms.urls')),
    path('api/v1/tenants/', include('apps.tenancy.urls')),
    path('api/v1/marketplace/', include('apps.marketplace.urls')),
    path('api/v1/catalog/', include('apps.catalog.urls')),
    path('api/v1/commissions/', include('apps.commissions.urls')),
    path('api/v1/analytics/', include('apps.analytics.urls')),
    path('api/v1/currencies/', include('apps.currencies.urls')),

    # API Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(
        url_name='schema'
    ), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(
        url_name='schema'
    ), name='redoc'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
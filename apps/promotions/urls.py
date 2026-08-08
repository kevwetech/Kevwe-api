from django.urls import path
from . import views

app_name = 'promotions'

urlpatterns = [
    path('', views.PromotionListView.as_view(), name='promotion_list'),
    path('<int:pk>/', views.PromotionDetailView.as_view(), name='promotion_detail'),
    path('validate/', views.PromotionValidateView.as_view(), name='promotion_validate'),
    path('redeem/', views.PromotionRedeemView.as_view(), name='promotion_redeem'),
]
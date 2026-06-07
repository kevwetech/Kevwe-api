from django.db import models
from apps.common.models import BaseItem, BaseCategory


class Category(BaseCategory):
    class Meta:
        verbose_name = 'Category'
        verbose_name_plural = 'Categories'


class Product(BaseItem):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='products'
    )
    stock = models.IntegerField(default=0)
    sku = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

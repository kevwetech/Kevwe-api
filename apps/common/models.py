from django.db import models


class TimeStampedModel(models.Model):
    """
    Base model with timestamps
    All models should inherit from this
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseItem(TimeStampedModel):
    """
    Generic base model for any industry
    Extend this for products, rooms, menu items etc
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    image = models.ImageField(
        upload_to='items/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class BaseCategory(TimeStampedModel):
    """
    Generic base category for any industry
    Extend this for product categories, room types etc
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='categories/',
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return self.name
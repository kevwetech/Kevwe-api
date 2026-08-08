from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from apps.common.models import TimeStampedModel


# How long a completed key is honored for replay before purge.
IDEMPOTENCY_TTL_HOURS = 24


def default_expiry():
    return timezone.now() + timedelta(hours=IDEMPOTENCY_TTL_HOURS)


class IdempotencyKey(TimeStampedModel):
    """
    Records a client-supplied Idempotency-Key against the response
    that was produced, so a retried request returns the original
    result instead of creating a second order/payment/booking.

    Scoped by (key, user, endpoint): the same key means "the same
    action" only for the same user hitting the same endpoint.

    user is NON-nullable by design — idempotent business operations
    (orders, payments, bookings, appointments, deliveries) are all
    authenticated, and a nullable user breaks the unique constraint
    under PostgreSQL (multiple NULLs are allowed).
    """
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = (
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
    )

    key = models.CharField(max_length=255, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='idempotency_keys',
    )
    endpoint = models.CharField(max_length=255)
    method = models.CharField(max_length=10, default='POST')

    # Hash of the request body — detects the SAME key reused with a
    # DIFFERENT payload (a client bug we must reject, not replay).
    request_fingerprint = models.CharField(
        max_length=64, blank=True, null=True)

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default=STATUS_PROCESSING)
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.JSONField(null=True, blank=True)

    expires_at = models.DateTimeField(default=default_expiry, db_index=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['key', 'user', 'endpoint'],
                name='unique_idempotency_key_scope',
            )
        ]
        indexes = [
            models.Index(fields=['key', 'user', 'endpoint']),
        ]

    def __str__(self):
        return f"{self.key} · {self.user_id} · {self.endpoint} · {self.status}"

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at
"""
Delete expired idempotency keys.
Run daily via cron / Railway scheduled task:
    python manage.py purge_idempotency_keys

By default deletes keys past their expires_at. Pass --all-older-than
to override with an explicit hours window instead.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.idempotency.models import IdempotencyKey


class Command(BaseCommand):
    help = 'Delete expired idempotency keys.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all-older-than', type=int, default=None,
            help='Ignore expires_at; delete keys older than N hours.')

    def handle(self, *args, **options):
        override = options['all_older_than']
        if override is not None:
            cutoff = timezone.now() - timedelta(hours=override)
            qs = IdempotencyKey.objects.filter(created_at__lt=cutoff)
            label = f'older than {override}h'
        else:
            qs = IdempotencyKey.objects.filter(
                expires_at__lte=timezone.now())
            label = 'past expiry'
        count = qs.count()
        qs.delete()
        self.stdout.write(self.style.SUCCESS(
            f'Deleted {count} idempotency key(s) {label}.'))
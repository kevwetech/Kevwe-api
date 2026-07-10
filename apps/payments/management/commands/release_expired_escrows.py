"""
Auto-release escrows past their deadline + expire stalled transactions.
Run daily: python manage.py release_expired_escrows
"""
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = 'Release escrows past auto_release_at deadline'

    def handle(self, *args, **options):
        from apps.payments.models import EscrowTransaction
        from apps.payments.escrow import release_escrow, EscrowTriggers

        expired = EscrowTransaction.objects.filter(
            status='held',
            auto_release_at__isnull=False,
            auto_release_at__lte=timezone.now(),
        )

        count = 0
        for escrow in expired:
            result = release_escrow(
                escrow.interaction_type,
                escrow.interaction_id,
                trigger=EscrowTriggers.AUTO_RELEASE,
                notes=f'Auto-released — no dispute within deadline '
                      f'(deadline was {escrow.auto_release_at})',
            )
            if result:
                count += 1
                self.stdout.write(
                    f'Released {escrow.reference} — '
                    f'{escrow.interaction_type} #{escrow.interaction_id} '
                    f'(₦{escrow.vendor_amount} to vendor)'
                )

        self.stdout.write(self.style.SUCCESS(
            f'Done. Released {count} escrow(s).'
        ))
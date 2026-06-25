import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.wallet.models import VendorWallet
from decimal import Decimal
import uuid

wallet = VendorWallet.objects.get(business__id=1)
wallet.refresh_from_db()
before = wallet.available_balance
print(f"Before: ₦{before}")

wallet.credit_earning(
    amount=2000,
    description='Test credit_earning fix',
    reference=f'TEST-{uuid.uuid4().hex[:10].upper()}',
    settlement_days=0
)

wallet.refresh_from_db()
after = wallet.available_balance
print(f"After:  ₦{after}")
print(f"Added:  ₦{after - before}")
print(f"Works:  {after - before == Decimal('2000')}")
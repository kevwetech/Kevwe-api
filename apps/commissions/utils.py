def get_commission_rule(business):
    """
    Get the most specific commission rule
    Priority: business > industry > global
    """
    from .models import CommissionRule

    # Business specific rule
    rule = CommissionRule.objects.filter(
        business=business,
        is_active=True
    ).first()
    if rule:
        return rule

    # Industry rule
    rule = CommissionRule.objects.filter(
        industry=business.industry,
        rule_type='industry',
        is_active=True
    ).first()
    if rule:
        return rule

    # Global rule
    rule = CommissionRule.objects.filter(
        rule_type='global',
        is_active=True
    ).first()
    return rule


def create_order_commission(order):
    """
    Auto create commission record when order is placed
    Called from orders view after order creation
    """
    from .models import Commission
    from apps.common.utils import generate_reference
    from decimal import Decimal

    if not order.business:
        return None

    business = order.business
    rule = get_commission_rule(business)

    # Use rule rates or fall back to business/industry rates
    if rule:
        splits = rule.calculate(order.subtotal)
        platform_commission = splits['platform']
        vendor_earnings = splits['vendor']
        driver_earnings = splits['driver']
        platform_rate = splits['platform_rate']
        vendor_rate = splits['vendor_rate']
        driver_rate = splits['driver_rate']
    else:
        # Fall back to industry/business rates
        platform_rate = business.commission_rate
        vendor_rate = business.industry.vendor_commission
        driver_rate = business.industry.driver_commission
        platform_commission = order.subtotal * Decimal(str(platform_rate)) / 100
        vendor_earnings = order.subtotal * Decimal(str(vendor_rate)) / 100
        driver_earnings = order.delivery_fee * Decimal('0.80')

    # Delivery commission
    delivery_driver = order.delivery_fee * Decimal('0.80')
    delivery_platform = order.delivery_fee * Decimal('0.20')

    commission = Commission.objects.create(
        rule=rule,
        business=business,
        vendor=business.owner,
        driver=order.driver,
        transaction_type='order',
        order=order,
        reference=generate_reference('COM'),
        gross_amount=order.subtotal,
        delivery_fee=order.delivery_fee,
        platform_commission=platform_commission + delivery_platform,
        vendor_earnings=vendor_earnings,
        driver_earnings=delivery_driver,
        platform_rate=platform_rate,
        vendor_rate=vendor_rate,
        driver_rate=driver_rate,
        status='pending',
    )

    return commission

def get_commission_rule(business):
    """
    Get commission rate considering subscription
    Priority: subscription override → business rule 
              → industry rule → global rule
    """
    from .models import CommissionRule

    # Check subscription commission override
    try:
        sub = business.subscription
        if sub and sub.is_active:
            effective_rate = sub.effective_commission_rate
            if effective_rate is not None:
                # Return a virtual rule with subscription rate
                rule = CommissionRule(
                    name=f'{sub.plan.name} Subscription Rate',
                    rule_type='business',
                    calculation_type='percentage',
                    platform_rate=effective_rate,
                    vendor_rate=100 - effective_rate - 20,
                    driver_rate=20,
                )
                return rule
    except Exception:
        pass

    # Business specific rule
    rule = CommissionRule.objects.filter(
        business=business,
        is_active=True
    ).first()
    if rule:
        return rule

    # Industry rule
    rule = CommissionRule.objects.filter(
        industry=business.industry,
        rule_type='industry',
        is_active=True
    ).first()
    if rule:
        return rule

    # Global rule
    rule = CommissionRule.objects.filter(
        rule_type='global',
        is_active=True
    ).first()
    return rule
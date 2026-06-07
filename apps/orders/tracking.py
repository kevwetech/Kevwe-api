from .models import OrderTracking


ORDER_STEPS = [
    {
        'status': 'pending',
        'label': 'Order Placed',
        'description': 'Your order has been placed successfully',
        'icon': '📦'
    },
    {
        'status': 'confirmed',
        'label': 'Order Confirmed',
        'description': 'Your order has been confirmed',
        'icon': '✅'
    },
    {
        'status': 'processing',
        'label': 'Processing',
        'description': 'Your order is being processed',
        'icon': '⚙️'
    },
    {
        'status': 'shipped',
        'label': 'Shipped',
        'description': 'Your order is on the way',
        'icon': '🚚'
    },
    {
        'status': 'delivered',
        'label': 'Delivered',
        'description': 'Your order has been delivered',
        'icon': '🎉'
    },
]


def create_order_tracking(order, status, description=None, location=None):
    """Create a tracking entry for an order"""
    default_description = next(
        (step['description'] for step in ORDER_STEPS
         if step['status'] == status),
        'Order status updated'
    )
    return OrderTracking.objects.create(
        order=order,
        status=status,
        description=description or default_description,
        location=location or ''
    )


def get_order_tracking_data(order):
    """Get full tracking data for an order"""
    tracking_entries = OrderTracking.objects.filter(order=order)
    tracking_dict = {
        entry.status: entry
        for entry in tracking_entries
    }

    steps = []
    current_index = next(
        (i for i, step in enumerate(ORDER_STEPS)
         if step['status'] == order.status),
        0
    )

    for i, step in enumerate(ORDER_STEPS):
        entry = tracking_dict.get(step['status'])
        steps.append({
            'status': step['status'],
            'label': step['label'],
            'description': entry.description if entry else step['description'],
            'icon': step['icon'],
            'location': entry.location if entry else None,
            'timestamp': entry.created_at if entry else None,
            'completed': i <= current_index,
            'current': step['status'] == order.status,
        })

    return {
        'reference': order.reference,
        'current_status': order.status,
        'payment_status': order.payment_status,
        'estimated_delivery': None,
        'tracking_steps': steps,
        'history': [
            {
                'status': entry.status,
                'description': entry.description,
                'location': entry.location,
                'timestamp': entry.created_at,
            }
            for entry in tracking_entries
        ]
    }
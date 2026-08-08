from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Q

from .models import Promotion
from .serializers import PromotionSerializer, PromotionValidateSerializer


class PromotionListView(generics.ListAPIView):
    '''Public — active promotions for a business (or platform-wide
    ones), for display: the banner strip on a business page reads
    this via marketplace.BusinessPromotion.promotion, but a client
    that wants the raw eligible list can hit this directly.'''
    serializer_class = PromotionSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        from django.utils import timezone
        now = timezone.now()
        qs = Promotion.objects.filter(is_active=True, status='active').filter(
            Q(ends_at__isnull=True) | Q(ends_at__gte=now)
        ).filter(starts_at__lte=now)

        business_id = self.request.query_params.get('business_id')
        if business_id:
            qs = qs.filter(Q(business_id=business_id) | Q(business__isnull=True))
        return qs


class PromotionDetailView(generics.RetrieveAPIView):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [permissions.AllowAny]


class PromotionValidateView(APIView):
    '''POST {code, business_id?, order_amount?} at checkout.
    Validates eligibility WITHOUT consuming a use — call
    PromotionRedeemView once the order actually completes.'''
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PromotionValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo = serializer.validated_data['promotion']
        order_amount = serializer.validated_data.get('order_amount')

        discount = promo.compute_discount(order_amount) if order_amount is not None else None

        return Response({
            'status': 'success',
            'data': {
                'promotion': PromotionSerializer(promo).data,
                'discount_amount': discount,
            },
        })


class PromotionRedeemView(APIView):
    '''POST {code, business_id?} once an order/booking actually
    completes. Separate from validate() so a user can preview a
    discount without it counting against usage_limit.'''
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PromotionValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promo = serializer.validated_data['promotion']

        try:
            promo.redeem(order_amount=serializer.validated_data.get('order_amount'))
        except Exception as exc:
            return Response(
                {'status': 'error', 'message': str(exc)},
                status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'status': 'success',
            'message': 'Promotion redeemed.',
            'data': PromotionSerializer(promo).data,
        })
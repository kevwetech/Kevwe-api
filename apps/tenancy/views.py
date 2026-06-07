from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from .models import (
    Tenant,
    TenantMembership,
    TenantInvitation,
    TenantBranch,
    TenantBilling,
    CreditAccount, 
    CreditTransaction,
    APIKey, 
    Webhook, 
    WebhookEvent, 
    APIUsage,
    Feature, 
    TenantFeature, 
    TenantSetting,
    AuditLog, 
    ActivityFeed, 
    UsageMetric,
    CustomDomain,
)
from .serializers import (
    TenantSerializer,
    TenantMembershipSerializer,
    TenantInvitationSerializer,
    TenantBranchSerializer,
    TenantBillingSerializer,
    CreateTenantSerializer,
    InviteMemberSerializer,
    CreditTransactionSerializer,
    CreditAccountSerializer,
    APIKeySerializer,
    WebhookSerializer,
    WebhookEventSerializer,
    APIUsageSerializer,
    FeatureSerializer,
    TenantFeatureSerializer,
    TenantSettingSerializer,
    AuditLogSerializer,
    ActivityFeedSerializer,
    UsageMetricSerializer,
    CustomDomainSerializer,
)


class TenantListCreateView(APIView):
    """List and create tenants"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Admin sees all tenants
        if request.user.role == 'admin':
            tenants = Tenant.objects.all()
        else:
            # User sees their own tenants
            membership_ids = TenantMembership.objects.filter(
                user=request.user,
                is_active=True
            ).values_list('tenant_id', flat=True)
            tenants = Tenant.objects.filter(
                id__in=membership_ids
            )

        tenant_status = request.query_params.get('status')
        industry = request.query_params.get('industry')
        if tenant_status:
            tenants = tenants.filter(status=tenant_status)
        if industry:
            tenants = tenants.filter(industry=industry)

        serializer = TenantSerializer(tenants, many=True)
        return api_response(
            'success',
            'Tenants retrieved successfully',
            data={
                'count': tenants.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = CreateTenantSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # Check slug is unique
            if Tenant.objects.filter(
                slug=data['slug']
            ).exists():
                return api_response(
                    'error',
                    'Slug already taken',
                    http_status=status.HTTP_400_BAD_REQUEST
                )

            # Get plan
            plan = None
            if data.get('plan_id'):
                from apps.subscriptions.models import Plan
                plan = Plan.objects.filter(
                    pk=data['plan_id'],
                    is_active=True
                ).first()

            # Get location
            from apps.locations.models import Country, State, City
            country = Country.objects.filter(
                pk=data.get('country')
            ).first() if data.get('country') else None
            state = State.objects.filter(
                pk=data.get('state')
            ).first() if data.get('state') else None
            city = City.objects.filter(
                pk=data.get('city')
            ).first() if data.get('city') else None

            # Create tenant
            tenant = Tenant.objects.create(
                name=data['name'],
                slug=data['slug'],
                description=data.get('description', ''),
                industry=data.get('industry', 'other'),
                email=data['email'],
                phone=data.get('phone', ''),
                website=data.get('website', ''),
                address=data.get('address', ''),
                country=country,
                state=state,
                city=city,
                plan=plan,
                owner=request.user,
                status='trial',
                trial_ends_at=timezone.now() + timedelta(days=14),
            )

            # Generate API keys
            tenant.generate_api_keys()

            # Add owner as member
            TenantMembership.objects.create(
                tenant=tenant,
                user=request.user,
                role='owner',
                can_manage_users=True,
                can_manage_products=True,
                can_manage_orders=True,
                can_manage_deliveries=True,
                can_manage_finance=True,
                can_view_reports=True,
                can_manage_settings=True,
            )

            # Send notification
            from apps.notifications.utils import send_notification
            send_notification(
                user=request.user,
                title='Tenant Created! 🎉',
                message=f'Your tenant {tenant.name} has been created successfully. Trial period: 14 days.',
                notification_type='system',
                data={
                    'tenant_id': tenant.id,
                    'tenant_name': tenant.name,
                    'api_key': tenant.api_key,
                }
            )

            return api_response(
                'success',
                f'Tenant {tenant.name} created successfully! 14-day trial started.',
                data=TenantSerializer(tenant).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class TenantDetailView(APIView):
    """Get, update and delete tenant"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            tenant = Tenant.objects.get(pk=pk)
            # Check if user has access
            if user.role == 'admin':
                return tenant
            if TenantMembership.objects.filter(
                tenant=tenant,
                user=user,
                is_active=True
            ).exists():
                return tenant
            return None
        except Tenant.DoesNotExist:
            return None

    def get(self, request, pk):
        tenant = self.get_object(pk, request.user)
        if not tenant:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TenantSerializer(tenant)
        return api_response(
            'success',
            'Tenant retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        tenant = self.get_object(pk, request.user)
        if not tenant:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True
        ).first()

        if not membership or (
            not membership.can_manage_settings
            and request.user.role != 'admin'
        ):
            return api_response(
                'error',
                'You do not have permission to update settings',
                http_status=status.HTTP_403_FORBIDDEN
            )

        serializer = TenantSerializer(
            tenant,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Tenant updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        tenant = self.get_object(pk, request.user)
        if not tenant:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Only owner or admin can delete
        if (
            tenant.owner != request.user
            and request.user.role != 'admin'
        ):
            return api_response(
                'error',
                'Only the owner can delete a tenant',
                http_status=status.HTTP_403_FORBIDDEN
            )

        tenant.is_active = False
        tenant.status = 'cancelled'
        tenant.save()

        return api_response(
            'success',
            'Tenant cancelled successfully'
        )


class RegenerateAPIKeyView(APIView):
    """Regenerate tenant API keys"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(
                pk=pk,
                owner=request.user
            )
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tenant.generate_api_keys()

        return api_response(
            'success',
            'API keys regenerated successfully',
            data={
                'api_key': tenant.api_key,
                'api_secret': tenant.api_secret,
            }
        )


class TenantMemberListView(APIView):
    """List and manage tenant members"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        members = TenantMembership.objects.filter(
            tenant=tenant,
            is_active=True
        )
        serializer = TenantMembershipSerializer(
            members,
            many=True
        )
        return api_response(
            'success',
            'Members retrieved successfully',
            data={
                'count': members.count(),
                'results': serializer.data
            }
        )


class InviteMemberView(APIView):
    """Invite user to tenant"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True,
            can_manage_users=True
        ).first()

        if not membership and request.user.role != 'admin':
            return api_response(
                'error',
                'You do not have permission to invite members',
                http_status=status.HTTP_403_FORBIDDEN
            )

        # Check member limit
        if tenant.total_users >= tenant.max_users:
            return api_response(
                'error',
                f'Member limit reached. Maximum {tenant.max_users} members allowed.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        serializer = InviteMemberSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            role = serializer.validated_data['role']

            import secrets
            token = secrets.token_urlsafe(32)

            invitation = TenantInvitation.objects.create(
                tenant=tenant,
                email=email,
                role=role,
                token=token,
                invited_by=request.user,
                expires_at=timezone.now() + timedelta(days=7)
            )

            # Send invitation email
            try:
                from apps.common.email import send_email
                send_email(
                    to_email=email,
                    subject=f'You are invited to join {tenant.name}',
                    html_content=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                        <h2>You have been invited!</h2>
                        <p>{request.user.full_name} has invited you to join <strong>{tenant.name}</strong> as a <strong>{role}</strong>.</p>
                        <p>Your invitation token: <strong>{token}</strong></p>
                        <p>This invitation expires in 7 days.</p>
                    </div>
                    """
                )
            except Exception:
                pass

            return api_response(
                'success',
                f'Invitation sent to {email}',
                data=TenantInvitationSerializer(invitation).data,
                http_status=status.HTTP_201_CREATED
            )

        return api_response(
            'error',
            'Invitation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class AcceptInvitationView(APIView):
    """Accept tenant invitation"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get('token')
        if not token:
            return api_response(
                'error',
                'Token is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        try:
            invitation = TenantInvitation.objects.get(
                token=token,
                status='pending'
            )
        except TenantInvitation.DoesNotExist:
            return api_response(
                'error',
                'Invalid or expired invitation',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if invitation.is_expired:
            invitation.status = 'expired'
            invitation.save()
            return api_response(
                'error',
                'Invitation has expired',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check email matches
        if invitation.email != request.user.email:
            return api_response(
                'error',
                'This invitation was sent to a different email',
                http_status=status.HTTP_403_FORBIDDEN
            )

        # Create membership
        membership, created = TenantMembership.objects.get_or_create(
            tenant=invitation.tenant,
            user=request.user,
            defaults={
                'role': invitation.role,
                'invited_by': invitation.invited_by,
            }
        )

        if not created:
            membership.is_active = True
            membership.role = invitation.role
            membership.save()

        # Update invitation
        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()

        return api_response(
            'success',
            f'Welcome to {invitation.tenant.name}!',
            data=TenantMembershipSerializer(membership).data
        )


class RemoveMemberView(APIView):
    """Remove member from tenant"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk, member_id):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            membership = TenantMembership.objects.get(
                pk=member_id,
                tenant=tenant
            )
        except TenantMembership.DoesNotExist:
            return api_response(
                'error',
                'Member not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Can't remove owner
        if membership.role == 'owner':
            return api_response(
                'error',
                'Cannot remove the owner',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        membership.is_active = False
        membership.save()

        return api_response(
            'success',
            'Member removed successfully'
        )


class TenantBranchListView(APIView):
    """Manage tenant branches"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        branches = TenantBranch.objects.filter(
            tenant=tenant,
            is_active=True
        )
        serializer = TenantBranchSerializer(branches, many=True)
        return api_response(
            'success',
            'Branches retrieved successfully',
            data={
                'count': branches.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check branch limit
        if tenant.total_branches >= tenant.max_branches:
            return api_response(
                'error',
                f'Branch limit reached. Maximum {tenant.max_branches} branches allowed.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        branch_id = request.data.get('branch_id')
        is_primary = request.data.get('is_primary', False)

        from apps.operations.models import Branch
        branch = Branch.objects.filter(pk=branch_id).first()

        if not branch:
            return api_response(
                'error',
                'Branch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # If setting as primary remove primary from others
        if is_primary:
            TenantBranch.objects.filter(
                tenant=tenant,
                is_primary=True
            ).update(is_primary=False)

        tenant_branch, created = TenantBranch.objects.get_or_create(
            tenant=tenant,
            branch=branch,
            defaults={'is_primary': is_primary}
        )

        if not created:
            tenant_branch.is_active = True
            tenant_branch.is_primary = is_primary
            tenant_branch.save()

        return api_response(
            'success',
            'Branch added to tenant successfully',
            data=TenantBranchSerializer(tenant_branch).data,
            http_status=status.HTTP_201_CREATED
        )


class TenantBillingListView(APIView):
    """View tenant billing history"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        billings = TenantBilling.objects.filter(tenant=tenant)

        total_paid = sum(
            b.amount for b in billings.filter(status='paid')
        )

        serializer = TenantBillingSerializer(billings, many=True)
        return api_response(
            'success',
            'Billing history retrieved successfully',
            data={
                'count': billings.count(),
                'total_paid': str(total_paid),
                'results': serializer.data
            }
        )


class TenantDashboardView(APIView):
    """Tenant dashboard stats"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Check membership
        membership = TenantMembership.objects.filter(
            tenant=tenant,
            user=request.user,
            is_active=True
        ).first()

        if not membership and request.user.role != 'admin':
            return api_response(
                'error',
                'Access denied',
                http_status=status.HTTP_403_FORBIDDEN
            )

        # Trial status
        trial_days_left = 0
        if tenant.trial_ends_at:
            delta = tenant.trial_ends_at - timezone.now()
            trial_days_left = max(0, delta.days)

        return api_response(
            'success',
            'Tenant dashboard retrieved',
            data={
                'tenant': TenantSerializer(tenant).data,
                'membership': TenantMembershipSerializer(
                    membership
                ).data if membership else None,
                'stats': {
                    'total_members': tenant.total_users,
                    'max_members': tenant.max_users,
                    'total_branches': tenant.total_branches,
                    'max_branches': tenant.max_branches,
                    'trial_days_left': trial_days_left,
                    'status': tenant.status,
                },
                'features': {
                    'enable_orders': tenant.enable_orders,
                    'enable_bookings': tenant.enable_bookings,
                    'enable_deliveries': tenant.enable_deliveries,
                    'enable_rides': tenant.enable_rides,
                    'enable_shipments': tenant.enable_shipments,
                    'enable_wallet': tenant.enable_wallet,
                    'enable_subscriptions': tenant.enable_subscriptions,
                    'enable_pos': tenant.enable_pos,
                },
            }
        )


class AdminTenantListView(APIView):
    """Admin - list all tenants with stats"""
    permission_classes = [IsAdmin]

    def get(self, request):
        tenants = Tenant.objects.all()

        tenant_status = request.query_params.get('status')
        industry = request.query_params.get('industry')

        if tenant_status:
            tenants = tenants.filter(status=tenant_status)
        if industry:
            tenants = tenants.filter(industry=industry)

        total_revenue = sum(
            b.amount
            for b in TenantBilling.objects.filter(status='paid')
        )

        serializer = TenantSerializer(tenants, many=True)
        return api_response(
            'success',
            'All tenants retrieved',
            data={
                'count': tenants.count(),
                'active': tenants.filter(status='active').count(),
                'trial': tenants.filter(status='trial').count(),
                'suspended': tenants.filter(
                    status='suspended'
                ).count(),
                'total_revenue': str(total_revenue),
                'results': serializer.data
            }
        )


class AdminTenantUpdateView(APIView):
    """Admin - update tenant status"""
    permission_classes = [IsAdmin]

    def patch(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        if new_status:
            tenant.status = new_status
            tenant.save()

            # Notify owner
            from apps.notifications.utils import send_notification
            send_notification(
                user=tenant.owner,
                title=f'Tenant Status Updated',
                message=f'Your tenant {tenant.name} status has been updated to {new_status}',
                notification_type='system'
            )

        serializer = TenantSerializer(tenant)
        return api_response(
            'success',
            'Tenant updated successfully',
            data=serializer.data
        )


class CreditAccountView(APIView):
    """Get tenant credit account"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Get or create credit account
        credit_account, created = CreditAccount.objects.get_or_create(
            tenant=tenant
        )

        serializer = CreditAccountSerializer(credit_account)
        return api_response(
            'success',
            'Credit account retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        """Update credit account settings"""
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        credit_account, created = CreditAccount.objects.get_or_create(
            tenant=tenant
        )

        serializer = CreditAccountSerializer(
            credit_account,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Credit account updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CreditTopUpView(APIView):
    """Top up tenant credit account"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        amount = request.data.get('amount')
        gateway = request.data.get('gateway', 'paystack')
        callback_url = request.data.get('callback_url')

        if not amount:
            return api_response(
                'error',
                'Amount is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        from decimal import Decimal
        amount = Decimal(str(amount))

        # Initialize payment
        reference = generate_reference('CRD')

        if gateway == 'paystack':
            from apps.payments.paystack import initialize_payment
            result = initialize_payment(
                email=request.user.email,
                amount=amount,
                reference=reference,
                callback_url=callback_url,
                metadata={
                    'type': 'credit_topup',
                    'tenant_id': tenant.id,
                    'amount': str(amount),
                }
            )

            if result.get('status'):
                return api_response(
                    'success',
                    'Payment initialized successfully',
                    data={
                        'reference': reference,
                        'amount': str(amount),
                        'gateway': gateway,
                        'authorization_url': result['data']['authorization_url'],
                        'access_code': result['data']['access_code'],
                    }
                )

        elif gateway == 'flutterwave':
            from apps.payments.flutterwave import initialize_payment
            result = initialize_payment(
                email=request.user.email,
                amount=amount,
                reference=reference,
                name=request.user.full_name,
                phone=request.user.phone,
                redirect_url=callback_url,
                metadata={
                    'type': 'credit_topup',
                    'tenant_id': tenant.id,
                    'amount': str(amount),
                }
            )

            if result.get('status') == 'success':
                return api_response(
                    'success',
                    'Payment initialized successfully',
                    data={
                        'reference': reference,
                        'amount': str(amount),
                        'gateway': gateway,
                        'payment_link': result['data']['link'],
                    }
                )

        return api_response(
            'error',
            'Payment initialization failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class ConfirmCreditTopUpView(APIView):
    """Confirm credit top up after payment"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        reference = request.data.get('reference')
        gateway = request.data.get('gateway', 'paystack')
        transaction_id = request.data.get('transaction_id')

        if not reference:
            return api_response(
                'error',
                'Reference is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check not already processed
        already = CreditTransaction.objects.filter(
            reference=reference,
            status='success'
        ).exists()

        if already:
            return api_response(
                'error',
                'Transaction already processed',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Verify payment
        verified = False
        amount = 0

        if gateway == 'paystack':
            from apps.payments.paystack import verify_payment
            result = verify_payment(reference)
            if (
                result.get('status') and
                result['data']['status'] == 'success'
            ):
                verified = True
                amount = result['data']['amount'] / 100

        elif gateway == 'flutterwave':
            from apps.payments.flutterwave import verify_payment_by_reference
            result = verify_payment_by_reference(reference)
            if result.get('status') == 'success':
                data = result.get('data', [])
                if isinstance(data, list) and len(data) > 0:
                    if data[0].get('status') == 'successful':
                        verified = True
                        amount = data[0].get('amount', 0)

        if verified:
            credit_account, _ = CreditAccount.objects.get_or_create(
                tenant=tenant
            )
            credit_account.credit(
                amount=amount,
                description=f'Credit top up via {gateway}',
                reference=reference
            )

            # Update description type
            CreditTransaction.objects.filter(
                reference=reference
            ).update(description_type='topup')

            # Send notification
            from apps.notifications.utils import send_notification
            send_notification(
                user=request.user,
                title='Credits Added! 🎉',
                message=f'₦{amount} credits added to {tenant.name}. New balance: ₦{credit_account.balance}',
                notification_type='system'
            )

            return api_response(
                'success',
                f'₦{amount} credits added successfully',
                data={
                    'amount_added': str(amount),
                    'new_balance': str(credit_account.balance),
                }
            )

        return api_response(
            'error',
            'Payment verification failed',
            http_status=status.HTTP_400_BAD_REQUEST
        )


class CreditTransactionListView(APIView):
    """Get credit transaction history"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        credit_account, _ = CreditAccount.objects.get_or_create(
            tenant=tenant
        )

        transactions = CreditTransaction.objects.filter(
            credit_account=credit_account
        )

        # Filters
        transaction_type = request.query_params.get('type')
        description_type = request.query_params.get('description_type')

        if transaction_type:
            transactions = transactions.filter(
                transaction_type=transaction_type
            )
        if description_type:
            transactions = transactions.filter(
                description_type=description_type
            )

        # Summary
        total_credits = sum(
            t.amount for t in transactions.filter(
                transaction_type='credit',
                status='success'
            )
        )
        total_debits = sum(
            t.amount for t in transactions.filter(
                transaction_type='debit',
                status='success'
            )
        )

        serializer = CreditTransactionSerializer(
            transactions,
            many=True
        )
        return api_response(
            'success',
            'Credit transactions retrieved successfully',
            data={
                'balance': str(credit_account.balance),
                'total_credits': str(total_credits),
                'total_debits': str(total_debits),
                'count': transactions.count(),
                'results': serializer.data
            }
        )


class AdminCreditView(APIView):
    """Admin - manually credit/debit tenant"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        action = request.data.get('action')  # credit or debit
        amount = request.data.get('amount')
        description = request.data.get(
            'description',
            'Admin adjustment'
        )
        description_type = request.data.get(
            'description_type',
            'adjustment'
        )

        if not action or not amount:
            return api_response(
                'error',
                'Action and amount are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        credit_account, _ = CreditAccount.objects.get_or_create(
            tenant=tenant
        )

        reference = generate_reference('ADM')

        if action == 'credit':
            credit_account.credit(
                amount=amount,
                description=description,
                reference=reference
            )
            # Update description type
            CreditTransaction.objects.filter(
                reference=reference
            ).update(
                description_type=description_type,
                performed_by=request.user
            )
            message = f'₦{amount} credited to {tenant.name}'

        elif action == 'debit':
            success = credit_account.debit(
                amount=amount,
                description=description,
                reference=reference
            )
            if not success:
                return api_response(
                    'error',
                    f'Insufficient balance. Current balance: ₦{credit_account.balance}',
                    http_status=status.HTTP_400_BAD_REQUEST
                )
            # Update description type
            CreditTransaction.objects.filter(
                reference=reference
            ).update(
                description_type=description_type,
                performed_by=request.user
            )
            message = f'₦{amount} debited from {tenant.name}'
        else:
            return api_response(
                'error',
                'Invalid action. Use credit or debit',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Notify tenant owner
        from apps.notifications.utils import send_notification
        send_notification(
            user=tenant.owner,
            title=f'Credit Account {action.capitalize()}ed',
            message=f'₦{amount} has been {action}ed {"to" if action == "credit" else "from"} your credit account. New balance: ₦{credit_account.balance}',
            notification_type='system'
        )

        return api_response(
            'success',
            message,
            data={
                'action': action,
                'amount': str(amount),
                'new_balance': str(credit_account.balance),
            }
        )

class APIKeyListCreateView(APIView):
    """Manage tenant API keys"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        keys = APIKey.objects.filter(tenant=tenant)
        serializer = APIKeySerializer(keys, many=True)
        return api_response(
            'success',
            'API keys retrieved successfully',
            data={
                'count': keys.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        name = request.data.get('name', 'API Key')
        description = request.data.get('description', '')
        can_read = request.data.get('can_read', True)
        can_write = request.data.get('can_write', True)
        can_delete = request.data.get('can_delete', False)
        rate_limit = request.data.get('rate_limit', 1000)
        expires_at = request.data.get('expires_at')

        # Generate API key
        api_key = APIKey.generate_key(
            tenant=tenant,
            name=name,
            created_by=request.user,
            description=description,
            can_read=can_read,
            can_write=can_write,
            can_delete=can_delete,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )

        # Get the raw key before it's gone
        raw_key = getattr(api_key, '_raw_key', None)

        serializer = APIKeySerializer(api_key)
        data = serializer.data
        if raw_key:
            data['raw_key'] = raw_key
            data['warning'] = 'Save this key now! It will never be shown again.'

        return api_response(
            'success',
            'API key created successfully',
            data=data,
            http_status=status.HTTP_201_CREATED
        )


class APIKeyDetailView(APIView):
    """Get, update and revoke API key"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, tenant_pk):
        try:
            return APIKey.objects.get(
                pk=pk,
                tenant__id=tenant_pk
            )
        except APIKey.DoesNotExist:
            return None

    def get(self, request, pk, key_id):
        api_key = self.get_object(key_id, pk)
        if not api_key:
            return api_response(
                'error',
                'API key not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = APIKeySerializer(api_key)
        return api_response(
            'success',
            'API key retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk, key_id):
        api_key = self.get_object(key_id, pk)
        if not api_key:
            return api_response(
                'error',
                'API key not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = APIKeySerializer(
            api_key,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'API key updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, key_id):
        """Revoke API key"""
        api_key = self.get_object(key_id, pk)
        if not api_key:
            return api_response(
                'error',
                'API key not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        api_key.status = 'revoked'
        api_key.save()
        return api_response(
            'success',
            'API key revoked successfully'
        )


class WebhookListCreateView(APIView):
    """Manage tenant webhooks"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        webhooks = Webhook.objects.filter(tenant=tenant)
        serializer = WebhookSerializer(webhooks, many=True)
        return api_response(
            'success',
            'Webhooks retrieved successfully',
            data={
                'count': webhooks.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        serializer = WebhookSerializer(data=request.data)
        if serializer.is_valid():
            webhook = serializer.save(
                tenant=tenant,
                created_by=request.user
            )
            # Generate secret
            secret = webhook.generate_secret()

            data = WebhookSerializer(webhook).data
            data['secret'] = secret
            data['warning'] = 'Save this secret! It will never be shown again.'

            return api_response(
                'success',
                'Webhook created successfully',
                data=data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class WebhookDetailView(APIView):
    """Get, update and delete webhook"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, tenant_pk):
        try:
            return Webhook.objects.get(
                pk=pk,
                tenant__id=tenant_pk
            )
        except Webhook.DoesNotExist:
            return None

    def get(self, request, pk, webhook_id):
        webhook = self.get_object(webhook_id, pk)
        if not webhook:
            return api_response(
                'error',
                'Webhook not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = WebhookSerializer(webhook)
        return api_response(
            'success',
            'Webhook retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk, webhook_id):
        webhook = self.get_object(webhook_id, pk)
        if not webhook:
            return api_response(
                'error',
                'Webhook not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = WebhookSerializer(
            webhook,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Webhook updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, webhook_id):
        webhook = self.get_object(webhook_id, pk)
        if not webhook:
            return api_response(
                'error',
                'Webhook not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        webhook.is_active = False
        webhook.status = 'inactive'
        webhook.save()
        return api_response(
            'success',
            'Webhook deleted successfully'
        )


class WebhookEventListView(APIView):
    """Get webhook delivery history"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, webhook_id):
        try:
            webhook = Webhook.objects.get(
                pk=webhook_id,
                tenant__id=pk
            )
        except Webhook.DoesNotExist:
            return api_response(
                'error',
                'Webhook not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        events = WebhookEvent.objects.filter(webhook=webhook)

        event_status = request.query_params.get('status')
        if event_status:
            events = events.filter(status=event_status)

        serializer = WebhookEventSerializer(events, many=True)
        return api_response(
            'success',
            'Webhook events retrieved successfully',
            data={
                'count': events.count(),
                'delivered': events.filter(
                    status='delivered'
                ).count(),
                'failed': events.filter(
                    status='failed'
                ).count(),
                'results': serializer.data
            }
        )


class ResendWebhookEventView(APIView):
    """Resend a failed webhook event"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, webhook_id, event_id):
        try:
            event = WebhookEvent.objects.get(
                pk=event_id,
                webhook__id=webhook_id,
                tenant__id=pk
            )
        except WebhookEvent.DoesNotExist:
            return api_response(
                'error',
                'Event not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Attempt redelivery
        try:
            import requests
            import json
            import hmac
            import hashlib

            webhook = event.webhook
            payload = json.dumps(event.payload)

            # Sign payload
            signature = hmac.new(
                webhook.secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()

            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': signature,
                'X-Event-Type': event.event_type,
                'X-Tenant-ID': str(pk),
            }

            import time
            start = time.time()
            response = requests.post(
                webhook.url,
                data=payload,
                headers=headers,
                timeout=30
            )
            response_time = int((time.time() - start) * 1000)

            event.attempt_count += 1
            event.response_status_code = response.status_code
            event.response_body = response.text[:500]
            event.response_time_ms = response_time

            if response.status_code < 300:
                event.status = 'delivered'
                event.delivered_at = timezone.now()
                webhook.successful_deliveries += 1
                webhook.last_success_at = timezone.now()
            else:
                event.status = 'failed'
                webhook.failed_deliveries += 1
                webhook.last_failure_at = timezone.now()

            event.save()
            webhook.total_deliveries += 1
            webhook.last_triggered_at = timezone.now()
            webhook.save()

        except Exception as e:
            event.status = 'failed'
            event.error_message = str(e)
            event.attempt_count += 1
            event.save()

        serializer = WebhookEventSerializer(event)
        return api_response(
            'success',
            'Webhook event resent',
            data=serializer.data
        )


class APIUsageView(APIView):
    """Get API usage stats for tenant"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        usage = APIUsage.objects.filter(tenant=tenant)

        # Filters
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        endpoint = request.query_params.get('endpoint')
        method = request.query_params.get('method')

        if from_date:
            usage = usage.filter(date__gte=from_date)
        if to_date:
            usage = usage.filter(date__lte=to_date)
        if endpoint:
            usage = usage.filter(
                endpoint__icontains=endpoint
            )
        if method:
            usage = usage.filter(method=method)

        # Stats
        total_requests = usage.count()
        successful = usage.filter(
            status_code__lt=400
        ).count()
        failed = usage.filter(
            status_code__gte=400
        ).count()

        avg_response_time = 0
        if total_requests > 0:
            avg_response_time = sum(
                u.response_time_ms for u in usage
            ) / total_requests

        # Top endpoints
        from collections import Counter
        endpoint_counts = Counter(
            usage.values_list('endpoint', flat=True)
        )
        top_endpoints = [
            {'endpoint': ep, 'count': count}
            for ep, count in endpoint_counts.most_common(10)
        ]

        # Daily breakdown
        from collections import defaultdict
        daily = defaultdict(int)
        for u in usage:
            daily[str(u.date)] += 1

        return api_response(
            'success',
            'API usage retrieved successfully',
            data={
                'summary': {
                    'total_requests': total_requests,
                    'successful': successful,
                    'failed': failed,
                    'success_rate': round(
                        (successful / total_requests * 100)
                        if total_requests > 0 else 100,
                        2
                    ),
                    'avg_response_time_ms': round(
                        avg_response_time,
                        2
                    ),
                },
                'top_endpoints': top_endpoints,
                'daily_breakdown': dict(daily),
            }
        )

class FeatureListCreateView(APIView):
    """List and create system features"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAdmin()]
        return []

    def get(self, request):
        features = Feature.objects.filter(is_active=True)
        category = request.query_params.get('category')
        pricing_type = request.query_params.get('pricing_type')
        if category:
            features = features.filter(category=category)
        if pricing_type:
            features = features.filter(
                pricing_type=pricing_type
            )
        serializer = FeatureSerializer(features, many=True)
        return api_response(
            'success',
            'Features retrieved successfully',
            data={
                'count': features.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FeatureSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Feature created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FeatureDetailView(APIView):
    """Get update delete feature"""
    permission_classes = []

    def get_permissions(self):
        if self.request.method in ['PATCH', 'DELETE']:
            return [IsAdmin()]
        return []

    def get_object(self, pk):
        try:
            return Feature.objects.get(pk=pk)
        except Feature.DoesNotExist:
            return None

    def get(self, request, pk):
        feature = self.get_object(pk)
        if not feature:
            return api_response(
                'error',
                'Feature not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FeatureSerializer(feature)
        return api_response(
            'success',
            'Feature retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        feature = self.get_object(pk)
        if not feature:
            return api_response(
                'error',
                'Feature not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FeatureSerializer(
            feature,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Feature updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        feature = self.get_object(pk)
        if not feature:
            return api_response(
                'error',
                'Feature not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        feature.is_active = False
        feature.save()
        return api_response(
            'success',
            'Feature deleted successfully'
        )


class TenantFeatureListView(APIView):
    """List tenant features"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        features = TenantFeature.objects.filter(
            tenant=tenant
        )
        category = request.query_params.get('category')
        if category:
            features = features.filter(
                feature__category=category
            )

        serializer = TenantFeatureSerializer(
            features,
            many=True
        )
        return api_response(
            'success',
            'Tenant features retrieved successfully',
            data={
                'count': features.count(),
                'active': sum(
                    1 for f in features if f.is_active
                ),
                'results': serializer.data
            }
        )


class EnableFeatureView(APIView):
    """Enable a feature for tenant"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        feature_id = request.data.get('feature_id')
        try:
            feature = Feature.objects.get(
                pk=feature_id,
                is_active=True
            )
        except Feature.DoesNotExist:
            return api_response(
                'error',
                'Feature not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tenant_feature, created = TenantFeature.objects.get_or_create(
            tenant=tenant,
            feature=feature,
            defaults={
                'status': 'active',
                'enabled_by': request.user,
                'custom_price': request.data.get('custom_price'),
                'usage_limit': request.data.get('usage_limit', 0),
                'expires_at': request.data.get('expires_at'),
                'config': request.data.get('config', {}),
                'notes': request.data.get('notes', ''),
            }
        )

        if not created:
            tenant_feature.status = 'active'
            tenant_feature.save()

        # Notify tenant owner
        from apps.notifications.utils import send_notification
        send_notification(
            user=tenant.owner,
            title=f'Feature Enabled: {feature.name}',
            message=f'{feature.name} has been enabled for {tenant.name}',
            notification_type='system'
        )

        return api_response(
            'success',
            f'{feature.name} enabled for {tenant.name}',
            data=TenantFeatureSerializer(tenant_feature).data,
            http_status=status.HTTP_201_CREATED
        )


class DisableFeatureView(APIView):
    """Disable a feature for tenant"""
    permission_classes = [IsAdmin]

    def post(self, request, pk, feature_id):
        try:
            tenant_feature = TenantFeature.objects.get(
                tenant__id=pk,
                feature__id=feature_id
            )
        except TenantFeature.DoesNotExist:
            return api_response(
                'error',
                'Feature not found for this tenant',
                http_status=status.HTTP_404_NOT_FOUND
            )

        tenant_feature.status = 'inactive'
        tenant_feature.save()

        return api_response(
            'success',
            f'{tenant_feature.feature.name} disabled successfully',
            data=TenantFeatureSerializer(tenant_feature).data
        )


class TenantSettingListCreateView(APIView):
    """Manage tenant settings"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        settings = TenantSetting.objects.filter(
            tenant=tenant
        )

        # Non-admins can only see public settings
        if request.user.role != 'admin':
            membership = TenantMembership.objects.filter(
                tenant=tenant,
                user=request.user,
                is_active=True
            ).first()
            if not membership or not membership.can_manage_settings:
                settings = settings.filter(is_public=True)

        category = request.query_params.get('category')
        if category:
            settings = settings.filter(category=category)

        serializer = TenantSettingSerializer(
            settings,
            many=True
        )
        return api_response(
            'success',
            'Settings retrieved successfully',
            data={
                'count': settings.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        key = request.data.get('key')
        value = request.data.get('value')
        data_type = request.data.get('data_type', 'string')
        category = request.data.get('category', 'general')
        description = request.data.get('description', '')
        is_public = request.data.get('is_public', False)
        is_encrypted = request.data.get('is_encrypted', False)

        if not key or value is None:
            return api_response(
                'error',
                'Key and value are required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Upsert setting
        setting, created = TenantSetting.objects.update_or_create(
            tenant=tenant,
            key=key,
            defaults={
                'value': str(value),
                'data_type': data_type,
                'category': category,
                'description': description,
                'is_public': is_public,
                'is_encrypted': is_encrypted,
                'updated_by': request.user,
            }
        )

        action = 'created' if created else 'updated'
        serializer = TenantSettingSerializer(setting)
        return api_response(
            'success',
            f'Setting {action} successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class TenantSettingDetailView(APIView):
    """Get update delete single setting"""
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, key):
        try:
            return TenantSetting.objects.get(
                tenant__id=pk,
                key=key
            )
        except TenantSetting.DoesNotExist:
            return None

    def get(self, request, pk, key):
        setting = self.get_object(pk, key)
        if not setting:
            return api_response(
                'error',
                'Setting not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TenantSettingSerializer(setting)
        return api_response(
            'success',
            'Setting retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk, key):
        setting = self.get_object(pk, key)
        if not setting:
            return api_response(
                'error',
                'Setting not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        new_value = request.data.get('value')
        if new_value is not None:
            setting.value = str(new_value)
            setting.updated_by = request.user
            setting.save()

        serializer = TenantSettingSerializer(setting)
        return api_response(
            'success',
            'Setting updated successfully',
            data=serializer.data
        )

    def delete(self, request, pk, key):
        setting = self.get_object(pk, key)
        if not setting:
            return api_response(
                'error',
                'Setting not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        setting.delete()
        return api_response(
            'success',
            'Setting deleted successfully'
        )


class BulkTenantSettingsView(APIView):
    """
    Get or set multiple settings at once
    Perfect for frontend to load all settings
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        """Get all settings as key/value dict"""
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        settings = TenantSetting.objects.filter(
            tenant=tenant
        )

        # Return as dict
        settings_dict = {}
        for s in settings:
            if not s.is_encrypted:
                settings_dict[s.key] = s.get_value()

        return api_response(
            'success',
            'Settings retrieved successfully',
            data=settings_dict
        )

    def post(self, request, pk):
        """Set multiple settings at once"""
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        settings_data = request.data.get('settings', {})
        category = request.data.get('category', 'general')

        if not settings_data:
            return api_response(
                'error',
                'Settings data is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        updated = []
        for key, value in settings_data.items():
            setting, _ = TenantSetting.objects.update_or_create(
                tenant=tenant,
                key=key,
                defaults={
                    'value': str(value),
                    'category': category,
                    'updated_by': request.user,
                }
            )
            updated.append(key)

        return api_response(
            'success',
            f'{len(updated)} settings saved successfully',
            data={'updated_keys': updated}
        )


class AuditLogListView(APIView):
    """Get tenant audit logs"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        logs = AuditLog.objects.filter(tenant=tenant)

        # Filters
        action = request.query_params.get('action')
        severity = request.query_params.get('severity')
        user_id = request.query_params.get('user')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if action:
            logs = logs.filter(action=action)
        if severity:
            logs = logs.filter(severity=severity)
        if user_id:
            logs = logs.filter(user__id=user_id)
        if from_date:
            logs = logs.filter(created_at__date__gte=from_date)
        if to_date:
            logs = logs.filter(created_at__date__lte=to_date)

        serializer = AuditLogSerializer(logs, many=True)
        return api_response(
            'success',
            'Audit logs retrieved successfully',
            data={
                'count': logs.count(),
                'results': serializer.data
            }
        )


class CreateAuditLogView(APIView):
    """Manually create audit log entry"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        from .utils import create_audit_log
        create_audit_log(
            tenant=tenant,
            user=request.user,
            action=request.data.get('action', 'other'),
            description=request.data.get('description', ''),
            severity=request.data.get('severity', 'info'),
            object_type=request.data.get('object_type'),
            object_id=request.data.get('object_id'),
            object_repr=request.data.get('object_repr'),
            changes=request.data.get('changes', {}),
            metadata=request.data.get('metadata'),
            request=request,
        )

        return api_response(
            'success',
            'Audit log created successfully',
            http_status=status.HTTP_201_CREATED
        )


class ActivityFeedView(APIView):
    """Get tenant activity feed"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        activities = ActivityFeed.objects.filter(
            tenant=tenant
        )

        activity_type = request.query_params.get('type')
        is_read = request.query_params.get('is_read')
        limit = int(request.query_params.get('limit', 20))

        if activity_type:
            activities = activities.filter(
                activity_type=activity_type
            )
        if is_read is not None:
            activities = activities.filter(
                is_read=is_read == 'true'
            )

        activities = activities[:limit]

        serializer = ActivityFeedSerializer(
            activities,
            many=True
        )
        return api_response(
            'success',
            'Activity feed retrieved successfully',
            data={
                'count': len(serializer.data),
                'unread': ActivityFeed.objects.filter(
                    tenant=tenant,
                    is_read=False
                ).count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        """Mark all activities as read"""
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        ActivityFeed.objects.filter(
            tenant=tenant,
            is_read=False
        ).update(is_read=True)

        return api_response(
            'success',
            'All activities marked as read'
        )


class CreateActivityView(APIView):
    """Create activity feed entry"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        from .utils import create_activity
        create_activity(
            tenant=tenant,
            user=request.user,
            title=request.data.get('title', ''),
            activity_type=request.data.get(
                'activity_type', 'other'
            ),
            description=request.data.get('description'),
            icon=request.data.get('icon'),
            color=request.data.get('color'),
            object_type=request.data.get('object_type'),
            object_id=request.data.get('object_id'),
            object_url=request.data.get('object_url'),
            metadata=request.data.get('metadata'),
        )

        return api_response(
            'success',
            'Activity created successfully',
            http_status=status.HTTP_201_CREATED
        )


class UsageMetricView(APIView):
    """Get tenant usage metrics"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        metrics = UsageMetric.objects.filter(tenant=tenant)

        period = request.query_params.get('period', 'daily')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        if period:
            metrics = metrics.filter(period=period)
        if from_date:
            metrics = metrics.filter(date__gte=from_date)
        if to_date:
            metrics = metrics.filter(date__lte=to_date)

        # Summary totals
        total_api_calls = sum(
            m.total_api_calls for m in metrics
        )
        total_revenue = sum(
            m.total_revenue for m in metrics
        )
        total_orders = sum(
            m.total_orders for m in metrics
        )
        total_deliveries = sum(
            m.total_deliveries for m in metrics
        )

        serializer = UsageMetricSerializer(
            metrics,
            many=True
        )
        return api_response(
            'success',
            'Usage metrics retrieved successfully',
            data={
                'summary': {
                    'total_api_calls': total_api_calls,
                    'total_revenue': str(total_revenue),
                    'total_orders': total_orders,
                    'total_deliveries': total_deliveries,
                },
                'count': metrics.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        """Generate metrics for a date"""
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        date_str = request.data.get('date')
        date = None

        if date_str:
            from datetime import datetime
            date = datetime.strptime(
                date_str, '%Y-%m-%d'
            ).date()

        from .utils import update_usage_metrics
        metric = update_usage_metrics(tenant, date)

        serializer = UsageMetricSerializer(metric)
        return api_response(
            'success',
            'Usage metrics generated successfully',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )

class CustomDomainListCreateView(APIView):
    """Manage tenant custom domains"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        domains = CustomDomain.objects.filter(tenant=tenant)
        serializer = CustomDomainSerializer(domains, many=True)
        return api_response(
            'success',
            'Domains retrieved successfully',
            data={
                'count': domains.count(),
                'results': serializer.data
            }
        )

    def post(self, request, pk):
        try:
            tenant = Tenant.objects.get(pk=pk)
        except Tenant.DoesNotExist:
            return api_response(
                'error',
                'Tenant not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        domain = request.data.get('domain', '').lower().strip()
        domain_type = request.data.get('domain_type', 'primary')
        is_primary = request.data.get('is_primary', False)
        notes = request.data.get('notes', '')

        if not domain:
            return api_response(
                'error',
                'Domain is required',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Check domain not already taken
        if CustomDomain.objects.filter(domain=domain).exists():
            return api_response(
                'error',
                'Domain already registered',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Validate domain format
        import re
        domain_pattern = r'^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
        if not re.match(domain_pattern, domain):
            return api_response(
                'error',
                'Invalid domain format',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # If setting as primary remove primary from others
        if is_primary:
            CustomDomain.objects.filter(
                tenant=tenant,
                is_primary=True
            ).update(is_primary=False)

        # Create domain
        custom_domain = CustomDomain.objects.create(
            tenant=tenant,
            domain=domain,
            domain_type=domain_type,
            is_primary=is_primary,
            added_by=request.user,
            notes=notes,
        )

        # Generate verification token and DNS records
        custom_domain.generate_verification_token()

        # Create audit log
        from .utils import create_audit_log
        create_audit_log(
            tenant=tenant,
            user=request.user,
            action='settings.updated',
            description=f'Added custom domain: {domain}',
            object_type='CustomDomain',
            object_id=custom_domain.id,
            object_repr=domain,
            request=request,
        )

        serializer = CustomDomainSerializer(custom_domain)
        return api_response(
            'success',
            f'Domain {domain} added successfully! Please add the DNS records to verify.',
            data=serializer.data,
            http_status=status.HTTP_201_CREATED
        )


class CustomDomainDetailView(APIView):
    """Get update delete domain"""
    permission_classes = [IsAuthenticated]

    def get_object(self, domain_id, tenant_pk):
        try:
            return CustomDomain.objects.get(
                pk=domain_id,
                tenant__id=tenant_pk
            )
        except CustomDomain.DoesNotExist:
            return None

    def get(self, request, pk, domain_id):
        domain = self.get_object(domain_id, pk)
        if not domain:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CustomDomainSerializer(domain)
        return api_response(
            'success',
            'Domain retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk, domain_id):
        domain = self.get_object(domain_id, pk)
        if not domain:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = CustomDomainSerializer(
            domain,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Domain updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk, domain_id):
        domain = self.get_object(domain_id, pk)
        if not domain:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if domain.is_primary:
            return api_response(
                'error',
                'Cannot delete primary domain. Set another domain as primary first.',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        domain_name = domain.domain
        domain.delete()

        return api_response(
            'success',
            f'Domain {domain_name} removed successfully'
        )


class VerifyDomainView(APIView):
    """Verify domain ownership"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, domain_id):
        try:
            domain = CustomDomain.objects.get(
                pk=domain_id,
                tenant__id=pk
            )
        except CustomDomain.DoesNotExist:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if domain.is_verified:
            return api_response(
                'success',
                'Domain is already verified',
                data=CustomDomainSerializer(domain).data
            )

        # Update status to verifying
        domain.status = 'verifying'
        domain.save()

        # Attempt verification
        verified = domain.verify_domain()

        if verified:
            # Update tenant domain
            tenant = domain.tenant
            if domain.is_primary:
                tenant.custom_domain = domain.domain
                tenant.save()

            # Create activity
            from .utils import create_activity
            create_activity(
                tenant=domain.tenant,
                user=request.user,
                title=f'Domain Verified: {domain.domain}',
                activity_type='system',
                description=f'Custom domain {domain.domain} has been verified successfully',
                icon='🌐',
                color='#00ff00',
                object_type='CustomDomain',
                object_id=domain.id,
            )

            # Notify owner
            from apps.notifications.utils import send_notification
            send_notification(
                user=domain.tenant.owner,
                title='Domain Verified! 🌐',
                message=f'Your domain {domain.domain} has been verified successfully.',
                notification_type='system'
            )

            return api_response(
                'success',
                f'Domain {domain.domain} verified successfully!',
                data=CustomDomainSerializer(domain).data
            )

        return api_response(
            'error',
            'Domain verification failed. Please check your DNS records.',
            data={
                'domain': domain.domain,
                'status': domain.status,
                'error': domain.check_error,
                'dns_records': domain.dns_records,
            },
            http_status=status.HTTP_400_BAD_REQUEST
        )


class SetPrimaryDomainView(APIView):
    """Set domain as primary"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, domain_id):
        try:
            domain = CustomDomain.objects.get(
                pk=domain_id,
                tenant__id=pk
            )
        except CustomDomain.DoesNotExist:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not domain.is_verified:
            return api_response(
                'error',
                'Domain must be verified before setting as primary',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Remove primary from others
        CustomDomain.objects.filter(
            tenant__id=pk,
            is_primary=True
        ).update(is_primary=False)

        # Set as primary
        domain.is_primary = True
        domain.save()

        # Update tenant
        tenant = domain.tenant
        tenant.custom_domain = domain.domain
        tenant.save()

        return api_response(
            'success',
            f'{domain.domain} set as primary domain',
            data=CustomDomainSerializer(domain).data
        )


class RefreshSSLView(APIView):
    """Request SSL certificate for domain"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, domain_id):
        try:
            domain = CustomDomain.objects.get(
                pk=domain_id,
                tenant__id=pk
            )
        except CustomDomain.DoesNotExist:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        if not domain.is_verified:
            return api_response(
                'error',
                'Domain must be verified before requesting SSL',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # In production integrate with Let's Encrypt or Cloudflare
        domain.ssl_status = 'pending'
        domain.save()

        return api_response(
            'success',
            'SSL certificate requested. This may take up to 24 hours.',
            data=CustomDomainSerializer(domain).data
        )


class AdminDomainListView(APIView):
    """Admin - list all domains"""
    permission_classes = [IsAdmin]

    def get(self, request):
        domains = CustomDomain.objects.all()

        domain_status = request.query_params.get('status')
        ssl_status = request.query_params.get('ssl_status')

        if domain_status:
            domains = domains.filter(status=domain_status)
        if ssl_status:
            domains = domains.filter(ssl_status=ssl_status)

        serializer = CustomDomainSerializer(domains, many=True)
        return api_response(
            'success',
            'All domains retrieved',
            data={
                'count': domains.count(),
                'active': domains.filter(
                    status='active'
                ).count(),
                'pending': domains.filter(
                    status='pending'
                ).count(),
                'ssl_active': domains.filter(
                    ssl_status='active'
                ).count(),
                'results': serializer.data
            }
        )

    def patch(self, request, domain_id):
        """Admin update domain status"""
        try:
            domain = CustomDomain.objects.get(pk=domain_id)
        except CustomDomain.DoesNotExist:
            return api_response(
                'error',
                'Domain not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        ssl_status = request.data.get('ssl_status')

        if new_status:
            domain.status = new_status
            if new_status == 'active':
                domain.verified_at = timezone.now()

        if ssl_status:
            domain.ssl_status = ssl_status
            if ssl_status == 'active':
                domain.ssl_issued_at = timezone.now()
                from datetime import timedelta
                domain.ssl_expires_at = (
                    timezone.now() + timedelta(days=90)
                )

        domain.save()

        # Notify tenant
        from apps.notifications.utils import send_notification
        send_notification(
            user=domain.tenant.owner,
            title=f'Domain Status Updated',
            message=f'Your domain {domain.domain} status: {domain.status}',
            notification_type='system'
        )

        return api_response(
            'success',
            'Domain updated successfully',
            data=CustomDomainSerializer(domain).data
        )
from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class Permission(TimeStampedModel):
    """
    Platform-defined permissions.
    Only platform admin creates these.
    Businesses assign them to roles.
    """
    CATEGORY_CHOICES = (
        ('bookings', 'Bookings'),
        ('orders', 'Orders'),
        ('products', 'Products & Services'),
        ('customers', 'Customers'),
        ('staff', 'Staff Management'),
        ('wallet', 'Wallet & Finance'),
        ('analytics', 'Analytics'),
        ('settings', 'Settings'),
        ('reviews', 'Reviews'),
        ('messages', 'Messages'),
        ('promotions', 'Promotions'),
        ('kyc', 'KYC & Verification'),
    )

    code = models.CharField(
        max_length=100, unique=True,
        help_text='e.g. view_bookings, cancel_orders'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES
    )
    is_active = models.BooleanField(default=True)
    is_owner_only = models.BooleanField(
        default=False,
        help_text=(
            'Restricted to business owner only '
            '(e.g. withdraw funds, delete business)'
        )
    )

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.code} ({self.category})"


class Role(TimeStampedModel):
    """
    A job role within a business.
    Can be created by the business owner.
    Permissions are assigned to the role.
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='staff_app_roles'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(
        default=False,
        help_text='Default role auto-assigned to new staff'
    )
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        related_name='staff_roles',
        blank=True
    )
    is_active = models.BooleanField(default=True)
    parent_role = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='child_roles',
        help_text='Parent role in hierarchy e.g. Manager supervises Receptionist'
    )

    class Meta:
        unique_together = ('business', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.business.name} — {self.name}"

    def has_permission(self, permission_code):
        return self.permissions.filter(
            code=permission_code,
            is_active=True
        ).exists()


class RolePermission(TimeStampedModel):
    """Through model for Role ↔ Permission."""
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='role_permissions'
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='granted_permissions'
    )
    scope = models.CharField(
        max_length=20,
        choices=(
            ('all', 'All Records'),
            ('own', 'Own Records Only'),
            ('branch', 'Branch Only'),
        ),
        default='all',
        help_text='Scope of this permission'
    )
    limit_amount = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text='Max amount for financial permissions e.g. max refund ₦20,000'
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Leave null for permanent permission'
    )

    class Meta:
        unique_together = ('role', 'permission')

    def __str__(self):
        return f"{self.role.name} → {self.permission.code}"


class BusinessMember(TimeStampedModel):
    """
    Links a user to a business with a role.
    A user can be a member of multiple businesses.
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='members'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='business_memberships'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_invitations_sent'
    )
    job_title = models.CharField(
        max_length=100, blank=True,
        help_text='Custom job title e.g. Front Desk Supervisor'
    )
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='members'
    )
    branch = models.ForeignKey(
        'operations.Branch',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='staff_members',
        help_text='Which branch this member is assigned to'
    )
    # Merged from StaffAccount
    must_change_password = models.BooleanField(default=False)
    password_changed_at = models.DateTimeField(
        null=True, blank=True
    )
    pin_enabled = models.BooleanField(default=False)
    impersonated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='impersonating_members',
        help_text='Set when owner is impersonating this member'
    )
    # Override permissions (per-member, beyond role)
    extra_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='extra_member_permissions',
        help_text='Additional permissions beyond role'
    )
    denied_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='denied_member_permissions',
        help_text='Permissions explicitly denied for this member'
    )

    class Meta:
        unique_together = ('business', 'user')
        ordering = ['-joined_at']

    def __str__(self):
        return (
            f"{self.user.full_name} @ "
            f"{self.business.name} "
            f"({self.role.name if self.role else 'No Role'})"
        )

    def has_permission(self, permission_code):
        """
        Check if member has a specific permission.
        Priority: denied > extra > role permissions.
        """
        # Owner always has all permissions
        if self.business.owner == self.user:
            return True

        # Check if explicitly denied
        if self.denied_permissions.filter(
            code=permission_code
        ).exists():
            return False

        # Check extra (individual) permissions
        if self.extra_permissions.filter(
            code=permission_code
        ).exists():
            return True

        # Check role permissions
        if self.role and self.role.has_permission(
            permission_code
        ):
            return True

        return False


class StaffInvitation(TimeStampedModel):
    """
    Invitation sent to a user to join a business as staff.
    Supports both email and phone invitations.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    )

    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='staff_invitations',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_staff_invite_notifications'
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invitations'
    )
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(
        max_length=20, blank=True, null=True
    )
    name = models.CharField(
        max_length=255, blank=True,
        help_text='Invited person name'
    )
    job_title = models.CharField(
        max_length=100, blank=True
    )
    token = models.CharField(
        max_length=64, unique=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accepted_staff_invitations'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    message = models.TextField(
        blank=True,
        help_text='Optional personal message to invitee'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        contact = self.email or self.phone
        return (
            f"Invitation: {contact} → "
            f"{self.business.name} ({self.status})"
        )

    def is_valid(self):
        from django.utils import timezone
        return (
            self.status == 'pending'
            and timezone.now() < self.expires_at
        )


class StaffAccount(TimeStampedModel):
    """
    Owner-created staff account with temporary password.
    Used when staff member doesn't have an existing account.
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='staff_accounts'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='staff_account_profiles'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_staff_accounts'
    )
    temp_password = models.CharField(
        max_length=255, blank=True,
        help_text='Hashed temporary password'
    )
    must_change_password = models.BooleanField(default=True)
    password_changed_at = models.DateTimeField(
        null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"StaffAccount: {self.user.full_name} @ "
            f"{self.business.name}"
        )


class WorkSchedule(TimeStampedModel):
    """
    Staff member's weekly work schedule.
    """
    DAY_CHOICES = (
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    )

    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='schedule'
    )
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    is_working = models.BooleanField(default=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    is_24_hours = models.BooleanField(default=False)

    class Meta:
        unique_together = ('member', 'day')
        ordering = ['day']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.day}"
        )


class StaffActivityLog(TimeStampedModel):
    """
    Audit log of all staff actions within a business.
    """
    ACTION_CHOICES = (
        ('login', 'Logged In'),
        ('logout', 'Logged Out'),
        ('view_booking', 'Viewed Booking'),
        ('create_booking', 'Created Booking'),
        ('cancel_booking', 'Cancelled Booking'),
        ('checkin_guest', 'Checked In Guest'),
        ('checkout_guest', 'Checked Out Guest'),
        ('view_order', 'Viewed Order'),
        ('update_order', 'Updated Order'),
        ('view_wallet', 'Viewed Wallet'),
        ('withdraw_funds', 'Withdrew Funds'),
        ('manage_product', 'Managed Product'),
        ('manage_staff', 'Managed Staff'),
        ('update_settings', 'Updated Settings'),
        ('other', 'Other'),
    )

    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='activity_logs'
    )
    action = models.CharField(
        max_length=30, choices=ACTION_CHOICES
    )
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    metadata = models.JSONField(default=dict)
    object_type = models.CharField(
        max_length=50, blank=True,
        help_text='e.g. Booking, Order, Customer'
    )
    object_id = models.IntegerField(
        null=True, blank=True
    )
    old_data = models.JSONField(
        default=dict, blank=True,
        help_text='State before the action'
    )
    new_data = models.JSONField(
        default=dict, blank=True,
        help_text='State after the action'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.action}"
        )

class Department(TimeStampedModel):
    """
    Department within a business.
    e.g. Front Desk, Kitchen, Housekeeping, Finance
    """
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='departments'
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head = models.ForeignKey(
        'BusinessMember',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='headed_departments'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('business', 'name')
        ordering = ['name']

    def __str__(self):
        return f"{self.business.name} — {self.name}"


class StaffShift(TimeStampedModel):
    """
    Specific shift assigned to a staff member.
    More granular than weekly schedule.
    """
    SHIFT_TYPE_CHOICES = (
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
        ('night', 'Night'),
        ('custom', 'Custom'),
    )
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('missed', 'Missed'),
        ('cancelled', 'Cancelled'),
    )

    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='shifts'
    )
    shift_type = models.CharField(
        max_length=20,
        choices=SHIFT_TYPE_CHOICES,
        default='morning'
    )
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['date', 'start_time']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.date} {self.shift_type}"
        )


class StaffAttendance(TimeStampedModel):
    """
    Daily attendance record for staff members.
    """
    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='attendance'
    )
    shift = models.ForeignKey(
        StaffShift,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='attendance'
    )
    date = models.DateField()
    clock_in = models.DateTimeField(null=True, blank=True)
    clock_out = models.DateTimeField(null=True, blank=True)
    is_late = models.BooleanField(default=False)
    late_minutes = models.IntegerField(default=0)
    overtime_minutes = models.IntegerField(default=0)
    clock_in_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    clock_in_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    clock_out_lat = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    clock_out_lng = models.DecimalField(
        max_digits=9, decimal_places=6,
        null=True, blank=True
    )
    clock_in_device = models.CharField(
        max_length=255, blank=True
    )
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('member', 'date')
        ordering = ['-date']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — {self.date}"
        )

    @property
    def hours_worked(self):
        if self.clock_in and self.clock_out:
            delta = self.clock_out - self.clock_in
            return round(delta.total_seconds() / 3600, 2)
        return 0


class StaffDevice(TimeStampedModel):
    """
    Trusted devices for staff members.
    Owner can revoke access per device.
    """
    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    device_name = models.CharField(max_length=255)
    browser = models.CharField(
        max_length=100, blank=True
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    device_fingerprint = models.CharField(
        max_length=64, blank=True
    )
    is_trusted = models.BooleanField(default=False)
    last_login = models.DateTimeField(
        null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_login']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.device_name}"
        )


class TemporaryPermission(TimeStampedModel):
    """
    Time-limited permission grant for a staff member.
    e.g. withdraw_funds for 24 hours.
    """
    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='temporary_permissions'
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name='temporary_grants'
    )
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='granted_temp_permissions'
    )
    reason = models.TextField(blank=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.permission.code} until {self.expires_at}"
        )

    def is_valid(self):
        from django.utils import timezone
        return (
            self.is_active
            and timezone.now() < self.expires_at
        )


class StaffNote(TimeStampedModel):
    """
    Manager/owner notes about a staff member.
    Never shown to the staff member.
    """
    NOTE_TYPE_CHOICES = (
        ('general', 'General'),
        ('performance', 'Performance'),
        ('disciplinary', 'Disciplinary'),
        ('commendation', 'Commendation'),
        ('training', 'Training Required'),
        ('promotion', 'Promotion Candidate'),
        ('warning', 'Warning'),
    )

    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='notes'
    )
    written_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='staff_notes_written'
    )
    note_type = models.CharField(
        max_length=20,
        choices=NOTE_TYPE_CHOICES,
        default='general'
    )
    content = models.TextField()
    is_private = models.BooleanField(
        default=True,
        help_text='Private notes only visible to owner/managers'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Note on {self.member.user.full_name} — "
            f"{self.note_type}"
        )


class StaffLeave(TimeStampedModel):
    """
    Leave/time-off requests from staff members.
    """
    LEAVE_TYPE_CHOICES = (
        ('vacation', 'Vacation'),
        ('sick', 'Sick Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('emergency', 'Emergency'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    member = models.ForeignKey(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.CharField(
        max_length=20,
        choices=LEAVE_TYPE_CHOICES
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_leave_requests'
    )
    reviewed_at = models.DateTimeField(
        null=True, blank=True
    )
    rejection_reason = models.TextField(
        blank=True, null=True
    )
    supporting_document = models.FileField(
        upload_to='staff_leave_docs/',
        null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.member.user.full_name} — "
            f"{self.leave_type} ({self.status})"
        )

    @property
    def days_requested(self):
        return (self.end_date - self.start_date).days + 1


class StaffPIN(TimeStampedModel):
    """
    Staff PIN for quick actions without full password.
    e.g. check-in guests, print invoices.
    """
    member = models.OneToOneField(
        BusinessMember,
        on_delete=models.CASCADE,
        related_name='pin'
    )
    pin_hash = models.CharField(max_length=128)
    pin_enabled = models.BooleanField(default=False)
    last_used = models.DateTimeField(null=True, blank=True)
    failed_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(
        null=True, blank=True
    )

    def __str__(self):
        return (
            f"PIN for {self.member.user.full_name}"
        )

    def verify_pin(self, raw_pin):
        from django.contrib.auth.hashers import check_password
        from django.utils import timezone
        if self.locked_until and (
            timezone.now() < self.locked_until
        ):
            return False, 'PIN locked. Try again later.'
        if check_password(raw_pin, self.pin_hash):
            self.failed_attempts = 0
            self.last_used = timezone.now()
            self.save()
            return True, 'OK'
        self.failed_attempts += 1
        if self.failed_attempts >= 5:
            from datetime import timedelta
            self.locked_until = (
                timezone.now() + timedelta(minutes=30)
            )
        self.save()
        return False, 'Invalid PIN'
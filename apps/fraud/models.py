from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class FraudRule(TimeStampedModel):
    """
    Configurable fraud detection rules.
    Admin can tune thresholds without code changes.
    """
    RULE_TYPE_CHOICES = (
        ('payment', 'Payment Fraud'),
        ('account', 'Account Fraud'),
        ('order', 'Order Fraud'),
    )
    ACTION_CHOICES = (
        ('log', 'Log Only'),
        ('flag', 'Flag for Review'),
        ('block', 'Auto Block'),
    )

    name = models.CharField(max_length=100)
    rule_type = models.CharField(
        max_length=20, choices=RULE_TYPE_CHOICES
    )
    description = models.TextField(blank=True)
    score = models.IntegerField(
        default=10,
        help_text='Risk score added when this rule triggers'
    )
    is_active = models.BooleanField(default=True)
    threshold = models.DecimalField(
        max_digits=12, decimal_places=2,
        null=True, blank=True,
        help_text='Numeric threshold for this rule (amount, count, etc)'
    )
    time_window_minutes = models.IntegerField(
        default=60,
        help_text='Time window to check for this rule in minutes'
    )

    class Meta:
        ordering = ['rule_type', 'name']

    def __str__(self):
        return f"{self.rule_type} — {self.name} ({self.score}pts)"


class BlockedEntity(TimeStampedModel):
    """
    Blocked IPs, emails, phone numbers, or users.
    """
    ENTITY_TYPE_CHOICES = (
        ('ip', 'IP Address'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('user', 'User Account'),
        ('device', 'Device ID'),
    )

    entity_type = models.CharField(
        max_length=20, choices=ENTITY_TYPE_CHOICES
    )
    value = models.CharField(
        max_length=255,
        help_text='The blocked value (IP, email, phone, user_id)'
    )
    reason = models.TextField()
    is_active = models.BooleanField(default=True)
    blocked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='blocked_entities'
    )
    auto_blocked = models.BooleanField(
        default=False,
        help_text='True if system auto-blocked, False if admin manually blocked'
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Leave null for permanent block'
    )

    class Meta:
        unique_together = ('entity_type', 'value')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entity_type}: {self.value}"

    def is_valid(self):
        """Check if block is still active and not expired."""
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class FraudAlert(TimeStampedModel):
    """
    Individual fraud signal detected by the system.
    """
    RISK_LEVEL_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('reviewed', 'Reviewed'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    )
    ALERT_TYPE_CHOICES = (
        ('payment', 'Payment Fraud'),
        ('account', 'Account Fraud'),
        ('order', 'Order Fraud'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fraud_alerts'
    )
    alert_type = models.CharField(
        max_length=20, choices=ALERT_TYPE_CHOICES
    )
    risk_level = models.CharField(
        max_length=20, choices=RISK_LEVEL_CHOICES
    )
    risk_score = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='open'
    )
    title = models.CharField(max_length=255)
    description = models.TextField()
    triggered_rules = models.JSONField(
        default=list,
        help_text='List of rule names that triggered this alert'
    )
    metadata = models.JSONField(
        default=dict,
        help_text='Extra context (IP, order_id, amount, etc)'
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    auto_blocked = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_alerts'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.risk_level.upper()} — {self.title}"


class FraudCase(TimeStampedModel):
    """
    Groups related FraudAlerts into a case for admin investigation.
    """
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )

    reference = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fraud_cases'
    )
    alerts = models.ManyToManyField(
        FraudAlert,
        related_name='cases',
        blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='open'
    )
    total_risk_score = models.IntegerField(default=0)
    summary = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_cases'
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_cases'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Case {self.reference} — {self.status}"


class FraudScore(TimeStampedModel):
    """
    Tracks fraud scores both per-event and as a running
    cumulative total per user.
    """
    EVENT_TYPE_CHOICES = (
        ('payment', 'Payment'),
        ('order', 'Order'),
        ('login', 'Login'),
        ('withdrawal', 'Withdrawal'),
        ('signup', 'Signup'),
        ('booking', 'Booking'),
    )

    # Per-event score
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='fraud_scores'
    )
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES
    )
    event_score = models.IntegerField(
        default=0,
        help_text='Score for this specific event'
    )
    triggered_rules = models.JSONField(default=list)
    event_reference = models.CharField(
        max_length=100, blank=True,
        help_text='Order/payment/booking reference'
    )
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )

    # Running user total
    cumulative_score = models.IntegerField(
        default=0,
        help_text='Running total score for this user'
    )
    risk_level = models.CharField(
        max_length=20,
        choices=FraudAlert.RISK_LEVEL_CHOICES,
        default='low'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.user.email} — {self.event_type} "
            f"({self.event_score}pts)"
        )

    def save(self, *args, **kwargs):
        from .utils import get_risk_level
        self.risk_level = get_risk_level(self.cumulative_score)
        super().save(*args, **kwargs)


class FraudEvent(TimeStampedModel):
    """
    Raw fraud events — every suspicious action is logged here
    before being scored and potentially escalated to a FraudAlert.
    """
    EVENT_TYPE_CHOICES = (
        ('login_failed', 'Failed Login'),
        ('login_success', 'Successful Login'),
        ('password_reset', 'Password Reset'),
        ('payment_attempt', 'Payment Attempt'),
        ('payment_failed', 'Payment Failed'),
        ('order_placed', 'Order Placed'),
        ('order_cancelled', 'Order Cancelled'),
        ('refund_requested', 'Refund Requested'),
        ('withdrawal_requested', 'Withdrawal Requested'),
        ('address_changed', 'Address Changed'),
        ('phone_changed', 'Phone Changed'),
        ('email_changed', 'Email Changed'),
        ('new_device', 'New Device Detected'),
        ('suspicious_ip', 'Suspicious IP'),
        ('chargeback', 'Chargeback Filed'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fraud_events'
    )
    event_type = models.CharField(
        max_length=30, choices=EVENT_TYPE_CHOICES
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    user_agent = models.TextField(blank=True, null=True)
    metadata = models.JSONField(
        default=dict,
        help_text='Extra context for this event'
    )
    risk_score_added = models.IntegerField(default=0)
    alert = models.ForeignKey(
        FraudAlert,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='events'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.event_type} — "
            f"{self.user.email if self.user else 'anonymous'}"
        )


class DeviceFingerprint(TimeStampedModel):
    """
    Full device fingerprint per user session.
    New device = flag for anomaly detection.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='device_fingerprints'
    )
    fingerprint_hash = models.CharField(
        max_length=64,
        help_text='SHA256 hash of combined device attributes'
    )
    # Device details
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    user_agent = models.TextField(blank=True, null=True)
    browser = models.CharField(
        max_length=100, blank=True, null=True
    )
    os = models.CharField(
        max_length=100, blank=True, null=True
    )
    device_type = models.CharField(
        max_length=50, blank=True, null=True,
        help_text='mobile, tablet, desktop'
    )
    screen_resolution = models.CharField(
        max_length=20, blank=True, null=True
    )
    timezone = models.CharField(
        max_length=50, blank=True, null=True
    )
    language = models.CharField(
        max_length=20, blank=True, null=True
    )
    country = models.CharField(
        max_length=100, blank=True, null=True
    )
    city = models.CharField(
        max_length=100, blank=True, null=True
    )
    # Trust status
    is_trusted = models.BooleanField(
        default=False,
        help_text='Admin or user marked this device as trusted'
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text='System flagged this device as suspicious'
    )
    first_seen = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(auto_now=True)
    seen_count = models.IntegerField(default=1)
    flagged_reason = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('user', 'fingerprint_hash')
        ordering = ['-last_seen']

    def __str__(self):
        return (
            f"{self.user.email} — {self.browser} "
            f"on {self.os} ({self.ip_address})"
        )


class FraudActionLog(TimeStampedModel):
    """
    Audit log of all fraud-related actions — both system
    auto-actions and admin manual actions.
    """
    ACTION_TYPE_CHOICES = (
        # System actions
        ('auto_block_user', 'Auto Blocked User'),
        ('auto_flag_alert', 'Auto Flagged Alert'),
        ('score_updated', 'Score Updated'),
        ('event_logged', 'Event Logged'),
        # Admin actions
        ('manual_block', 'Manual Block'),
        ('manual_unblock', 'Manual Unblock'),
        ('alert_reviewed', 'Alert Reviewed'),
        ('alert_resolved', 'Alert Resolved'),
        ('false_positive', 'Marked False Positive'),
        ('score_override', 'Score Overridden'),
        ('whitelist_added', 'Added to Whitelist'),
        ('blacklist_added', 'Added to Blacklist'),
        ('chargeback_filed', 'Chargeback Filed'),
        ('chargeback_resolved', 'Chargeback Resolved'),
    )

    action_type = models.CharField(
        max_length=30, choices=ACTION_TYPE_CHOICES
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fraud_actions_performed',
        help_text='Null if system auto-action'
    )
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='fraud_actions_received'
    )
    alert = models.ForeignKey(
        FraudAlert,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='action_logs'
    )
    is_system_action = models.BooleanField(
        default=False,
        help_text='True if performed automatically by the system'
    )
    reason = models.TextField()
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        actor = (
            self.performed_by.email
            if self.performed_by else 'System'
        )
        return f"{actor} — {self.action_type}"


class Chargeback(TimeStampedModel):
    """
    Tracks both customer disputes and gateway chargebacks.
    """
    TYPE_CHOICES = (
        ('customer_dispute', 'Customer Dispute'),
        ('gateway_chargeback', 'Gateway Chargeback'),
    )
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('under_review', 'Under Review'),
        ('won', 'Won'),
        ('lost', 'Lost'),
        ('resolved', 'Resolved'),
        ('cancelled', 'Cancelled'),
    )
    REASON_CHOICES = (
        ('not_received', 'Item Not Received'),
        ('not_as_described', 'Not As Described'),
        ('unauthorized', 'Unauthorized Transaction'),
        ('duplicate', 'Duplicate Charge'),
        ('fraud', 'Fraud'),
        ('other', 'Other'),
    )

    reference = models.CharField(max_length=100, unique=True)
    chargeback_type = models.CharField(
        max_length=30, choices=TYPE_CHOICES
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='open'
    )
    reason = models.CharField(
        max_length=30, choices=REASON_CHOICES
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chargebacks'
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chargebacks'
    )
    payment_reference = models.CharField(
        max_length=100, blank=True
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2
    )
    currency = models.CharField(max_length=5, default='NGN')
    description = models.TextField()
    evidence = models.JSONField(
        default=list,
        help_text='List of evidence URLs or descriptions'
    )
    gateway = models.CharField(
        max_length=20, blank=True,
        help_text='paystack, flutterwave, etc'
    )
    gateway_chargeback_id = models.CharField(
        max_length=100, blank=True,
        help_text='ID from the payment gateway'
    )
    filed_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_chargebacks'
    )
    resolution_notes = models.TextField(blank=True, null=True)
    alert = models.ForeignKey(
        FraudAlert,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='chargebacks'
    )

    class Meta:
        ordering = ['-filed_at']

    def __str__(self):
        return f"Chargeback {self.reference} — {self.status}"


class BlacklistHistory(TimeStampedModel):
    """
    Full history of blacklist/blocklist changes.
    Tracks who was blocked, when, why, and who unblocked them.
    """
    entity = models.ForeignKey(
        BlockedEntity,
        on_delete=models.CASCADE,
        related_name='history'
    )
    ACTION_CHOICES = (
        ('blocked', 'Blocked'),
        ('unblocked', 'Unblocked'),
        ('extended', 'Block Extended'),
        ('reason_updated', 'Reason Updated'),
    )
    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='blacklist_actions'
    )
    is_system_action = models.BooleanField(default=False)
    reason = models.TextField()
    previous_state = models.JSONField(
        default=dict,
        help_text='State of the entity before this action'
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.action} — {self.entity.entity_type}: "
            f"{self.entity.value}"
        )


class RuleCondition(TimeStampedModel):
    """
    Conditions attached to a FraudRule.
    Multiple conditions per rule, joined by AND/OR logic.
    """
    OPERATOR_CHOICES = (
        ('gt', 'Greater Than'),
        ('gte', 'Greater Than or Equal'),
        ('lt', 'Less Than'),
        ('lte', 'Less Than or Equal'),
        ('eq', 'Equal To'),
        ('neq', 'Not Equal To'),
        ('contains', 'Contains'),
        ('not_contains', 'Does Not Contain'),
        ('in', 'In List'),
        ('not_in', 'Not In List'),
    )
    JOIN_CHOICES = (
        ('AND', 'AND'),
        ('OR', 'OR'),
    )

    rule = models.ForeignKey(
        FraudRule,
        on_delete=models.CASCADE,
        related_name='conditions'
    )
    field = models.CharField(
        max_length=100,
        help_text='Field to check e.g. amount, user.age_days, order_count'
    )
    operator = models.CharField(
        max_length=20, choices=OPERATOR_CHOICES
    )
    value = models.CharField(
        max_length=255,
        help_text='Value to compare against'
    )
    join_with_next = models.CharField(
        max_length=3,
        choices=JOIN_CHOICES,
        default='AND',
        help_text='How this condition joins with the next one'
    )
    order = models.IntegerField(
        default=0,
        help_text='Evaluation order (lower = first)'
    )

    class Meta:
        ordering = ['order']

    def __str__(self):
        return (
            f"{self.rule.name}: {self.field} "
            f"{self.operator} {self.value}"
        )


class Whitelist(TimeStampedModel):
    """
    Trusted entities that bypass fraud checks entirely.
    """
    ENTITY_TYPE_CHOICES = (
        ('ip', 'IP Address'),
        ('email', 'Email'),
        ('phone', 'Phone Number'),
        ('user', 'User Account'),
        ('device', 'Device Fingerprint'),
    )

    entity_type = models.CharField(
        max_length=20, choices=ENTITY_TYPE_CHOICES
    )
    value = models.CharField(max_length=255)
    reason = models.TextField()
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='whitelist_entries'
    )
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text='Leave null for permanent whitelist'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('entity_type', 'value')
        ordering = ['-created_at']

    def __str__(self):
        return f"Whitelist: {self.entity_type} — {self.value}"

    def is_valid(self):
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True


class VelocityTracking(TimeStampedModel):
    """
    Tracks event velocity per user (how many times something
    happens in a given time window).
    Used for rate-limiting and fraud detection.
    """
    EVENT_TYPE_CHOICES = (
        ('login', 'Login'),
        ('payment', 'Payment'),
        ('order', 'Order'),
        ('refund', 'Refund'),
        ('withdrawal', 'Withdrawal'),
        ('otp_request', 'OTP Request'),
        ('address_change', 'Address Change'),
        ('booking', 'Booking'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='velocity_tracking'
    )
    event_type = models.CharField(
        max_length=30, choices=EVENT_TYPE_CHOICES
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    # Counters per time window
    count_1min = models.IntegerField(default=0)
    count_5min = models.IntegerField(default=0)
    count_15min = models.IntegerField(default=0)
    count_1hour = models.IntegerField(default=0)
    count_24hour = models.IntegerField(default=0)
    count_7days = models.IntegerField(default=0)

    last_event_at = models.DateTimeField(auto_now=True)
    window_reset_at = models.DateTimeField(
        null=True, blank=True,
        help_text='When the counters were last reset'
    )
    is_throttled = models.BooleanField(
        default=False,
        help_text='True if this user is being rate-limited'
    )
    throttled_until = models.DateTimeField(
        null=True, blank=True
    )

    class Meta:
        unique_together = ('user', 'event_type')
        ordering = ['-last_event_at']

    def __str__(self):
        return (
            f"{self.user.email} — {self.event_type} "
            f"(1hr: {self.count_1hour})"
        )

    def increment(self, ip_address=None):
        """
        Increment all counters and check if user
        should be throttled.
        """
        from django.utils import timezone
        from datetime import timedelta

        now = timezone.now()

        # Reset counters if window has expired
        if (
            not self.window_reset_at
            or now - self.window_reset_at > timedelta(days=7)
        ):
            self.count_1min = 0
            self.count_5min = 0
            self.count_15min = 0
            self.count_1hour = 0
            self.count_24hour = 0
            self.count_7days = 0
            self.window_reset_at = now

        self.count_1min += 1
        self.count_5min += 1
        self.count_15min += 1
        self.count_1hour += 1
        self.count_24hour += 1
        self.count_7days += 1

        if ip_address:
            self.ip_address = ip_address

        self.save()
        return self
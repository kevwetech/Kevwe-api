from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel


class KYCConfiguration(TimeStampedModel):
    """
    Platform-wide KYC settings configurable by admin.
    No code changes needed to adjust KYC behavior.
    """
    name = models.CharField(
        max_length=100, default='default'
    )
    max_retry_count = models.PositiveIntegerField(default=3)
    auto_approve_threshold = models.DecimalField(
        max_digits=5, decimal_places=2, default=90.00,
        help_text='Confidence score above which KYC is auto-approved'
    )
    manual_review_threshold = models.DecimalField(
        max_digits=5, decimal_places=2, default=65.00,
        help_text='Score below this triggers manual review'
    )
    kyc_expiry_days = models.PositiveIntegerField(
        default=365,
        help_text='Days before KYC expires (0 = never)'
    )
    supported_countries = models.JSONField(
        default=list,
        help_text='ISO country codes supported e.g. ["NG", "GH"]'
    )
    require_selfie = models.BooleanField(default=True)
    require_id_document = models.BooleanField(default=True)
    require_address = models.BooleanField(default=False)
    require_business_docs = models.BooleanField(default=False)
    kyc_version = models.CharField(
        max_length=20, default='v1'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"KYC Config {self.name} ({self.kyc_version})"

    @classmethod
    def get_active(cls):
        return cls.objects.filter(is_active=True).first()


class KYCRequirement(TimeStampedModel):
    """
    Defines what documents are required per use case.
    Configurable per industry/role without code changes.
    """
    USE_CASE_CHOICES = (
        ('booking', 'Booking'),
        ('vendor', 'Vendor'),
        ('driver', 'Driver'),
        ('general', 'General'),
    )

    use_case = models.CharField(
        max_length=20, choices=USE_CASE_CHOICES,
        unique=True
    )
    required_documents = models.JSONField(
        default=list,
        help_text=(
            'List of required document types '
            'e.g. ["nin", "selfie", "utility_bill"]'
        )
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['use_case']

    def __str__(self):
        return f"KYC Requirements for {self.use_case}"


class KYCProfile(TimeStampedModel):
    """
    One KYC profile per user per use case.
    Tracks overall verification status.
    """
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('pending', 'Pending Review'),
        ('auto_approved', 'Auto Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    )
    USE_CASE_CHOICES = (
        ('booking', 'Booking Verification'),
        ('vendor', 'Vendor Onboarding'),
        ('driver', 'Driver Verification'),
        ('general', 'General'),
    )
    VERIFICATION_METHOD_CHOICES = (
        ('sumsub', 'Sumsub'),
        ('manual', 'Manual'),
        ('government_api', 'Government API'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='kyc_profiles'
    )
    use_case = models.CharField(
        max_length=20, choices=USE_CASE_CHOICES,
        default='booking'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='not_started'
    )
    verification_method = models.CharField(
        max_length=20,
        choices=VERIFICATION_METHOD_CHOICES,
        default='sumsub'
    )
    retry_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        null=True, blank=True,
        help_text='Verification confidence percentage from Sumsub'
    )
    kyc_version = models.CharField(
        max_length=20, default='v1'
    )

    # Sumsub integration
    sumsub_applicant_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    sumsub_inspection_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    sumsub_correlation_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    sumsub_review_result = models.JSONField(
        default=dict, blank=True
    )
    last_webhook = models.JSONField(
        default=dict, blank=True,
        help_text='Last raw webhook payload from Sumsub'
    )

    # Verified identity fields (trusted source of truth)
    verified_first_name = models.CharField(
        max_length=100, blank=True, null=True
    )
    verified_last_name = models.CharField(
        max_length=100, blank=True, null=True
    )
    verified_dob = models.DateField(null=True, blank=True)
    verified_gender = models.CharField(
        max_length=20, blank=True, null=True
    )
    verified_address = models.TextField(blank=True, null=True)
    verified_nationality = models.CharField(
        max_length=100, blank=True, null=True
    )

    # Review details
    rejection_reason = models.TextField(blank=True, null=True)
    rejection_labels = models.JSONField(default=list, blank=True)
    internal_notes = models.TextField(
        blank=True, null=True,
        help_text='Admin-only notes, never shown to customer'
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kyc_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    risk_level = models.CharField(
        max_length=20, blank=True, null=True
    )
    country = models.CharField(
        max_length=100, blank=True, null=True
    )

    # Timeline
    submitted_at = models.DateTimeField(null=True, blank=True)
    processing_started_at = models.DateTimeField(
        null=True, blank=True
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'use_case')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['use_case']),
        ]

    def __str__(self):
        return (
            f"{self.user.email} — {self.use_case} "
            f"({self.status})"
        )

    @property
    def is_verified(self):
        return self.status in ('approved', 'auto_approved')

    @property
    def is_pending(self):
        return self.status == 'pending'


class KYCSession(TimeStampedModel):
    """
    Tracks each verification attempt/session.
    One profile can have many sessions (retries, re-verifications).
    """
    STATUS_CHOICES = (
        ('started', 'Started'),
        ('documents_uploaded', 'Documents Uploaded'),
        ('selfie_uploaded', 'Selfie Uploaded'),
        ('submitted', 'Submitted for Review'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    )

    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES,
        default='started'
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    device = models.CharField(
        max_length=255, blank=True
    )
    browser = models.CharField(
        max_length=100, blank=True
    )
    user_agent = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    sumsub_sdk_token = models.CharField(
        max_length=500, blank=True, null=True
    )
    failure_reason = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"session {self.id} ({self.status})"
        )


class KYCDocument(TimeStampedModel):
    """
    ID documents submitted for KYC verification.
    """
    DOCUMENT_TYPE_CHOICES = (
        ('nin', 'National ID (NIN)'),
        ('passport', 'International Passport'),
        ('drivers_license', "Driver's License"),
        ('voters_card', "Voter's Card"),
        ('bvn', 'BVN'),
        ('utility_bill', 'Utility Bill'),
        ('bank_statement', 'Bank Statement'),
        ('cac', 'CAC Certificate'),
        ('tin', 'TIN Certificate'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30, choices=DOCUMENT_TYPE_CHOICES
    )
    document_number = models.CharField(
        max_length=100, blank=True, null=True
    )
    file = models.FileField(
        upload_to='kyc_documents/',
        null=True, blank=True,
        help_text='Supports images and PDFs'
    )
    sumsub_document_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    verification_notes = models.TextField(blank=True)

    # Extracted data
    extracted_name = models.CharField(
        max_length=255, blank=True, null=True
    )
    extracted_dob = models.DateField(null=True, blank=True)
    extracted_expiry = models.DateField(null=True, blank=True)
    country_of_issue = models.CharField(
        max_length=100, blank=True, null=True
    )

    class Meta:
        ordering = ['-created_at']
        unique_together = ('kyc_profile', 'document_type')
        indexes = [
            models.Index(fields=['document_type']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"{self.document_type} ({self.status})"
        )


class KYCSelfie(TimeStampedModel):
    """
    Selfie/liveness check for face matching against ID.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='selfies'
    )
    file = models.ImageField(upload_to='kyc_selfies/')
    sumsub_selfie_id = models.CharField(
        max_length=100, blank=True, null=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    liveness_score = models.FloatField(null=True, blank=True)
    face_match_score = models.FloatField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    captured_at = models.DateTimeField(null=True, blank=True)
    device = models.CharField(
        max_length=255, blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"selfie ({self.status})"
        )


class KYCMatch(TimeStampedModel):
    """
    Stores face match result between selfie and ID document.
    Separate from KYCSelfie for cleaner data.
    """
    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='matches'
    )
    document = models.ForeignKey(
        KYCDocument,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='matches'
    )
    selfie = models.ForeignKey(
        KYCSelfie,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='matches'
    )
    score = models.FloatField(
        help_text='Face match confidence score 0-100'
    )
    passed = models.BooleanField(default=False)
    method = models.CharField(
        max_length=50, default='sumsub',
        help_text='Which service performed the match'
    )
    raw_result = models.JSONField(default=dict)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"match score: {self.score} "
            f"({'passed' if self.passed else 'failed'})"
        )


class KYCIdentity(TimeStampedModel):
    """
    Hashed identity store to detect duplicate identities
    across multiple accounts.
    One NIN/passport → many accounts = fraud.
    """
    DOCUMENT_TYPE_CHOICES = KYCDocument.DOCUMENT_TYPE_CHOICES

    document_type = models.CharField(
        max_length=30, choices=DOCUMENT_TYPE_CHOICES
    )
    document_hash = models.CharField(
        max_length=64, unique=True,
        help_text='SHA256 hash of document number'
    )
    document_number_masked = models.CharField(
        max_length=50, blank=True,
        help_text='Last 4 digits only e.g. ****1234'
    )
    country = models.CharField(max_length=100, blank=True)
    verified = models.BooleanField(default=False)
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='kyc_identities',
        blank=True
    )
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-first_seen_at']

    def __str__(self):
        return (
            f"{self.document_type} — "
            f"{self.document_number_masked} "
            f"({self.users.count()} accounts)"
        )

    @property
    def is_duplicate(self):
        return self.users.count() > 1

    @classmethod
    def hash_document(cls, document_number):
        import hashlib
        return hashlib.sha256(
            document_number.strip().upper().encode()
        ).hexdigest()

    @classmethod
    def check_and_register(cls, document_type, document_number, user):
        """
        Hash and register a document number.
        Returns (identity, is_duplicate).
        """
        doc_hash = cls.hash_document(document_number)
        masked = (
            '*' * (len(document_number) - 4)
            + document_number[-4:]
        )

        identity, created = cls.objects.get_or_create(
            document_hash=doc_hash,
            defaults={
                'document_type': document_type,
                'document_number_masked': masked,
            }
        )
        identity.users.add(user)
        identity.save()

        return identity, identity.is_duplicate


class KYCAddress(TimeStampedModel):
    """
    Address verification for KYC.
    Some jurisdictions require address proof separately.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    kyc_profile = models.OneToOneField(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='address'
    )
    street = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    postal_code = models.CharField(
        max_length=20, blank=True
    )
    proof_document = models.FileField(
        upload_to='kyc_address_proofs/',
        null=True, blank=True
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"{self.city}, {self.country}"
        )


class KYCWatchlist(TimeStampedModel):
    """
    PEP, sanctions, AML, terrorist watchlist screening results.
    """
    TYPE_CHOICES = (
        ('pep', 'Politically Exposed Person'),
        ('sanction', 'Sanctions List'),
        ('aml', 'AML Watchlist'),
        ('terrorist', 'Terrorist List'),
        ('adverse_media', 'Adverse Media'),
    )
    STATUS_CHOICES = (
        ('clear', 'Clear'),
        ('potential_match', 'Potential Match'),
        ('confirmed_match', 'Confirmed Match'),
        ('false_positive', 'False Positive'),
    )

    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='watchlist_checks'
    )
    watchlist_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='clear'
    )
    matched = models.BooleanField(default=False)
    confidence = models.FloatField(
        null=True, blank=True,
        help_text='Match confidence score 0-100'
    )
    source = models.CharField(
        max_length=100, blank=True,
        help_text='Which watchlist source e.g. UN, OFAC, EU'
    )
    match_details = models.JSONField(default=dict)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='watchlist_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"{self.watchlist_type}: {self.status}"
        )


class KYCConsent(TimeStampedModel):
    """
    Records that the user explicitly consented to KYC verification.
    Required for privacy and regulatory compliance.
    """
    kyc_profile = models.OneToOneField(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='consent'
    )
    accepted = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    user_agent = models.TextField(blank=True, null=True)
    consent_version = models.CharField(
        max_length=20, default='v1',
        help_text='Version of consent terms accepted'
    )
    accepted_at = models.DateTimeField(null=True, blank=True)
    consent_text = models.TextField(
        blank=True,
        help_text='Exact text the user agreed to'
    )

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"consent {'accepted' if self.accepted else 'pending'}"
        )


class KYCWebhook(TimeStampedModel):
    """
    Stores all incoming Sumsub webhook payloads.
    Makes debugging easy — nothing is ever lost.
    """
    SOURCE_CHOICES = (
        ('sumsub', 'Sumsub'),
        ('manual', 'Manual'),
    )

    source = models.CharField(
        max_length=20, choices=SOURCE_CHOICES,
        default='sumsub'
    )
    event_type = models.CharField(max_length=100, blank=True)
    applicant_id = models.CharField(
        max_length=100, blank=True
    )
    payload = models.JSONField(default=dict)
    signature = models.CharField(
        max_length=255, blank=True
    )
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(
        blank=True, null=True
    )
    received_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='webhooks'
    )

    class Meta:
        ordering = ['-received_at']

    def __str__(self):
        return (
            f"{self.source} webhook — "
            f"{self.event_type} "
            f"({'processed' if self.processed else 'pending'})"
        )


class BusinessKYC(TimeStampedModel):
    """
    Business/company-level KYC verification.
    Completely separate from personal KYC.
    For vendors, hotels, logistics companies.
    """
    STATUS_CHOICES = (
        ('not_started', 'Not Started'),
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    )

    business = models.OneToOneField(
        'marketplace.Business',
        on_delete=models.CASCADE,
        related_name='business_kyc'
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='business_kyc_submissions'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='not_started'
    )
    rejection_reason = models.TextField(blank=True, null=True)
    internal_notes = models.TextField(blank=True, null=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='business_kyc_reviews'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    sumsub_company_id = models.CharField(
        max_length=100, blank=True, null=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.business.name} — "
            f"Business KYC ({self.status})"
        )

    @property
    def is_verified(self):
        return self.status == 'approved'


class BusinessKYCDocument(TimeStampedModel):
    """
    Business-specific documents for company KYC.
    Kept completely separate from personal ID documents.
    """
    DOCUMENT_TYPE_CHOICES = (
        ('cac_certificate', 'CAC Certificate'),
        ('cac_status_report', 'CAC Status Report'),
        ('tin_certificate', 'TIN Certificate'),
        ('tax_clearance', 'Tax Clearance Certificate'),
        ('business_license', 'Business License'),
        ('memorandum', 'Memorandum of Association'),
        ('proof_of_address', 'Proof of Business Address'),
        ('bank_statement', 'Business Bank Statement'),
        ('director_id', 'Director ID'),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    business_kyc = models.ForeignKey(
        BusinessKYC,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=30, choices=DOCUMENT_TYPE_CHOICES
    )
    file = models.FileField(
        upload_to='business_kyc_documents/'
    )
    document_number = models.CharField(
        max_length=100, blank=True, null=True,
        help_text='CAC reg number, TIN number, etc.'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending'
    )
    verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    expiry_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('business_kyc', 'document_type')

    def __str__(self):
        return (
            f"{self.business_kyc.business.name} — "
            f"{self.document_type} ({self.status})"
        )


class KYCDuplicateIdentity(TimeStampedModel):
    """
    Flags when the same identity document is used
    across multiple accounts.
    Triggers fraud investigation automatically.
    """
    STATUS_CHOICES = (
        ('open', 'Open'),
        ('investigating', 'Investigating'),
        ('resolved', 'Resolved'),
        ('false_positive', 'False Positive'),
    )

    identity = models.ForeignKey(
        KYCIdentity,
        on_delete=models.CASCADE,
        related_name='duplicates'
    )
    users = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='duplicate_identity_flags'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='open'
    )
    confidence = models.FloatField(default=100.0)
    fraud_alert = models.ForeignKey(
        'fraud.FraudAlert',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='duplicate_identities'
    )
    notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='resolved_duplicates'
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"Duplicate: {self.identity.document_type} — "
            f"{self.users.count()} accounts"
        )


class KYCReviewLog(TimeStampedModel):
    """
    Audit log of all KYC review actions.
    """
    ACTION_CHOICES = (
        ('submitted', 'Submitted'),
        ('auto_approved', 'Auto Approved'),
        ('auto_rejected', 'Auto Rejected'),
        ('manual_approved', 'Manually Approved'),
        ('manual_rejected', 'Manually Rejected'),
        ('resubmitted', 'Resubmitted'),
        ('expired', 'Expired'),
        ('webhook_received', 'Webhook Received'),
        ('consent_given', 'Consent Given'),
        ('duplicate_detected', 'Duplicate Detected'),
        ('watchlist_flagged', 'Watchlist Flagged'),
    )

    kyc_profile = models.ForeignKey(
        KYCProfile,
        on_delete=models.CASCADE,
        related_name='review_logs'
    )
    action = models.CharField(
        max_length=30, choices=ACTION_CHOICES
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='kyc_actions'
    )
    is_system_action = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    metadata = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(
        null=True, blank=True
    )
    user_agent = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return (
            f"{self.kyc_profile.user.email} — "
            f"{self.action}"
        )
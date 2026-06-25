from django.db import models
from django.conf import settings
from apps.common.models import TimeStampedModel
from django.utils import timezone


class Branch(TimeStampedModel):
    """
    Physical branch/office location
    Can be HQ, regional office, warehouse etc
    """
    BRANCH_TYPE_CHOICES = (
        ('hq', 'Headquarters'),
        ('regional', 'Regional Office'),
        ('warehouse', 'Warehouse'),
        ('pickup_point', 'Pickup Point'),
        ('delivery_hub', 'Delivery Hub'),
    )

    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Under Maintenance'),
    )
    business = models.ForeignKey(
        'marketplace.Business',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='branches'
    )

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=20, unique=True)
    branch_type = models.CharField(
        max_length=20,
        choices=BRANCH_TYPE_CHOICES,
        default='regional'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Manager
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_branches'
    )

    # Contact
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    alternate_phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    # Location
    address = models.TextField()
    country = models.ForeignKey(
        'locations.Country',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches'
    )
    state = models.ForeignKey(
        'locations.State',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches'
    )
    city = models.ForeignKey(
        'locations.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches'
    )
    zone = models.ForeignKey(
        'locations.Zone',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='branches'
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    # Operations
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    working_days = models.JSONField(
        default=list,
        blank=True
    )  # ['monday', 'tuesday', ...]

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Branches'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Territory(TimeStampedModel):
    """
    Service territory covered by a branch
    Defines which areas a branch serves
    """
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='territories'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    # Coverage
    countries = models.ManyToManyField(
        'locations.Country',
        blank=True,
        related_name='territories'
    )
    states = models.ManyToManyField(
        'locations.State',
        blank=True,
        related_name='territories'
    )
    cities = models.ManyToManyField(
        'locations.City',
        blank=True,
        related_name='territories'
    )
    zones = models.ManyToManyField(
        'locations.Zone',
        blank=True,
        related_name='territories'
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Territories'

    def __str__(self):
        return f"{self.name} - {self.branch.name}"


class Fleet(TimeStampedModel):
    """
    Fleet belonging to a branch
    Groups vehicles together
    """
    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='fleets'
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.branch.name}"

    @property
    def total_vehicles(self):
        return self.vehicles.count()

    @property
    def available_vehicles(self):
        return self.vehicles.filter(
            status='available'
        ).count()


class FleetVehicle(TimeStampedModel):
    """
    Individual vehicle in a fleet
    """
    STATUS_CHOICES = (
        ('available', 'Available'),
        ('on_trip', 'On Trip'),
        ('maintenance', 'Under Maintenance'),
        ('inactive', 'Inactive'),
    )

    fleet = models.ForeignKey(
        Fleet,
        on_delete=models.CASCADE,
        related_name='vehicles'
    )
    vehicle_type = models.ForeignKey(
        'drivers.VehicleType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fleet_vehicles'
    )

    # Assigned driver
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fleet_vehicle'
    )

    # Vehicle details
    plate_number = models.CharField(max_length=20, unique=True)
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    color = models.CharField(max_length=50)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )

    # Current location
    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    last_location_update = models.DateTimeField(
        null=True,
        blank=True
    )
    # Documents
    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    insurance_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    insurance_expiry = models.DateField(
        null=True,
        blank=True
    )
    license_expiry = models.DateField(
        null=True,
        blank=True
    )
    registration_expiry = models.DateField(
        null=True,
        blank=True
    )

    # Maintenance
    last_service_date = models.DateField(null=True, blank=True)
    next_service_date = models.DateField(null=True, blank=True)
    mileage = models.IntegerField(default=0)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['plate_number']

    def __str__(self):
        return f"{self.plate_number} - {self.brand} {self.model}"


class Dispatch(TimeStampedModel):
    """
    Dispatch assignment - links driver/vehicle
    to a delivery or shipment
    """
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('en_route_pickup', 'En Route to Pickup'),
        ('at_pickup', 'At Pickup'),
        ('picked_up', 'Picked Up'),
        ('en_route_delivery', 'En Route to Delivery'),
        ('at_delivery', 'At Delivery'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('returned', 'Returned'),
    )

    DISPATCH_TYPE_CHOICES = (
        ('delivery', 'Delivery'),
        ('shipment', 'Shipment'),
        ('ride', 'Ride'),
        ('custom', 'Custom'),
    )

    # Branch & Fleet
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )
    fleet = models.ForeignKey(
        Fleet,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )
    fleet_vehicle = models.ForeignKey(
        FleetVehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )

    # Driver
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )

    # What is being dispatched
    dispatch_type = models.CharField(
        max_length=20,
        choices=DISPATCH_TYPE_CHOICES,
        default='delivery'
    )
    delivery = models.ForeignKey(
        'deliveries.DeliveryRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )
    shipment = models.ForeignKey(
        'shipments.Shipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dispatches'
    )

    # Reference
    reference = models.CharField(max_length=100, unique=True)

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Timestamps
    assigned_at = models.DateTimeField(null=True, blank=True)
    picked_up_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    # Location tracking
    current_lat = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )
    current_lng = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)
    priority = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Dispatch {self.reference}"


class FuelType(TimeStampedModel):
    """Types of fuel"""
    name = models.CharField(max_length=50, unique=True)  # Petrol, Diesel, Gas, Electric
    unit = models.CharField(max_length=20, default='litres')
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class FuelRecord(TimeStampedModel):
    """Track fuel consumption per vehicle"""
    FUEL_TYPE_CHOICES = (
        ('refuel', 'Refuel'),
        ('consumption', 'Consumption'),
    )

    fleet_vehicle = models.ForeignKey(
        FleetVehicle,
        on_delete=models.CASCADE,
        related_name='fuel_records'
    )
    driver = models.ForeignKey(
        'drivers.DriverProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fuel_records'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fuel_records'
    )
    fuel_type = models.ForeignKey(
        FuelType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='fuel_records'
    )

    record_type = models.CharField(
        max_length=20,
        choices=FUEL_TYPE_CHOICES,
        default='refuel'
    )

    # Fuel details
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )  # in litres
    price_per_unit = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    total_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    # Mileage
    mileage_before = models.IntegerField(default=0)
    mileage_after = models.IntegerField(default=0)

    # Station details
    station_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    station_location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Receipt
    receipt_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    receipt_image = models.ImageField(
        upload_to='fuel_receipts/',
        null=True,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.fleet_vehicle.plate_number} - {self.quantity}L - {self.created_at.date()}"

    def save(self, *args, **kwargs):
        # Auto calculate total cost
        if self.quantity and self.price_per_unit:
            self.total_cost = self.quantity * self.price_per_unit
        # Update vehicle mileage
        if self.mileage_after > 0:
            self.fleet_vehicle.mileage = self.mileage_after
            self.fleet_vehicle.save()
        super().save(*args, **kwargs)

    @property
    def km_per_litre(self):
        """Calculate fuel efficiency"""
        distance = self.mileage_after - self.mileage_before
        if distance > 0 and self.quantity > 0:
            return round(distance / float(self.quantity), 2)
        return 0




class MaintenanceType(TimeStampedModel):
    """Types of maintenance"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class MaintenanceRecord(TimeStampedModel):
    """Track vehicle maintenance and repairs"""
    STATUS_CHOICES = (
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    PRIORITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    fleet_vehicle = models.ForeignKey(
        FleetVehicle,
        on_delete=models.CASCADE,
        related_name='maintenance_records'
    )
    branch = models.ForeignKey(
        Branch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_records'
    )
    maintenance_type = models.ForeignKey(
        MaintenanceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='records'
    )

    # ── Vehicle Details at time of maintenance ──
    vehicle_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    vehicle_model = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    plate_number = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )
    license_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )
    registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True
    )

    # Details
    title = models.CharField(max_length=255)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='scheduled'
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium'
    )

    # Dates
    scheduled_date = models.DateTimeField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Cost
    estimated_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    actual_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    # Mileage
    mileage_at_service = models.IntegerField(default=0)
    next_service_mileage = models.IntegerField(
        null=True,
        blank=True
    )

    # Service provider
    service_provider = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )
    service_location = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    # Performed by
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='maintenance_records'
    )

    # Parts replaced
    parts_replaced = models.JSONField(
        default=list,
        blank=True
    )

    notes = models.TextField(blank=True, null=True)
    receipt_image = models.ImageField(
        upload_to='maintenance_receipts/',
        null=True,
        blank=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.fleet_vehicle.plate_number} - {self.title}"

    def save(self, *args, **kwargs):
        # Auto fill vehicle details from fleet vehicle
        if self.fleet_vehicle and not self.plate_number:
            self.plate_number = self.fleet_vehicle.plate_number
        if self.fleet_vehicle and not self.vehicle_name:
            self.vehicle_name = self.fleet_vehicle.brand
        if self.fleet_vehicle and not self.vehicle_model:
            self.vehicle_model = self.fleet_vehicle.model

        # Update vehicle status based on maintenance status
        if self.status == 'in_progress':
            self.fleet_vehicle.status = 'maintenance'
            self.fleet_vehicle.save()
        elif self.status == 'completed':
            self.fleet_vehicle.status = 'available'
            if self.completed_at is None:
                self.completed_at = timezone.now()
            if self.next_service_mileage:
                self.fleet_vehicle.last_service_date = (
                    self.completed_at.date()
                )
                self.fleet_vehicle.save()
        super().save(*args, **kwargs)


class BranchManager(TimeStampedModel):
    """
    Track branch manager assignments
    Supports history of managers per branch
    """
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('on_leave', 'On Leave'),
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name='manager_assignments'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='branch_assignments'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active'
    )

    # Assignment details
    assigned_date = models.DateField()
    end_date = models.DateField(
        null=True,
        blank=True
    )

    # Permissions
    can_approve_dispatches = models.BooleanField(default=True)
    can_manage_fleet = models.BooleanField(default=True)
    can_manage_drivers = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=True)
    can_manage_fuel = models.BooleanField(default=True)
    can_manage_maintenance = models.BooleanField(default=True)

    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('branch', 'user', 'assigned_date')

    def __str__(self):
        return f"{self.user.full_name} - {self.branch.name}"

    def save(self, *args, **kwargs):
        # If setting as active update branch manager field
        if self.status == 'active':
            self.branch.manager = self.user
            self.branch.save()
        super().save(*args, **kwargs)
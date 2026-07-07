from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.utils import timezone
from django.db import transaction, models
from datetime import datetime, timedelta
import uuid

from apps.common.views import api_response
from apps.common.permissions import IsAdmin

from .models import (
    AppointmentService, AppointmentStaff, AppointmentSlot,
    AppointmentBlock, AppointmentAvailabilityException,
    Appointment, AppointmentTracking, AppointmentPayment,
    AppointmentRating, AppointmentWaitlist, AppointmentReminder,
)
from .serializers import (
    AppointmentServiceSerializer, AppointmentStaffSerializer,
    AppointmentSlotSerializer, AppointmentBlockSerializer,
    AppointmentAvailabilityExceptionSerializer,
    AppointmentSerializer, AppointmentTrackingSerializer,
    AppointmentPaymentSerializer, AppointmentRatingSerializer,
    AppointmentWaitlistSerializer, AppointmentReminderSerializer,
    BookAppointmentSerializer, CheckInSerializer,
    RateAppointmentSerializer,
)


# ── Services ──────────────────────────────────────
class AppointmentServiceListView(APIView):
    """
    GET  /api/v1/appointments/services/?business_id=1
    POST /api/v1/appointments/services/
    """
    permission_classes = []

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = AppointmentService.objects.filter(is_active=True)
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response('success', 'Services retrieved',
            data=AppointmentServiceSerializer(qs, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        serializer = AppointmentServiceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Service created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


class AppointmentServiceDetailView(APIView):
    """
    GET/PATCH/DELETE /api/v1/appointments/services/<pk>/
    """
    permission_classes = []

    def get_object(self, pk):
        try:
            return AppointmentService.objects.get(pk=pk)
        except AppointmentService.DoesNotExist:
            return None

    def get(self, request, pk):
        obj = self.get_object(pk)
        if not obj:
            return api_response('error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Service retrieved',
            data=AppointmentServiceSerializer(obj).data)

    def patch(self, request, pk):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        obj = self.get_object(pk)
        if not obj:
            return api_response('error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND)
        serializer = AppointmentServiceSerializer(
            obj, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Service updated',
                data=serializer.data)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        obj = self.get_object(pk)
        if not obj:
            return api_response('error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND)
        obj.is_active = False
        obj.save()
        return api_response('success', 'Service deactivated')


# ── Staff ─────────────────────────────────────────
class AppointmentStaffListView(APIView):
    """
    GET  /api/v1/appointments/staff/?business_id=1
    POST /api/v1/appointments/staff/
    """
    permission_classes = []

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = AppointmentStaff.objects.filter(is_active=True)
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response('success', 'Staff retrieved',
            data=AppointmentStaffSerializer(qs, many=True).data)

    def post(self, request):
        if not request.user.is_authenticated:
            return api_response('error', 'Authentication required',
                http_status=status.HTTP_401_UNAUTHORIZED)
        serializer = AppointmentStaffSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Staff created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Availability ──────────────────────────────────
class AppointmentAvailabilityView(APIView):
    """
    GET /api/v1/appointments/availability/
        ?business_id=1&service_id=2&date=2026-07-10&staff_id=3
    Returns available time slots for a given date.
    """
    permission_classes = []

    def get(self, request):
        business_id = request.query_params.get('business_id')
        service_id  = request.query_params.get('service_id')
        date_str    = request.query_params.get('date')
        staff_id    = request.query_params.get('staff_id')

        if not business_id or not service_id or not date_str:
            return api_response('error',
                'business_id, service_id and date are required',
                http_status=status.HTTP_400_BAD_REQUEST)

        try:
            service = AppointmentService.objects.get(
                pk=service_id, business_id=business_id, is_active=True)
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (AppointmentService.DoesNotExist, ValueError):
            return api_response('error', 'Service not found or invalid date',
                http_status=status.HTTP_400_BAD_REQUEST)

        day_of_week = date.weekday()  # 0=Monday

        # Check for full-day blocks
        is_blocked = AppointmentBlock.objects.filter(
            business_id=business_id,
            date=date,
            all_day=True,
        ).exists()
        if is_blocked:
            return api_response('success', 'No availability — day is blocked',
                data={'slots': [], 'blocked': True})

        # Check for closed exception
        exception = AppointmentAvailabilityException.objects.filter(
            business_id=business_id,
            date=date,
            exception_type='closed',
        ).first()
        if exception:
            return api_response('success', 'No availability',
                data={'slots': [], 'blocked': True})

        # Get slots for this day
        slots_qs = AppointmentSlot.objects.filter(
            business_id=business_id,
            day=day_of_week,
            is_active=True,
        )
        if staff_id:
            slots_qs = slots_qs.filter(
                models.Q(staff_id=staff_id) | models.Q(staff__isnull=True)
            )

        # Get existing appointments for this date
        existing = Appointment.objects.filter(
            business_id=business_id,
            date=date,
            status__in=['pending', 'confirmed', 'checked_in', 'in_progress'],
        )
        if staff_id:
            existing = existing.filter(staff_id=staff_id)

        booked_times = [(a.start_time, a.end_time) for a in existing]

        # Generate available time slots
        duration = service.total_duration_minutes
        available_slots = []

        for slot in slots_qs:
            current = datetime.combine(date, slot.start_time)
            slot_end = datetime.combine(date, slot.end_time)

            while current + timedelta(minutes=duration) <= slot_end:
                slot_start_time = current.time()
                slot_end_time = (current + timedelta(minutes=duration)).time()

                # Skip break time
                if slot.break_start and slot.break_end:
                    if slot_start_time < slot.break_end and slot_end_time > slot.break_start:
                        current = datetime.combine(date, slot.break_end)
                        continue

                # Check against existing bookings
                is_taken = any(
                    b_start < slot_end_time and b_end > slot_start_time
                    for b_start, b_end in booked_times
                )

                if not is_taken:
                    available_slots.append({
                        'start_time': slot_start_time.strftime('%H:%M'),
                        'end_time':   slot_end_time.strftime('%H:%M'),
                        'staff_id':   slot.staff_id,
                    })

                current += timedelta(minutes=duration)

        return api_response('success', f'{len(available_slots)} slots available',
            data={'date': date_str, 'slots': available_slots})


# ── Book appointment ──────────────────────────────
class BookAppointmentView(APIView):
    """
    POST /api/v1/appointments/book/
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = BookAppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response('error', 'Validation failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        # Get service
        try:
            service = AppointmentService.objects.get(
                pk=data['service_id'],
                business_id=data['business_id'],
                is_active=True,
            )
        except AppointmentService.DoesNotExist:
            return api_response('error', 'Service not found',
                http_status=status.HTTP_404_NOT_FOUND)

        # Get staff if specified
        staff = None
        if data.get('staff_id'):
            try:
                staff = AppointmentStaff.objects.get(
                    pk=data['staff_id'],
                    business_id=data['business_id'],
                    is_active=True,
                )
            except AppointmentStaff.DoesNotExist:
                return api_response('error', 'Staff not found',
                    http_status=status.HTTP_404_NOT_FOUND)

        # Calculate end time
        start_dt = datetime.combine(data['date'], data['start_time'])
        end_dt   = start_dt + timedelta(minutes=service.total_duration_minutes)
        end_time = end_dt.time()

        # Check for overlaps
        has_overlap = Appointment.check_overlap(
            business_id=data['business_id'],
            staff=staff,
            date=data['date'],
            start_time=data['start_time'],
            end_time=end_time,
        )
        if has_overlap:
            return api_response('error',
                'This time slot is no longer available',
                http_status=status.HTTP_409_CONFLICT)

        # Calculate earnings
        commission_rate = service.business.commission_rate or 10
        platform_commission = float(service.price) * float(commission_rate) / 100
        staff_commission = 0
        if staff and staff.commission_percentage:
            staff_commission = float(service.price) * float(staff.commission_percentage) / 100
        business_earnings = float(service.price) - platform_commission - staff_commission

        # Create appointment
        appointment = Appointment.objects.create(
            business_id=data['business_id'],
            customer=request.user,
            service=service,
            staff=staff,
            date=data['date'],
            start_time=data['start_time'],
            end_time=end_time,
            duration_minutes=service.total_duration_minutes,
            amount=service.price,
            deposit_amount=service.deposit_amount,
            platform_commission=platform_commission,
            business_earnings=business_earnings,
            staff_commission=staff_commission,
            payment_method=data['payment_method'],
            customer_note=data.get('customer_note', ''),
            status='pending' if service.requires_confirmation else 'confirmed',
        )

        # Auto-confirm if not requiring manual confirmation
        if not service.requires_confirmation:
            appointment.confirmed_at = timezone.now()
            appointment.save()

        # Log tracking
        AppointmentTracking.objects.create(
            appointment=appointment,
            status=appointment.status,
            note='Appointment created',
            updated_by=request.user,
        )

        return api_response('success', 'Appointment booked successfully',
            data=AppointmentSerializer(appointment).data,
            http_status=status.HTTP_201_CREATED)


# ── Customer: my appointments ─────────────────────
class MyAppointmentsView(APIView):
    """GET /api/v1/appointments/my/"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = Appointment.objects.filter(customer=request.user)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return api_response('success', 'Appointments retrieved',
            data=AppointmentSerializer(qs, many=True).data)


# ── Appointment detail ────────────────────────────
class AppointmentDetailView(APIView):
    """
    GET    /api/v1/appointments/<pk>/
    PATCH  /api/v1/appointments/<pk>/  ← update status (business)
    DELETE /api/v1/appointments/<pk>/  ← cancel
    """
    permission_classes = [IsAuthenticated]

    def get_object(self, pk, user):
        try:
            return Appointment.objects.get(
                pk=pk,
                customer=user,
            )
        except Appointment.DoesNotExist:
            # Try business owner
            try:
                return Appointment.objects.get(
                    pk=pk,
                    business__owner=user,
                )
            except Appointment.DoesNotExist:
                return None

    def get(self, request, pk):
        obj = self.get_object(pk, request.user)
        if not obj:
            return api_response('error', 'Appointment not found',
                http_status=status.HTTP_404_NOT_FOUND)
        return api_response('success', 'Appointment retrieved',
            data=AppointmentSerializer(obj).data)

    def patch(self, request, pk):
        try:
            obj = Appointment.objects.get(pk=pk, business__owner=request.user)
        except Appointment.DoesNotExist:
            return api_response('error', 'Appointment not found',
                http_status=status.HTTP_404_NOT_FOUND)

        new_status = request.data.get('status')
        note       = request.data.get('note', '')

        if new_status:
            obj.status = new_status
            now = timezone.now()
            if new_status == 'confirmed':
                obj.confirmed_at = now
            elif new_status == 'in_progress':
                obj.started_at = now
            elif new_status == 'completed':
                obj.completed_at = now
                obj.completed_by = request.user
            obj.save()

            AppointmentTracking.objects.create(
                appointment=obj, status=new_status,
                note=note, updated_by=request.user)

        return api_response('success', 'Appointment updated',
            data=AppointmentSerializer(obj).data)

    def delete(self, request, pk):
        obj = self.get_object(pk, request.user)
        if not obj:
            return api_response('error', 'Appointment not found',
                http_status=status.HTTP_404_NOT_FOUND)

        if obj.status not in ['pending', 'confirmed']:
            return api_response('error', 'Cannot cancel this appointment',
                http_status=status.HTTP_400_BAD_REQUEST)

        obj.status = 'cancelled'
        obj.cancelled_at = timezone.now()
        obj.cancellation_reason = request.data.get('reason', '')
        obj.save()

        AppointmentTracking.objects.create(
            appointment=obj, status='cancelled',
            note=obj.cancellation_reason,
            updated_by=request.user)

        # Notify waitlist
        waitlist = AppointmentWaitlist.objects.filter(
            business=obj.business,
            service=obj.service,
            preferred_date=obj.date,
            status='waiting',
        ).first()
        if waitlist:
            waitlist.status = 'notified'
            waitlist.notified_at = timezone.now()
            waitlist.save()

        return api_response('success', 'Appointment cancelled')


# ── Check-in ──────────────────────────────────────
class AppointmentCheckInView(APIView):
    """
    POST /api/v1/appointments/check-in/
    Body: { check_in_code }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckInSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response('error', 'Validation failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['check_in_code']

        try:
            appointment = Appointment.objects.get(check_in_code=code)
        except Appointment.DoesNotExist:
            return api_response('error', 'Invalid check-in code',
                http_status=status.HTTP_404_NOT_FOUND)

        if appointment.status != 'confirmed':
            return api_response('error',
                f'Cannot check in — appointment is {appointment.status}',
                http_status=status.HTTP_400_BAD_REQUEST)

        appointment.status = 'checked_in'
        appointment.checked_in_at = timezone.now()
        appointment.save()

        AppointmentTracking.objects.create(
            appointment=appointment,
            status='checked_in',
            note='Checked in at reception',
            updated_by=request.user,
        )

        return api_response('success', 'Checked in successfully',
            data=AppointmentSerializer(appointment).data)


# ── Rate appointment ──────────────────────────────
class AppointmentRatingView(APIView):
    """
    POST /api/v1/appointments/<pk>/rate/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            appointment = Appointment.objects.get(
                pk=pk, customer=request.user, status='completed')
        except Appointment.DoesNotExist:
            return api_response('error',
                'Appointment not found or not completed',
                http_status=status.HTTP_404_NOT_FOUND)

        if hasattr(appointment, 'rating'):
            return api_response('error', 'Already rated',
                http_status=status.HTTP_400_BAD_REQUEST)

        serializer = RateAppointmentSerializer(data=request.data)
        if not serializer.is_valid():
            return api_response('error', 'Validation failed',
                errors=serializer.errors,
                http_status=status.HTTP_400_BAD_REQUEST)

        rating = AppointmentRating.objects.create(
            appointment=appointment,
            **serializer.validated_data,
        )

        return api_response('success', 'Rating submitted',
            data=AppointmentRatingSerializer(rating).data,
            http_status=status.HTTP_201_CREATED)


# ── Waitlist ──────────────────────────────────────
class AppointmentWaitlistView(APIView):
    """
    POST /api/v1/appointments/waitlist/
    GET  /api/v1/appointments/waitlist/  ← customer's waitlist
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = AppointmentWaitlist.objects.filter(customer=request.user)
        return api_response('success', 'Waitlist retrieved',
            data=AppointmentWaitlistSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AppointmentWaitlistSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(customer=request.user)
            return api_response('success', 'Added to waitlist',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)


# ── Business: appointments dashboard ─────────────
class BusinessAppointmentsView(APIView):
    """
    GET /api/v1/appointments/business/<business_id>/
        ?date=2026-07-10&status=confirmed&staff_id=1
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, business_id):
        qs = Appointment.objects.filter(business_id=business_id)

        date_filter   = request.query_params.get('date')
        status_filter = request.query_params.get('status')
        staff_filter  = request.query_params.get('staff_id')

        if date_filter:   qs = qs.filter(date=date_filter)
        if status_filter: qs = qs.filter(status=status_filter)
        if staff_filter:  qs = qs.filter(staff_id=staff_filter)

        return api_response('success', 'Appointments retrieved',
            data=AppointmentSerializer(qs, many=True).data)


# ── Slots management ──────────────────────────────
class AppointmentSlotView(APIView):
    """
    GET  /api/v1/appointments/slots/?business_id=1
    POST /api/v1/appointments/slots/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        business_id = request.query_params.get('business_id')
        qs = AppointmentSlot.objects.filter(is_active=True)
        if business_id:
            qs = qs.filter(business_id=business_id)
        return api_response('success', 'Slots retrieved',
            data=AppointmentSlotSerializer(qs, many=True).data)

    def post(self, request):
        serializer = AppointmentSlotSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response('success', 'Slot created',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED)
        return api_response('error', 'Validation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST)
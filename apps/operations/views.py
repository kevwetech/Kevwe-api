from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from apps.common.views import api_response
from apps.common.permissions import IsAdmin
from apps.common.utils import generate_reference
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Q

from .models import (
    Branch, Territory, Fleet, FleetVehicle, Dispatch,
    MaintenanceType, MaintenanceRecord, BranchManager,
)
from .serializers import (
    BranchSerializer,
    TerritorySerializer,
    FleetSerializer,
    FleetVehicleSerializer,
    DispatchSerializer,
    FuelRecordSerializer,
    FuelTypeSerializer,
    MaintenanceTypeSerializer,
    MaintenanceRecordSerializer,
)



class BranchListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        branches = Branch.objects.filter(is_active=True)
        branch_type = request.query_params.get('type')
        state_id = request.query_params.get('state')
        business_id = request.query_params.get('business_id')
        search = request.query_params.get('search')
        if branch_type:
            branches = branches.filter(branch_type=branch_type)
        if state_id:
            branches = branches.filter(state__id=state_id)
        if business_id:
            branches = branches.filter(business__id=business_id)
        if search:
            branches = branches.filter(name__icontains=search)
            
        serializer = BranchSerializer(branches, many=True)
        return api_response(
            'success',
            'Branches retrieved successfully',
            data={
                'count': branches.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = BranchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Branch created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BranchDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Branch.objects.get(pk=pk)
        except Branch.DoesNotExist:
            return None

    def get(self, request, pk):
        branch = self.get_object(pk)
        if not branch:
            return api_response(
                'error',
                'Branch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BranchSerializer(branch)
        return api_response(
            'success',
            'Branch retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        branch = self.get_object(pk)
        if not branch:
            return api_response(
                'error',
                'Branch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BranchSerializer(
            branch,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Branch updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        branch = self.get_object(pk)
        if not branch:
            return api_response(
                'error',
                'Branch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        branch.is_active = False
        branch.save()
        return api_response(
            'success',
            'Branch deleted successfully'
        )


# ─── Territory Views ─────────────────────────────

class TerritoryListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        territories = Territory.objects.filter(is_active=True)

        branch_id = request.query_params.get('branch')
        if branch_id:
            territories = territories.filter(branch__id=branch_id)

        serializer = TerritorySerializer(territories, many=True)
        return api_response(
            'success',
            'Territories retrieved successfully',
            data={
                'count': territories.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = TerritorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Territory created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class TerritoryDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Territory.objects.get(pk=pk)
        except Territory.DoesNotExist:
            return None

    def get(self, request, pk):
        territory = self.get_object(pk)
        if not territory:
            return api_response(
                'error',
                'Territory not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TerritorySerializer(territory)
        return api_response(
            'success',
            'Territory retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        territory = self.get_object(pk)
        if not territory:
            return api_response(
                'error',
                'Territory not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = TerritorySerializer(
            territory,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Territory updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        territory = self.get_object(pk)
        if not territory:
            return api_response(
                'error',
                'Territory not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        territory.is_active = False
        territory.save()
        return api_response(
            'success',
            'Territory deleted successfully'
        )


# ─── Fleet Views ─────────────────────────────────

class FleetListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        fleets = Fleet.objects.filter(is_active=True)

        branch_id = request.query_params.get('branch')
        if branch_id:
            fleets = fleets.filter(branch__id=branch_id)

        serializer = FleetSerializer(fleets, many=True)
        return api_response(
            'success',
            'Fleets retrieved successfully',
            data={
                'count': fleets.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FleetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Fleet created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FleetDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Fleet.objects.get(pk=pk)
        except Fleet.DoesNotExist:
            return None

    def get(self, request, pk):
        fleet = self.get_object(pk)
        if not fleet:
            return api_response(
                'error',
                'Fleet not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FleetSerializer(fleet)
        return api_response(
            'success',
            'Fleet retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        fleet = self.get_object(pk)
        if not fleet:
            return api_response(
                'error',
                'Fleet not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FleetSerializer(
            fleet,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Fleet updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        fleet = self.get_object(pk)
        if not fleet:
            return api_response(
                'error',
                'Fleet not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        fleet.is_active = False
        fleet.save()
        return api_response(
            'success',
            'Fleet deleted successfully'
        )


# ─── Fleet Vehicle Views ─────────────────────────

class FleetVehicleListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        vehicles = FleetVehicle.objects.all()

        fleet_id = request.query_params.get('fleet')
        vehicle_status = request.query_params.get('status')
        branch_id = request.query_params.get('branch')

        if fleet_id:
            vehicles = vehicles.filter(fleet__id=fleet_id)
        if vehicle_status:
            vehicles = vehicles.filter(status=vehicle_status)
        if branch_id:
            vehicles = vehicles.filter(fleet__branch__id=branch_id)

        serializer = FleetVehicleSerializer(vehicles, many=True)
        return api_response(
            'success',
            'Fleet vehicles retrieved successfully',
            data={
                'count': vehicles.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FleetVehicleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Vehicle added to fleet successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FleetVehicleDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return FleetVehicle.objects.get(pk=pk)
        except FleetVehicle.DoesNotExist:
            return None

    def get(self, request, pk):
        vehicle = self.get_object(pk)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FleetVehicleSerializer(vehicle)
        return api_response(
            'success',
            'Vehicle retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        vehicle = self.get_object(pk)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FleetVehicleSerializer(
            vehicle,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Vehicle updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        vehicle = self.get_object(pk)
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        vehicle.status = 'inactive'
        vehicle.save()
        return api_response(
            'success',
            'Vehicle deactivated successfully'
        )


class AssignDriverToVehicleView(APIView):
    """Assign a driver to a fleet vehicle"""
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        vehicle = FleetVehicle.objects.filter(pk=pk).first()
        if not vehicle:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        driver_id = request.data.get('driver_id')
        from apps.drivers.models import DriverProfile
        driver = DriverProfile.objects.filter(
            pk=driver_id,
            status='verified'
        ).first()

        if not driver:
            return api_response(
                'error',
                'Driver not found or not verified',
                http_status=status.HTTP_404_NOT_FOUND
            )

        vehicle.driver = driver
        vehicle.save()

        return api_response(
            'success',
            f'Driver {driver.user.full_name} assigned to vehicle {vehicle.plate_number}',
            data=FleetVehicleSerializer(vehicle).data
        )


# ─── Dispatch Views ──────────────────────────────

class DispatchListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        dispatches = Dispatch.objects.all()

        dispatch_status = request.query_params.get('status')
        branch_id = request.query_params.get('branch')
        dispatch_type = request.query_params.get('type')
        driver_id = request.query_params.get('driver')

        if dispatch_status:
            dispatches = dispatches.filter(status=dispatch_status)
        if branch_id:
            dispatches = dispatches.filter(branch__id=branch_id)
        if dispatch_type:
            dispatches = dispatches.filter(dispatch_type=dispatch_type)
        if driver_id:
            dispatches = dispatches.filter(driver__id=driver_id)

        serializer = DispatchSerializer(dispatches, many=True)
        return api_response(
            'success',
            'Dispatches retrieved successfully',
            data={
                'count': dispatches.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        """Create a dispatch assignment"""
        data = request.data  # ← get all data
        branch_id = request.data.get('branch_id')
        fleet_id = request.data.get('fleet_id')
        fleet_vehicle_id = request.data.get('fleet_vehicle_id')
        driver_id = request.data.get('driver_id')
        dispatch_type = request.data.get('dispatch_type', 'delivery')
        delivery_id = request.data.get('delivery_id')
        shipment_id = request.data.get('shipment_id')
        notes = request.data.get('notes', '')
        priority = request.data.get('priority', 0)

        print(f"branch_id: {branch_id}")        # ← debug
        print(f"fleet_id: {fleet_id}")          # ← debug
        print(f"driver_id: {driver_id}")        # ← debug
        print(f"delivery_id: {delivery_id}")    # ← debug


        # Get branch
        branch = None
        if branch_id:
            branch = Branch.objects.filter(pk=branch_id).first()
            print(f"branch found: {branch}")    # ← debug

        # Get fleet
        fleet = Fleet.objects.filter(pk=fleet_id).first()

        # Get fleet vehicle
        fleet_vehicle = FleetVehicle.objects.filter(
            pk=fleet_vehicle_id,
            status='available'
        ).first()

        if fleet_vehicle_id and not fleet_vehicle:
            return api_response(
                'error',
                'Vehicle not available',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        # Get driver
        from apps.drivers.models import DriverProfile
        driver = DriverProfile.objects.filter(
            pk=driver_id,
            status='verified'
        ).first()

        if driver_id and not driver:
            return api_response(
                'error',
                'Driver not found or not verified',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # Get delivery or shipment
        delivery = None
        shipment = None

        if dispatch_type == 'delivery' and delivery_id:
            from apps.deliveries.models import DeliveryRequest
            delivery = DeliveryRequest.objects.filter(
                pk=delivery_id
            ).first()
            print(f"delivery found: {delivery}")    # ← debug
        elif dispatch_type == 'shipment' and shipment_id:
            from apps.shipments.models import Shipment
            shipment = Shipment.objects.filter(
                pk=shipment_id
            ).first()

        # Create dispatch
        dispatch = Dispatch.objects.create(
            branch=branch,
            fleet=fleet,
            fleet_vehicle=fleet_vehicle,
            driver=driver,
            dispatch_type=dispatch_type,
            delivery=delivery,
            shipment=shipment,
            reference=generate_reference('DSP'),
            status='assigned',
            assigned_at=timezone.now(),
            notes=notes,
            priority=priority,
        )

        # Update vehicle status
        if fleet_vehicle:
            fleet_vehicle.status = 'on_trip'
            fleet_vehicle.save()

        # Update delivery/shipment status
        if delivery:
            delivery.status = 'assigned'
            delivery.dispatcher = driver
            delivery.save()

        if shipment:
            shipment.status = 'assigned'
            shipment.driver = driver
            shipment.save()

        # Notify driver via WebSocket
        if driver:
            try:
                from channels.layers import get_channel_layer
                from asgiref.sync import async_to_sync
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f'driver_rides_{driver.id}',
                    {
                        'type': 'ride_request',
                        'dispatch_id': dispatch.id,
                        'reference': dispatch.reference,
                        'dispatch_type': dispatch_type,
                        'message': f'New {dispatch_type} dispatch assigned',
                    }
                )
            except Exception:
                pass

        return api_response(
            'success',
            'Dispatch created successfully',
            data=DispatchSerializer(dispatch).data,
            http_status=status.HTTP_201_CREATED
        )


class DispatchDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return Dispatch.objects.get(pk=pk)
        except Dispatch.DoesNotExist:
            return None

    def get(self, request, pk):
        dispatch = self.get_object(pk)
        if not dispatch:
            return api_response(
                'error',
                'Dispatch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = DispatchSerializer(dispatch)
        return api_response(
            'success',
            'Dispatch retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        """Update dispatch status"""
        dispatch = self.get_object(pk)
        if not dispatch:
            return api_response(
                'error',
                'Dispatch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        current_lat = request.data.get('current_lat')
        current_lng = request.data.get('current_lng')
        notes = request.data.get('notes', '')

        if new_status:
            dispatch.status = new_status

            if new_status == 'picked_up':
                dispatch.picked_up_at = timezone.now()
            elif new_status in ['delivered', 'failed', 'returned']:
                dispatch.delivered_at = timezone.now()

                # Free up vehicle
                if dispatch.fleet_vehicle:
                    dispatch.fleet_vehicle.status = 'available'
                    dispatch.fleet_vehicle.save()

        if current_lat:
            dispatch.current_lat = current_lat
        if current_lng:
            dispatch.current_lng = current_lng
        if notes:
            dispatch.notes = notes

        dispatch.save()

        return api_response(
            'success',
            'Dispatch updated successfully',
            data=DispatchSerializer(dispatch).data
        )


class DriverDispatchView(APIView):
    """Driver view their dispatches"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            driver = request.user.driver_profile
        except Exception:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        dispatches = Dispatch.objects.filter(driver=driver)

        dispatch_status = request.query_params.get('status')
        if dispatch_status:
            dispatches = dispatches.filter(status=dispatch_status)

        serializer = DispatchSerializer(dispatches, many=True)
        return api_response(
            'success',
            'Dispatches retrieved successfully',
            data={
                'count': dispatches.count(),
                'results': serializer.data
            }
        )

    def patch(self, request, pk):
        """Driver updates dispatch status"""
        try:
            driver = request.user.driver_profile
        except Exception:
            return api_response(
                'error',
                'Driver profile not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        try:
            dispatch = Dispatch.objects.get(pk=pk, driver=driver)
        except Dispatch.DoesNotExist:
            return api_response(
                'error',
                'Dispatch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        new_status = request.data.get('status')
        current_lat = request.data.get('current_lat')
        current_lng = request.data.get('current_lng')

        valid_statuses = [
            'en_route_pickup',
            'at_pickup',
            'picked_up',
            'en_route_delivery',
            'at_delivery',
            'delivered',
            'failed',
        ]

        if new_status not in valid_statuses:
            return api_response(
                'error',
                f'Invalid status',
                http_status=status.HTTP_400_BAD_REQUEST
            )

        dispatch.status = new_status

        if current_lat:
            dispatch.current_lat = current_lat
        if current_lng:
            dispatch.current_lng = current_lng

        if new_status == 'picked_up':
            dispatch.picked_up_at = timezone.now()
        elif new_status == 'delivered':
            dispatch.delivered_at = timezone.now()
            if dispatch.fleet_vehicle:
                dispatch.fleet_vehicle.status = 'available'
                dispatch.fleet_vehicle.save()

        dispatch.save()

        # Update linked delivery/shipment
        if dispatch.delivery:
            status_map = {
                'picked_up': 'picked_up',
                'en_route_delivery': 'in_transit',
                'delivered': 'delivered',
                'failed': 'failed',
            }
            if new_status in status_map:
                dispatch.delivery.status = status_map[new_status]
                if current_lat:
                    dispatch.delivery.current_lat = current_lat
                if current_lng:
                    dispatch.delivery.current_lng = current_lng
                dispatch.delivery.save()

        if dispatch.shipment:
            status_map = {
                'picked_up': 'picked_up',
                'en_route_delivery': 'in_transit',
                'delivered': 'delivered',
                'failed': 'failed',
            }
            if new_status in status_map:
                dispatch.shipment.status = status_map[new_status]
                if current_lat:
                    dispatch.shipment.current_lat = current_lat
                if current_lng:
                    dispatch.shipment.current_lng = current_lng
                dispatch.shipment.save()

        return api_response(
            'success',
            'Dispatch updated successfully',
            data=DispatchSerializer(dispatch).data
        )


class OperationsDashboardView(APIView):
    """Operations overview dashboard"""
    permission_classes = [IsAdmin]

    def get(self, request):
        branch_id = request.query_params.get('branch')

        branches = Branch.objects.filter(is_active=True)
        fleets = Fleet.objects.filter(is_active=True)
        vehicles = FleetVehicle.objects.all()
        dispatches = Dispatch.objects.all()

        if branch_id:
            branches = branches.filter(id=branch_id)
            fleets = fleets.filter(branch__id=branch_id)
            vehicles = vehicles.filter(fleet__branch__id=branch_id)
            dispatches = dispatches.filter(branch__id=branch_id)

        return api_response(
            'success',
            'Operations dashboard retrieved',
            data={
                'branches': {
                    'total': branches.count(),
                    'active': branches.filter(
                        status='active'
                    ).count(),
                },
                'fleets': {
                    'total': fleets.count(),
                },
                'vehicles': {
                    'total': vehicles.count(),
                    'available': vehicles.filter(
                        status='available'
                    ).count(),
                    'on_trip': vehicles.filter(
                        status='on_trip'
                    ).count(),
                    'maintenance': vehicles.filter(
                        status='maintenance'
                    ).count(),
                },
                'dispatches': {
                    'total': dispatches.count(),
                    'pending': dispatches.filter(
                        status='pending'
                    ).count(),
                    'active': dispatches.filter(
                        status__in=[
                            'assigned',
                            'en_route_pickup',
                            'picked_up',
                            'en_route_delivery',
                        ]
                    ).count(),
                    'delivered': dispatches.filter(
                        status='delivered'
                    ).count(),
                    'failed': dispatches.filter(
                        status='failed'
                    ).count(),
                },
            }
        )

class FuelTypeListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        fuel_types = FuelType.objects.filter(is_active=True)
        serializer = FuelTypeSerializer(fuel_types, many=True)
        return api_response(
            'success',
            'Fuel types retrieved successfully',
            data={
                'count': fuel_types.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FuelTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Fuel type created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FuelRecordListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        records = FuelRecord.objects.all()

        vehicle_id = request.query_params.get('vehicle')
        branch_id = request.query_params.get('branch')
        driver_id = request.query_params.get('driver')
        record_type = request.query_params.get('type')

        if vehicle_id:
            records = records.filter(
                fleet_vehicle__id=vehicle_id
            )
        if branch_id:
            records = records.filter(branch__id=branch_id)
        if driver_id:
            records = records.filter(driver__id=driver_id)
        if record_type:
            records = records.filter(record_type=record_type)

        # Summary stats
        total_fuel = sum(
            r.quantity for r in records.filter(
                record_type='refuel'
            )
        )
        total_cost = sum(
            r.total_cost for r in records.filter(
                record_type='refuel'
            )
        )

        serializer = FuelRecordSerializer(records, many=True)
        return api_response(
            'success',
            'Fuel records retrieved successfully',
            data={
                'summary': {
                    'total_fuel_litres': str(total_fuel),
                    'total_cost': str(total_cost),
                    'total_records': records.count(),
                },
                'count': records.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = FuelRecordSerializer(data=request.data)
        if serializer.is_valid():
            # Auto set driver from request user if driver
            driver = None
            try:
                driver = request.user.driver_profile
            except Exception:
                pass

            record = serializer.save(driver=driver)

            return api_response(
                'success',
                'Fuel record added successfully',
                data=FuelRecordSerializer(record).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Failed to add fuel record',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class FuelRecordDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, pk):
        try:
            return FuelRecord.objects.get(pk=pk)
        except FuelRecord.DoesNotExist:
            return None

    def get(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Fuel record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FuelRecordSerializer(record)
        return api_response(
            'success',
            'Fuel record retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Fuel record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = FuelRecordSerializer(
            record,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Fuel record updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Fuel record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        record.delete()
        return api_response(
            'success',
            'Fuel record deleted successfully'
        )


class VehicleFuelReportView(APIView):
    """Fuel report for a specific vehicle"""
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            vehicle = FleetVehicle.objects.get(pk=pk)
        except FleetVehicle.DoesNotExist:
            return api_response(
                'error',
                'Vehicle not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        records = FuelRecord.objects.filter(
            fleet_vehicle=vehicle
        )

        # Calculate stats
        total_fuel = sum(r.quantity for r in records)
        total_cost = sum(r.total_cost for r in records)

        # Average efficiency
        efficiencies = [
            r.km_per_litre for r in records
            if r.km_per_litre > 0
        ]
        avg_efficiency = (
            sum(efficiencies) / len(efficiencies)
            if efficiencies else 0
        )

        # Monthly breakdown
        from collections import defaultdict
        monthly = defaultdict(lambda: {
            'fuel': 0, 'cost': 0, 'records': 0
        })
        for record in records:
            key = record.created_at.strftime('%Y-%m')
            monthly[key]['fuel'] += float(record.quantity)
            monthly[key]['cost'] += float(record.total_cost)
            monthly[key]['records'] += 1

        serializer = FuelRecordSerializer(records, many=True)

        return api_response(
            'success',
            'Vehicle fuel report retrieved',
            data={
                'vehicle': {
                    'plate_number': vehicle.plate_number,
                    'brand': vehicle.brand,
                    'model': vehicle.model,
                    'current_mileage': vehicle.mileage,
                },
                'summary': {
                    'total_fuel_litres': str(total_fuel),
                    'total_cost': str(total_cost),
                    'avg_km_per_litre': round(avg_efficiency, 2),
                    'total_records': records.count(),
                },
                'monthly_breakdown': dict(monthly),
                'records': serializer.data,
            }
        )


class MaintenanceTypeListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        types = MaintenanceType.objects.filter(is_active=True)
        serializer = MaintenanceTypeSerializer(types, many=True)
        return api_response(
            'success',
            'Maintenance types retrieved successfully',
            data={
                'count': types.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = MaintenanceTypeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Maintenance type created successfully',
                data=serializer.data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class MaintenanceRecordListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        records = MaintenanceRecord.objects.all()

        vehicle_id = request.query_params.get('vehicle')
        branch_id = request.query_params.get('branch')
        record_status = request.query_params.get('status')
        priority = request.query_params.get('priority')

        if vehicle_id:
            records = records.filter(
                fleet_vehicle__id=vehicle_id
            )
        if branch_id:
            records = records.filter(branch__id=branch_id)
        if record_status:
            records = records.filter(status=record_status)
        if priority:
            records = records.filter(priority=priority)

        # Summary
        total_estimated = sum(
            r.estimated_cost for r in records
        )
        total_actual = sum(
            r.actual_cost for r in records
            if r.actual_cost
        )

        serializer = MaintenanceRecordSerializer(
            records,
            many=True
        )
        return api_response(
            'success',
            'Maintenance records retrieved successfully',
            data={
                'summary': {
                    'total_records': records.count(),
                    'scheduled': records.filter(
                        status='scheduled'
                    ).count(),
                    'in_progress': records.filter(
                        status='in_progress'
                    ).count(),
                    'completed': records.filter(
                        status='completed'
                    ).count(),
                    'total_estimated_cost': str(total_estimated),
                    'total_actual_cost': str(total_actual),
                },
                'count': records.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = MaintenanceRecordSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save(
                performed_by=request.user
            )
            return api_response(
                'success',
                'Maintenance record created successfully',
                data=MaintenanceRecordSerializer(record).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Creation failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class MaintenanceRecordDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return MaintenanceRecord.objects.get(pk=pk)
        except MaintenanceRecord.DoesNotExist:
            return None

    def get(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Maintenance record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = MaintenanceRecordSerializer(record)
        return api_response(
            'success',
            'Maintenance record retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Maintenance record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = MaintenanceRecordSerializer(
            record,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Maintenance record updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        record = self.get_object(pk)
        if not record:
            return api_response(
                'error',
                'Maintenance record not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        record.delete()
        return api_response(
            'success',
            'Maintenance record deleted successfully'
        )


class BranchManagerListCreateView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        managers = BranchManager.objects.all()

        branch_id = request.query_params.get('branch')
        manager_status = request.query_params.get('status')

        if branch_id:
            managers = managers.filter(branch__id=branch_id)
        if manager_status:
            managers = managers.filter(status=manager_status)

        serializer = BranchManagerSerializer(managers, many=True)
        return api_response(
            'success',
            'Branch managers retrieved successfully',
            data={
                'count': managers.count(),
                'results': serializer.data
            }
        )

    def post(self, request):
        serializer = BranchManagerSerializer(data=request.data)
        if serializer.is_valid():
            # Deactivate previous active manager
            branch_id = serializer.validated_data['branch'].id
            BranchManager.objects.filter(
                branch__id=branch_id,
                status='active'
            ).update(status='inactive')

            manager = serializer.save()
            return api_response(
                'success',
                'Branch manager assigned successfully',
                data=BranchManagerSerializer(manager).data,
                http_status=status.HTTP_201_CREATED
            )
        return api_response(
            'error',
            'Assignment failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )


class BranchManagerDetailView(APIView):
    permission_classes = [IsAdmin]

    def get_object(self, pk):
        try:
            return BranchManager.objects.get(pk=pk)
        except BranchManager.DoesNotExist:
            return None

    def get(self, request, pk):
        manager = self.get_object(pk)
        if not manager:
            return api_response(
                'error',
                'Branch manager not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BranchManagerSerializer(manager)
        return api_response(
            'success',
            'Branch manager retrieved successfully',
            data=serializer.data
        )

    def patch(self, request, pk):
        manager = self.get_object(pk)
        if not manager:
            return api_response(
                'error',
                'Branch manager not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        serializer = BranchManagerSerializer(
            manager,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return api_response(
                'success',
                'Branch manager updated successfully',
                data=serializer.data
            )
        return api_response(
            'error',
            'Update failed',
            errors=serializer.errors,
            http_status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        manager = self.get_object(pk)
        if not manager:
            return api_response(
                'error',
                'Branch manager not found',
                http_status=status.HTTP_404_NOT_FOUND
            )
        manager.status = 'inactive'
        manager.end_date = timezone.now().date()
        manager.save()
        return api_response(
            'success',
            'Branch manager deactivated successfully'
        )

class BranchDashboardView(APIView):
    """
    Per-branch performance dashboard with time period filtering.
    GET /api/v1/operations/branches/<pk>/dashboard/
        ?period=today|this_week|this_month (default: this_month)
    """
    permission_classes = [IsAdmin]

    def get(self, request, pk):
        try:
            branch = Branch.objects.get(pk=pk)
        except Branch.DoesNotExist:
            return api_response(
                'error', 'Branch not found',
                http_status=status.HTTP_404_NOT_FOUND
            )

        # ── Period filter ──
        period = request.query_params.get('period', 'this_month')
        now = timezone.now()

        if period == 'today':
            period_start = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            period_label = 'Today'
        elif period == 'this_week':
            period_start = now - timedelta(days=now.weekday())
            period_start = period_start.replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            period_label = 'This Week'
        else:  # this_month
            period_start = now.replace(
                day=1, hour=0, minute=0,
                second=0, microsecond=0
            )
            period_label = 'This Month'

        # ── Base dispatch queryset for this branch ──
        dispatches = Dispatch.objects.filter(branch=branch)
        period_dispatches = dispatches.filter(
            created_at__gte=period_start
        )

        # ── Deliveries ──
        delivery_dispatches = period_dispatches.filter(
            dispatch_type='delivery'
        )
        deliveries_total = delivery_dispatches.count()
        deliveries_completed = delivery_dispatches.filter(
            status='delivered'
        ).count()
        deliveries_failed = delivery_dispatches.filter(
            status='failed'
        ).count()
        deliveries_pending = delivery_dispatches.filter(
            status='pending'
        ).count()
        deliveries_in_progress = delivery_dispatches.filter(
            status__in=[
                'assigned', 'en_route_pickup',
                'at_pickup', 'picked_up',
                'en_route_delivery', 'at_delivery',
            ]
        ).count()

        # ── Shipments ──
        shipment_dispatches = period_dispatches.filter(
            dispatch_type='shipment'
        )
        shipments_total = shipment_dispatches.count()
        shipments_completed = shipment_dispatches.filter(
            status='delivered'
        ).count()
        shipments_failed = shipment_dispatches.filter(
            status='failed'
        ).count()
        shipments_pending = shipment_dispatches.filter(
            status='pending'
        ).count()

        # ── Revenue (from linked delivery fees) ──
        delivery_ids = delivery_dispatches.filter(
            status='delivered',
            delivery__isnull=False
        ).values_list('delivery_id', flat=True)

        from apps.deliveries.models import DeliveryRequest
        revenue = DeliveryRequest.objects.filter(
            id__in=delivery_ids
        ).aggregate(
            total=Sum('price')
        )['total'] or 0

        # ── Drivers ──
        branch_drivers = dispatches.filter(
            driver__isnull=False
        ).values_list(
            'driver_id', flat=True
        ).distinct()
        total_drivers = branch_drivers.count()

        active_today = dispatches.filter(
            created_at__gte=now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ),
            driver__isnull=False,
            status__in=[
                'assigned', 'en_route_pickup',
                'at_pickup', 'picked_up',
                'en_route_delivery', 'at_delivery',
            ]
        ).values('driver_id').distinct().count()

        # Top performer — driver with most completed deliveries
        from django.db.models import Count as DCount
        top_driver_data = period_dispatches.filter(
            status='delivered',
            driver__isnull=False
        ).values(
            'driver__id',
            'driver__user__full_name',
        ).annotate(
            completed=DCount('id')
        ).order_by('-completed').first()

        top_driver = None
        if top_driver_data:
            top_driver = {
                'driver_id': top_driver_data['driver__id'],
                'name': top_driver_data['driver__user__full_name'],
                'completed_deliveries': top_driver_data['completed'],
            }

        # ── Fleet ──
        fleet_vehicles = FleetVehicle.objects.filter(
            fleet__branch=branch
        )
        vehicles_total = fleet_vehicles.count()
        vehicles_available = fleet_vehicles.filter(
            status='available'
        ).count()
        vehicles_on_trip = fleet_vehicles.filter(
            status='on_trip'
        ).count()
        vehicles_maintenance = fleet_vehicles.filter(
            status='maintenance'
        ).count()

        # ── Dispatch status breakdown ──
        dispatch_breakdown = {}
        for s, _ in Dispatch.STATUS_CHOICES:
            dispatch_breakdown[s] = period_dispatches.filter(
                status=s
            ).count()

        return api_response(
            'success',
            f'Branch dashboard for {branch.name}',
            data={
                'branch': {
                    'id': branch.id,
                    'name': branch.name,
                    'code': branch.code,
                    'type': branch.branch_type,
                    'status': branch.status,
                    'city': (
                        branch.city.name
                        if branch.city else None
                    ),
                    'state': (
                        branch.state.name
                        if branch.state else None
                    ),
                    'manager': (
                        branch.manager.full_name
                        if branch.manager else None
                    ),
                    'business': {
                        'id': branch.business.id,
                        'name': branch.business.name,
                        'industry': branch.business.industry.name,
                    } if branch.business else None,
                
                    'manager': (
                        branch.manager.get_full_name()
                        if branch.manager else None
                    ),
                },
                'period': {
                    'label': period_label,
                    'from': period_start.isoformat(),
                    'to': now.isoformat(),
                },
                'deliveries': {
                    'total': deliveries_total,
                    'completed': deliveries_completed,
                    'failed': deliveries_failed,
                    'pending': deliveries_pending,
                    'in_progress': deliveries_in_progress,
                    'completion_rate': (
                        round(
                            deliveries_completed
                            / deliveries_total * 100, 1
                        )
                        if deliveries_total else 0
                    ),
                },
                'shipments': {
                    'total': shipments_total,
                    'completed': shipments_completed,
                    'failed': shipments_failed,
                    'pending': shipments_pending,
                },
                'revenue': {
                    'total': str(revenue),
                    'currency': 'NGN',
                },
                'drivers': {
                    'total_assigned': total_drivers,
                    'active_today': active_today,
                    'top_performer': top_driver,
                },
                'fleet': {
                    'total_vehicles': vehicles_total,
                    'available': vehicles_available,
                    'on_trip': vehicles_on_trip,
                    'under_maintenance': vehicles_maintenance,
                },
                'dispatch_breakdown': dispatch_breakdown,
            }
        )
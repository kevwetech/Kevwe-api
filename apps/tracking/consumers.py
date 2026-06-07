import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class RideTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time ride tracking
    Riders connect to track their ride in real time
    
    Connect: ws://localhost:8000/ws/rides/{ride_id}/
    """

    async def connect(self):
        self.ride_id = self.scope['url_route']['kwargs']['ride_id']
        self.room_group_name = f'ride_{self.ride_id}'

        # Join ride group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Send connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'ride_id': self.ride_id,
            'message': f'Connected to ride {self.ride_id} tracking',
            'timestamp': str(timezone.now()),
        }))

        # Send current ride status
        ride_data = await self.get_ride_data(self.ride_id)
        if ride_data:
            await self.send(text_data=json.dumps({
                'type': 'ride_status',
                'data': ride_data,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': str(timezone.now()),
            }))

        elif message_type == 'get_status':
            ride_data = await self.get_ride_data(self.ride_id)
            if ride_data:
                await self.send(text_data=json.dumps({
                    'type': 'ride_status',
                    'data': ride_data,
                }))

    async def ride_update(self, event):
        """Receive ride update from channel layer and send to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'ride_update',
            'status': event.get('status'),
            'driver_lat': event.get('driver_lat'),
            'driver_lng': event.get('driver_lng'),
            'message': event.get('message', ''),
            'timestamp': event.get('timestamp', str(timezone.now())),
        }))

    @database_sync_to_async
    def get_ride_data(self, ride_id):
        try:
            from apps.rides.models import Ride
            ride = Ride.objects.get(pk=ride_id)
            return {
                'id': ride.id,
                'reference': ride.reference,
                'status': ride.status,
                'driver_name': ride.driver.user.full_name if ride.driver else None,
                'driver_lat': str(ride.driver_current_lat) if ride.driver_current_lat else None,
                'driver_lng': str(ride.driver_current_lng) if ride.driver_current_lng else None,
                'pickup_address': ride.pickup_address,
                'destination_address': ride.destination_address,
                'estimated_fare': str(ride.estimated_fare) if ride.estimated_fare else None,
            }
        except Exception:
            return None


class DriverRideConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for driver ride management
    Drivers connect to receive ride requests
    and send location updates

    Connect: ws://localhost:8000/ws/driver/rides/{driver_id}/
    """

    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.room_group_name = f'driver_rides_{self.driver_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        # Mark driver as online
        await self.update_driver_status(self.driver_id, True)

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'driver_id': self.driver_id,
            'message': 'You are now online and available for rides',
            'timestamp': str(timezone.now()),
        }))

    async def disconnect(self, close_code):
        # Mark driver as offline
        await self.update_driver_status(self.driver_id, False)

        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'location_update':
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            ride_id = data.get('ride_id')

            # Update driver location in database
            await self.update_driver_location(
                self.driver_id,
                latitude,
                longitude
            )

            # Broadcast to rider if active ride
            if ride_id:
                await self.channel_layer.group_send(
                    f'ride_{ride_id}',
                    {
                        'type': 'ride_update',
                        'status': 'in_progress',
                        'driver_lat': str(latitude),
                        'driver_lng': str(longitude),
                        'message': 'Driver location updated',
                        'timestamp': str(timezone.now()),
                    }
                )

            await self.send(text_data=json.dumps({
                'type': 'location_received',
                'latitude': str(latitude),
                'longitude': str(longitude),
                'timestamp': str(timezone.now()),
            }))

        elif message_type == 'accept_ride':
            ride_id = data.get('ride_id')
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            success = await self.accept_ride(
                self.driver_id,
                ride_id,
                latitude,
                longitude
            )

            if success:
                # Notify rider
                await self.channel_layer.group_send(
                    f'ride_{ride_id}',
                    {
                        'type': 'ride_update',
                        'status': 'accepted',
                        'driver_lat': str(latitude),
                        'driver_lng': str(longitude),
                        'message': 'Driver accepted your ride!',
                        'timestamp': str(timezone.now()),
                    }
                )

                await self.send(text_data=json.dumps({
                    'type': 'ride_accepted',
                    'ride_id': ride_id,
                    'message': 'Ride accepted successfully',
                    'timestamp': str(timezone.now()),
                }))
            else:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Failed to accept ride',
                }))

        elif message_type == 'update_ride_status':
            ride_id = data.get('ride_id')
            new_status = data.get('status')
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            await self.update_ride_status(
                ride_id,
                new_status,
                latitude,
                longitude
            )

            # Notify rider
            await self.channel_layer.group_send(
                f'ride_{ride_id}',
                {
                    'type': 'ride_update',
                    'status': new_status,
                    'driver_lat': str(latitude) if latitude else None,
                    'driver_lng': str(longitude) if longitude else None,
                    'message': f'Ride status: {new_status}',
                    'timestamp': str(timezone.now()),
                }
            )

        elif message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': str(timezone.now()),
            }))

    async def ride_request(self, event):
        """Send new ride request to driver"""
        await self.send(text_data=json.dumps({
            'type': 'new_ride_request',
            'ride_id': event['ride_id'],
            'reference': event['reference'],
            'pickup_address': event['pickup_address'],
            'pickup_lat': event['pickup_lat'],
            'pickup_lng': event['pickup_lng'],
            'destination_address': event['destination_address'],
            'estimated_fare': event['estimated_fare'],
            'rider_name': event['rider_name'],
            'timestamp': str(timezone.now()),
        }))

    @database_sync_to_async
    def update_driver_status(self, driver_id, is_online):
        from apps.drivers.models import DriverProfile
        try:
            driver = DriverProfile.objects.get(pk=driver_id)
            driver.is_online = is_online
            driver.is_available = is_online
            driver.save()
        except DriverProfile.DoesNotExist:
            pass

    @database_sync_to_async
    def update_driver_location(self, driver_id, lat, lng):
        from apps.drivers.models import DriverProfile
        try:
            driver = DriverProfile.objects.get(pk=driver_id)
            driver.current_lat = lat
            driver.current_lng = lng
            driver.last_location_update = timezone.now()
            driver.save()
        except DriverProfile.DoesNotExist:
            pass

    @database_sync_to_async
    def accept_ride(self, driver_id, ride_id, lat, lng):
        from apps.rides.models import Ride, RideTracking
        from apps.drivers.models import DriverProfile
        try:
            ride = Ride.objects.get(pk=ride_id)
            driver = DriverProfile.objects.get(pk=driver_id)
            ride.driver = driver
            ride.status = 'accepted'
            ride.accepted_at = timezone.now()
            ride.driver_current_lat = lat
            ride.driver_current_lng = lng
            ride.save()

            RideTracking.objects.create(
                ride=ride,
                driver_lat=lat or 0,
                driver_lng=lng or 0,
                status='accepted',
                description=f'Driver {driver.user.full_name} accepted your ride'
            )
            return True
        except Exception:
            return False

    @database_sync_to_async
    def update_ride_status(self, ride_id, new_status, lat, lng):
        from apps.rides.models import Ride, RideTracking
        try:
            ride = Ride.objects.get(pk=ride_id)
            ride.status = new_status

            if lat and lng:
                ride.driver_current_lat = lat
                ride.driver_current_lng = lng

            if new_status == 'in_progress':
                ride.started_at = timezone.now()
            elif new_status == 'completed':
                ride.completed_at = timezone.now()
                ride.actual_fare = ride.estimated_fare

            ride.save()

            if lat and lng:
                RideTracking.objects.create(
                    ride=ride,
                    driver_lat=lat,
                    driver_lng=lng,
                    status=new_status,
                    description=f'Status updated to {new_status}'
                )
        except Exception:
            pass


class ShipmentTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time shipment tracking
    Anyone with tracking number can connect

    Connect: ws://localhost:8000/ws/shipments/{tracking_number}/
    """

    async def connect(self):
        self.tracking_number = self.scope['url_route']['kwargs']['tracking_number']
        self.room_group_name = f'shipment_{self.tracking_number}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'tracking_number': self.tracking_number,
            'message': f'Connected to shipment {self.tracking_number} tracking',
            'timestamp': str(timezone.now()),
        }))

        # Send current shipment status
        shipment_data = await self.get_shipment_data(
            self.tracking_number
        )
        if shipment_data:
            await self.send(text_data=json.dumps({
                'type': 'shipment_status',
                'data': shipment_data,
            }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': str(timezone.now()),
            }))

        elif message_type == 'get_status':
            shipment_data = await self.get_shipment_data(
                self.tracking_number
            )
            if shipment_data:
                await self.send(text_data=json.dumps({
                    'type': 'shipment_status',
                    'data': shipment_data,
                }))

    async def shipment_update(self, event):
        """Receive shipment update and send to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'shipment_update',
            'status': event.get('status'),
            'location': event.get('location'),
            'latitude': event.get('latitude'),
            'longitude': event.get('longitude'),
            'description': event.get('description'),
            'timestamp': event.get('timestamp', str(timezone.now())),
        }))

    @database_sync_to_async
    def get_shipment_data(self, tracking_number):
        try:
            from apps.shipments.models import Shipment
            shipment = Shipment.objects.get(
                tracking_number=tracking_number
            )
            return {
                'tracking_number': shipment.tracking_number,
                'reference': shipment.reference,
                'status': shipment.status,
                'current_location': shipment.current_location,
                'current_lat': str(shipment.current_lat) if shipment.current_lat else None,
                'current_lng': str(shipment.current_lng) if shipment.current_lng else None,
                'driver_name': shipment.driver.user.full_name if shipment.driver else None,
                'driver_lat': str(shipment.driver.current_lat) if shipment.driver and shipment.driver.current_lat else None,
                'driver_lng': str(shipment.driver.current_lng) if shipment.driver and shipment.driver.current_lng else None,
                'receiver_name': shipment.receiver_name,
                'delivery_address': shipment.delivery_address,
            }
        except Exception:
            return None


class DriverShipmentConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for driver shipment updates
    Drivers connect to update shipment location

    Connect: ws://localhost:8000/ws/driver/shipments/{driver_id}/
    """

    async def connect(self):
        self.driver_id = self.scope['url_route']['kwargs']['driver_id']
        self.room_group_name = f'driver_shipments_{self.driver_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'driver_id': self.driver_id,
            'message': 'Connected to shipment tracking',
            'timestamp': str(timezone.now()),
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')

        if message_type == 'location_update':
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            tracking_number = data.get('tracking_number')
            location_name = data.get('location_name', '')

            # Update driver location
            await self.update_driver_location(
                self.driver_id,
                latitude,
                longitude
            )

            # Update shipment location
            if tracking_number:
                await self.update_shipment_location(
                    tracking_number,
                    latitude,
                    longitude,
                    location_name
                )

                # Broadcast to shipment tracking group
                await self.channel_layer.group_send(
                    f'shipment_{tracking_number}',
                    {
                        'type': 'shipment_update',
                        'status': 'in_transit',
                        'location': location_name,
                        'latitude': str(latitude),
                        'longitude': str(longitude),
                        'description': 'Driver location updated',
                        'timestamp': str(timezone.now()),
                    }
                )

            await self.send(text_data=json.dumps({
                'type': 'location_received',
                'latitude': str(latitude),
                'longitude': str(longitude),
                'timestamp': str(timezone.now()),
            }))

        elif message_type == 'ping':
            await self.send(text_data=json.dumps({
                'type': 'pong',
                'timestamp': str(timezone.now()),
            }))

    @database_sync_to_async
    def update_driver_location(self, driver_id, lat, lng):
        from apps.drivers.models import DriverProfile
        try:
            driver = DriverProfile.objects.get(pk=driver_id)
            driver.current_lat = lat
            driver.current_lng = lng
            driver.last_location_update = timezone.now()
            driver.save()
        except DriverProfile.DoesNotExist:
            pass

    @database_sync_to_async
    def update_shipment_location(
        self, tracking_number, lat, lng, location_name
    ):
        from apps.shipments.models import Shipment
        try:
            shipment = Shipment.objects.get(
                tracking_number=tracking_number
            )
            shipment.current_lat = lat
            shipment.current_lng = lng
            shipment.current_location = location_name
            shipment.save()
        except Shipment.DoesNotExist:
            pass
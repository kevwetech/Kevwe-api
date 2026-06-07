import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone


class DeliveryTrackingConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time delivery tracking
    Connect: ws://localhost:8000/ws/deliveries/{tracking_number}/
    """

    async def connect(self):
        self.tracking_number = self.scope['url_route']['kwargs']['tracking_number']
        self.room_group_name = f'delivery_{self.tracking_number}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'tracking_number': self.tracking_number,
            'message': f'Connected to delivery {self.tracking_number} tracking',
            'timestamp': str(timezone.now()),
        }))

        # Send current delivery status
        delivery_data = await self.get_delivery_data(
            self.tracking_number
        )
        if delivery_data:
            await self.send(text_data=json.dumps({
                'type': 'delivery_status',
                'data': delivery_data,
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
            delivery_data = await self.get_delivery_data(
                self.tracking_number
            )
            if delivery_data:
                await self.send(text_data=json.dumps({
                    'type': 'delivery_status',
                    'data': delivery_data,
                }))

    async def delivery_update(self, event):
        """Receive delivery update and send to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'delivery_update',
            'status': event.get('status'),
            'location': event.get('location'),
            'latitude': event.get('latitude'),
            'longitude': event.get('longitude'),
            'description': event.get('description'),
            'timestamp': event.get('timestamp', str(timezone.now())),
        }))

    @database_sync_to_async
    def get_delivery_data(self, tracking_number):
        try:
            from apps.deliveries.models import DeliveryRequest
            delivery = DeliveryRequest.objects.get(
                tracking_number=tracking_number
            )
            return {
                'tracking_number': delivery.tracking_number,
                'reference': delivery.reference,
                'status': delivery.status,
                'package_name': delivery.package_name,
                'current_location': delivery.current_location,
                'current_lat': str(delivery.current_lat) if delivery.current_lat else None,
                'current_lng': str(delivery.current_lng) if delivery.current_lng else None,
                'dispatcher_name': delivery.dispatcher.user.full_name if delivery.dispatcher else None,
                'dispatcher_lat': str(delivery.dispatcher.current_lat) if delivery.dispatcher and delivery.dispatcher.current_lat else None,
                'dispatcher_lng': str(delivery.dispatcher.current_lng) if delivery.dispatcher and delivery.dispatcher.current_lng else None,
                'pickup_address': delivery.pickup_address,
                'dropoff_address': delivery.dropoff_address,
            }
        except Exception:
            return None
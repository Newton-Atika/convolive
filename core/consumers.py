import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from django.apps import apps

class EventLikeConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope["url_route"]["kwargs"]["event_id"]
        self.room_group_name = f"event_{self.event_id}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_id = data.get("event_id")
        action = data.get("action")
        user = self.scope["user"]

        if event_id and action in ["like", "unlike"]:
            Event = apps.get_model('core', 'Event')
            event = await sync_to_async(Event.objects.get)(id=event_id)
            if user.is_authenticated:
                if action == "like":
                    await sync_to_async(event.likes.add)(user)
                elif action == "unlike":
                    await sync_to_async(event.likes.remove)(user)
                total_likes = await sync_to_async(lambda: event.likes.count())()
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "like_update",
                        "total_likes": total_likes
                    }
                )

        elif "gift" in data and user.is_authenticated:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "gift",
                    "user": user.username,
                    "gift": data["gift"]
                }
            )

        elif data.get("live_started") is True:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "live_started"
                }
            )

    async def like_update(self, event):
        await self.send(text_data=json.dumps({
            "type": "like_update",
            "total_likes": event["total_likes"]
        }))

    async def gift(self, event):
        await self.send(text_data=json.dumps({
            "type": "gift",
            "user": event["user"],
            "gift": event["gift"]
        }))

    async def live_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "live_started"
        }))


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.room_group_name = f'chat_{self.event_id}'

        try:
            Event = apps.get_model('core', 'Event')
            await sync_to_async(Event.objects.get)(id=self.event_id, is_live=True)
        except Event.DoesNotExist:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            user = self.scope['user']
            username = user.username if user.is_authenticated else 'Anonymous'

            if data.get("type") == "message":
                await self.save_message(username, data["message"])
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': data["message"],
                        'username': username
                    }
                )
            elif data.get("type") in ["mic_request", "mic_approved", "mic_denied", "mic_revoked"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": data["type"],
                        "username": data["username"]
                    }
                )
            elif data.get("type") == "mute_user":
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "mute_user",
                        "username": data["username"]
                    }
                )
        except Exception as e:
            print(f"Error in receive: {e}")

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat',
            'message': event['message'],
            'username': event['username']
        }))

    async def mic_request(self, event):
        await self.send(text_data=json.dumps({
            "type": "mic_request",
            "username": event["username"]
        }))

    async def mic_approved(self, event):
        await self.send(text_data=json.dumps({
            "type": "mic_approved",
            "username": event["username"]
        }))

    async def mic_denied(self, event):
        await self.send(text_data=json.dumps({
            "type": "mic_denied",
            "username": event["username"]
        }))

    async def mic_revoked(self, event):
        await self.send(text_data=json.dumps({
            "type": "mic_revoked",
            "username": event["username"]
        }))

    async def mute_user(self, event):
        await self.send(text_data=json.dumps({
            "type": "mute_user",
            "username": event["username"]
        }))

    @sync_to_async
    def save_message(self, username, message):
        Event = apps.get_model('core', 'Event')
        ChatMessage = apps.get_model('core', 'ChatMessage')
        event = Event.objects.get(id=self.event_id)
        ChatMessage.objects.create(event=event, username=username, message=message)


class StreamConsumer(AsyncWebsocketConsumer):
    organizers = {}

    async def connect(self):
        self.event_id = self.scope["url_route"]["kwargs"]["event_id"]
        self.group_name = f"stream_{self.event_id}"
        user = self.scope["user"]

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        if await self.is_organizer(user, self.event_id):
            StreamConsumer.organizers[self.event_id] = self.channel_name
            self.is_organizer = True
        else:
            self.is_organizer = False

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if self.is_organizer:
            StreamConsumer.organizers.pop(self.event_id, None)
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "organizer_left"}
            )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")
        user = self.scope["user"]

        if self.is_organizer:
            if msg_type == "organizer_answer":
                target_channel = data["target"]
                await self.channel_layer.send(
                    target_channel,
                    {
                        "type": "send_answer_to_viewer",
                        "answer": data["answer"]
                    }
                )
            elif msg_type == "organizer_ice":
                target_channel = data["target"]
                await self.channel_layer.send(
                    target_channel,
                    {
                        "type": "send_ice_to_viewer",
                        "candidate": data["candidate"]
                    }
                )
            elif msg_type == "live_started":
                await self.channel_layer.group_send(
                    self.group_name,
                    {"type": "live_started"}
                )
        else:
            organizer_channel = StreamConsumer.organizers.get(self.event_id)
            if not organizer_channel:
                await self.send(text_data=json.dumps({
                    "type": "error",
                    "message": "Organizer not connected"
                }))
                return

            if msg_type == "viewer_offer":
                await self.channel_layer.send(
                    organizer_channel,
                    {
                        "type": "send_offer_to_organizer",
                        "viewer_id": self.channel_name,
                        "offer": data["offer"]
                    }
                )
            elif msg_type == "viewer_ice":
                await self.channel_layer.send(
                    organizer_channel,
                    {
                        "type": "send_ice_to_organizer",
                        "candidate": data["candidate"],
                        "viewer_id": self.channel_name
                    }
                )

    async def send_offer_to_organizer(self, event):
        if self.is_organizer:
            await self.send(text_data=json.dumps({
                "type": "viewer_offer",
                "viewer_id": event["viewer_id"],
                "offer": event["offer"]
            }))

    async def send_answer_to_viewer(self, event):
        if not self.is_organizer:
            await self.send(text_data=json.dumps({
                "type": "organizer_answer",
                "answer": event["answer"]
            }))

    async def send_ice_to_organizer(self, event):
        if self.is_organizer:
            await self.send(text_data=json.dumps({
                "type": "viewer_ice",
                "candidate": event["candidate"],
                "viewer_id": event["viewer_id"]
            }))

    async def send_ice_to_viewer(self, event):
        if not self.is_organizer:
            await self.send(text_data=json.dumps({
                "type": "organizer_ice",
                "candidate": event["candidate"]
            }))

    async def live_started(self, event):
        await self.send(text_data=json.dumps({
            "type": "live_started"
        }))

    async def organizer_left(self, event):
        await self.send(text_data=json.dumps({
            "type": "organizer_left",
            "message": "Organizer has disconnected."
        }))

    @sync_to_async
    def is_organizer(self, user, event_id):
        Event = apps.get_model('core', 'Event')
        try:
            event = Event.objects.get(id=event_id)
            return user.is_authenticated and user.id == event.organizer_id
        except Event.DoesNotExist:
            return False

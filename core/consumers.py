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

from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model

class StreamConsumer(AsyncWebsocketConsumer):
    organizers = {}  # event_id => channel_name
    viewers = {}     # event_id => { username: channel_name }

    async def connect(self):
        self.event_id = self.scope['url_route']['kwargs']['event_id']
        self.group_name = f"stream_{self.event_id}"
        self.user = self.scope["user"]
        self.username = str(self.user.username) if self.user.is_authenticated else "anonymous"
        self.user_id = str(self.user.pk) if self.user.is_authenticated else "0"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Organizer detection
        self.is_organizer = self.user.is_authenticated and self.scope["session"].get("organizer_pk") == str(self.user.pk)

        if self.is_organizer:
            StreamConsumer.organizers[self.event_id] = self.channel_name
            print(f"[ORGANIZER CONNECTED] {self.username} -> {self.channel_name} for event {self.event_id}")
        else:
            StreamConsumer.viewers.setdefault(self.event_id, {})[self.username] = self.channel_name
            print(f"[VIEWER CONNECTED] {self.username} -> {self.channel_name} for event {self.event_id}")

        await self.accept()

        # Notify clients of stream status
        if self.event_id in StreamConsumer.organizers and not self.is_organizer:
            await self.send(json.dumps({"type": "live_started"}))
            print(f"[LIVE_STARTED] Notified {self.username} for event {self.event_id}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if self.is_organizer:
            StreamConsumer.organizers.pop(self.event_id, None)
            print(f"[ORGANIZER DISCONNECTED] {self.username} from event {self.event_id}")
        else:
            viewers = StreamConsumer.viewers.get(self.event_id, {})
            viewers.pop(self.username, None)
            print(f"[VIEWER DISCONNECTED] {self.username} from event {self.event_id}")

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get("type")

        if msg_type == "live_started" and self.is_organizer:
            print(f"[LIVE_STARTED] Broadcasting for event {self.event_id}")
            await self.channel_layer.group_send(
                self.group_name,
                {"type": "broadcast_live_started"}
            )
        elif msg_type == "check_stream":
            if self.event_id in StreamConsumer.organizers:
                await self.send(json.dumps({"type": "stream_active"}))
                print(f"[CHECK_STREAM] Organizer live for event {self.event_id}")
            else:
                print(f"[CHECK_STREAM] Organizer not live for event {self.event_id}")
        elif msg_type == "mic_request" and not self.is_organizer:
            print(f"[MIC_REQUEST] {self.username} for event {self.event_id}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "mic_request",
                    "username": self.username
                }
            )
        elif msg_type == "like_update":
            print(f"[LIKE_UPDATE] {self.username} action: {data['action']}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "like_update",
                    "total_likes": data.get("total_likes", 0)
                }
            )
        elif msg_type == "gift":
            print(f"[GIFT] {data['gift']} from {self.username}")
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "gift",
                    "gift": data["gift"],
                    "user": self.username
                }
            )

    async def broadcast_live_started(self, event):
        print(f"[BROADCAST_LIVE_STARTED] Sending to group stream_{self.event_id}")
        await self.send(json.dumps({"type": "live_started"}))

    async def mic_request(self, event):
        await self.send(json.dumps({
            "type": "mic_request",
            "username": event["username"]
        }))

    async def like_update(self, event):
        await self.send(json.dumps({
            "type": "like_update",
            "total_likes": event["total_likes"]
        }))

    async def gift(self, event):
        await self.send(json.dumps({
            "type": "gift",
            "gift": event["gift"],
            "user": event["user"]
        }))

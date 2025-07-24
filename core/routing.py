from django.urls import re_path
from . import consumers
websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<event_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/event/(?P<event_id>\d+)/$', consumers.EventLikeConsumer.as_asgi()),
    re_path(r'ws/stream/(?P<event_id>[\w\-]+)/$', consumers.StreamConsumer.as_asgi())
  # ADD THIS LINE
]

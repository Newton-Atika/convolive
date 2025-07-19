# utils/livekit_utils.py
import os
from livekit import api

LIVEKIT_URL = 'wss://convolive-1v7m4e6q.livekit.cloud'
LIVEKIT_API_KEY = "API3mLfygt68Dxs"
LIVEKIT_API_SECRET = "nyDCJgfJ2OF8daESzSje8rrVJnZBWFzv5vXKZNeqF1oA"
WEB_SOCKET_URL = "wss://convolive-1v7m4e6q.livekit.cloud"
def create_token(identity: str, room: str, publish: bool):
    at = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
    at.with_identity(identity).with_name(identity)
    grants = api.VideoGrants(room_join=True, room=room, can_subscribe=True)
    if publish:
        grants.can_publish = True
        grants.can_publish_data = True
    at.with_video_grants(grants)
    return at.to_jwt()

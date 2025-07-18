import mux_python
from mux_python.rest import ApiException
from django.conf import settings

def create_mux_stream():
    configuration = mux_python.Configuration()
    configuration.username = settings.MUX_TOKEN_ID
    configuration.password = settings.MUX_TOKEN_SECRET
    api_client = mux_python.ApiClient(configuration)

    live_api = mux_python.LiveStreamsApi(api_client)

    stream_create_req = mux_python.CreateLiveStreamRequest(
        playback_policy=["public"],
        new_asset_settings={"playback_policy": ["public"]},
        reconnect_window=60,
        test=False
    )

    try:
        live_stream = live_api.create_live_stream(stream_create_req)
        return {
            "stream_key": live_stream.data.stream_key,
            "playback_id": live_stream.data.playback_ids[0].id,
        }
    except ApiException as e:
        print("Error creating Mux stream:", e)
        return None

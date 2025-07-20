from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import EventForm, CustomUserCreationForm
from .models import Event, LiveStatus,Gift
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import mux_python
from mux_python.rest import ApiException
from mux_python.models.create_asset_request import CreateAssetRequest
from mux_python.models.create_playback_id_request import CreatePlaybackIDRequest
from mux_python.models.create_live_stream_request import CreateLiveStreamRequest

configuration = mux_python.Configuration()
configuration.username = settings.MUX_TOKEN_ID
configuration.password = settings.MUX_TOKEN_SECRET
# views.py
from django.shortcuts import render, redirect, get_object_or_404
from .forms import EventForm
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.conf import settings

# Mux SDK imports
import mux_python
from mux_python.models.create_live_stream_request import CreateLiveStreamRequest

# Mux config
configuration = mux_python.Configuration()
configuration.username = settings.MUX_TOKEN_ID
configuration.password = settings.MUX_TOKEN_SECRET
mux_api = mux_python.LiveStreamsApi(mux_python.ApiClient(configuration))

from mux_python.models import CreateLiveStreamRequest
from .utils.mux import mux_api

from django.http import JsonResponse
from .utils.livekit_utils import create_token
# views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
import hmac
import hashlib
import time
import base64
import json
from .models import Event, LiveStatus, LiveParticipant, Payment
import os
import logging


from django.shortcuts import render
from django.http import JsonResponse
import random
import time
from agora_token_builder import RtcTokenBuilder, RtcTokenBuilderRole
from .models import LiveParticipant, Event  # Adjust model names as needed
import json
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.csrf import csrf_exempt
import os
import logging

logger = logging.getLogger(__name__)

# Load credentials from environment variables
AGORA_APP_ID = os.getenv("AGORA_APP_ID", "5a7551a1892a47258b7e9f7f264e6196")
AGORA_APP_CERTIFICATE = os.getenv("AGORA_APP_CERTIFICATE", "27b20c8f267e4235b207d6aef1bf7dea")

def landing(request):
    events = Event.objects.all()
    return render(request, 'landing.html', {'events': events})

def join_event(request, event_id):
    try:
        event = Event.objects.get(id=event_id)
        user_has_paid = True  # Implement payment check logic
        participants = LiveParticipant.objects.filter(event=event)
        context = {
            'event': event,
            'user_has_paid': user_has_paid,
            'participants': participants,
            'organizer_id': event.organizer.id if event.organizer else 0,
            'participant_count': participants.count(),
        }
        return render(request, 'index.html', context)
    except Event.DoesNotExist:
        return render(request, '404.html', status=404)

def end_event(request, event_id):
    # Existing end event logic
    pass

def getToken(request):
    channel = request.GET.get('channel')
    if not channel:
        return JsonResponse({'error': 'Channel is required'}, status=400)
    uid = random.randint(1, 230)
    current_time = int(time.time())
    expiration = current_time + 3600  # 1 hour

    token = RtcTokenBuilder.buildTokenWithUid(
        AGORA_APP_ID,
        AGORA_APP_CERTIFICATE,
        channel,
        uid,
        RtcTokenBuilderRole.PUBLISHER,
        expiration
    )

    logger.debug(f"Generated token for channel {channel}, uid {uid}: {token}")
    return JsonResponse({'token': token, 'uid': uid}, safe=False)

@require_POST
def createMember(request):
    try:
        data = json.loads(request.body)
        member, created = LiveParticipant.objects.get_or_create(
            user__username=data['name'],  # Adjust field based on your model
            uid=data['UID'],
            event_id=data['room_name']  # Use event_id as room_name
        )
        return JsonResponse({'name': data['name']}, safe=False)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def getMember(request):
    uid = request.GET.get('UID')
    room_name = request.GET.get('room_name')
    if not uid or not room_name:
        return JsonResponse({'error': 'UID and room_name are required'}, status=400)
    try:
        member = LiveParticipant.objects.get(uid=uid, event_id=room_name)
        return JsonResponse({'name': member.user.username}, safe=False)  # Adjust field
    except LiveParticipant.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)

@require_POST
def deleteMember(request):
    try:
        data = json.loads(request.body)
        member = LiveParticipant.objects.get(
            user__username=data['name'],
            uid=data['UID'],
            event_id=data['room_name']
        )
        member.delete()
        return JsonResponse('Member deleted', safe=False)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except LiveParticipant.DoesNotExist:
        return JsonResponse({'error': 'Member not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
def create_token(identity, room, can_publish=False):
    now = int(time.time())
    exp = now + 3600  # Token valid for 1 hour

    payload = {
        "jti": f"{identity}-{now}",
        "iss": settings.LIVEKIT_API_KEY,
        "sub": identity,
        "aud": "livekit",
        "exp": exp,
        "nbf": now,
        "video": {
            "roomJoin": True,
            "room": room,
            "canPublish": can_publish,
            "canSubscribe": True,
        },
    }

    token = jwt.encode(payload, settings.LIVEKIT_API_SECRET, algorithm="HS256")
    return token


def get_livekit_token(request, event_id):
    user = request.user
    room = f"event_{event_id}"

    # Only the organizer is allowed to publish
    event = Event.objects.get(pk=event_id)
    can_publish = user.pk == event.organizer_id

    token = create_token(user.username, room, can_publish)

    return JsonResponse({
        "token": token,
        "url": settings.LIVEKIT_URL,
        "room": room
    })


def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()

            # ✅ Create Mux Live Stream
            mux_stream = mux_api.create_live_stream(CreateLiveStreamRequest(
                playback_policy=["public"],
                new_asset_settings={"playback_policy": ["public"]},
                test=False  # Set to True for testing without cost
            ))

            # ✅ Save stream info
            event.mux_stream_key = mux_stream.data.stream_key
            event.mux_playback_id = mux_stream.data.playback_ids[0].id
            event.save()

            return redirect('event_detail', event_id=event.id)
    else:
        form = EventForm()

    return render(request, 'create_event.html', {'form': form})

@login_required
def create_conversation(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        form = ConversationForm(request.POST)
        if form.is_valid():
            conversation = form.save(commit=False)
            conversation.event = event
            conversation.creator = request.user
            conversation.save()
            return redirect('conversation_detail', event_id=event.id, conversation_id=conversation.id)
    else:
        form = ConversationForm()

    return render(request, 'create_conversation.html', {'form': form, 'event': event})

# views.py
from django.views.decorators.csrf import csrf_exempt
import uuid

@login_required
@csrf_exempt
def initiate_gift_payment(request, event_id):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        event = get_object_or_404(Event, id=event_id)
        user = request.user
        reference = str(uuid.uuid4())
        callback_url = request.build_absolute_uri('/verify-gift-payment/')

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "email": user.email,
            "amount": int(amount) * 100,  # convert to kobo
            "reference": reference,
            "callback_url": callback_url,
        }

        # store reference temporarily in session
        request.session['gift_reference'] = reference
        request.session['gift_amount'] = amount
        request.session['gift_event_id'] = event_id

        try:
            response = requests.post("https://api.paystack.co/transaction/initialize", headers=headers, json=data)
            response.raise_for_status()
            res_data = response.json()
            return redirect(res_data['data']['authorization_url'])
        except Exception as e:
            return render(request, "payment_error.html", {"error": str(e)})
    return redirect('join_event', event_id=event_id)
@login_required
def verify_gift_payment(request):
    reference = request.GET.get('reference')
    expected_ref = request.session.get('gift_reference')

    event = None  # Initialize event

    if not reference or reference != expected_ref:
        event_id = request.session.get('gift_event_id')
        if event_id:
            event = Event.objects.filter(id=event_id).first()
        return render(request, "payment_error.html", {"error": "Invalid reference.", "event": event})

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        res = requests.get(f"https://api.paystack.co/transaction/verify/{reference}", headers=headers)
        res_data = res.json()

        if res_data['data']['status'] == 'success':
            # Save gift
            event_id = request.session.get('gift_event_id')
            event = get_object_or_404(Event, id=event_id)
            amount = request.session.get('gift_amount')

            Gift.objects.create(user=request.user, event=event, amount=amount)

            # Optionally clear session
            for key in ['gift_reference', 'gift_event_id', 'gift_amount']:
                request.session.pop(key, None)

            return redirect('join_event', event_id=event.id)

        event_id = request.session.get('gift_event_id')
        if event_id:
            event = Event.objects.filter(id=event_id).first()
        return render(request, "payment_error.html", {
            "error": "Gift payment not successful.",
            "event": event
        })

    except Exception as e:
        event_id = request.session.get('gift_event_id')
        if event_id:
            event = Event.objects.filter(id=event_id).first()
        return render(request, "payment_error.html", {"error": str(e), "event": event})
# views.py

import uuid
import requests
from django.conf import settings
from django.shortcuts import redirect

def initiate_paystack_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Check if already paid
    if Payment.objects.filter(user=request.user, event=event, verified=True).exists():
        return redirect('join_event', event_id=event.id)

    # Create unique reference
    reference = str(uuid.uuid4())

    # Create Payment record with verified=False
    payment = Payment.objects.create(
        user=request.user,
        event=event,
        reference=reference,
        amount=50  # Fixed price
    )

    callback_url = request.build_absolute_uri(reverse('verify_payment')) + f"?ref={reference}"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": request.user.email,
        "amount": int(payment.amount * 100),  # Convert to kobo
        "reference": reference,
        "callback_url": callback_url,
    }

    response = requests.post('https://api.paystack.co/transaction/initialize', json=data, headers=headers)
    response_data = response.json()

    if response.status_code == 200 and response_data['status']:
        return redirect(response_data['data']['authorization_url'])
    else:
        return HttpResponse("Error initiating payment", status=400)
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def verify_payment(request):
    reference = request.GET.get('ref')
    payment = get_object_or_404(Payment, reference=reference)

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    response = requests.get(url, headers=headers)
    res_data = response.json()

    if res_data['status'] and res_data['data']['status'] == 'success':
        payment.verified = True
        payment.save()
        return redirect('join_event', event_id=payment.event.id)

    return HttpResponse("Payment not successful", status=400)


from django.db.models.functions import Cast
from django.db.models import Sum, IntegerField
from .models import Event, Gift, Payment
@login_required
def organizer_dashboard(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_organizer:
        return render(request, 'not_authorized.html')

    my_events = Event.objects.filter(organizer=request.user).order_by('-start_time')

    total_gift_revenue = Gift.objects.filter(event__organizer=request.user).annotate(
        amount_int=Cast('amount', IntegerField())
    ).aggregate(total=Sum('amount_int'))['total'] or 0

    total_join_revenue = Payment.objects.filter(event__organizer=request.user, verified=True).aggregate(
        total=Sum('amount')
    )['total'] or 0

    total_revenue = (total_gift_revenue or 0) + (total_join_revenue or 0)

    return render(request, 'organizer_dashboard.html', {
        'my_events': my_events,
        'total_gift_revenue': total_gift_revenue,
        'total_join_revenue': total_join_revenue,
        'total_revenue': total_revenue,
    })


@user_passes_test(lambda u: u.is_superuser)
def manage_organizers(request):
    users = User.objects.all().exclude(is_superuser=True)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('organizers')
        for user in users:
            user.profile.is_organizer = str(user.id) in selected_ids
            user.profile.save()
        return HttpResponseRedirect(reverse('manage_organizers'))

    return render(request, 'manage_organizers.html', {'users': users})


def landing_page(request):
    now = timezone.now()
    next_hour = now + timedelta(hours=1)

    active_event_ids = LiveStatus.objects.filter(is_active=True).values_list('event_id', flat=True)

    lives_now = Event.objects.filter(is_live=True, start_time__lte=now, id__in=active_event_ids)
    conversations_now = Event.objects.filter(is_live=False, start_time__lte=now, id__in=active_event_ids)
    upcoming = Event.objects.filter(start_time__gt=now, start_time__lte=next_hour)
    ended = Event.objects.exclude(id__in=active_event_ids)

    return render(request, 'landing.html', {
        'lives_now': lives_now,
        'conversations_now': conversations_now,
        'upcoming': upcoming,
        'ended': ended,
    })


def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('landing')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('landing')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})
def end_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Ensure only the organizer can end the event
    if request.user != event.organizer:
        return redirect('landing')

    event.is_live = False
    event.save()
    # Optionally notify WebSocket consumers if implemented
    return redirect('landing')

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Event

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    user_has_liked = False
    if request.user.is_authenticated:
        user_has_liked = event.likes.filter(id=request.user.id).exists()
    return render(request, 'event_detail.html', {'event': event, 'user_has_liked': user_has_liked})
from django.views.decorators.http import require_POST
# views.py

from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import json

from django.views.decorators.csrf import csrf_exempt
@csrf_exempt
@login_required
def toggle_like(request):
    data = json.loads(request.body)
    event_id = data.get("event_id")
    event = get_object_or_404(Event, id=event_id)

    if request.user in event.likes.all():
        event.likes.remove(request.user)
        liked = False
    else:
        event.likes.add(request.user)
        liked = True

    total_likes = event.likes.count()

    # Send update to WebSocket group
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"event_{event_id}",
        {
            "type": "like_update",
            "total_likes": total_likes
        }
    )

    return JsonResponse({"liked": liked, "total_likes": total_likes})
# core/views.py


def stream_view(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'stream.html', {'event': event})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import EventForm, CustomUserCreationForm
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import mux_python
from mux_python.rest import ApiException
from mux_python.models.create_asset_request import CreateAssetRequest
from mux_python.models.create_playback_id_request import CreatePlaybackIDRequest
from mux_python.models.create_live_stream_request import CreateLiveStreamRequest
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import uuid
import requests
import logging
from django.db.models import Sum, IntegerField, Count  # Added Count to the import
from django.db.models.functions import Cast
from .models import Event, LiveStatus, Gift, Payment, LiveParticipant
from .forms import EventForm
from mux_python.models.create_live_stream_request import CreateLiveStreamRequest
import mux_python
from django.conf import settings
configuration = mux_python.Configuration()
configuration.username = settings.MUX_TOKEN_ID
configuration.password = settings.MUX_TOKEN_SECRET
# views.py
from .forms import EventForm
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
from django.http import JsonResponse
import hmac
import hashlib
import time
import base64
import json
from .models import Event, LiveStatus, LiveParticipant, Payment
import os
import logging


import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
import json
from django.conf import settings
from .RtcTokenBuilder2 import RtcTokenBuilder, Role_Publisher, Role_Subscriber
from .models import Event  # Adjust based on your app structure

# Global constants
AGORA_APP_ID = getattr(settings, 'AGORA_APP_ID', None)
AGORA_APP_CERTIFICATE = getattr(settings, 'AGORA_APP_CERTIFICATE', None)
TOKEN_EXPIRE = 3600  # 1 hour
PRIVILEGE_EXPIRE = 3600  # 1 hour

logger = logging.getLogger(__name__)

def build_agora_token(channel_name, uid, role):
    if not AGORA_APP_ID or not AGORA_APP_CERTIFICATE:
        logger.error("Agora credentials are not configured.")
        raise ValueError("Agora credentials are not configured.")

    # Map role to Agora's Role_Publisher or Role_Subscriber
    agora_role = Role_Publisher if role == 'publisher' else Role_Subscriber

    logger.debug(f"Generating token with app_id={AGORA_APP_ID}, channel={channel_name}, uid={uid}, role={agora_role}, expire={TOKEN_EXPIRE}")

    token = RtcTokenBuilder.build_token_with_uid(
        app_id=AGORA_APP_ID,
        app_certificate=AGORA_APP_CERTIFICATE,
        channel_name=channel_name,
        uid=str(uid),
        role=agora_role,
        token_expire=TOKEN_EXPIRE,
        privilege_expire=PRIVILEGE_EXPIRE
    )

    logger.debug(f"Generated token: {token}")
    return token, TOKEN_EXPIRE

@csrf_exempt
@require_POST
def generate_agora_token(request):
    try:
        body = json.loads(request.body)
        channel_name = body.get("channel_name")
        uid = body.get("uid")
        role = body.get("role", "subscriber")  # Default to subscriber

        if not channel_name or uid is None:
            logger.error("Missing required fields: channel_name or uid.")
            return JsonResponse({"error": "Missing required fields: channel_name and uid."}, status=400)

        token, token_expire = build_agora_token(
            channel_name=channel_name,
            uid=uid,
            role=role
        )

        return JsonResponse({
            "token": token,
            "channel_name": channel_name,
            "uid": uid,
            "role": role,
            "expires_in": token_expire
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON input.")
        return JsonResponse({"error": "Invalid JSON input."}, status=400)
    except ValueError as e:
        logger.error(f"Token generation failed: {str(e)}")
        return JsonResponse({"error": str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Token generation failed: {str(e)}")
        return JsonResponse({"error": f"Token generation failed: {str(e)}"}, status=500)

def get_agora_token(request):
    try:
        event_id = request.GET.get("event_id")
        if not event_id:
            logger.error("Missing event_id parameter.")
            return JsonResponse({'error': 'Missing event_id parameter'}, status=400)

        event = get_object_or_404(Event, id=event_id)
        channel_name = str(event.id)
        uid = request.user.id if request.user.is_authenticated else 0
        role = 'publisher' if request.user.is_authenticated and request.user == event.organizer else 'subscriber'

        logger.debug(f"Generating token for event_id={event_id}, channel={channel_name}, uid={uid}, role={role}")

        token, token_expire = build_agora_token(
            channel_name=channel_name,
            uid=uid,
            role=role
        )

        return JsonResponse({
            'token': token,
            'uid': uid,
            'channel': channel_name,
            'role': role,
        })
    except ValueError as e:
        logger.error(f"Failed to generate Agora token: {str(e)}")
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        logger.exception(f"Failed to generate Agora token: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from datetime import timedelta
import uuid
import requests
import logging
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from .models import Event, LiveStatus, Gift, Payment, LiveParticipant
from .forms import EventForm
from mux_python.models.create_live_stream_request import CreateLiveStreamRequest
import mux_python
from django.conf import settings

# Initialize Mux API client
mux_api = mux_python.LiveStreamsApi()

# Set up logging
logger = logging.getLogger(__name__)

def landing_page(request):
    now = timezone.now()
    next_hour = now + timedelta(hours=1)
    
    lives_now = Event.objects.filter(
        is_live=True,
        start_time__lte=now,
        livestatus__is_active=True
    ).select_related('organizer').annotate(
        viewer_count=Count('liveparticipant'),
        like_count=Count('eventlike')
    )
    
    conversations_now = Event.objects.filter(
        is_live=False,
        start_time__lte=now,
        livestatus__is_active=True
    ).select_related('organizer').annotate(
        viewer_count=Count('liveparticipant'),
        like_count=Count('eventlike')
    )
    
    upcoming = Event.objects.filter(
        start_time__gt=now,
        start_time__lte=next_hour,
        livestatus__is_active=True
    ).select_related('organizer').annotate(
        viewer_count=Count('liveparticipant'),
        like_count=Count('eventlike')
    )
    
    return render(request, 'landing.html', {
        'lives_now': lives_now,
        'conversations_now': conversations_now,
        'upcoming': upcoming,
    })

@login_required
def organizer_dashboard(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_organizer:
        return render(request, 'not_authorized.html')
    
    my_events = Event.objects.filter(organizer=request.user).select_related('livestatus').order_by('-start_time')
    
    # Cast Gift.amount to IntegerField for summation
    total_gift_revenue = Gift.objects.filter(event__organizer=request.user).annotate(
        amount_int=Cast('amount', IntegerField())
    ).aggregate(total=Sum('amount_int'))['total'] or 0
    
    total_join_revenue = Payment.objects.filter(event__organizer=request.user, verified=True).aggregate(total=Sum('amount'))['total'] or 0
    total_revenue = (total_gift_revenue or 0) + (total_join_revenue or 0)
    
    return render(request, 'organizer_dashboard.html', {
        'my_events': my_events,
        'total_gift_revenue': total_gift_revenue,
        'total_join_revenue': total_join_revenue,
        'total_revenue': total_revenue,
    })

@login_required
def toggle_event_status(request, event_id):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_organizer:
        return render(request, 'not_authorized.html')
    
    event = Event.objects.filter(id=event_id, organizer=request.user).first()
    if not event:
        messages.error(request, "Event not found or you are not the organizer.")
        return redirect('organizer_dashboard')
    
    live_status, created = LiveStatus.objects.get_or_create(event=event, defaults={'is_active': True})
    if request.method == 'POST':
        live_status.is_active = not live_status.is_active
        live_status.save()
        status = "active" if live_status.is_active else "inactive"
        messages.success(request, f"Event '{event.title}' is now {status}.")
    
    return redirect('organizer_dashboard')

@login_required
def create_event(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_organizer:
        return render(request, 'not_authorized.html')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            
            # Ensure start_time is timezone-aware in EAT (Africa/Nairobi)
            start_time = form.cleaned_data['start_time']
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.get_default_timezone())
            event.start_time = start_time
            
            event.save()
            
            # Create LiveStatus with is_active=True
            LiveStatus.objects.create(event=event, is_active=True)
            
            # Create Mux Live Stream for live events
            if event.is_live:
                try:
                    mux_stream = mux_api.create_live_stream(CreateLiveStreamRequest(
                        playback_policy=["public"],
                        new_asset_settings={"playback_policy": ["public"]},
                        test=False
                    ))
                    event.mux_stream_key = mux_stream.data.stream_key
                    event.mux_playback_id = mux_stream.data.playback_ids[0].id
                    event.save()
                except Exception as e:
                    logger.error(f"Mux stream creation failed for event {event.id}: {str(e)}")
                    messages.error(request, "Failed to create live stream. Event created without streaming.")
            
            messages.success(request, f"{'Live event' if event.is_live else 'Conversation'} '{event.title}' created successfully.")
            return redirect('join_event', event_id=event.id)
    else:
        form = EventForm()
    
    return render(request, 'create_event.html', {'form': form})

@login_required
def create_conversation(request):
    if not hasattr(request.user, 'profile') or not request.user.profile.is_organizer:
        return render(request, 'not_authorized.html')
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.is_live = False  # Force is_live=False for conversations
            
            # Ensure start_time is timezone-aware in EAT (Africa/Nairobi)
            start_time = form.cleaned_data['start_time']
            if timezone.is_naive(start_time):
                start_time = timezone.make_aware(start_time, timezone.get_default_timezone())
            event.start_time = start_time
            
            event.save()
            
            # Create LiveStatus with is_active=True
            LiveStatus.objects.create(event=event, is_active=True)
            
            messages.success(request, f"Conversation '{event.title}' created successfully.")
            return redirect('join_event', event_id=event.id)
    else:
        form = EventForm(initial={'is_live': False})
    
    return render(request, 'create_conversation.html', {'form': form})

logger = logging.getLogger(__name__)

@login_required
def join_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Check if the event has ended
    try:
        status = LiveStatus.objects.get(event=event)
        if not status.is_active:
            logger.info(f"User {request.user.id} attempted to join inactive event {event.id}")
            messages.error(request, f"The {'live event' if event.is_live else 'conversation'} has ended.")
            return render(request, 'live_has_ended.html', {'event': event})
    except LiveStatus.DoesNotExist:
        logger.warning(f"No LiveStatus for event {event.id}")
        pass

    # Conversations require payment, live events do not
    has_paid = False
    if not event.is_live:
        payment_query = Payment.objects.filter(user=request.user, event=event, verified=True)
        has_paid = payment_query.exists()
        logger.debug(f"Payment check for user {request.user.id}, event {event.id}: has_paid={has_paid}, payments={list(payment_query.values('reference', 'verified', 'created_at'))}")
        if not has_paid:
            logger.info(f"User {request.user.id} needs payment for conversation {event.id}")
            messages.info(request, "Payment of 50 KES is required to join this conversation.")
            return redirect('pay_event', event_id=event.id)

    # Add user as a live participant
    LiveParticipant.objects.get_or_create(event=event, user=request.user)

    # Get participant count
    participant_count = LiveParticipant.objects.filter(event=event).count()

    # If organizer, list all participants
    participants = []
    if request.user == event.organizer:
        participants = LiveParticipant.objects.filter(event=event).select_related('user')

    is_organizer = request.user.is_authenticated and request.user == event.organizer

    logger.info(f"User {request.user.id} joined {'live event' if event.is_live else 'conversation'} {event.id}, has_paid: {has_paid}")

    return render(request, 'index.html', {
        'event': event,
        'has_paid': has_paid,
        'participants': participants,
        'participant_count': participant_count,
        'is_organizer': 'true' if is_organizer else 'false',
        'organizer_id': event.organizer.pk,
        'mux_playback_id': event.mux_playback_id,
    })
import uuid
import logging
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.contrib import messages

from .models import Event, Payment  # adjust path if different

logger = logging.getLogger(__name__)

def initiate_paystack_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # Live events don't require payment
    if event.is_live:
        logger.info(f"User {request.user.id} joining live event {event.id} without payment")
        return redirect('join_event', event_id=event.id)

    # Check if already paid
    if Payment.objects.filter(user=request.user, event=event, verified=True).exists():
        logger.info(f"User {request.user.id} already paid for conversation {event.id}")
        return redirect('join_event', event_id=event.id)

    # Create unique reference
    reference = str(uuid.uuid4())

    # Create Payment record with verified=False
    payment = Payment.objects.create(
        user=request.user,
        event=event,
        reference=reference,
        amount=60  # Fixed price in KES
    )

    callback_url = request.build_absolute_uri(
        reverse('verify_payment')
    ) + f"?ref={reference}"

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    data = {
        "email": request.user.email,
        "amount": int(payment.amount * 100),  # Paystack expects amount in subunits
        "reference": reference,
        "currency": "KES",  # ✅ Important for Kenya
        "callback_url": callback_url,
    }

    try:
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json=data,
            headers=headers
        )
        response.raise_for_status()
        response_data = response.json()

        logger.info(f"Paystack init response: {response_data}")  # ✅ Log everything

        if (
            response_data.get('status')
            and 'data' in response_data
            and 'authorization_url' in response_data['data']
        ):
            logger.info(
                f"Payment initiated for user {request.user.id}, conversation {event.id}, reference {reference}"
            )
            return redirect(response_data['data']['authorization_url'])
        else:
            logger.error(f"Paystack initialization failed for reference {reference}: {response_data}")
            payment.delete()
            messages.error(request, "Failed to initiate payment. Please try again.")
            return redirect('join_event', event_id=event.id)

    except requests.RequestException as e:
        logger.error(f"Paystack API error for reference {reference}: {str(e)}")
        payment.delete()
        messages.error(request, "Payment service unavailable. Please try again later.")
        return redirect('join_event', event_id=event.id)


from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
import requests
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

def verify_payment(request):
    reference = request.GET.get("reference") or request.GET.get("ref")
    if not reference:
        messages.error(request, "Invalid payment reference")
        return redirect("home")  # fallback

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    url = f"https://api.paystack.co/transaction/verify/{reference}"

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        logger.info(f"Paystack verify response for {reference}: {data}")

        if data.get("status") and data["data"]["status"] == "success":
            payment = Payment.objects.filter(reference=reference).first()
            if payment:
                payment.verified = True
                payment.save()
                messages.success(request, "Payment successful! 🎉")
                return redirect("join_event", event_id=payment.event.id)
            else:
                messages.error(request, "Payment record not found")
                return redirect("home")
        else:
            messages.error(request, "Payment verification failed")
            return redirect("home")

    except requests.RequestException as e:
        logger.error(f"Paystack verify API error for reference {reference}: {str(e)}")
        messages.error(request, "Error verifying payment. Try again.")
        return redirect("home")

# views.py
from django.views.decorators.csrf import csrf_exempt
import uuid

@login_required
@csrf_exempt
import uuid
import logging
import requests
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Event, Gift  # adjust imports if needed

logger = logging.getLogger(__name__)

@login_required
def initiate_gift_payment(request, event_id):
    if request.method == 'POST':
        amount = request.POST.get('amount')
        if not amount or not amount.isdigit():
            messages.error(request, "Invalid gift amount.")
            return redirect('join_event', event_id=event_id)

        event = get_object_or_404(Event, id=event_id)
        user = request.user
        reference = str(uuid.uuid4())

        # Use named URL for callback instead of hardcoding
        callback_url = request.build_absolute_uri(
            reverse('verify_gift_payment')
        ) + f"?ref={reference}"

        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        data = {
            "email": user.email,
            "amount": int(amount) * 100,  # Paystack expects subunits
            "reference": reference,
            "currency": "KES",  # ✅ Important for Kenya
            "callback_url": callback_url,
        }

        # Store reference temporarily in session
        request.session['gift_reference'] = reference
        request.session['gift_amount'] = amount
        request.session['gift_event_id'] = event_id

        try:
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                headers=headers,
                json=data
            )
            response.raise_for_status()
            res_data = response.json()

            logger.info(f"Gift init response: {res_data}")

            if res_data.get("status") and "authorization_url" in res_data["data"]:
                return redirect(res_data["data"]["authorization_url"])
            else:
                messages.error(request, f"Gift payment init failed: {res_data.get('message')}")
                return redirect('join_event', event_id=event_id)

        except Exception as e:
            logger.error(f"Gift payment init error: {str(e)}")
            return render(request, "payment_error.html", {"error": str(e)})

    return redirect('join_event', event_id=event_id)

@login_required
def verify_gift_payment(request):
    reference = request.GET.get('reference') or request.GET.get('ref')
    expected_ref = request.session.get('gift_reference')
    event_id = request.session.get('gift_event_id')
    event = Event.objects.filter(id=event_id).first() if event_id else None

    if not reference or reference != expected_ref:
        return render(request, "payment_error.html", {
            "error": "Invalid payment reference.",
            "event": event
        })

    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }

    try:
        res = requests.get(
            f"https://api.paystack.co/transaction/verify/{reference}",
            headers=headers
        )
        res.raise_for_status()
        res_data = res.json()

        logger.info(f"Gift verify response for {reference}: {res_data}")

        if res_data.get("status") and res_data["data"]["status"] == "success":
            amount = request.session.get('gift_amount')
            if not event:
                return render(request, "payment_error.html", {"error": "Event not found."})

            # Save gift
            Gift.objects.create(
                user=request.user,
                event=event,
                amount=amount,
                reference=reference  # ✅ useful for records
            )

            # Clear session
            for key in ['gift_reference', 'gift_event_id', 'gift_amount']:
                request.session.pop(key, None)

            messages.success(request, "Gift sent successfully! 🎁")
            return redirect('join_event', event_id=event.id)

        return render(request, "payment_error.html", {
            "error": "Gift payment was not successful.",
            "event": event
        })

    except Exception as e:
        logger.error(f"Gift payment verify error for {reference}: {str(e)}")
        return render(request, "payment_error.html", {"error": str(e), "event": event})

# views.py
from django.db.models.functions import Cast
from django.db.models import Sum, IntegerField
from .models import Event, Gift, Payment

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




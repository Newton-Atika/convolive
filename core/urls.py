from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views
urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('get-agora-token/', views.get_agora_token, name='get_agora_token'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='landing'), name='logout'),
    path('manage-organizers/', views.manage_organizers, name='manage_organizers'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('organizer/create-event/', views.create_event, name='create_event'),
    path('organizer/create-conversation/', views.create_conversation, name='create_conversation'),
    path('event/<int:event_id>/end/', views.end_event, name='end_event'),
    path('events/<int:event_id>/pay/', views.initiate_paystack_payment, name='pay_event'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('events/<int:event_id>/gift/', views.initiate_gift_payment, name='gift_payment'),
    path('verify-gift-payment/', views.verify_gift_payment, name='verify_gift_payment'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('stream/<int:event_id>/', views.stream_view, name='stream'),
    path('toggle-like/', views.toggle_like, name='toggle_like'),
    path('livekit/token/<int:event_id>/', views.get_livekit_token, name='get_livekit_token'),
    path('stream/<str:room_name>/', views.stream_view, name='stream'),
    path('join/<int:event_id>/', views.join_event, name='join_event'),  # Join event page
    path('end/<int:event_id>/', views.end_event, name='end_event'),  # End event
    path('getToken/', views.getToken, name='get_token'),  # Token generation endpoint
    path('createMember/', views.createMember, name='create_member'),  # Create member
    path('getMember/', views.getMember, name='get_member'),  # Get member
    path('deleteMember/', views.deleteMember, name='delete_member'),
]

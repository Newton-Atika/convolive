from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = 'events'  # Namespace for this app

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('get-agora-token/', views.get_agora_token, name='get_agora_token'),  # Standardized to hyphen
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', LogoutView.as_view(next_page='landing'), name='logout'),
    path('manage-organizers/', views.manage_organizers, name='manage_organizers'),
    path('organizer/dashboard/', views.organizer_dashboard, name='organizer_dashboard'),
    path('organizer/create-event/', views.create_event, name='create_event'),
    path('organizer/create-conversation/', views.create_conversation, name='create_conversation'),
    path('event/<int:event_id>/join/', views.join_event, name='join_event'),
    path('event/<int:event_id>/end/', views.end_event, name='end_event'),
    path('events/<int:event_id>/pay/', views.initiate_paystack_payment, name='pay_event'),
    path('verify-payment/', views.verify_payment, name='verify_payment'),
    path('events/<int:event_id>/gift/', views.initiate_gift_payment, name='gift_payment'),
    path('verify-gift-payment/', views.verify_gift_payment, name='verify_gift_payment'),
    path('event/<int:event_id>/', views.event_detail, name='event_detail'),
    path('stream/<int:event_id>/', views.stream_view, name='stream'),  # Using event_id for consistency
    path('toggle-like/', views.toggle_like, name='toggle_like'),
]

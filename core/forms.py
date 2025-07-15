from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Event

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'start_time', 'is_live']
        widgets = {
            'start_time': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                    'style': 'background-color: #000; color: #fff; border: 1px solid #fff;'
                }
            ),
            'description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'style': 'background-color: #000; color: #fff; border: 1px solid #fff;'
                }
            )
        }
#python -m daphne -b 127.0.0.1 -p 8001 convolive.asgi:application

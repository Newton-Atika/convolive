from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Event, Conversation

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
            'is_live': forms.Select(
                choices=[(True, 'Live Event'), (False, 'Conversation')],
                attrs={'style': 'background-color: #000; color: #fff; border: 1px solid #fff;'}
            ),
            'title': forms.TextInput(
                attrs={'style': 'background-color: #000; color: #fff; border: 1px solid #fff;'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['start_time'].label = 'Start Time (EAT, Nairobi)'

class ConversationForm(forms.ModelForm):
    class Meta:
        model = Conversation
        fields = ['title']  # Adjust based on actual Conversation model
        widgets = {
            'title': forms.TextInput(
                attrs={'style': 'background-color: #000; color: #fff; border: 1px solid #fff;'}
            ),
        }

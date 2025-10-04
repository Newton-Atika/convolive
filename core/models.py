from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_organizer = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    instance.profile.save()
from django.db import models
from django.contrib.auth.models import User

from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
from django.core.exceptions import ValidationError

class Event(models.Model):
    title = models.CharField(max_length=255)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    is_live = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    likes = models.ManyToManyField(User, related_name='liked_events', blank=True)
    mux_stream_key = models.CharField(max_length=255, null=True, blank=True)
    mux_playback_id = models.CharField(max_length=255, null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=70)

    def clean(self):
        """Ensure the fee is not less than 70."""
        if self.fee < 70:
            raise ValidationError("The event fee cannot be less than 70.")
    def total_likes(self):
        return self.likes.count()

    def get_gift_revenue(self):
        return Gift.objects.filter(event=self).annotate(
            amount_int=Cast('amount', IntegerField())
        ).aggregate(total=Sum('amount_int'))['total'] or 0

    def get_join_revenue(self):
        return Payment.objects.filter(event=self, verified=True).aggregate(
            total=Sum('amount')
        )['total'] or 0

    def get_total_revenue(self):
        return (self.get_gift_revenue() or 0) + (self.get_join_revenue() or 0)

    # Add other fields if needed
class LiveParticipant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('event', 'user')  # Prevent duplicates

    def __str__(self):
        return f"{self.user.username} joined {self.event.title}"
class EventView(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'user')

class EventLike(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('event', 'user')

class EventComment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class Gift(models.Model):
    GIFT_CHOICES = [
        ('10', 'Coin x10'),
        ('20', 'Coin x20'),
        ('50', 'Coin x50'),
    ]
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.CharField(max_length=10, choices=GIFT_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
from django.db.models import Sum, IntegerField
from django.db.models.functions import Cast
def total_gift_amount(self):
    from django.db.models import Sum
    return Gift.objects.filter(event=self).annotate(
            amount_int=Cast('amount', IntegerField())
            ).aggregate(total=Sum('amount_int'))['total'] or 0

class Payment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.event.title} - {self.amount}"
from django.db.models import Sum

def total_revenue(self):
    return self.payment_set.filter(verified=True).aggregate(models.Sum('amount'))['amount__sum'] or 0

class LiveStatus(models.Model):
    event = models.OneToOneField(Event, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
class ChatMessage(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='chat_messages')
    username = models.CharField(max_length=150)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']



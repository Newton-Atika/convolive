from django.contrib import admin
from django.db.models.functions import Cast
from django.db.models import IntegerField
from django.db.models import Sum
from .models import Profile,Event,EventLike,EventView,EventComment,LiveParticipant,EventView,Gift,Payment,LiveStatus,ChatMessage
admin.site.register(EventComment)
admin.site.register(Payment)
admin.site.register(Gift)
admin.site.register(LiveStatus)
admin.site.register(LiveParticipant)
admin.site.register(Profile)
admin.site.register(EventLike)
admin.site.register(EventView)
admin.site.register(ChatMessage)
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'is_live', 'start_time', 'total_revenue', 'gift_revenue')

    def total_revenue(self, obj):
        revenue = Payment.objects.filter(event=obj, verified=True).aggregate(Sum('amount'))['amount__sum']
        return f"KES {revenue:.2f}" if revenue else "KES 0.00"
    total_revenue.short_description = 'Conversation Revenue'

    def gift_revenue(self, obj):
        gifts = Gift.objects.filter(event=obj).annotate(
            amount_int=Cast('amount', IntegerField())
        ).aggregate(Sum('amount_int'))['amount_int__sum']
        return f"KES {gifts}" if gifts else "KES 0"
    gift_revenue.short_description = 'Live Gifts'
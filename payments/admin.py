from django.contrib import admin
from admins.models import SubscriptionPlan
from payments.models import CustomerCards, Transaction

# Register your models here.


@admin.register(CustomerCards)
class CustomerCardsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user',)


@admin.register(SubscriptionPlan)
class CardAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'amount',)


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'transaction_time',)

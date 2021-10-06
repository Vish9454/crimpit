from django.db import models
from accounts.models import User
from admins.models import SubscriptionPlan
from core.models import BaseModel

# Create your models here.


class Customers(BaseModel):
    """
        Model to map Customers
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customers")
    stripe_customer_id = models.CharField(max_length=30)


class CustomerCards(BaseModel):
    """
        Model to map Customer Cards
    """
    customer = models.ForeignKey(Customers, on_delete=models.CASCADE, related_name="cards")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="customers_cards")
    card_id = models.CharField(max_length=50)
    fingerprint = models.CharField(max_length=30)


class CustomerSubscription(BaseModel):
    """
        Model to map all the subscription user has created.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cus_subscription")
    subscription_id = models.CharField(max_length=30)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, related_name="cus_subscription_plan", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    subscription_end = models.DateTimeField(verbose_name='Subscription End', null=True, blank=True)

    class Meta:
        verbose_name = 'CustomerSubscription'
        verbose_name_plural = 'CustomerSubscriptions'


class Transaction(BaseModel):
    """
        Model to store transaction details of ordered food
    """

    class TransactionType(models.IntegerChoices):
        """
            TransactionType Models used for the transaction type
        """
        DEBIT = 1
        CREDIT = 2

    class TransactionStatus(models.IntegerChoices):
        """
            TransactionStatus Models used for the transaction status
        """
        SUCCESS = 1
        FAILED = 2
        PENDING = 3

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL, related_name="transaction_user")
    transaction_type = models.IntegerField(choices=TransactionType.choices, blank=False, verbose_name="Transaction Mode")
    subscription_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Subscription Id")
    transaction_time = models.DateTimeField(blank=True, null=True, verbose_name="Transaction Time")
    total_amount = models.FloatField(blank=True, null=True, verbose_name="Total Amount")
    card_type = models.CharField(max_length=50, blank=True, null=True, verbose_name="Card Type")
    payment_status = models.IntegerField(choices=TransactionStatus.choices, blank=True, null=True, verbose_name="Transaction Status")

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

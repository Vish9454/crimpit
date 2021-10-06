from datetime import datetime

import pytz
import stripe
from config.local import STRIPE_SECRET_KEY, STRIPE_PROD_ID
from accounts.models import User, UserSubscription
from payments.models import Customers, CustomerCards, Transaction

stripe.api_key = STRIPE_SECRET_KEY


class Stripe:

    def __init__(self, user_id):
        self.user_id = user_id

    def stripe_customer_create(self):
        user_obj = User.objects.get(id=self.user_id)
        stripe_customer = stripe.Customer.create(
            description="Creating stripe customer",
            email=user_obj.email,
            name=user_obj.full_name,
            phone=user_obj.phone_number,
        )
        return stripe_customer

    def stripe_create_card(self, card_token):
        customer_obj = Customers.objects.get(user_id=self.user_id)
        stripe_card = stripe.Customer.create_source(customer_obj.stripe_customer_id, source=card_token, )
        return stripe_card

    def stripe_retrieve_card(self, card_token):
        customer_obj = Customers.objects.get(user_id=self.user_id)
        stripe_card = stripe.Customer.retrieve_source(customer_obj.stripe_customer_id, card_token, )
        return stripe_card

    def stripe_delete_card(self, card_id):
        customer_obj = Customers.objects.get(user_id=self.user_id)
        stripe_card = stripe.Customer.delete_source(customer_obj.stripe_customer_id, card_id, )
        return stripe_card["deleted"]

    def stripe_list_card(self):
        customer_obj = Customers.objects.get(user_id=self.user_id)
        stripe_card = stripe.Customer.list_sources(customer_obj.stripe_customer_id, object="card")
        return stripe_card


def stripe_plan_create(request):
    stripe_plan = stripe.Plan.create(
        amount=request.data['amount']*100,
        interval=request.data['interval'],
        product=STRIPE_PROD_ID,
        currency=request.data['currency'],
        nickname=request.data['title']
    )
    return stripe_plan


def plan_amount_change(plan_id, amount):
    plan_data = stripe.Plan.retrieve(plan_id)
    interval = plan_data['interval']
    currency = plan_data['currency']
    nickname = plan_data['nickname']
    # deleting old plan
    stripe.Plan.delete(plan_id)
    # creating new plan for new amount given by user
    stripe_plan = stripe.Plan.create(
        amount=int(amount)*100,
        interval=interval,
        product=STRIPE_PROD_ID,
        currency=currency,
        nickname=nickname,
    )
    return stripe_plan


def create_transaction_detail_on_webhook(subscription_data, requested_user):
    try:
        data_dict = {
            'user': requested_user,
            'transaction_type': Transaction.TransactionType.DEBIT,
            'subscription_id': subscription_data['data']['object']['id'],
            'transaction_time': datetime.fromtimestamp(subscription_data['data']['object']['created']).replace(
                tzinfo=pytz.UTC),
            'total_amount': float(subscription_data['data']['object']['items']['data'][0]['price']['unit_amount_decimal']) / 100,
            'payment_status': Transaction.TransactionStatus.SUCCESS
        }
        Transaction.objects.create(**data_dict)
    except Exception as ex:
        print(ex)


def create_transaction_detail_on_subscription_create(subscription, requested_user):
    try:
        data_dict = {
            'user': requested_user,
            'transaction_type': Transaction.TransactionType.DEBIT,
            'subscription_id': subscription['id'],
            'transaction_time': datetime.fromtimestamp(subscription['created']).replace(
                tzinfo=pytz.UTC),
            'total_amount': float(subscription['items']['data'][0]['price']['unit_amount_decimal'])/100,
            'payment_status': Transaction.TransactionStatus.SUCCESS
        }
        Transaction.objects.create(**data_dict)
    except Exception as ex:
        print(ex)


def create_subscription(card_id, plan_id, stripe_customer_id, requested_user):
    # make default card of customer for recurring payments
    stripe.Customer.modify(stripe_customer_id, default_source=card_id)
    # create subscription
    subscription = stripe.Subscription.create(
        customer=stripe_customer_id,
        items=[
            {
                "plan": plan_id
            }
        ]
    )
    create_transaction_detail_on_subscription_create(subscription, requested_user)
    # try:
    #     stripe.Invoice.create(
    #         customer=stripe_customer_id,
    #         subscription=subscription.id
    #     )
    # except Exception as e:
    #     print(e)
    return subscription


def delete_subscription(subscription_id):
    stripe.Subscription.delete(subscription_id)
    return True


def update_users_for_subscription(subscribed_users, new_stripe_plan):
    for each in subscribed_users:
        try:
            stripe.Subscription.delete(each.subscription_id)
        except Exception as ex:
            print(ex)

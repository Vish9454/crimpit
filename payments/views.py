from django.shortcuts import render
import stripe
import pytz
from datetime import datetime
from django.utils import timezone
from rest_framework import mixins, viewsets,status
from rest_framework import status as status_code
from rest_framework.views import APIView
from rest_framework.response import Response
from payments.models import Customers, CustomerCards
from accounts.models import User, UserSubscription
from admins.models import SubscriptionPlan
from config.local import STRIPE_SECRET_KEY
from core.exception import get_custom_error, CustomException
from core.messages import success_message, validation_message
from core.pagination import CustomPagination
from core.permissions import IsGymOwner
from core import utils as core_utils
from core.authentication import CustomTokenAuthentication
from core.serializers import get_serialized_data
stripe.api_key = STRIPE_SECRET_KEY
from rest_framework import mixins, viewsets
from rest_framework import serializers
from payments.stripe_functions import Stripe, create_subscription, delete_subscription, \
    create_transaction_detail_on_webhook
from core.response import SuccessResponse
from payments.serializers import SubscriptionSerializer
import logging
log = logging.getLogger(__name__)

# Create your views here.


class CreateStripeCustomer(mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsGymOwner,)

    def create(self, request):
        customer_obj = Customers.objects.filter(user_id=request.user.id, stripe_customer_id__isnull=False).first()
        if customer_obj:
            stripe_customer_detail = stripe.Customer.retrieve(customer_obj.stripe_customer_id)
            return SuccessResponse(stripe_customer_detail, status=status_code.HTTP_200_OK)
            # return Response(get_custom_error(message=validation_message.get('CUSTOMER_ALREADY_EXISTS'),
            #                                  error_location='stripe_customer', status=400),
            #                 status=status_code.HTTP_400_BAD_REQUEST)
        # calling the stripe constructor
        # stripe is object of the class Stripe
        # reponse is the calling of method with the object
        try:
            stripe_call = Stripe(request.user.id)
            response = stripe_call.stripe_customer_create()
            customer_obj = Customers.objects.create(user_id=request.user.id, stripe_customer_id=response.id)
            customer_obj.user.user_subscription.is_stripe_customer = True
            customer_obj.user.user_subscription.save()
            return SuccessResponse(response, status=status_code.HTTP_200_OK)
        except Exception:
            return Response(get_custom_error(message=validation_message.get('ERROR_CREATING_CUSTOMER'),
                                             error_location='stripe_customer', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)


class Card(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.DestroyModelMixin,
           viewsets.GenericViewSet):
    """
    Add,list and delete customer card
    """
    permission_classes = (IsGymOwner,)

    def create(self, request, *args, **kwargs):
        """adding customer stripe card"""
        try:
            card_token = request.query_params.get('card_token')
            stripe_obj = Stripe(request.user.id)
            stripe_card = stripe_obj.stripe_create_card(card_token)

            # to remove duplicacy of customer cards
            card_obj = CustomerCards.objects.filter(user=request.user.id, fingerprint=stripe_card.fingerprint).first()
            if card_obj:
                stripe.Customer.delete_source(request.user.customers.first().stripe_customer_id, stripe_card.id)
                return Response(get_custom_error(message=validation_message.get('CARD_EXISTS'),
                                                 error_location='Create Card', status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
            CustomerCards.objects.create(
                customer=request.user.customers.first(),
                user=request.user,
                card_id=stripe_card.id,
                fingerprint=stripe_card.fingerprint
            )
            return SuccessResponse({"message": success_message.get('CARD_ADDED'),
                                    }, status=status_code.HTTP_200_OK)
        except Exception as ex:
            print(ex)
            msg = core_utils.create_exception_message(ex)
            # return Response(get_custom_error(message=validation_message.get('ERROR_ADDING_CARD'),
            return Response(get_custom_error(message=msg,
                                             error_location='Create Card', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        try:
            stripe = Stripe(request.user.id)
            stripe_card = stripe.stripe_list_card()
            return SuccessResponse(stripe_card, status=status_code.HTTP_200_OK)
        except Exception:
            return Response(get_custom_error(message=validation_message.get('ERROR_LISTING_CARD'),
                                             error_location='list Card', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)

    def destroy(self, request, *args, **kwargs):
        card_id = request.query_params.get('card_id')
        if not card_id:
            return Response(get_custom_error(message=validation_message.get('CARD_ERROR'),
                                             error_location='delete Card', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        try:
            stripe = Stripe(request.user.id)
            stripe_obj = stripe.stripe_delete_card(card_id)
            if stripe_obj == True:
                CustomerCards.objects.filter(card_id=card_id).delete()
                return SuccessResponse({"message": success_message.get('CARD_DELETE_SUCSSES'),
                                        }, status=status_code.HTTP_200_OK)
        except Exception as ex:
            msg = core_utils.create_exception_message(ex)
            # return Response(get_custom_error(message=validation_message.get('ERROR_DELETE_CARD'),
            return Response(get_custom_error(message=msg,
                                             error_location='delete Card', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)


class Subscription(mixins.ListModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin,
                   viewsets.GenericViewSet):
    """
        Handle subscription of gym owners
    """
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    serializer_class = SubscriptionSerializer

    def list(self, request):
        subscription_obj = UserSubscription.objects.filter(user=request.user, is_deleted=False
                                                           ).order_by('-created_at').all()
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(subscription_obj, request)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.serializer_class(subscription_obj,many=True)
        return SuccessResponse(serializer.data)

    def create(self, request):
        card_id = request.data.get('card_id')
        card_obj = CustomerCards.objects.filter(user=request.user, card_id=card_id).first()
        if not card_obj:
            return Response(get_custom_error(message=validation_message.get('CARD_ERROR'),
                                             error_location='Create Subscription', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        plan_id = request.data.get('plan_id')
        stripe_customer_id = request.user.customers.first().stripe_customer_id
        if not card_id or not plan_id or not stripe_customer_id:
            return Response(
                get_custom_error(message=validation_message.get('PLAN_CARD_CUSTOMER_ERROR'),
                                 error_location='Create Subscription',
                                 status=400), status=status_code.HTTP_400_BAD_REQUEST)
        try:
            subscription = create_subscription(card_id, plan_id, stripe_customer_id, request.user)
            plan_obj = SubscriptionPlan.objects.filter(plan_id=plan_id).first()
            # delete existing subscription for the user(gym_owner)
            subscription_obj = UserSubscription.objects.filter(user=request.user).first()
            if subscription_obj:
                try:
                    subscription_id = subscription_obj.subscription_id
                    delete_subscription(subscription_id)
                except Exception:
                    pass
                subscription_obj.delete()
            # creating new subscription object for gym owner
            user_subscriber_obj = UserSubscription.objects.create(
                user=request.user, is_stripe_customer=True, is_subscribed=True,
                subscription_start=datetime.fromtimestamp(subscription.current_period_start).replace(tzinfo=pytz.UTC), subscription_end=datetime.fromtimestamp(
                    subscription.current_period_end).replace(tzinfo=pytz.UTC),
                subscription_interval=subscription.plan.interval, subscription_id=subscription.id,
                subscription_status=UserSubscription.ACTIVE, plan=plan_obj)
            log.info(user_subscriber_obj)
        except Exception:
            return Response(
                get_custom_error(message=validation_message.get('CREATE_ERROR_SUBSCRIPTION'),
                                 error_location='Create Subscription',
                                 status=400), status=status_code.HTTP_400_BAD_REQUEST)
        return SuccessResponse({"message": "Subscription Purchased"}, status=status_code.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        subscription_obj = UserSubscription.objects.filter(user=request.user, is_deleted=False).first()
        if not subscription_obj:
            return Response(
                get_custom_error(message=validation_message.get('SUBSCRIPTION_NOT_FOUND'),
                                 error_location='Delete Subscription',
                                 status=400), status=status_code.HTTP_400_BAD_REQUEST)
        subscription_id = subscription_obj.subscription_id
        try:
            delete_subscription(subscription_id)
            subscription_obj.is_subscribed = False
            subscription_obj.subscription_status = UserSubscription.INACTIVE
            subscription_obj.subscription_interval = "subscription cancel"
            subscription_obj.subscription_id = None
            subscription_obj.plan = None
            # subscription_obj.is_deleted = True
            subscription_obj.save()
        except Exception as ex:
            print(ex)
            return Response(
                get_custom_error(message=validation_message.get('DELETE_ERROR_SUBSCRIPTION'),
                                 error_location='Delete Subscription',
                                 status=400), status=status_code.HTTP_400_BAD_REQUEST)
        return SuccessResponse({"message":"Unsubscribed successfully"})


class StripeWebhook(APIView):
    """
        A web hook to handle stripe invoice payment succeeded event.
    """
    def post(self,request):
        data = request.data
        log.info(data)
        customer_obj = Customers.objects.filter(stripe_customer_id=data['data']['object']['customer']).first()
        subscription_obj = UserSubscription.objects.filter(user=customer_obj.user, is_deleted=False).first()
        if subscription_obj:
            if 'paid' in data['data']['object']:
                """
                    this will be executed when invoice get failed
                """
                subscription_obj.is_subscribed = False
                subscription_obj.subscription_status = UserSubscription.INACTIVE
                subscription_obj.subscription_interval = "subscription expired"
                subscription_obj.subscription_id = None
                subscription_obj.plan = None
                subscription_obj.save()
                return Response(status=200)
            """
            This will be executed when subscription get created or updated
            """
            subscription_start = datetime.fromtimestamp(data['data']['object']['current_period_start']).replace(
                tzinfo=pytz.UTC)
            subscription_end = datetime.fromtimestamp(data['data']['object']['current_period_end']).replace(
                tzinfo=pytz.UTC)
            current_date = timezone.now()
            if (subscription_end - current_date).days < 0:
                subscription_obj.is_subscribed = False
                subscription_obj.subscription_status = UserSubscription.INACTIVE
                subscription_obj.subscription_interval = "subscription expired"
                subscription_obj.subscription_id = None
                subscription_obj.plan = None
                subscription_obj.save()
            else:
                subscription_obj.is_subscribed = True
                subscription_obj.subscription_start = subscription_start
                subscription_obj.subscription_end = subscription_end
                subscription_obj.interval = data['data']['object']['plan']['interval']
                plan_obj = SubscriptionPlan.objects.filter(plan_id=data['data']['object']['plan']["id"]).first()
                if plan_obj:
                    subscription_obj.plan_id = plan_obj.id
                subscription_obj.subscription_status = UserSubscription.ACTIVE
                subscription_obj.save()
                subscription_obj = UserSubscription.objects.filter(user=subscription_obj.user).first()
                if subscription_obj:
                    subscription_obj.subscription_id = data['data']['object']['id']
                    subscription_obj.save()
                if data["type"] == "customer.subscription.updated":
                    print("11111")
                    create_transaction_detail_on_webhook(data, subscription_obj.user)
        return Response(status=200)

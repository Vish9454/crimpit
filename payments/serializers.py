from rest_framework import serializers
from admins.models import SubscriptionPlan
from accounts.models import UserSubscription

class PlanSerializer(serializers.ModelSerializer):
    """
        Serializer to give response to plan objects
    """
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'title', 'amount', "currency", "plan_id", "product", "interval",
                  'access_to_wall_pics', 'uploaded_wall_number',
                  "active_gymstaff_number", 'active_gymstaff_number', 'access_feedback_per_month',
                  'announcements_create', 'access_to_biometric_data', 'access_to_sign_up_info',
                  'clicks_of_advertising_space', 'gym_ads_on_app'
                  )

class SubscriptionSerializer(serializers.ModelSerializer):
    """
        Serializer to give response to UserSubscription objects
    """
    plan = PlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ("id",'user','is_stripe_customer','is_subscribed','subscription_start',
                  'subscription_end','subscription_interval','subscription_status',
                  'is_free','is_trial','trial_end','subscription_id','plan')


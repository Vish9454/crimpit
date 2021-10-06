from django.db import models
from core.models import BaseModel


# Create your models here.

class SubscriptionPlan(BaseModel):
    """
    Admin will be adding subscription plans for the Gym Owner
    """
    title = models.CharField(max_length=30, blank=True, null=True, verbose_name='Subscription Title')
    # Wall related
    access_to_wall_pics = models.BooleanField(default=False, verbose_name='Access To Wall Pics')
    uploaded_wall_number = models.CharField(max_length=4, blank=True, null=True, verbose_name='Wall Num Upload Limit')
    # Gym staff related
    access_to_gym_staff = models.BooleanField(default=False, verbose_name='Access To Gym Staff')
    active_gymstaff_number = models.CharField(max_length=3, blank=True, null=True, verbose_name='Active Gym Staff Number')
    # feedback by climbers related
    access_feedback_per_month = models.CharField(max_length=3, blank=True, null=True, verbose_name='Feedback Access')
    # Boolean values
    announcements_create = models.BooleanField(default=False, verbose_name='Announcements')
    access_to_biometric_data = models.BooleanField(default=False, verbose_name='Biometric Data Access of Climbers')
    access_to_sign_up_info = models.BooleanField(default=False, verbose_name='SignUp Info Access of Climbers')
    # Stripe end parameters
    plan_id = models.CharField(null=True, blank=True, max_length=30)
    product = models.CharField(null=True, blank=True, max_length=30)
    amount = models.FloatField(null=True, blank=True, verbose_name='Amount per month')
    currency = models.CharField(null=True, blank=True, max_length=10)
    interval = models.CharField(null=True, blank=True, max_length=30)
    # not in this phase
    gym_ads_on_app = models.BooleanField(default=False, verbose_name='Gym Ads')
    clicks_of_advertising_space = models.CharField(max_length=5, blank=True, null=True,
                                                   verbose_name='Clicks On Advertising Space')

    class Meta:
        verbose_name = 'SubscriptionPlan'
        verbose_name_plural = 'SubscriptionPlans'


class Domain(BaseModel):
    name = models.CharField(max_length=100, verbose_name='Domain Name')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')

    class Meta:
        verbose_name = 'Domain'
        verbose_name_plural = 'Domains'

from rest_framework import serializers
from accounts.models import (User, UserDetails, Role, AccountVerification,UserRouteFeedback,
                             SavedEvent, UserSubscription, UserRouteFeedback, SavedEvent, UserRouteFeedback)
from gyms.models import GymDetails, Event, Announcement, GymLayout
from django.contrib.auth import authenticate
from core import utils as core_utils
from core.messages import validation_message
from django.db import transaction
from core.exception import CustomException
from core import serializers as core_serializers
from config.local import forgotpassword_url, emailverification_url, admin_forgotpassword_url
from multiprocessing import Process
from rest_framework.authtoken.models import Token
from core.serializers import DynamicFieldsModelSerializer
from django.contrib.gis.db import models
from admins.models import SubscriptionPlan, Domain
from core.serializers import DynamicFieldsModelSerializer
from django.contrib.gis.db import models
from admins.models import SubscriptionPlan
from rest_framework.response import Response
from config.local import ADMIN_MAIL
from django.core.mail import EmailMessage

from payments.models import Transaction
from payments.serializers import PlanSerializer


class AdminLoginSerializer(serializers.ModelSerializer):
    """
        AdminLoginSerializer serializer is used to verify admin credentials
    """
    email = serializers.EmailField(min_length=5,max_length=50,required=True)
    password = serializers.CharField(min_length=8, max_length=15, required=True)
    # is_superuser = serializers.BooleanField(default=False,required=False)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'].lower(), password=attrs['password'])
        if user is not None:
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(validation_message.get('INVALID_CREDENTIAL'))

    def check_user_role(self, user):
        user_role_var = user.user_role.filter(name=Role.RoleType.ADMIN_USER,role_status=True).first()
        if user_role_var:
            return True

    def to_representation(self, instance):
        data = super(AdminLoginSerializer, self).to_representation(instance)
        data['token'] = core_utils.get_or_create_user_token(instance)
        return data

    def create(self,validated_data):
        with transaction.atomic():
            instance = validated_data.get('user')
            role = self.check_user_role(instance)
            if role is True:
                return instance
            else:
                raise CustomException(status_code=400, message=validation_message.get("NOT_AN_ADMIN_USER"),
                                      location=validation_message.get("LOCATION"))

    class Meta:
        model = User
        fields = ('id', 'email', 'password')


class AdminForgetPasswordSerializer(serializers.Serializer):
    """
        Forget password serializer used to validation of Admin email
    """
    email = serializers.EmailField(min_length=5,max_length=50,required=True)

    def create(self, validated_data):
        """
            Method used to create the data
        :param validated_data:
        :return:
        """
        with transaction.atomic():
            instance = User.objects.filter(user_role__name=Role.RoleType.ADMIN_USER, user_role__role_status=True,
                                           email=validated_data.get('email').lower()).only('id', 'email').first()
            if not instance:
                raise CustomException(status_code=400, message=validation_message.get("NOT_AN_ADMIN_USER"),
                                      location=validation_message.get("LOCATION"))
            forgot_password_token = core_utils.generate_verification_token(instance,
                                                                           AccountVerification.VerificationType.
                                                                           FORGOT_PASSWORD)
            forgot_password_url = admin_forgotpassword_url + forgot_password_token.token + "/"

            p = Process(target=core_utils.send_forgot_password_link_to_email,
                        args=('neha.tyagi@mobicules.com', forgot_password_url,))
                        # args=(instance.email, forgot_password_url,))
            p.start()
            self.validated_data["forgot_password_url"] = forgot_password_url
            return True


class AdminResetPasswordSerializer(serializers.Serializer):
    """
        Reset password serializer to reset password of Admin
    """

    token = serializers.CharField(required=True)
    password=serializers.CharField(min_length=8,max_length=15,required=True)

    @staticmethod
    def get_account_verification_detail(forgot_password_token):
        account_verify = AccountVerification.objects.select_related('user'). \
            filter(token=forgot_password_token, verification_type=AccountVerification.VerificationType.
                   FORGOT_PASSWORD).only('expired_at', 'is_used', 'user').first()
        if not account_verify:
            raise CustomException(status_code=400, message=validation_message.get("INVALID_FORGOT_PASS_LINK"),
                                  location=validation_message.get("LOCATION"))
        return account_verify


    def create(self, validated_data):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        account_verify = self.get_account_verification_detail(validated_data['token'])
        if account_verify.is_used:
            return False
        # To check expiration time of link
        if account_verify.expired_at < core_utils.get_current_date_time_object():
            raise CustomException(status_code=400, message=validation_message.get("RESET_PASS_LINK_EXPIRED"),
                                  location=validation_message.get("LOCATION"))
        user_obj = account_verify.user
        user_obj.set_password(validated_data["password"])
        user_obj.save()
        # deleting token to signout user from  other devices
        Token.objects.filter(user=user_obj).delete()
        Token.objects.get_or_create(user=user_obj)

        # To mark token as used
        account_verify.is_used = True
        account_verify.save()
        return True

class ListSubscriptionSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'title', 'amount', "currency", "plan_id", "product", "interval",
                  'access_to_wall_pics', 'uploaded_wall_number',
                  "active_gymstaff_number", 'active_gymstaff_number', 'access_feedback_per_month',
                  'announcements_create', 'access_to_biometric_data', 'access_to_sign_up_info',
                  'clicks_of_advertising_space', 'gym_ads_on_app'
                  )


class RoleSerializer(core_serializers.DynamicFieldsModelSerializer):
    class Meta:
        model = Role
        fields = ('user', 'name', 'role_status')


class GymSerializer(core_serializers.DynamicFieldsModelSerializer):
    class Meta:
        model = GymDetails
        fields = ('user', 'gym_name')


class GymAssociatedSerializer(core_serializers.DynamicFieldsModelSerializer):
    home_gym = GymSerializer()

    class Meta:
        model = UserDetails
        fields = ('user', 'home_gym')


class ListOfUserSerializer(core_serializers.DynamicFieldsModelSerializer):
    gym_detail_user = GymSerializer(fields=('user', 'gym_name'))
    user_details = GymAssociatedSerializer(fields=('user', 'home_gym'))
    user_role = RoleSerializer(fields=('user', 'name', 'role_status'), many=True)
    is_climber_user = serializers.SerializerMethodField()

    def get_is_climber_user(self, obj):
        try:
            if obj.user_details:
                return True
        except:
            pass
        return False

    class Meta:
        model = User
        fields = ('id', 'is_climber_user', 'full_name', 'email', 'user_details', 'gym_detail_user', 'user_role',
                  'created_at', 'is_active',)


class SpecificUserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('full_name', 'email')


# class GymEmailSerializer(serializers.ModelSerializer):
#     message = serializers.CharField()
#
#     class Meta:
#         model = User
#         fields = ('email')

# class EventSerializer(serializers.ModelSerializer):
#     class Meta:
#         model=Event
#         fields = ('title','thumbnail')
#
# class AnnouncementSerializer(serializers.ModelSerializer):
#     class Meta:
#         model=Announcement
#         fields = ('gym','title')
#
# class GlobalSearchSerializer(serializers.ModelSerializer):
#     event=EventSerializer(many=True)
#     announcement=AnnouncementSerializer(many=True)
#
#     class Meta:
#         model=User
#         fields=('id','full_name','email','event','announcement')
#
#
# class DeleteUserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model=User
#         fields=('id','is_active')

class FeedbackDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    class Meta:
        model = UserRouteFeedback
        fields = ('user','updated_at','climb_count')


class ClimberProfileSerializer(core_serializers.DynamicFieldsModelSerializer):
    # user_route_feedback=FeedbackDetailSerializer(fields=('user', 'updated_at', 'climb_count'))

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email',)


class UserSubscriptionSerializer(core_serializers.DynamicFieldsModelSerializer):
    plan = PlanSerializer()

    class Meta:
        model = UserSubscription
        fields = ('user', 'subscription_status', 'plan',)


class UserSerializer(core_serializers.DynamicFieldsModelSerializer):
    user_subscription = UserSubscriptionSerializer()

    class Meta:
        model = User
        fields = ('id', 'email', 'user_subscription',)


class GymProfileSerializer(core_serializers.DynamicFieldsModelSerializer):
    user = UserSerializer(fields=('id', 'email',))

    class Meta:
        model = GymDetails
        fields = ('id', 'user', 'gym_name')


class EmailSerializer(core_serializers.DynamicFieldsModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email','created_at')


class ListOfReviewSerializer(core_serializers.DynamicFieldsModelSerializer):
    user = EmailSerializer(fields=('id', 'email', 'created_at'))

    class Meta:
        model = GymDetails
        fields = ('gym_name', 'address', 'user',)


class DetailReviewSerializer(core_serializers.DynamicFieldsModelSerializer):
    user = EmailSerializer(fields=('id', 'email', 'created_at'))

    class Meta:
        model = GymDetails
        fields = ('id', 'user', 'gym_name', 'gym_phone_number', 'address', 'gym_avatar', 'zipcode',
                  'easy_direction_link', 'website_link', 'description', 'week_day', 'start_time', 'end_time',
                  'RopeClimbing', 'Bouldering', 'is_profile_complete', 'is_admin_approved')


class PaymentGraphSerializer(core_serializers.DynamicFieldsModelSerializer):
    # user = EmailSerializer(fields=('id', 'email', 'created_at'))

    class Meta:
        model = Transaction
        fields = ('id', 'user', 'transaction_type', 'subscription_id', 'transaction_time', 'total_amount',
                  'payment_status',)


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


class CustomEmailSerializer(serializers.Serializer):
    gym_user_ids = serializers.ListField(required=True)
    subject = serializers.CharField(max_length=100, allow_blank=True, required=True)
    message = serializers.CharField(min_length=1, max_length=500, required=True)

    def create(self, validated_data):
        email_list = User.all_objects.filter(id__in=validated_data['gym_user_ids']).values_list('email',
                                                                                                flat=True).distinct()
        # send custom mail to gym users
        core_utils.send_custom_mail_to_gyms(email_list, validated_data['subject'], validated_data['message'])
        print(email_list)
        return True


class DomainSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=100, required=True)

    def create(self, validated_data):
        print(validated_data)
        instance = Domain.objects.create(**validated_data)
        return instance

    class Meta:
        model = Domain
        fields = ('id', 'name', 'is_active',)

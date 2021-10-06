from datetime import datetime, timezone
from multiprocessing import Process

''' project level imports '''
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
from django.db.models import Count, Q
from fcm_django.models import FCMDevice
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from accounts.models import (AccountVerification, Role, User, UserPreference, GRADING_CHOICES, UserDetails,
                             ListCategory, RouteSaveList, UserRouteFeedback, SavedEvent, UserBiometricData,
                             UserDetailPercentage, WallVisit, QuestionAnswer, )
from config.local import forgotpassword_url, emailverification_url
from core import utils as core_utils
from core.exception import CustomException
from core.messages import validation_message, variables
from core import serializers as core_serializers
from gyms.models import (GymDetails, GymLayout, WallRoute, Event, Announcement, LayoutSection, SectionWall, GradeType,
                         PreLoadedTemplate, WallType, ColorType, RouteType, )


class UserSignUpSerializer(serializers.ModelSerializer):
    """
        UserSignUpSerializer class used for the user sign up
    """
    full_name = serializers.CharField(min_length=3, max_length=100, required=True)
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    password = serializers.CharField(min_length=8, max_length=15, required=True)

    @staticmethod
    def validate_email(email: str):
        """
            method used to check email already exits in users table or not.
        :param email:
        :return:
        """
        if User.all_objects.filter(email=email.lower()).exists():
            raise serializers.ValidationError(validation_message.get("EMAIL_ALREADY_EXIST"))
        return email.lower()

    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        user_password = validated_data.pop('password')
        with transaction.atomic():
            try:
                user_instance = User.all_delete_objects.filter(email=validated_data.get('email'),
                                                               user_role__name=Role.RoleType.CLIMBER)
                if user_instance.exists():
                    user_instance.update(is_deleted=False, is_email_verified=False)
                    full_name = validated_data.get('full_name', '')
                    if full_name:
                        user_instance.update(full_name=full_name)
                    user_detail = getattr(user_instance.first(), 'user_details', None)
                    if user_detail:
                        user_detail.login_count = 0
                        user_detail.save()
                    instance = user_instance.first()
                else:
                    instance = User.objects.create(**validated_data)
            except IntegrityError as e:
                print(e)
                raise CustomException(status_code=400, message=validation_message.get("EMAIL_ALREADY_EXIST"),
                                      location=validation_message.get("LOCATION"))
            instance.set_password(user_password)
            instance.save()
            # create the user Role
            core_utils.create_user_role(instance, Role.RoleType.CLIMBER)
            # create the user preference
            core_utils.create_user_preference(instance)
            # create the email verification token
            verification_token = core_utils.generate_verification_token(instance,
                                                                        AccountVerification.VerificationType.
                                                                        EMAIL_VERIFICATION)
            email_verification_url = emailverification_url + verification_token.token + "/"

            # send verification token to email
            p = Process(target=core_utils.send_verification_link_to_email,
                        args=(instance.email, email_verification_url,))
            p.start()
            # Remove during production
            self.validated_data['email_verification_token'] = email_verification_url
            return instance

    def to_representation(self, instance):
        data = super(UserSignUpSerializer, self).to_representation(instance)
        data['token'] = core_utils.get_or_create_user_token(instance)
        return data

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'password', 'is_email_verified')


class VerifyEmailSerializer(serializers.Serializer):
    """
        VerifyEmailSerializer used to verify the email address.
    """
    otp = serializers.CharField(required=True)

    def create(self, validated_data):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        account_verify = AccountVerification.objects.select_related('user').\
            filter(token=validated_data.get('otp'), verification_type=AccountVerification.VerificationType.
                   EMAIL_VERIFICATION).only('expired_at', 'is_used', 'user').first()
        if not account_verify:
            raise CustomException(status_code=400, message=validation_message.get("INVALID_EMAIL_VERIFY_LINK"),
                                  location=validation_message.get("LOCATION"))
        if account_verify.is_used:
            return False
        account_verify.user.is_email_verified = True
        account_verify.is_used = True
        account_verify.save()
        account_verify.user.save()
        return True


class ResendEmailVerifyLinkSerializer(serializers.Serializer):
    """
        ResendEmailVerifyLinkSerializer used to resend email verification link.
    """

    def create(self, validated_data):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        with transaction.atomic():
            # create the email verification token
            instance = self.context.get('request')
            verification_token = core_utils.generate_verification_token(instance,
                                                                        AccountVerification.VerificationType.
                                                                        EMAIL_VERIFICATION)
            email_verification_url = emailverification_url + verification_token.token + "/"
            # send verification token to email
            p = Process(target=core_utils.send_verification_link_to_email,
                        args=(instance.email, email_verification_url,))
            p.start()
            # core_utils.send_verification_link_to_email(instance.email, email_verification_url)
            return True


class ClimbingPreferenceSerializer(serializers.ModelSerializer):
    """
        ClimbingPreferenceSerializer Serializer to get the user climbing preference
    """
    class Meta:
        model = UserPreference
        fields = ('id', 'prefer_climbing', 'rope_grading', 'bouldering_grading', 'bouldering', 'top_rope',
                  'lead_climbing',)


class AddClimbingPreferenceSerializer(serializers.ModelSerializer):
    """
        AddClimbingPreferenceSerializer used to add the user climbing preference
    """
    prefer_climbing = serializers.IntegerField(min_value=0, max_value=2, required=False)
    # grading = serializers.MultipleChoiceField(choices=GRADING_CHOICES, required=False)
    # bouldering = serializers.ChoiceField(min_value=0, max_value=9, required=False)
    # top_rope = serializers.ChoiceField(min_value=0, max_value=4, required=False)
    # lead_climbing = serializers.ChoiceField(min_value=0, max_value=4, required=False)

    def update(self, instance, validated_data):
        for i, j in validated_data.items():
            setattr(instance, i, j)
        instance.save()
        core_utils.get_climbing_percentage(instance)
        return instance

    class Meta:
        model = UserPreference
        fields = ('id', 'prefer_climbing', 'rope_grading', 'bouldering_grading', 'bouldering', 'top_rope',
                  'lead_climbing',)


class LogInSerializer(serializers.ModelSerializer):
    """
        LogInSerializer serializer used verify the login credentials.
    """
    ROLE_MAPPING = {
        "CLIMBER": 1,
        "GYM_STAFF": 3
    }
    ROLE_CHOICES = (
        ("CLIMBER", "CLIMBER"),
        ("GYM_STAFF", "GYM_STAFF"),
    )
    role_type = serializers.ChoiceField(choices=ROLE_CHOICES, required=True, write_only=True)
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    password = serializers.CharField(min_length=8, max_length=15, required=True)

    def validate(self, attrs):
        check_user_deactive = User.all_objects.filter(email=attrs['email'].lower()).first()
        if check_user_deactive and check_user_deactive.is_active == False:
            raise serializers.ValidationError(validation_message.get('ACCOUNT_DEACTIVATED'))
        user = authenticate(email=attrs['email'].lower(), password=attrs['password'])
        if user is not None:
            # add user in attrs
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(validation_message.get('INVALID_CREDENTIAL'))

    def check_user_role(self, user, validated_data):
        """
            method used to check the role of the user.
        :param user:
        :param validated_data:
        :return:
        """
        user_role = self.ROLE_MAPPING.get(validated_data.get('role_type'))
        user_role_check = user.user_role.filter(name=user_role, role_status=True)
        if user_role_check.exists():
            return user_role_check
        raise CustomException(status_code=403, message=validation_message.get("INVALID_USER_ROLE"),
                              location=validation_message.get("LOCATION"))

    def to_representation(self, instance):
        data = super(LogInSerializer, self).to_representation(instance)
        data['token'] = core_utils.get_or_create_user_token(instance)
        user_role = self.ROLE_MAPPING.get(self.validated_data.get('role_type'))
        data['role_type'] = self.validated_data.get('role_type')
        if user_role == Role.RoleType.CLIMBER:
            data['login_count'] = instance.user_details.login_count
            user_pre_instance = getattr(instance, 'user_preference')
            data['is_user_preference'] = False
            if user_pre_instance and user_pre_instance.prefer_climbing is not None:
                data['is_user_preference'] = True
        return data

    def create(self, validated_data):
        with transaction.atomic():
            instance = validated_data.get('user')
            user_role_check = self.check_user_role(instance, validated_data)
            core_utils.create_user_details_instance(instance, user_role_check)
            return instance

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'password', 'is_email_verified', 'role_type',)


class ForgotPasswordSerializer(serializers.Serializer):
    """
        Forgot password serializer used to validation of email
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)

    def create(self, validated_data):
        # with transaction.atomic():
        instance = User.objects.filter((Q(user_role__name=Role.RoleType.CLIMBER, user_role__role_status=True) |
                                        Q(user_role__name=Role.RoleType.GYM_STAFF, user_role__role_status=True)),
                                       email=validated_data.get('email').lower()).only('id', 'email',).first()
        if not instance:
            raise CustomException(status_code=400, message=validation_message.get("USER_NOT_FOUND"),
                                  location=validation_message.get("LOCATION"))
        elif not instance.is_email_verified:
            core_utils.resend_email_verify_link(instance)
            raise CustomException(status_code=400, message=validation_message.get("EMAIL_NOT_VERIFIED"),
                                  location=validation_message.get("LOCATION"))
        # create the forgot password token
        forgot_password_token = core_utils.generate_verification_token(instance,
                                                                       AccountVerification.VerificationType.
                                                                       FORGOT_PASSWORD)
        forgot_password_url = forgotpassword_url + forgot_password_token.token + "/"
        # send forgot password token to email
        p = Process(target=core_utils.send_forgot_password_link_to_email,
                    args=(instance.email, forgot_password_url,))
        p.start()
        # Remove during production
        self.validated_data["forgot_password_url"] = forgot_password_url
        return True


class OldResetPasswordSerializer(serializers.Serializer):
    """method to reset user's password"""

    forgot_password_token = serializers.CharField(required=False)
    password = serializers.CharField(min_length=8, max_length=15, required=False)

    @staticmethod
    def get_account_verification_detail(forgot_password_token):
        account_verify = AccountVerification.objects.select_related('user').\
            filter(token=forgot_password_token, verification_type=AccountVerification.VerificationType.
                   FORGOT_PASSWORD).only('expired_at', 'is_used', 'user').first()
        if not account_verify:
            raise CustomException(status_code=400, message=validation_message.get("INVALID_FORGOT_PASS_LINK"),
                                  location=validation_message.get("LOCATION"))
        return account_verify

    def validate(self, attrs):
        """validating attributes"""
        if not attrs.get('forgot_password_token') and not attrs.get('password'):
            raise CustomException(status_code=400, message=validation_message.get("RESET_PASSWORD_NONE_DATA"),
                                  location=validation_message.get("LOCATION"))
        if attrs.get('forgot_password_token') and not attrs.get('password'):
            account_verify = self.get_account_verification_detail(attrs['forgot_password_token'])
            if account_verify.is_used:
                raise CustomException(status_code=400,
                                      message=validation_message.get("FORGOT_PASS_LINK_ALREADY_VERIFIED"),
                                      location=validation_message.get("LOCATION"))
            account_verify.is_used = True
            account_verify.save()
            return True, 1
        elif attrs.get('forgot_password_token') and attrs.get('password'):
            account_verify = self.get_account_verification_detail(attrs['forgot_password_token'])
            if not account_verify.is_used:
                raise CustomException(status_code=400, message=validation_message.get("FORGOT_PASSWORD_TOKEN_NOT_VERIFY"),
                                location=validation_message.get("LOCATION"))
            user_obj = account_verify.user
            user_obj.set_password(attrs["password"])
            user_obj.save()
            # deleting token to signout user out of other device
            Token.objects.filter(user=user_obj).delete()
            Token.objects.get_or_create(user=user_obj)
            return True, 2


class ResetPasswordSerializer(serializers.Serializer):
    """method to reset user's password"""

    token = serializers.CharField(required=True)
    password = serializers.CharField(min_length=8, max_length=15, required=True)

    @staticmethod
    def get_account_verification_detail(forgot_password_token):
        account_verify = AccountVerification.objects.select_related('user').\
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
        # deleting token to signout user out of other device
        Token.objects.filter(user=user_obj).delete()
        Token.objects.get_or_create(user=user_obj)

        # To mark token as used
        account_verify.is_used = True
        account_verify.save()
        return True


class ResendForgotPasswordLinkSerializer(serializers.Serializer):
    """
        ResendForgotPasswordLinkSerializer used to resend forgot password link.
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)

    def create(self, validated_data):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        with transaction.atomic():
            instance = User.objects.filter((Q(user_role__name=Role.RoleType.CLIMBER, user_role__role_status=True) |
            Q(user_role__name=Role.RoleType.GYM_STAFF, user_role__role_status=True)),
                                           email=validated_data.get('email').lower()).only('id', 'email', ).first()
            if not instance:
                raise CustomException(status_code=400, message=validation_message.get("USER_NOT_FOUND"),
                                      location=validation_message.get("LOCATION"))
            # create the forgot password token
            verification_token = core_utils.generate_verification_token(instance,
                                                                        AccountVerification.VerificationType.
                                                                        FORGOT_PASSWORD)
            forgot_password_token = emailverification_url + verification_token.token + "/"
            # send forgot password token to email
            core_utils.send_verification_link_to_email(instance.email, forgot_password_token)
            return True


class UserBasicDetailSerilaizer(core_serializers.DynamicFieldsModelSerializer):
    """
        UserBasicDetailSerilaizer used to update the climber basic details.
    """
    class Meta:
        model = UserDetails
        fields = ('id', 'user_avatar')


class UserDetailUpdateSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        UserDetailUpdateSerializer used to update the climber details.
    """
    user_details = UserBasicDetailSerilaizer(fields=('id', 'user_avatar'), read_only=True)
    full_name = serializers.CharField(min_length=3, max_length=100, required=True)
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    # phone_number = serializers.CharField(min_length=8,allow_blank=True, max_length=25, required=True)
    prefer_climbing = serializers.IntegerField(min_value=-1, max_value=2, allow_null=True,
                                               required=True, write_only=True)
    user_preference = ClimbingPreferenceSerializer(read_only=True)
    overall_percentage = serializers.SerializerMethodField()

    def get_overall_percentage(self, obj):
        percentage_data, created = UserDetailPercentage.objects.get_or_create(user=obj)
        updated_percentage_data = core_utils.get_basic_percentage(obj, percentage_data)
        overall_percentage = round(updated_percentage_data.overall_detail, 2)
        return overall_percentage

    def validate_prefer_climbing(self, value):
        if value == -1:
            return None
        return value

    @staticmethod
    def check_email_already_exist(email: str):
        """
            method used to check email already exits in users table or not.
        :param email:
        :return:
        """
        # For Future Purpose
        if User.all_objects.filter(email=email).exists():
            raise CustomException(status_code=400, message=validation_message.get("EMAIL_ALREADY_EXIST"),
                                  location=validation_message.get("LOCATION"))
        return email

    @staticmethod
    def create_email_verification_token(instance):
        # create the email verification token
        verification_token = core_utils.generate_verification_token(instance,
                                                                    AccountVerification.VerificationType.
                                                                    EMAIL_VERIFICATION)
        email_verification_url = emailverification_url + verification_token.token + "/"

        # send verification token to email
        core_utils.send_verification_link_to_email(instance.email, email_verification_url)
        instance.is_email_verified = False
        instance.save()
        return email_verification_url

    def update(self, instance, validated_data):
        """
            method used to update the user details.
        :param validated_data:
        :param instance:
        :return:
        """
        with transaction.atomic():
            email = validated_data.get('email').lower()
            email_verification_token = ''
            if instance.email != email:
                self.check_email_already_exist(email)
                email_verification_token = self.create_email_verification_token(instance)
            instance = super(UserDetailUpdateSerializer, self).update(instance, validated_data)
            user_preference, created = UserPreference.objects.get_or_create(user=instance)
            user_preference.prefer_climbing = validated_data.get('prefer_climbing')
            user_preference.save()
            # Remove during production total if condition
            if email_verification_token:
                self.validated_data['email_verification_token'] = email_verification_token
            return instance

    class Meta:
        model = User
        fields = ('id', 'full_name', 'user_details', 'email', 'is_email_verified', 'prefer_climbing', 'user_preference',
                  'overall_percentage',)


class NotFoundGymSerializer(serializers.Serializer):
    """
        NotFoundGymSerializer used to send not found gym details to admin.
    """
    gym_name = serializers.CharField(min_length=3, max_length=100, required=True)
    gym_location = serializers.CharField(min_length=3, max_length=200, required=True)

    def create(self, validated_data):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        with transaction.atomic():
            requested_user = self.context.get('request')
            validated_data['email'] = requested_user.email
            # send not found gym detail to admin
            core_utils.send_not_found_gym_to_admin(validated_data)
            return True


class GradeTypeSerializer(serializers.ModelSerializer):
    """
        GradeTypeSerializer class used to handle Grade Type.
    """
    class Meta:
        model = GradeType
        fields = ('id', 'grading_system', 'sub_category', 'sub_category_value',)


class ClimberHomeListSerializer(serializers.ModelSerializer):
    """
        ClimberHomeListSerializer class used to handle Climber Home List serializer.
    """
    # is_home_gym = serializers.SerializerMethodField()
    #
    # def get_is_home_gym(self, obj):
    #     """
    #         method used to mark gym is home-gym or not
    #     :param obj:
    #     :return:
    #     """
    #     home_gym = self.context.get('home_gym_v')
    #     if home_gym and obj == home_gym:
    #         return True
    #     return False

    class Meta:
        model = GymDetails
        # exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'is_active',
        #            'is_admin_approved')
        fields = ('id', 'gym_name', 'gym_avatar', 'zipcode',)


class ClimberHomeDetailSerializer(serializers.ModelSerializer):
    """
        ClimberHomeDetailSerializer class used to handle Climber Home Detail serializer.
    """
    is_home_gym = serializers.SerializerMethodField()
    lat = serializers.SerializerMethodField()
    lng = serializers.SerializerMethodField()

    @staticmethod
    def get_lat(obj):
        """
            method used to get the latitude of the address
        :param obj:
        :return:
        """
        latitude = core_utils.get_latitude_from_obj(obj)
        return latitude

    @staticmethod
    def get_lng(obj):
        """
            method used to get the latitude of the address
        :param obj:
        :return:
        """
        longitude = core_utils.get_longitude_from_obj(obj)
        return longitude

    def get_is_home_gym(self, obj):
        """
            method used to mark gym is home-gym or not
        :param obj:
        :return:
        """
        home_gym = self.context.get('home_gym_v')
        if home_gym and obj == home_gym:
            return True
        return False

    class Meta:
        model = GymDetails
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'is_active',
                   'is_admin_approved')


class GetHomeGymSerializer(serializers.ModelSerializer):
    """
        GetHomeGymSerializer class used to get the home-gym of the user.
    """
    is_active = serializers.SerializerMethodField()

    def get_is_active(self, obj):
        if obj.user.is_active:
            return True
        return False

    class Meta:
        model = GymDetails
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'is_admin_approved')


class MarkHomeGymSerializer(serializers.Serializer):
    """
        MarkHomeGymSerializer used to add the gym as home-gym.
    """
    gym_id = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.filter(user__is_active=True,
                                                                                   is_admin_approved=True).
                                                only('id'), required=True, many=False)

    def create(self, validated_data):
        """
            method used to add the gym as home-gym
        :param validated_data:
        :return:
        """
        instance = self.context.get('user_detail')
        instance.home_gym = validated_data.get('gym_id')
        instance.home_gym_added_on = datetime.now(timezone.utc)
        instance.save()
        return True


class UnmarkHomeGymSerializer(serializers.Serializer):
    """
        UnmarkHomeGymSerializer class used to unmark gym from home-gym.
    """
    gym_id = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.filter(user__is_active=True).
                                                only('id'), required=True, many=False)

    def update(self, instance, validated_data):
        """
            method used to update the gym as non-home gym
        :param instance:
        :param validated_data:
        :return:
        """
        if instance.home_gym == validated_data['gym_id']:
            instance.home_gym = None
            instance.save()
        return True


class ListCategorySerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ListCategorySerializer class used to list and create list category.
    """
    # gym = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.filter(user__is_active=True).
    #                                          only('id'), required=True, many=False)
    name = serializers.CharField(max_length=50, required=True)
    image = serializers.CharField(max_length=255, allow_blank=True, required=True)

    # last_image = serializers.SerializerMethodField()
    #
    # def get_last_image(self, obj):
    #     user = self.context.get('request')
    #     route_save_list = RouteSaveList.objects.prefetch_related('route', 'route__section_wall').filter(list_category=obj.id, user=user).\
    #         order_by('created_at').first()
    #     if route_save_list:
    #         return route_save_list.route.first().section_wall.image
    #     return None

    def create(self, validated_data):
        """
            method used to add the category (in which route will save)
        :param validated_data:
        :return:
        """
        user_instance = self.context.get('user')
        validated_data['user'] = user_instance
        instance = ListCategory.objects.create(**validated_data)
        return instance

    class Meta:
        model = ListCategory
        # fields = ('id', 'name', 'image', 'user', 'gym', 'is_common', 'last_image')
        fields = ('id', 'name', 'image', 'user', 'gym',)


class RouteIntoCategoryDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    category_name = serializers.SerializerMethodField()
    list_category_is_deleted = serializers.SerializerMethodField()

    def get_category_name(self, obj):
        return obj.list_category.name

    def get_list_category_is_deleted(self, obj):
        return obj.list_category.is_deleted

    class Meta:
        model = RouteSaveList
        fields = ('id', 'list_category', 'list_category_is_deleted', 'user', 'gym', 'route', 'category_name',)


class ClimberColorTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ColorType
        fields = ('id', 'gym', 'name', 'hex_value',)


class WallRouteWithCategoryInfoSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        WallRouteWithCategoryInfoSerializer class used to provide Wall Route with Category Detail.
    """
    route_save_list = RouteIntoCategoryDetailSerializer(fields=('user', 'category_name', 'list_category_is_deleted',),
                                                        many=True)
    grade = GradeTypeSerializer()
    color = ClimberColorTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'name', 'grade', 'color', 'image_size', 'tag_point', 'route_save_list',)


class ClimberWallTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WallType
        fields = ('id', 'gym', 'name',)


class SectionWallDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        SectionWallDetailSerializer class used to provide Section Wall Detail.
    """
    count_detail = serializers.SerializerMethodField()
    route_data = serializers.SerializerMethodField()
    wall_type = ClimberWallTypeSerializer()

    def get_count_detail(self, obj):
        # Add or Get visit instance
        visit_instance, created = WallVisit.objects.get_or_create(wall=obj, user=self.context.get('request'))
        # visit_instance.user.add(self.context.get('request'))
        # visit_instance.save()
        count_data = core_utils.get_round_completed_data(obj, visit_instance)
        return count_data

    def get_route_data(self, obj):
        route_tags = WallRoute.objects.select_related('grade', 'color',).prefetch_related(
            'route_save_list', 'route_save_list__list_category'). \
            filter(section_wall=self.context.get('section_wall')).order_by('id')
        route_serializer = WallRouteWithCategoryInfoSerializer(route_tags, many=True,
                                                               context={'request': self.context.get('request')})
        # To filter category only for login user
        core_utils.update_route_category_data(route_serializer.data, self.context.get('request'))
        return route_serializer.data

    class Meta:
        model = SectionWall
        fields = ('id', 'layout_section', 'gym_layout', 'image', 'image_size', 'name', 'wall_type', 'wall_height',
                  'count_detail', 'route_data', 'reset_timer',)


class ClimberRouteTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteType
        fields = ('id', 'gym', 'name',)


class WallRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        WallRouteListSerializer class used to provide Wall Route Detail.
    """
    grade = GradeTypeSerializer()
    section_wall = SectionWallDetailSerializer(fields=('id', 'name',))
    gym_id = serializers.ReadOnlyField()
    gym_name = serializers.ReadOnlyField()
    color = ClimberColorTypeSerializer()
    route_type = ClimberRouteTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'tag_point',
                  'section_wall', 'gym_id', 'gym_name',)


class OnlyWallRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        OnlyWallRouteListSerializer class used to provide Wall Route Detail with Wall detail.
    """
    grade = GradeTypeSerializer()
    color = ClimberColorTypeSerializer()
    route_type = ClimberRouteTypeSerializer()
    created_by = UserDetailUpdateSerializer(fields=('id', 'full_name',))
    grade_percentage = serializers.SerializerMethodField()
    no_climber_completed = serializers.SerializerMethodField()
    is_added_into_category = serializers.SerializerMethodField()
    section_wall = SectionWallDetailSerializer(fields=('id', 'image', 'name',))

    def get_grade_percentage(self, obj):
        query_set = UserRouteFeedback.objects.filter(
            route=obj.id).values('grade').annotate(grade_count=Count('id'))
        grade_count1, grade_count2, grade_count3 = core_utils.get_sequence_data(query_set)
        # grade_count1 = UserRouteFeedback.objects.filter(
        #     route=obj.id, grade=UserRouteFeedback.CommunityGradeType.NEGATIVE).count()
        # grade_count2 = UserRouteFeedback.objects.filter(
        #     route=obj.id, grade=UserRouteFeedback.CommunityGradeType.NORMAL).count()
        # grade_count3 = UserRouteFeedback.objects.filter(
        #     route=obj.id, grade=UserRouteFeedback.CommunityGradeType.POSITIVE).count()
        data = core_utils.get_percentage_from_grade_count([grade_count1, grade_count2, grade_count3])
        return data

    def get_no_climber_completed(self, obj):
        climber_completed = User.all_delete_objects.filter(
            user_route_feedback__route=obj.id, user_route_feedback__route_progress__in=[1, 2, 3]).distinct().count()
        return climber_completed

    def get_is_added_into_category(self, obj):
        user = self.context.get('user')
        # route_save_obj = obj.route_save_list.filter(user_id=user).first()
        route_save_obj = obj.route_save_list.filter(user_id=user, list_category__is_deleted=False).first()
        if route_save_obj:
            return True
        return False

    class Meta:
        model = WallRoute
        fields = ('id', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'tag_point',
                  'grade_percentage', 'no_climber_completed', 'is_added_into_category', 'section_wall',)


class LayoutSectionDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        LayoutSectionDetailSerializer class used to provide Layout Section Detail.
    """
    section_wall = SectionWallDetailSerializer(fields=('id', 'layout_section', 'gym_layout', 'image', 'name',
                                                       'reset_timer',), many=True)

    class Meta:
        model = LayoutSection
        fields = ('id', 'gym_layout', 'name', 'section_wall',)


class OnlyLayoutSectionDetailSerializer(serializers.ModelSerializer):
    """
        LayoutSectionDetailSerializer class used to provide Layout Section Detail.
    """
    section_point = serializers.SerializerMethodField()

    def get_section_point(self, obj):
        obj_section_point = obj.section_point
        if obj_section_point:
            linear_point = obj_section_point[0]
            point = [linear_point[each] for each in range(len(linear_point))]
            point_4 = point[:4]
            return point_4
        return None

    class Meta:
        model = LayoutSection
        fields = ('id', 'name', 'image_size', 'section_point',)


class GymLayoutDetailSerializer(serializers.ModelSerializer):
    """
        GymLayoutDetailSerializer class used to provide Gym Layout Detail.
    """
    gym_layout_section = LayoutSectionDetailSerializer(many=True)

    class Meta:
        model = GymLayout
        fields = ('id', 'gym', 'category', 'layout_image', 'image_size', 'title',  'gym_layout_section',)


class RouteIntoCategorySerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        RouteIntoCategorySerializer class used to list and add route into category.
    """
    list_category = serializers.PrimaryKeyRelatedField(queryset=ListCategory.objects.all().only('id'),
                                                       required=True, many=False)
    gym = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.filter(user__is_active=True).
                                             only('id'), required=True, many=False)
    route = serializers.PrimaryKeyRelatedField(queryset=WallRoute.objects.all().only('id'),
                                               required=True, write_only=True)

    def create(self, validated_data):
        """
            method used to add the route into category
        :param validated_data:
        :return:
        """
        user_instance = self.context.get('user')
        validated_data['user'] = user_instance
        route = validated_data.pop('route')
        instance = RouteSaveList.objects.create(**validated_data)
        instance.route.add(route)
        return True

    class Meta:
        model = RouteSaveList
        fields = ('id', 'list_category', 'gym', 'route',)


class GymDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymDetailSerializer class used to provide gym details.
    """
    class Meta:
        model = GymDetails
        fields = ('id', 'gym_name',)


class RouteFeedbackDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        RouteFeedbackDetailSerializer class used to provide route feedback details.
    """
    gym = GymDetailSerializer(fields=('id', 'gym_name',))
    route = OnlyWallRouteDetailSerializer(fields=('id', 'name', 'grade', 'color', 'route_type', 'setter_tip',
                                                  'section_wall',))
    is_added_into_category = serializers.SerializerMethodField()

    def get_is_added_into_category(self, obj):
        user = self.context.get('request')
        route_save_obj = getattr(obj.route, 'route_save_list').filter(user_id=user, list_category__is_deleted=False).\
            first()
        # if route_save_list:
        #     route_save_obj = route_save_list.filter(user_id=user).first()
        # tyr:
        # route_save_obj = obj.route.route_save_list.filter(user_id=user).first()
        if route_save_obj:
            return True
        return False


    class Meta:
        model = UserRouteFeedback
        fields = ('id', 'user', 'gym', 'route', 'route_progress', 'attempt_count', 'route_note',
                  'climb_count', 'grade', 'rating', 'feedback', 'created_at', 'is_added_into_category',
                  'first_time_read', 'second_time_read',)


class RouteFeedbackSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        RouteFeedbackSerializer class used to add route feedback.
    """
    route = serializers.PrimaryKeyRelatedField(queryset=WallRoute.objects.all().only('id'),
                                               required=True)
    route_progress = serializers.IntegerField(min_value=0, max_value=4, required=True)

    def create(self, validated_data):
        """
            method used to add the route into category
        :param validated_data:
        :return:
        """
        user_instance = self.context.get('request')
        validated_data['user'] = user_instance
        instance = UserRouteFeedback.objects.create(**validated_data)
        # To track gym visit
        core_utils.track_gym_visit_by_user(user_instance, validated_data['route'], instance.id)
        return instance

    class Meta:
        model = UserRouteFeedback
        fields = ('id', 'user', 'gym', 'route', 'route_progress', 'attempt_count', 'route_note', 'climb_count', 'grade',
                  'rating', 'feedback',)


class PercentageDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        PercentageDetailSerializer class used to get user percentage details.
    """
    class Meta:
        model = UserDetailPercentage
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at',)


class ClimbingInfoDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ClimbingInfoSerializer class used to get user climbing info.
    """
    strength_and_weakness = serializers.SerializerMethodField()

    def get_strength_and_weakness(self, obj):
        climbing_data = obj.user.user_details
        dict_data = {
            # 'strength': climbing_data.strength,
            'strength_hold': climbing_data.strength_hold,
            'strength_move': climbing_data.strength_move,
            'weakness_hold':  climbing_data.weakness_hold,
            'weakness_move':  climbing_data.weakness_move
        }
        return dict_data

    class Meta:
        model = UserPreference
        fields = ('rope_grading', 'bouldering_grading', 'bouldering', 'top_rope', 'lead_climbing',
                  'strength_and_weakness',)


class ClimbingInfoSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ClimbingInfoSerializer class used to update user climbing info.
    """
    # strength = serializers.ListField(required=True, write_only=True)
    strength_hold = serializers.ListField(required=True, write_only=True)
    strength_move = serializers.ListField(required=True, write_only=True)
    weakness_hold = serializers.ListField(required=True, write_only=True)
    weakness_move = serializers.ListField(required=True, write_only=True)

    def update(self, instance, validated_data):
        # for i, j in validated_data.items():
        #     setattr(instance, i, j)
        # instance.save()
        # requested_user = self.context.get('request')
        # user_data = requested_user.user_details
        # user_data.strength = validated_data['strength']
        # user_data.weakness_hold = validated_data['weakness_hold']
        # user_data.weakness_move = validated_data['weakness_move']
        # user_data.save()
        pop_validated_data = {
            # 'strength': validated_data.pop('strength'),
            'strength_hold': validated_data.pop('strength_hold'),
            'strength_move': validated_data.pop('strength_move'),
            'weakness_hold': validated_data.pop('weakness_hold'),
            'weakness_move': validated_data.pop('weakness_move')
        }
        instance = super(ClimbingInfoSerializer, self).update(instance, validated_data)
        requested_user = self.context.get('request')
        user_data = requested_user.user_details
        # user_data.strength = pop_validated_data['strength']
        user_data.strength_hold = pop_validated_data['strength_hold']
        user_data.strength_move = pop_validated_data['strength_move']
        user_data.weakness_hold = pop_validated_data['weakness_hold']
        user_data.weakness_move = pop_validated_data['weakness_move']
        user_data.save()
        core_utils.get_climbing_percentage(instance, pop_validated_data)
        return instance

    class Meta:
        model = UserPreference
        fields = ('id', 'rope_grading', 'bouldering_grading', 'bouldering', 'top_rope', 'lead_climbing',
                  'strength_hold', 'strength_move', 'weakness_hold', 'weakness_move',)


class BiometricDataDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        BiometricDataDetailSerializer class used to get user biometric details.
    """
    class Meta:
        model = UserBiometricData
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at',)


class BiometricDataSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        BiometricDataSerializer class used to update user biometric data.
    """
    def to_internal_value(self, data):
        for i, j in data.items():
            if j == '':
                data[i] = None
        return super(BiometricDataSerializer, self).to_internal_value(data)

    def update(self, instance, validated_data: dict):
        """
            method used to create the biometric data.
        :param validated_data:
        :param instance:
        :return:
        """
        for i, j in validated_data.items():
            setattr(instance, i, j)
        instance.save()
        biometric_percentage = core_utils.get_biometric_percentage(validated_data)
        UserDetailPercentage.objects.filter(user=validated_data['user']).\
            update(biometric_detail=biometric_percentage)
        # u_d_percent = UserDetailPercentage.objects.filter(user=validated_data['user']).first()
        # if u_d_percent:
        #     u_d_percent.biometric_detail = biometric_percentage
        #     u_d_percent.save()
        return instance

    class Meta:
        model = UserBiometricData
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at',)


class PreLoadedTemplateSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        PreLoadedTemplateSerializer class used to serialize pre-loaded template.
    """
    class Meta:
        model = PreLoadedTemplate
        fields = ('id', 'uploaded_template',)


class ClimberAnnounceDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ClimberAnnounceDetailSerializer class used to get announcement details.
    """
    template = PreLoadedTemplateSerializer()

    class Meta:
        model = Announcement
        fields = ('id', 'banner', 'template', 'template_type', 'picture', 'title', 'sub_title', 'created_at',
                  'updated_at', 'is_active',)


class ClimberEventDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ClimberEventDetailSerializer class used to get event details.
    """
    other_info = serializers.SerializerMethodField()

    def get_other_info(self, obj):
        event_saved_info = obj.mark_event.filter(user=self.context.get('request')).first()
        dict_data = dict()
        if event_saved_info:
            dict_data.update({'is_going': event_saved_info.is_going, 'is_saved': event_saved_info.is_saved})
        return dict_data

    class Meta:
        model = Event
        fields = ('id', 'thumbnail', 'title', 'start_date', 'description', 'other_info',)


class SaveEventDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        SaveEventDetailSerializer class used to show saved event details.
    """
    save_event = ClimberEventDetailSerializer(fields=('id', 'thumbnail', 'title', 'start_date', 'description',))

    class Meta:
        model = SavedEvent
        fields = ('id', 'user', 'save_event', 'is_going', 'is_saved')


class ClimberSaveEventSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        ClimberSaveEventSerializer class used to save/remove event.
    """
    save_event = serializers.PrimaryKeyRelatedField(queryset=Event.all_objects.all(), required=True)
    is_going = serializers.IntegerField(required=True)
    is_saved = serializers.BooleanField(required=True)

    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        request_user = self.context.get('request')
        save_event = validated_data.pop('save_event')
        with transaction.atomic():
            instance, created = SavedEvent.objects.update_or_create(user=request_user, save_event=save_event,
                                                                    defaults=validated_data)
        return instance

    class Meta:
        model = SavedEvent
        fields = ('id', 'user', 'save_event', 'is_going', 'is_saved')


class QuestionAnswerSerializer(serializers.ModelSerializer):
    """
        QuestionAnswerSerializer class used to get question/answer details.
    """
    class Meta:
        model = QuestionAnswer
        fields = ('id', 'question', 'answer')

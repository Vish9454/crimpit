from datetime import datetime
from multiprocessing import Process

from pytz import utc

''' project level imports '''
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.gis.geos import Point
from django.db import transaction, IntegrityError
from fcm_django.models import FCMDevice
from rest_framework import serializers, fields
from rest_framework.authtoken.models import Token
from accounts.models import (AccountVerification, Role, User, UserPreference, GRADING_CHOICES, UserRouteFeedback,
                             UserDetails, UserBiometricData, UserSubscription)
from config.local import gym_forgotpassword_url, gym_emailverification_url
from core import utils as core_utils
from core.exception import CustomException
from core.messages import validation_message, variables
from core import serializers as core_serializers
from gyms.models import GymDetails, GymLayout, LayoutSection, SectionWall, WallRoute, Event, GradeType, Announcement, \
    PreLoadedTemplate, ChangeRequestGymDetails, GlobalSearch, OpenFeedback, WallType, ColorType, RouteType, \
    GhostWallRoute
from django.contrib.gis.db import models
from core.serializers import DynamicFieldsModelSerializer
from django.db.models import Count, Avg, Max
from admins.models import SubscriptionPlan, Domain

"""Email domains are as follows"""
email_domains = ['gmail.com', 'getnada.com']


class GymOwnerSignUpSerializer(serializers.ModelSerializer):
    """
        GymOwnerSignUpSerializer class used for gym owner sign up
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    password = serializers.CharField(min_length=8, max_length=20, required=True, write_only=True)
    gym_name = serializers.CharField(min_length=3, max_length=100, required=True, write_only=True)

    def validate_email(self, email):
        """
            method used to check email already exits in users table or not.
        :param email:
        :return:
        """
        request_domain = email[email.index('@') + 1:]
        """When customer gives the domain then we can remove the comment."""
        valid_domain = Domain.objects.filter(name__iexact=request_domain, is_deleted=False).first()
        # if request_domain not in email_domains:
        if not valid_domain:
            raise serializers.ValidationError(validation_message.get("EMAIL_DOMAIN_WRONG"))
        if User.all_objects.filter(email=email.lower()).exists():
            raise serializers.ValidationError(validation_message.get("EMAIL_ALREADY_EXIST"))
        return email.lower()

    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        # create user object
        with transaction.atomic():
            # user_obj = User.objects.create(email=validated_data.get('email').lower(), full_name="Gym")
            user_obj = User.objects.create(email=validated_data.get('email').lower())
            user_obj.set_password(validated_data.get("password"))
            user_obj.save()
            # create gym ovject
            gym_object = GymDetails.objects.create(user=user_obj, gym_name=validated_data.get('gym_name'))
            # create the user Role
            core_utils.create_user_role(user_obj, Role.RoleType.GYM_OWNER)
            UserSubscription.objects.create(user=user_obj)
            # Function to create wall type for this gym
            core_utils.create_wall_type(gym_object)
            # Function to create color type for this gym
            core_utils.create_color_type(gym_object)
            # Function to create route type for this gym
            core_utils.create_route_type(gym_object)
            return user_obj

    def to_representation(self, instance):
        data = super(GymOwnerSignUpSerializer, self).to_representation(instance)
        data['token'] = core_utils.get_or_create_user_token(instance)
        data['gym_name'] = instance.gym_detail_user.gym_name
        return data

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'gym_name']


class GymOwnerSignUpCompleteSerializer(serializers.ModelSerializer):
    class WeekDays(models.IntegerChoices):
        SUNDAY = 1
        MONDAY = 2
        TUESDAY = 3
        WEDNESDAY = 4
        THURSDAY = 5
        FRIDAY = 6
        SATURDAY = 7

    week_day = fields.MultipleChoiceField(choices=WeekDays.choices)

    def validate(self, attrs):
        request = self.context.get('request')
        if attrs.get('address') and (not request.data.get('lat') or not request.data.get('lng')):
            raise serializers.ValidationError(validation_message.get("LAT_LNG_FOR_ADDRESS"))
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get('request')
        lat = float(request.data.get('lat'))
        lng = float(request.data.get('lng'))
        point = Point(x=lng, y=lat, srid=4326)
        validated_data.update({"geo_point": point})
        GymDetails.objects.filter(id=instance.id).update(**validated_data)
        return validated_data

    class Meta:
        model = GymDetails
        fields = ('id', 'user_id', 'gym_phone_number',
                  'address', 'gym_avatar', 'zipcode', 'easy_direction_link', 'website_link',
                  'description', 'week_day', 'start_time', 'end_time', "RopeClimbing",
                  "Bouldering", "documents","temp_documents", "document_state", 'is_profile_complete', 'is_admin_approved')


class OwnerLogInSerializer(serializers.ModelSerializer):
    """
        OwnerLogInSerializer serializer used verify the login credentials.
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)
    password = serializers.CharField(min_length=8, max_length=20, required=True)

    def validate(self, attrs):
        user = authenticate(email=attrs['email'].lower(), password=attrs['password'])
        # if user and user.user_role.filter(name=Role.RoleType.GYM_OWNER, role_status=True).exists():
        if user and user.user_role.filter(name__in=[Role.RoleType.GYM_OWNER, Role.RoleType.GYM_STAFF],
                                          role_status=True).exists():
            # add user in attrs
            attrs['user'] = user
            return attrs
        else:
            raise serializers.ValidationError(validation_message.get('INVALID_CREDENTIAL'))

    def to_representation(self, instance):
        data = super(OwnerLogInSerializer, self).to_representation(instance)
        user_role_name = self.context.get('user_role_name')
        data['token'] = core_utils.get_or_create_user_token(instance)
        if user_role_name == Role.RoleType.GYM_OWNER:
            data['is_profile_complete'] = instance.gym_detail_user.is_profile_complete
            data['gym_name'] = instance.gym_detail_user.gym_name
            data['gym_id'] = instance.gym_detail_user.id
            data['user_role'] = user_role_name
        else:
            staff_instance = instance.user_details.home_gym
            data['gym_name'] = staff_instance.gym_name
            data['gym_id'] = staff_instance.id
            data['user_role'] = 3
        return data

    def create(self, validated_data):
        with transaction.atomic():
            instance = validated_data.get('user')
            return instance

    class Meta:
        model = User
        fields = ('id', 'email', 'password')


class GymForgotPasswordSerializer(serializers.Serializer):
    """
        GymForgotPasswordSerializer used forgot password
    """
    email = serializers.EmailField(min_length=5, max_length=50, required=True)

    def create(self, validated_data):
        with transaction.atomic():
            # instance = User.objects.filter(email=validated_data.get('email').lower(),
            #                                user_role__name=Role.RoleType.GYM_OWNER, user_role__role_status=True). \
            #     only('id', 'email', ).first()
            instance = User.objects.filter(email=validated_data.get('email').lower(),
                                           user_role__name__in=[Role.RoleType.GYM_OWNER, Role.RoleType.GYM_STAFF],
                                           user_role__role_status=True).only('id', 'email', ).first()
            if not instance:
                raise CustomException(status_code=400, message=validation_message.get("USER_NOT_FOUND"),
                                      location=validation_message.get("LOCATION"))
            # create the forgot password token
            forgot_password_token = core_utils.generate_verification_token(instance,
                                                                           AccountVerification.VerificationType.
                                                                           FORGOT_PASSWORD)
            forgot_password_url = gym_forgotpassword_url + forgot_password_token.token + "/"
            # send forgot password token to email
            p = Process(target=core_utils.send_forgot_password_link_to_email,
                        args=(instance.email, forgot_password_url,))
            p.start()
            # Remove during production
            self.validated_data["forgot_password_url"] = forgot_password_url
            return True


class GymResetPasswordSerializer(serializers.Serializer):
    """method to reset user's password"""

    token = serializers.CharField(required=True)
    password = serializers.CharField(min_length=8, max_length=20, required=True)

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
        print(validated_data["password"], "validated_data[password] is as -")
        user_obj.set_password(validated_data["password"])
        user_obj.save()
        # deleting token to signout user out of other device
        Token.objects.filter(user=user_obj).delete()
        Token.objects.get_or_create(user=user_obj)

        # To mark token as used
        account_verify.is_used = True
        account_verify.save()
        return True


class UserSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'full_name', 'phone_number', 'is_email_verified',
                  'is_phone_verified', 'is_active', 'is_staff', 'is_superuser')


class GymOwnerListSerializer(DynamicFieldsModelSerializer):
    user = UserSerializer(allow_null=True, fields=('id', 'email'))

    class Meta:
        model = GymDetails
        fields = ('id', 'user', 'gym_name', 'gym_avatar', 'gym_phone_number', 'week_day', 'start_time', 'end_time',
                  'address', 'zipcode', 'easy_direction_link', 'website_link', "RopeClimbing", "Bouldering",
                  'description', "documents", "temp_documents", "document_state", 'is_profile_complete', 'is_admin_approved')


class GymlayoutCreateSerializer(serializers.ModelSerializer):
    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        request = self.context.get('request')
        with transaction.atomic():
            layout_obj = GymLayout.objects.create(**validated_data)
        return layout_obj

    class Meta:
        model = GymLayout
        fields = ('id', 'layout_image', 'title', 'gym', 'category', 'image_size', 'is_active')


class GymlayoutUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GymLayout
        fields = ('id', 'layout_image', 'title', 'gym', 'image_size', 'category')


class GymlayoutRetrieveSerializer(DynamicFieldsModelSerializer):
    gym = GymOwnerListSerializer(allow_null=True, fields=('id', 'gym_name', 'user'))

    class Meta:
        model = GymLayout
        fields = ('id', 'layout_image', 'title', 'gym', 'category', 'image_size', 'is_deleted')


class LayoutSectionSerializer(serializers.ModelSerializer):
    section_point = serializers.CharField(required=False)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        request = self.context.get('request')
        try:
            layout_obj = LayoutSection.objects.create(**validated_data)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return layout_obj

    def update(self, instance, validated_data):
        try:
            LayoutSection.objects.filter(id=instance.id).update(**validated_data)
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return_obj = LayoutSection.objects.filter(id=instance.id).first()
        return return_obj

    class Meta:
        model = LayoutSection
        fields = ('id', 'gym_layout', 'name', 'section_point', 'image_size')


class LayoutSectionRetrieveSerializer(DynamicFieldsModelSerializer):
    gym_layout = GymlayoutRetrieveSerializer(allow_null=True, fields=('id', 'title', 'gym'))
    section_point = serializers.SerializerMethodField()

    def get_section_point(self, obj):
        obj_section_point = obj.section_point
        if obj_section_point:
            linear_point = obj_section_point[0]
            point = [linear_point[each] for each in range(len(linear_point))]
            point_4 = point[:4]
            return point_4

    class Meta:
        model = LayoutSection
        fields = ('id', 'name', 'section_point', 'gym_layout', 'image_size')


class GetGymOwnerProfileSerializer(DynamicFieldsModelSerializer):
    user = UserSerializer(allow_null=True, fields=('id', 'email'))
    is_gym_owner = serializers.SerializerMethodField()

    def get_is_gym_owner(self, obj):
        role_name = self.context.get('role_name')
        if role_name == Role.RoleType.GYM_OWNER:
            data = True
        else:
            data = False
        return data

    class Meta:
        model = GymDetails
        fields = ('id', 'gym_name', 'user', 'gym_avatar', 'gym_phone_number',
                  'address', 'zipcode', 'easy_direction_link', 'website_link',
                  'description', 'week_day', 'start_time', 'end_time', "RopeClimbing",
                  "Bouldering", "documents", "temp_documents", "document_state", 'is_profile_complete',
                  'is_admin_approved', 'is_gym_owner',)


class GymWallTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_obj = self.context.get('gym_obj')
        try:
            wall_obj = WallType.objects.create(**validated_data, gym=gym_obj)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return wall_obj

    def update(self, instance, validated_data):
        try:
            instance.name = validated_data.get('name')
            instance.save()
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return instance

    class Meta:
        model = WallType
        fields = ('id', 'gym', 'name',)


class GymWallSerializer(serializers.ModelSerializer):
    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        section_obj = self.context.get('section_obj')
        requested_user = self.context.get('request').user
        layout_obj = section_obj.gym_layout_id
        try:
            wall_obj = SectionWall.objects.create(**validated_data, gym_layout_id=layout_obj,
                                                  created_by=requested_user)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return wall_obj

    def update(self, instance, validated_data):
        try:
            reset_time = instance.reset_timer
            if reset_time:
                current_time = datetime.today().replace(tzinfo=utc)
                reset_time = reset_time.replace(tzinfo=utc)
                if reset_time < current_time and validated_data.get('image') != instance.image:
                    validated_data['reset_timer'] = None
            # To delete ghost route if ghost wall is deleted
            if not validated_data.get('ghost_wall_name'):
                GhostWallRoute.objects.filter(section_wall=instance).update(is_deleted=True)
            SectionWall.objects.filter(id=instance.id).update(**validated_data)
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return_obj = SectionWall.objects.filter(id=instance.id).first()
        return return_obj

    class Meta:
        model = SectionWall
        fields = ('id', 'category', 'gym_layout', 'layout_section', 'image', 'image_size', 'name',
                  'wall_type', 'wall_height', 'reset_timer', 'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',
                  'created_at', 'updated_at',)


class GymWallRetrieveSerializer(DynamicFieldsModelSerializer):
    layout_section = LayoutSectionRetrieveSerializer(allow_null=True)
    wall_type = GymWallTypeSerializer()

    class Meta:
        model = SectionWall
        fields = ('id', 'category', 'image', 'image_size', 'name', 'wall_type', 'wall_height',
                  'gym_layout', 'layout_section', 'created_at', 'updated_at', 'reset_timer',
                  'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',)


class GymGhostWallSerializer(serializers.ModelSerializer):
    def update(self, instance, validated_data):
        try:
            SectionWall.objects.filter(id=instance.id).update(**validated_data)
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return_obj = SectionWall.objects.filter(id=instance.id).first()
        return return_obj

    class Meta:
        model = SectionWall
        fields = ('id', 'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',)


class PreLoadedTemplateSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        PreLoadedTemplateSerializer class used to serialize pre-loaded template.
    """

    class Meta:
        model = PreLoadedTemplate
        fields = ('id', 'uploaded_template',)


class GymAnnouncementDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymAnnouncementDetailSerializer class used to get serialized announcement.
    """
    template = PreLoadedTemplateSerializer()

    class Meta:
        model = Announcement
        fields = ('id', 'gym', 'banner', 'template', 'template_type', 'picture', 'title', 'sub_title', 'priority',
                  'created_at', 'is_active',)


class GymAnnouncementSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymAnnouncementSerializer class used to add/update announcement.
    """
    gym = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.all(), required=True)
    banner = serializers.CharField(max_length=255, required=False)
    template = serializers.PrimaryKeyRelatedField(queryset=PreLoadedTemplate.objects.all(), required=False)
    picture = serializers.CharField(max_length=255, required=False)
    title = serializers.CharField(max_length=200, required=False)
    sub_title = serializers.CharField(max_length=200, required=False)

    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        banner_data = validated_data.get('banner')
        template_data = validated_data.get('template')
        validated_data['template_type'] = 0 if banner_data else template_data.id
        instance = super(GymAnnouncementSerializer, self).create(validated_data)
        return instance

    def update(self, instance, validated_data):
        """
            method used to update the data.
        :param instance:
        :param validated_data:
        :return:
        """
        var_none = None
        if validated_data.get('banner'):
            validated_data['template'] = var_none
            validated_data['template_type'] = 0
            validated_data['picture'] = var_none
            validated_data['title'] = var_none
            validated_data['sub_title'] = var_none
        else:
            validated_data['banner'] = var_none
            validated_data['template_type'] = validated_data.get('template').id
        instance = super(GymAnnouncementSerializer, self).update(instance, validated_data)
        return instance

    class Meta:
        model = Announcement
        fields = ('id', 'gym', 'banner', 'template', 'template_type', 'picture', 'title', 'sub_title', 'priority',
                  'created_at', 'is_active',)


class GymEventSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymEventSerializer class used to add/update event.
    """
    gym = serializers.PrimaryKeyRelatedField(queryset=GymDetails.objects.all(), required=True)
    thumbnail = serializers.CharField(max_length=255, required=True)
    title = serializers.CharField(max_length=200, required=True)
    start_date = serializers.DateTimeField(required=True)
    description = serializers.CharField(max_length=500, allow_blank=True, required=True)

    def create(self, validated_data: dict):
        """
            method used to create the data.
        :param validated_data:
        :return:
        """
        instance = super(GymEventSerializer, self).create(validated_data)
        return instance

    def update(self, instance, validated_data):
        """
            method used to update the data.
        :param instance:
        :param validated_data:
        :return:
        """
        instance = super(GymEventSerializer, self).update(instance, validated_data)
        return instance

    class Meta:
        model = Event
        fields = ('id', 'gym', 'thumbnail', 'title', 'start_date', 'description', 'is_active',)


class GymColorTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)
    hex_value = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_obj = self.context.get('gym_obj')
        try:
            color_obj = ColorType.objects.create(**validated_data, gym=gym_obj)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return color_obj

    def update(self, instance, validated_data):
        try:
            instance.name = validated_data.get('name')
            instance.hex_value = validated_data.get('hex_value')
            instance.save()
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return instance

    class Meta:
        model = ColorType
        fields = ('id', 'gym', 'name', 'hex_value',)


class GymRouteTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_obj = self.context.get('gym_obj')
        try:
            route_obj = RouteType.objects.create(**validated_data, gym=gym_obj)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return route_obj

    def update(self, instance, validated_data):
        try:
            instance.name = validated_data.get('name')
            instance.save()
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return instance

    class Meta:
        model = RouteType
        fields = ('id', 'gym', 'name',)


class GymWallRouteSerializer(serializers.ModelSerializer):
    # color = GymColorTypeSerializer()
    # route_type = GymRouteTypeSerializer()

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        request = self.context.get("request")
        try:
            route_obj = WallRoute.objects.create(**validated_data, created_by=request.user)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return route_obj

    def update(self, instance, validated_data):
        try:
            WallRoute.objects.filter(id=instance.id).update(**validated_data)
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return_obj = WallRoute.objects.filter(id=instance.id).first()
        return return_obj

    class Meta:
        model = WallRoute
        fields = ('id', 'section_wall', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'tag_point',
                  "created_by", "image_size")


class ListGymGradeTypeSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = GradeType
        fields = ('id', 'grading_system', 'sub_category', 'sub_category_value')


class GymWallRouteRetrieveSerializer(DynamicFieldsModelSerializer):
    created_by = UserSerializer(allow_null=True, fields=("id", "full_name", "email"))
    grade = ListGymGradeTypeSerializer(allow_null=True)
    color = GymColorTypeSerializer()
    route_type = GymRouteTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'section_wall', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'tag_point',
                  "created_by", "image_size")


class GhostWallRouteSerializer(serializers.ModelSerializer):
    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        request = self.context.get("request")
        try:
            route_obj = GhostWallRoute.objects.create(**validated_data, created_by=request.user)
            # To send notification
            staff_ids = [validated_data.get('assigned_to').id]
            title = 'New Route Tag Assigned'
            message = 'You have assigned a route tag.'
            data = {'wall_id': validated_data.get('section_wall').id, 'route_id': route_obj.id}
            core_utils.send_notification_to_gym_staff(staff_ids, title, message, data)
        except Exception:
            raise serializers.ValidationError(validation_message.get("SOMETHING_WENT_WRONG"))
        return route_obj

    def update(self, instance, validated_data):
        try:
            assigned_to_old = instance.assigned_to
            assigned_to_new = validated_data.get('assigned_to')
            GhostWallRoute.objects.filter(id=instance.id).update(**validated_data)
        except Exception:
            raise CustomException(status_code=400, message=validation_message.get("SOMETHING_WENT_WRONG"),
                                  location=validation_message.get("LOCATION"))
        return_obj = GhostWallRoute.objects.filter(id=instance.id).first()
        # To send notification
        if assigned_to_old != assigned_to_new:
            staff_ids = [assigned_to_new.id]
            title = 'New Route Tag Assigned'
            message = 'You have assigned a route tag.'
            data = {'wall_id': validated_data.get('section_wall').id, 'route_id': instance.id}
            core_utils.send_notification_to_gym_staff(staff_ids, title, message, data)
        return return_obj

    class Meta:
        model = GhostWallRoute
        fields = ('id', 'section_wall', 'name', 'assigned_to', 'grade', 'created_by', 'tag_point',
                  'image_size',)


class GhostWallRouteRetrieveSerializer(DynamicFieldsModelSerializer):
    assigned_to = UserSerializer(allow_null=True, fields=("id", "full_name", "email"))
    created_by = UserSerializer(allow_null=True, fields=("id", "full_name", "email"))
    grade = ListGymGradeTypeSerializer(allow_null=True)

    class Meta:
        model = GhostWallRoute
        fields = ('id', 'section_wall', 'name', 'assigned_to', 'grade', 'created_by', 'tag_point',
                  "created_by", "image_size",)


class ChangePasswordSerializer(serializers.Serializer):
    """Login Serializer to validate user credentials"""

    old_password = serializers.CharField(
        required=True, write_only=True, min_length=8, max_length=20
    )
    new_password = serializers.CharField(
        required=True, write_only=True, min_length=8, max_length=20
    )

    def validate(self, attrs):
        """to validate attributes"""
        request = self.context.get("request")
        user_obj = authenticate(
            email=request.user.email.lower(), password=attrs.get("old_password")
        )
        if not user_obj:
            raise CustomException(status_code=400, message=validation_message.get("OLD_PASSWORD_WRONG"),
                                  location=validation_message.get("LOCATION"))
        user_obj.set_password(attrs["new_password"])
        user_obj.save()

        # deleting token to signout user out of other device
        Token.objects.filter(user=user_obj).delete()
        token, created = Token.objects.get_or_create(user=user_obj)
        attrs["token"] = token.key
        return attrs


class GymWallRouteListSerializer(DynamicFieldsModelSerializer):
    grade = ListGymGradeTypeSerializer()
    created_by = UserSerializer(allow_null=True, fields=("id", "full_name", "email"))
    color = GymColorTypeSerializer()
    route_type = GymRouteTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'section_wall', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'tag_point',
                  "created_by", "image_size")


class RouteTagListCommunityRGradeSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = UserRouteFeedback
        fields = ('id', 'user', 'gym', 'route', 'route_progress', 'attempt_count', 'route_note', 'climb_count',
                  'grade', 'rating', 'feedback')


class RouteTagListFeedbackListSerializer(DynamicFieldsModelSerializer):
    user = UserSerializer(allow_null=True, fields=('id', 'full_name'))
    route = GymWallRouteRetrieveSerializer(allow_null=True, fields=('id', 'name', 'grade'))

    class Meta:
        model = UserRouteFeedback
        fields = ('id', 'updated_at', 'user', 'route', 'route_progress', 'attempt_count', 'route_note', 'climb_count',
                  'grade', 'rating', 'feedback')


class GymOwnerProfileUpdateSerializer(serializers.ModelSerializer):
    class WeekDays(models.IntegerChoices):
        SUNDAY = 1
        MONDAY = 2
        TUESDAY = 3
        WEDNESDAY = 4
        THURSDAY = 5
        FRIDAY = 6
        SATURDAY = 7

    week_day = fields.MultipleChoiceField(choices=WeekDays.choices)

    def validate(self, attrs):
        request = self.context.get('request')
        if attrs.get('address') and (not request.data.get('lat') or not request.data.get('lng')):
            raise serializers.ValidationError(validation_message.get("LAT_LNG_FOR_ADDRESS"))
        try:
            if User.all_objects.filter(email=request.data.get('email').lower()).exists():
                raise serializers.ValidationError(validation_message.get("EMAIL_ALREADY_EXIST"))
        except Exception:
            pass
        return attrs

    def update(self, instance, validated_data):
        request = self.context.get('request')
        try:
            lat = float(request.data.get('lat'))
            lng = float(request.data.get('lng'))
            point = Point(x=lng, y=lat, srid=4326)
            validated_data.update({"geo_point": point})
        except Exception:
            pass
        # if request.data.get('temp_documents'):
        #     GymDetails.objects.filter(id=instance.id).update(document_state=GymDetails.DocumentChoices.PENDING)
        """
        emp_dict = dict()
        if request.data.get("email") != instance.user.email:
            emp_dict['email'] = request.data.get("email")
        if validated_data.get("gym_name") != instance.gym_name:
            emp_dict['gym_name'] = validated_data.pop("gym_name")
        if validated_data.get("easy_direction_link") != instance.easy_direction_link:
            emp_dict['easy_direction_link'] = validated_data.pop("easy_direction_link")
        if validated_data.get("website_link") != instance.website_link:
            emp_dict['website_link'] = validated_data.pop("website_link")
        if len(emp_dict) > 0:
            emp_dict['gym_detail'] = instance
            print(emp_dict)
            cr, bool_val = ChangeRequestGymDetails.objects.get_or_create(gym_detail=instance)
            for i, j in emp_dict.items():
                setattr(cr, i, j)
            cr.save()
        """
        data = GymDetails.objects.filter(id=instance.id)
        data.update(**validated_data)
        return_obj = data.first()
        if request.data.get('email'):
            # create the email verification token
            email = request.data.get('email').lower()
            verification_token = core_utils.generate_verification_token(request.user,
                                                                        AccountVerification.VerificationType.
                                                                        EMAIL_VERIFICATION)
            email_verification_url = gym_emailverification_url + "?otp=" + verification_token.token + "&email=" \
                                     + request.data.get("email")
            # send verification token to email
            p = Process(target=core_utils.send_verification_link_to_email,
                        args=(email, email_verification_url,))
            p.start()
            # Remove during production
            self.validated_data['email_verification_token'] = email_verification_url
        # return_obj = GymDetails.objects.filter(id=instance.id).first()
        return return_obj

    def to_representation(self, instance):
        data = super(GymOwnerProfileUpdateSerializer, self).to_representation(instance)
        data['email'] = instance.user.email
        return data

    class Meta:
        model = GymDetails
        fields = ('id', 'gym_name', 'gym_phone_number', 'user', 'start_time', 'end_time',
                  'address', 'zipcode', 'easy_direction_link', 'website_link',
                  'description', 'gym_avatar', 'week_day', "RopeClimbing",
                  "Bouldering", "documents", "temp_documents", "document_state", 'is_profile_complete', 'is_admin_approved')


class ListWallSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = SectionWall
        fields = ('id', 'name')


class ListSectionSerializer(DynamicFieldsModelSerializer):
    section_wall = ListWallSerializer(many=True)

    class Meta:
        model = LayoutSection
        fields = ('id', 'name', 'section_wall')


class ListLayoutSerializer(DynamicFieldsModelSerializer):
    gym_layout_section = ListSectionSerializer(many=True)

    class Meta:
        model = GymLayout
        fields = ('id', 'title', 'gym_layout_section')


class RolesSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = Role
        fields = ('id', 'name', 'role_status')


class ListAllUsersSerializer(DynamicFieldsModelSerializer):
    user_role = RolesSerializer(many=True)

    class Meta:
        model = User
        fields = ('id', 'email', 'user_role', 'full_name')


class UserDetailSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = UserDetails
        fields = "__all__"


class UserBiometricSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = UserBiometricData
        fields = "__all__"


class UserPreferenceSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = UserPreference
        fields = "__all__"


class ListGymUsersSerializer(DynamicFieldsModelSerializer):
    user_details = UserDetailSerializer(fields=('age', 'user_avatar', 'updated_at',))
    user_biometric = UserBiometricSerializer(fields=('gender', 'updated_at',))
    user_preference = UserPreferenceSerializer(fields=('bouldering', 'top_rope', 'lead_climbing', 'updated_at',))
    submitted_route = serializers.SerializerMethodField()

    def get_submitted_route(self, obj):
        requested_user = self.context.get('request')
        count_data = UserRouteFeedback.objects.filter(user=obj, gym=requested_user).count()
        return count_data

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'user_details', 'user_biometric', 'user_preference', 'submitted_route',
                  'updated_at',)


class GymRouteSerializer(DynamicFieldsModelSerializer):
    section_wall = ListWallSerializer()
    grade = ListGymGradeTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'section_wall', 'name', 'grade')


class GymUserRouteFeedbackSerializer(DynamicFieldsModelSerializer):
    route = GymRouteSerializer(fields=('section_wall', 'name', 'grade'))
    is_opened = serializers.SerializerMethodField()

    def get_is_opened(self, obj):
        user = self.context.get('request')
        if OpenFeedback.objects.filter(gym_user=user, feedback=obj).exists():
            return True
        return "False"

    class Meta:
        model = UserRouteFeedback
        fields = ('id', 'user', 'gym', 'route', 'route_progress', 'attempt_count',
                  'route_note', 'climb_count', 'grade', 'rating', 'feedback', 'created_at', 'is_opened',)


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
        request = self.context.get('request')
        account_verify = AccountVerification.objects.select_related('user'). \
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
        user_id = account_verify.user_id
        User.objects.filter(id=user_id).update(email=request.data.get('email').lower())
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
            email = self.context.get('email')

            # Check valid domain
            request_domain = email[email.index('@') + 1:]
            valid_domain = Domain.objects.filter(name__iexact=request_domain, is_deleted=False).first()
            if not valid_domain:
                raise CustomException(status_code=400, message=validation_message.get("EMAIL_DOMAIN_WRONG"),
                                      location=validation_message.get("LOCATION"))
                # raise serializers.ValidationError(validation_message.get("EMAIL_DOMAIN_WRONG"))

            instance = self.context.get('request')
            verification_token = core_utils.generate_verification_token(instance,
                                                                        AccountVerification.VerificationType.
                                                                        EMAIL_VERIFICATION)
            email_verification_url = gym_emailverification_url + "?otp=" + verification_token.token + "&email=" \
                                     + email
            # send verification token to email
            p = Process(target=core_utils.send_verification_link_to_email,
                        args=(email, email_verification_url,))
            p.start()
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


class GlobalSearchKeywordSerializer(DynamicFieldsModelSerializer):
    class Meta:
        model = GlobalSearch
        fields = ('id', 'parent', 'child', "sub_child", "sub_child_1",)

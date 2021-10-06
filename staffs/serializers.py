''' project level imports '''
from datetime import datetime

from django.contrib.auth import authenticate
from django.contrib.gis.geos import Point
from django.db import transaction
from fcm_django.models import FCMDevice
from pytz import utc
from rest_framework import serializers
from accounts.models import (AccountVerification, Role, User, UserPreference, GRADING_CHOICES, UserDetails,
                             ListCategory, RouteSaveList, UserRouteFeedback, SavedEvent, UserBiometricData,
                             UserDetailPercentage, WallVisit, QuestionAnswer, UserSubscription, )
from accounts.serializers import GradeTypeSerializer
from admins.models import SubscriptionPlan
from core import utils as core_utils
from core.exception import CustomException
from core.messages import validation_message, variables
from core import serializers as core_serializers
from gyms.models import (GymDetails, GymLayout, WallRoute, Event, Announcement, LayoutSection, SectionWall, WallType,
                         RouteType, ColorType, GhostWallRoute, )


class UserDeviceSerializer(serializers.Serializer):
    """
        UserDeviceSerializer used to save the user fcm token.
    """
    DEVICE_CHOICE = (
        'ios', 'ios',
        'android', 'android',
        'web', 'web'
    )

    device_type = serializers.ChoiceField(choices=DEVICE_CHOICE, required=True)
    registration_id = serializers.CharField(required=True, min_length=10)

    def update(self, instance, validated_data):
        """
            method used to update the user location Serializer.
        :param instance:
        :param validated_data:
        :return:
        """
        with transaction.atomic():
            core_utils.update_or_create_fcm_detail(instance, validated_data.get('registration_id'),
                                                   validated_data.get('device_type'))
            return True


class UserDeviceDetailSerializer(serializers.ModelSerializer):
    """
        UserDeviceDetailSerializer used to get the user details.
    """
    class Meta:
        model = FCMDevice
        fields = ('id', 'user', 'registration_id', 'type',)


class StaffGymDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffGymDetailSerializer class used to provide Gym Details.
    """
    is_gym_staff = serializers.SerializerMethodField()

    def get_is_gym_staff(self, obj):
        requested_user = self.context.get('request')
        staff_role = Role.objects.filter(user=requested_user, name=Role.RoleType.GYM_STAFF, role_status=True)
        if staff_role:
            return True
        return False

    class Meta:
        model = GymDetails
        fields = ('id', 'gym_name', 'is_gym_staff',)


class StaffColorTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)
    hex_value = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_id = self.context.get('gym_id')
        try:
            color_obj = ColorType.objects.create(**validated_data, gym_id=gym_id)
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


class StaffOnlyRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffOnlyRouteDetailSerializer class used to provide Only Wall Route Detail.
    """
    grade = GradeTypeSerializer()
    color = StaffColorTypeSerializer()

    class Meta:
        model = WallRoute
        fields = ('id', 'name', 'grade', 'color', 'image_size', 'tag_point',)


class StaffWallTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_id = self.context.get('gym_id')
        try:
            wall_obj = WallType.objects.create(**validated_data, gym_id=gym_id)
        except Exception as e:
            print(e)
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


class StaffWallDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffWallDetailSerializer used to retrieve wall details.
    """
    is_added_by_me = serializers.SerializerMethodField()
    wall_type = StaffWallTypeSerializer()

    def get_is_added_by_me(self, obj):
        user = self.context.get('request')
        create_by = obj.created_by
        if create_by and create_by == user:
            return True
        return False

    class Meta:
        model = SectionWall
        fields = ('id', 'image', 'image_size', 'name', 'wall_type', 'wall_height', 'is_added_by_me', 'reset_timer',
                  'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',)


class StaffWallSerializer(serializers.ModelSerializer):
    """
        StaffWallSerializer used to add/update staff wall.
    """
    category = serializers.ChoiceField(choices=SectionWall.ClimbingType.choices, required=True)
    gym_layout = serializers.PrimaryKeyRelatedField(queryset=GymLayout.objects.all(), required=True)
    layout_section = serializers.PrimaryKeyRelatedField(queryset=LayoutSection.objects.all(), required=True)
    image = serializers.CharField(max_length=255, required=True)
    image_size1 = serializers.FloatField(required=True, write_only=True)
    image_size2 = serializers.FloatField(required=True, write_only=True)
    name = serializers.CharField(max_length=50, required=True)
    # wall_type = serializers.ChoiceField(choices=SectionWall.WallType.choices, required=True)
    wall_type = serializers.PrimaryKeyRelatedField(queryset=WallType.objects.all(), required=True)

    def create(self, validated_data):
        """
            method used to add the wall detail
        :param validated_data:
        :return:
        """
        validated_data['created_by'] = self.context.get('request')
        validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        with transaction.atomic():
            instance = super(StaffWallSerializer, self).create(validated_data)
            return instance

    def update(self, instance, validated_data):
        """
            method used to update the wall detail
        :param instance:
        :param validated_data:
        :return:
        """
        validated_data['created_by'] = self.context.get('request')
        validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        with transaction.atomic():
            reset_time = instance.reset_timer
            if reset_time:
                current_time = datetime.today().replace(tzinfo=utc)
                reset_time = reset_time.replace(tzinfo=utc)
                if reset_time < current_time and validated_data.get('image') != instance.image:
                    validated_data['reset_timer'] = None
            # To delete ghost route if ghost wall is deleted
            if not validated_data.get('ghost_wall_name'):
                GhostWallRoute.objects.filter(section_wall=instance).update(is_deleted=True)
            instance = super(StaffWallSerializer, self).update(instance, validated_data)
            return instance

    class Meta:
        model = SectionWall
        fields = ('id', 'category', 'gym_layout', 'layout_section', 'image', 'image_size', 'image_size1', 'image_size2',
                  'name', 'wall_type', 'created_by', 'reset_timer', 'ghost_wall_image', 'ghost_wall_size',
                  'ghost_wall_name',)


class StaffGhostWallDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffGhostWallDetailSerializer used to retrieve ghost wall details.
    """
    is_added_by_me = serializers.SerializerMethodField()

    def get_is_added_by_me(self, obj):
        user = self.context.get('request')
        create_by = obj.created_by
        if create_by and create_by == user:
            return True
        return False

    class Meta:
        model = SectionWall
        fields = ('id', 'is_added_by_me', 'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',)


class StaffGhostWallSerializer(serializers.ModelSerializer):
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


class UserDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        UserDetailSerializer class used to provide Staff Detail.
    """
    class Meta:
        model = User
        fields = ('id', 'full_name', 'email',)


class StaffOnlyGhostRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffOnlyGhostRouteDetailSerializer class used to provide Only Ghost Wall Route Detail.
    """
    assigned_to = UserDetailSerializer()
    grade = GradeTypeSerializer()

    class Meta:
        model = GhostWallRoute
        fields = ('id', 'name', 'assigned_to', 'grade', 'tag_point', 'image_size',)


class StaffLayoutSectionDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffLayoutSectionDetailSerializer class used to provide Layout Section Detail.
    """
    section_wall = StaffWallDetailSerializer(fields=('id', 'layout_section', 'gym_layout', 'image', 'name',
                                                     'reset_timer',), many=True)

    class Meta:
        model = LayoutSection
        fields = ('id', 'gym_layout', 'name', 'section_wall',)


class StaffOnlyLayoutSectionDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffOnlyLayoutSectionDetailSerializer class used to provide Layout Section Detail.
    """
    section_point = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    def get_section_point(self, obj):
        obj_section_point = obj.section_point
        if obj_section_point:
            linear_point = obj_section_point[0]
            point = [linear_point[each] for each in range(len(linear_point))]
            point_4 = point[:4]
            return point_4
        return None

    def get_title(self, obj):
        return obj.name

    class Meta:
        model = LayoutSection
        fields = ('id', 'name', 'title', 'image_size', 'section_point',)


class StaffGymLayoutDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffGymLayoutDetailSerializer class used to provide Gym Layout Detail.
    """
    gym_layout_section = StaffLayoutSectionDetailSerializer(many=True)

    class Meta:
        model = GymLayout
        fields = ('id', 'gym', 'category', 'layout_image', 'image_size', 'title',  'gym_layout_section',)


class StaffRouteTypeSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, required=True)

    def create(self, validated_data: dict):
        """
        method used to create the data.
        :param validated_data:
        :return:
        """
        gym_id = self.context.get('gym_id')
        try:
            route_obj = RouteType.objects.create(**validated_data, gym_id=gym_id)
        except Exception as e:
            print(e)
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


class StaffRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffRouteDetailSerializer class used to provide Route Detail with Wall details.
    """
    grade = GradeTypeSerializer()
    color = StaffColorTypeSerializer()
    route_type = StaffRouteTypeSerializer()
    section_wall = StaffWallDetailSerializer(fields=('id', 'image', 'name',))
    is_added_by_me = serializers.SerializerMethodField()

    def get_is_added_by_me(self, obj):
        user = self.context.get('request')
        create_by = obj.created_by
        if create_by and create_by == user:
            return True
        return False

    class Meta:
        model = WallRoute
        fields = ('id', 'name', 'grade', 'color', 'route_type', 'setter_tip', 'created_by', 'image_size', 'tag_point',
                  'section_wall', 'is_added_by_me',)


class StaffRouteSerializer(serializers.ModelSerializer):
    """
        StaffRouteSerializer used to add/update staff route.
    """
    section_wall = serializers.PrimaryKeyRelatedField(queryset=SectionWall.objects.all(), required=True)
    name = serializers.CharField(max_length=100, allow_blank=True, required=True)
    # color = serializers.ChoiceField(choices=WallRoute.ColorType.choices, required=True)
    color = serializers.PrimaryKeyRelatedField(queryset=ColorType.objects.all(), required=True)
    # route_type = serializers.ChoiceField(choices=WallRoute.RouteType.choices, required=True)
    route_type = serializers.PrimaryKeyRelatedField(queryset=RouteType.objects.all(), required=True)
    setter_tip = serializers.CharField(max_length=200, allow_blank=True, required=True)
    # image_size = serializers.ListField(required=True)
    image_size1 = serializers.FloatField(required=True, write_only=True)
    image_size2 = serializers.FloatField(required=True, write_only=True)
    # tag_point = serializers.ListField(required=True)
    tag_point = serializers.ListField(default=0)
    tag_point1 = serializers.FloatField(required=True, write_only=True)
    tag_point2 = serializers.FloatField(required=True, write_only=True)

    def create(self, validated_data):
        """
            method used to add the route detail
        :param validated_data:
        :return:
        """
        validated_data['created_by'] = self.context.get('request')
        validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        validated_data['tag_point'] = [validated_data.pop('tag_point1'), validated_data.pop('tag_point2')]
        with transaction.atomic():
            instance = super(StaffRouteSerializer, self).create(validated_data)
            return instance

    def update(self, instance, validated_data):
        """
            method used to update the route detail
        :param instance:
        :param validated_data:
        :return:
        """
        validated_data['created_by'] = self.context.get('request')
        validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        validated_data['tag_point'] = [validated_data.pop('tag_point1'), validated_data.pop('tag_point2')]
        with transaction.atomic():
            instance = super(StaffRouteSerializer, self).update(instance, validated_data)
            return instance

    class Meta:
        model = WallRoute
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'is_active',)


class OnlyStaffWallDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        OnlyStaffWallDetailSerializer used to retrieve wall details.
    """
    category = serializers.SerializerMethodField()
    gym_layout = StaffGymLayoutDetailSerializer(fields=('id', 'title',))
    layout_section = StaffOnlyLayoutSectionDetailSerializer(fields=('id', 'title',))
    is_added_by_me = serializers.SerializerMethodField()
    wall_type = StaffWallTypeSerializer()

    def get_category(self, obj):
        if obj.category == 0:
            # data = {"id": 0, "category_name": "Rope Climbing"}
            data = {"id": 0, "title": "Rope Climbing"}
        else:
            # data = {"id": 1, "category_name": "Bouldering"}
            data = {"id": 1, "title": "Bouldering"}
        return data

    def get_is_added_by_me(self, obj):
        user = self.context.get('request')
        create_by = obj.created_by
        if create_by and create_by == user:
            return True
        return False

    class Meta:
        model = SectionWall
        fields = ('id', 'image', 'image_size', 'name', 'category', 'gym_layout', 'layout_section', 'wall_type',
                  'wall_height', 'is_added_by_me', 'ghost_wall_image', 'ghost_wall_size', 'ghost_wall_name',)


class StaffGhostRouteSerializer(serializers.ModelSerializer):
    """
        StaffGhostRouteSerializer used to add/update staff route.
    """
    section_wall = serializers.PrimaryKeyRelatedField(queryset=SectionWall.objects.all(), required=True)
    name = serializers.CharField(max_length=100, allow_blank=True, required=True)
    assigned_to = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)
    image_size1 = serializers.FloatField(required=False, write_only=True)
    image_size2 = serializers.FloatField(required=False, write_only=True)
    tag_point = serializers.ListField(default=0)
    tag_point1 = serializers.FloatField(required=False, write_only=True)
    tag_point2 = serializers.FloatField(required=False, write_only=True)

    def create(self, validated_data):
        """
            method used to add the ghost route detail
        :param validated_data:
        :return:
        """
        validated_data['created_by'] = self.context.get('request')
        if validated_data.get('image_size1') and validated_data.get('image_size2'):
            validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        if validated_data.get('tag_point1') and validated_data.get('tag_point2'):
            validated_data['tag_point'] = [validated_data.pop('tag_point1'), validated_data.pop('tag_point2')]
        with transaction.atomic():
            instance = super(StaffGhostRouteSerializer, self).create(validated_data)
            # To send notification
            staff_ids = [validated_data.get('assigned_to').id]
            title = 'New Route Tag Assigned'
            message = 'You have assigned a route tag.'
            data = {'wall_id': validated_data.get('section_wall').id, 'route_id': instance.id}
            core_utils.send_notification_to_gym_staff(staff_ids, title, message, data)
            return instance

    def update(self, instance, validated_data):
        """
            method used to update the ghost route detail
        :param instance:
        :param validated_data:
        :return:
        """
        if validated_data.get('image_size1') and validated_data.get('image_size2'):
            validated_data['image_size'] = [validated_data.pop('image_size1'), validated_data.pop('image_size2')]
        if validated_data.get('tag_point1') and validated_data.get('tag_point2'):
            validated_data['tag_point'] = [validated_data.pop('tag_point1'), validated_data.pop('tag_point2')]
        with transaction.atomic():
            assigned_to_old = instance.assigned_to
            assigned_to_new = validated_data.get('assigned_to')
            instance = super(StaffGhostRouteSerializer, self).update(instance, validated_data)
            # To send notification
            if assigned_to_old != assigned_to_new:
                staff_ids = [assigned_to_new.id]
                title = 'New Route Tag Assigned'
                message = 'You have assigned a route tag.'
                data = {'wall_id': validated_data.get('section_wall').id, 'route_id': instance.id}
                core_utils.send_notification_to_gym_staff(staff_ids, title, message, data)
            return instance

    class Meta:
        model = GhostWallRoute
        exclude = ('created_at', 'updated_at', 'updated_by', 'is_deleted', 'deleted_at', 'is_active',)
        # fields = ('id', 'section_wall', 'name', 'assigned_to', 'grade', 'created_by', 'tag_point', 'image_size',
        #           'image_size1', 'image_size2', 'tag_point1', 'tag_point2',)


class StaffGhostRouteDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffGhostRouteDetailSerializer class used to provide Route Detail with Wall details.
    """
    grade = GradeTypeSerializer()
    section_wall = StaffWallDetailSerializer(fields=('id', 'image', 'name',))

    class Meta:
        model = GhostWallRoute
        fields = ('id', 'section_wall', 'name', 'assigned_to', 'grade', 'created_by', 'tag_point',
                  "created_by", "image_size",)


# Profile

class StaffDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        StaffDetailSerializer class used to provide Staff Detail.
    """
    user_avatar = serializers.SerializerMethodField()

    def get_user_avatar(self, obj):
        detail_instance = getattr(obj, 'user_details')
        if detail_instance:
            return detail_instance.user_avatar
        return None

    class Meta:
        model = User
        fields = ('id', 'full_name', 'email', 'user_avatar',)


class PlanDetailSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymPlanSerializer class used to provide Plan Details.
    """
    class Meta:
        model = SubscriptionPlan
        fields = ('id', 'title', 'amount', "currency", "plan_id", "product", "interval",
                  'access_to_wall_pics', 'uploaded_wall_number',
                  "active_gymstaff_number", 'active_gymstaff_number', 'access_feedback_per_month',
                  'announcements_create', 'access_to_biometric_data', 'access_to_sign_up_info',
                  'clicks_of_advertising_space', 'gym_ads_on_app'
                  )


class GymPlanSerializer(core_serializers.DynamicFieldsModelSerializer):
    """
        GymPlanSerializer class used to provide Plan Details.
    """
    plan = PlanDetailSerializer()
    is_active_subscription = serializers.BooleanField(default=True)

    class Meta:
        model = UserSubscription
        fields = ('id', 'user', 'is_stripe_customer', 'is_subscribed', 'subscription_start', 'subscription_end',
                  'subscription_interval', 'subscription_status', 'subscription_id', 'plan', 'is_active_subscription',)

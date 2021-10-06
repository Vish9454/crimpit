from datetime import datetime, timezone

from django.db import transaction
from fcm_django.models import FCMDevice

from accounts.serializers import GradeTypeSerializer

''' rest framework import '''
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Avg, Count, Sum, Q
from rest_framework import status as status_code
from rest_framework import mixins, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authtoken.models import Token

''' project level import '''
from accounts.models import UserPreference, ListCategory, RouteSaveList, UserRouteFeedback, SavedEvent, \
    UserBiometricData, UserDetailPercentage, WallVisit, UserDetails, QuestionAnswer, User, Role
from staffs.serializers import (StaffWallSerializer, StaffRouteSerializer, StaffWallDetailSerializer,
                                StaffOnlyRouteDetailSerializer, StaffRouteDetailSerializer, StaffGymDetailSerializer,
                                StaffOnlyLayoutSectionDetailSerializer, StaffGymLayoutDetailSerializer,
                                StaffDetailSerializer, OnlyStaffWallDetailSerializer, GymPlanSerializer,
                                StaffWallTypeSerializer, StaffColorTypeSerializer, StaffRouteTypeSerializer,
                                StaffGhostWallDetailSerializer, StaffOnlyGhostRouteDetailSerializer,
                                StaffGhostWallSerializer, StaffGhostRouteSerializer, StaffGhostRouteDetailSerializer,
                                UserDeviceDetailSerializer, UserDeviceSerializer, )
from core.authentication import CustomTokenAuthentication
from core.exception import get_custom_error, CustomException
from core.messages import success_message, validation_message
from core.pagination import CustomPagination
from core.permissions import (AppStaffPermission,)
from core.response import SuccessResponse
from core import utils as core_utils
from gyms.models import GymDetails, GymLayout, LayoutSection, WallRoute, SectionWall, Event, Announcement, GradeType, \
    WallType, ColorType, RouteType, GhostWallRoute


class UpdateDeviceDetailViewSet(viewsets.ViewSet):
    """
        AddDeviceDetailViewSet used to update the user devices details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppStaffPermission,)
    action_serializer = {
        'retrieve': UserDeviceDetailSerializer,
        'perform_update': UserDeviceSerializer
    }

    def retrieve(self, request):
        """
            retrieve method used to get the device fcm details.
        :param request:
        :return:
        """
        fcm_user = FCMDevice.objects.select_related('user').filter(user=request.user, active=True)
        serializer = self.action_serializer.get(self.action)(fcm_user, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            update method used to update the device details.
        :param request:
        :return:
        """
        serializer = self.action_serializer.get(self.action)(data=request.data, instance=request.user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('DEVICE_SUCCESS_MESSAGE')},
                               status=status_code.HTTP_200_OK)

    def perform_destroy(self, request):
        """
            method used to delete the current user device token
        :param request:
        :return:
        """
        device_type = request.GET.get('device_type')
        # FCMDevice.objects.filter(user=request.user, type=device_type).update(active=False)
        FCMDevice.objects.filter(user=request.user, type=device_type).delete()
        return SuccessResponse({"message": success_message.get('DEVICE_DELETED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class StaffHomeGymCheckViewSet(viewsets.ViewSet):
    """
    StaffHomeGymCheckViewSet
        This class combines the logic of CRUD operations for gym staff home gym check. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    action_serializers = {
        'retrieve': StaffGymDetailSerializer
    }

    def retrieve(self, request):
        """
            retrieve method used to check staff gym.
        :param request:
        :return: response
        """
        staff_gym = request.user.user_details.home_gym
        if not staff_gym:
            data = {"id": None, "gym_name": None, "is_gym_staff": False}
            return SuccessResponse(data, status=status_code.HTTP_200_OK)
            # return Response(get_custom_error(message=validation_message.get('NOT_ASSOCIATED_TO_GYM'),
            #                                  error_location=validation_message.get('STAFF_WALL'), status=400),
            #                 status=status_code.HTTP_400_BAD_REQUEST)
        serializer = StaffGymDetailSerializer(staff_gym, context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


# class StaffHomeViewSet(viewsets.ViewSet):
#     """
#         StaffHomeViewSet class used to handle the Staff home layout detail.
#     """
#     authentication_classes = (CustomTokenAuthentication,)
#     permission_classes = (IsAuthenticated, AppStaffPermission,)
#
#     def retrieve(self, request, gym_id):
#         """
#             retrieve method used for the gym info.
#         :param request:
#         :param gym_id:
#         :return: response
#         """
#         floor_id = request.GET.get('floor_id', '')
#         category_id = request.GET.get('category_id', '')
#         category = int(category_id) if category_id else 0
#
#         gym_layout = GymLayout.objects.filter(gym=gym_id, category=category).all()
#         if gym_layout:
#             if floor_id:
#                 get_floor_id = floor_id
#             else:
#                 get_floor_id = gym_layout.first().id
#             # To show floor list only
#             floor_list = core_utils.get_is_selected_floor(gym_layout.values('id', 'title'), get_floor_id)
#             gym_layout_data = {'floor_list': floor_list}
#             floor_gym_layout = gym_layout.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall').\
#                 filter(id=get_floor_id).first()
#
#             # To get all section point only
#             only_layout_section = LayoutSection.objects.filter(gym_layout=floor_gym_layout)
#             only_layout_serialized_data = StaffOnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
#             gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})
#
#             # To get section + its wall details
#             serialized_data = StaffGymLayoutDetailSerializer(floor_gym_layout)
#             gym_layout_data.update(serialized_data.data)
#
#             # To get remaining wall slot
#             # wall_slot_left = core_utils.get_wall_slot_left(gym_id)
#             # gym_layout_data.update({'wall_slot_left': wall_slot_left})
#             return SuccessResponse({'gym_layout_data': gym_layout_data,
#                                     'category': category}, status=status_code.HTTP_200_OK)
#         gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": []}
#         # gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": [],
#         #                    'wall_slot_left': []}
#         return SuccessResponse({'gym_layout_data': gym_layout_data,
#                                 'category': category}, status=status_code.HTTP_200_OK)


# CR
class StaffHomeViewSet(viewsets.ViewSet):
    """
        StaffHomeViewSet class used to handle the Staff home layout detail.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppStaffPermission,)

    def retrieve(self, request, gym_id):
        """
            retrieve method used for the gym info.
        :param request:
        :param gym_id:
        :return: response
        """
        # Cr
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        r = gym_detail.RopeClimbing
        b = gym_detail.Bouldering
        if r and b:
            rb = [0, 1]
        elif r:
            rb = [0]
        else:
            rb = [1]
        gym_data = rb

        floor_id = request.GET.get('floor_id', '')
        category_id = request.GET.get('category_id', '')
        category = int(category_id) if category_id else rb[0]

        gym_layout = GymLayout.objects.filter(gym=gym_id, category=category).all()
        if gym_layout:
            if floor_id:
                get_floor_id = floor_id
            else:
                get_floor_id = gym_layout.first().id
            # To show floor list only
            floor_list = core_utils.get_is_selected_floor(gym_layout.values('id', 'title'), get_floor_id)
            gym_layout_data = {'floor_list': floor_list}
            floor_gym_layout = gym_layout.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
                filter(id=get_floor_id).first()

            # To get all section point only
            only_layout_section = LayoutSection.objects.filter(gym_layout=floor_gym_layout)
            only_layout_serialized_data = StaffOnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
            gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})

            # To get section + its wall details
            serialized_data = StaffGymLayoutDetailSerializer(floor_gym_layout)
            gym_layout_data.update(serialized_data.data)

            # To get remaining wall slot
            # wall_slot_left = core_utils.get_wall_slot_left(gym_id)
            # gym_layout_data.update({'wall_slot_left': wall_slot_left})
            return SuccessResponse({'gym_data': gym_data, 'gym_layout_data': gym_layout_data,
                                    'category': category}, status=status_code.HTTP_200_OK)
        gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": []}
        # gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": [],
        #                    'wall_slot_left': []}
        return SuccessResponse({'gym_data': gym_data, 'gym_layout_data': gym_layout_data,
                                'category': category}, status=status_code.HTTP_200_OK)


class StaffWallViewSet(viewsets.ViewSet):
    """
    StaffWallViewSet
        This class combines the logic of CRUD operations for gym staff walls. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    action_serializers = {
        'create': StaffWallSerializer,
        'perform_update': StaffWallSerializer,
        'retrieve': StaffWallDetailSerializer
    }
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for listing of Category based on Category and Floors based on Category
        and Sections based on Floors.
            :param request:
            :return: response
        """
        process = int(request.GET.get('process'))
        gym_id = request.GET.get('gym_id')

        if process == 1:
            gym_layout = GymLayout.objects.filter(gym=gym_id, gym_layout_section__isnull=False).distinct().\
                order_by('category').values('category', 'gym__RopeClimbing', 'gym__Bouldering',)
            proceed_data = core_utils.map_with_category(gym_layout)
            return SuccessResponse(proceed_data, status=status_code.HTTP_200_OK)
        elif process == 2:
            category = request.GET.get('category_type')
            floor_list = GymLayout.objects.filter(gym=gym_id, category=category, gym_layout_section__isnull=False).\
                distinct().order_by('id').\
                values('id', 'title')
            return SuccessResponse(floor_list, status=status_code.HTTP_200_OK)
        elif process == 3:
            floor_id = request.GET.get('floor_id')
            section_list = LayoutSection.objects.filter(gym_layout=floor_id).order_by('id').\
                extra(select={'title': 'name'}).values('id', 'title')
            return SuccessResponse(section_list, status=status_code.HTTP_200_OK)
        return Response(get_custom_error(message="Please provide valid process id.", error_location="staff wall",
                                         status=400), status=status_code.HTTP_400_BAD_REQUEST)

    def create(self, request):
        """
            post method used to add wall.
        :param request:
        :return: response
        """
        # To add subscription restrictions
        # requested_user = request.user.user_details.home_gym.user
        # bool_val, msg = core_utils.is_subscription_access_wall(requested_user)
        # if not bool_val:
        #     return Response(get_custom_error(message=msg, error_location='add staff member', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        # bool_val1, msg1 = core_utils.is_subscription_wall_number(requested_user)
        # if not bool_val1:
        #     return Response(get_custom_error(message=msg1, error_location='add staff member', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        #
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            update method used to update wall details.
        :param request:
        :return: response
        """
        wall_id = request.GET.get('wall_id')
        if not wall_id:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_WALL'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        section_wall_detail = SectionWall.objects.filter(id=wall_id).first()
        if not section_wall_detail:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location=validation_message.get('STAFF_WALL'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(section_wall_detail, data=request.data,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    # def retrieve(self, request, wall_id):
    #     """
    #     retrieve method used for wall details.
    #         :param request:
    #         :param wall_id:
    #         :return: response
    #     """
    #     wall_detail = SectionWall.objects.select_related('wall_type').filter(id=wall_id).first()
    #     if wall_detail:
    #         serializer = self.action_serializers.get(self.action)(wall_detail, context={'request': request.user})
    #         dict_data = dict()
    #         dict_data.update(serializer.data)
    #         # To show list of route tags
    #         route_tags = WallRoute.objects.select_related('grade', 'color').filter(section_wall=wall_detail)
    #
    #         pagination_class = self.pagination_class()
    #         page = pagination_class.paginate_queryset(route_tags, request)
    #         if page is not None:
    #             route_serializer = StaffOnlyRouteDetailSerializer(page, many=True)
    #             result_data = pagination_class.get_paginated_response(route_serializer.data).data
    #         else:
    #             route_serializer = StaffOnlyRouteDetailSerializer(route_tags, many=True)
    #             result_data = route_serializer.data
    #         dict_data.update({"route_data": result_data})
    #         return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)
    #     return SuccessResponse({}, status=status_code.HTTP_200_OK)

    # With wall and ghost wall route tag
    def retrieve(self, request, wall_id):
        """
        retrieve method used for wall details.
            :param request:
            :param wall_id:
            :return: response
        """
        wall_detail = SectionWall.objects.select_related('wall_type').filter(id=wall_id).first()
        if wall_detail:
            serializer = self.action_serializers.get(self.action)(wall_detail, context={'request': request.user})
            dict_data = dict()
            dict_data.update(serializer.data)
            # To show list of route tags
            route_tags = WallRoute.objects.select_related('grade', 'color').filter(section_wall=wall_detail)
            route_serializer = StaffOnlyRouteDetailSerializer(route_tags, many=True)
            result_data = route_serializer.data
            dict_data.update({"route_data": result_data})

            # To show list of ghost route tags
            ghost_route_tags = GhostWallRoute.objects.select_related('assigned_to', 'grade',).filter(section_wall=wall_detail)
            ghost_route_serializer = StaffOnlyGhostRouteDetailSerializer(ghost_route_tags, many=True)
            ghost_result_data = ghost_route_serializer.data
            dict_data.update({"ghost_route_data": ghost_result_data})
            return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def perform_delete(self, request):
        """
            delete method used to delete the wall.
        :param request:
        :return: response
        """
        wall_id = request.GET.get('wall_id')
        if not wall_id:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_WALL'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            SectionWall.objects.filter(id=wall_id).update(is_deleted=True)
            # To delete all routes related to this wall
            WallRoute.objects.filter(section_wall=wall_id).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get("WALL_DELETED_SUCCESSFULLY")},
                               status=status_code.HTTP_200_OK)


class OnlyStaffWallDetailViewSet(viewsets.ViewSet):
    """
    OnlyStaffWallDetailViewSet
        This class combines the logic of CRUD operations for gym staff walls. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    action_serializers = {
        'retrieve': OnlyStaffWallDetailSerializer
    }

    def retrieve(self, request, wall_id):
        """
        retrieve method used for only wall details, not route details.
            :param request:
            :param wall_id:
            :return: response
        """
        wall_detail = SectionWall.objects.select_related('gym_layout', 'layout_section', 'wall_type').\
            filter(id=wall_id).first()
        if wall_detail:
            serializer = self.action_serializers.get(self.action)(wall_detail, context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class StaffManualWallType(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Wall Type listing, add, update
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': StaffWallTypeSerializer,
        'update': StaffWallTypeSerializer,
        'list': StaffWallTypeSerializer,
    }

    def create(self, request):
        gym_id = request.GET.get('gym_id')
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_id': gym_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update wall type
        :param request:
        :return: response
        """
        wall_obj = WallType.objects.filter(id=request.data.get('id')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('INVALID_WALL_TYPE_ID'),
                                             error_location=validation_message.get('GYM_WALL_TYPE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=wall_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym wall type listing.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id')
        wall_type_obj = WallType.objects.filter(gym=gym_id).order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(wall_type_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(wall_type_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class StaffGhostWallViewSet(viewsets.ViewSet):
    """
    StaffGhostWallViewSet
        This class combines the logic of CRUD operations for gym staff ghost walls. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    action_serializers = {
        'update': StaffGhostWallSerializer,
        'list': StaffGhostWallDetailSerializer
    }
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for listing of Category based on Category and Floors based on Category
        and Sections based on Floors.
            :param request:
            :return: response
        """
        wall_id = request.GET.get('wall_id')
        wall_detail = SectionWall.objects.filter(id=wall_id).first()
        if wall_detail:
            serializer = self.action_serializers.get(self.action)(wall_detail, context={'request': request.user})
            dict_data = dict()
            dict_data.update(serializer.data)
            # To show list of ghost route tags
            route_tags = GhostWallRoute.objects.select_related('grade',).filter(section_wall=wall_detail)

            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(route_tags, request)
            if page is not None:
                route_serializer = StaffOnlyGhostRouteDetailSerializer(page, many=True)
                result_data = pagination_class.get_paginated_response(route_serializer.data).data
            else:
                route_serializer = StaffOnlyGhostRouteDetailSerializer(route_tags, many=True)
                result_data = route_serializer.data
            dict_data.update({"route_data": result_data})
            return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to add ghost wall.
        :param request:
        :return: response
        """
        wall_obj = SectionWall.objects.filter(id=request.data.get('wall_id')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=wall_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class ManualColorType(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Color Type listing, add, update
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': StaffColorTypeSerializer,
        'update': StaffColorTypeSerializer,
        'list': StaffColorTypeSerializer,
    }

    def create(self, request):
        gym_id = request.GET.get('gym_id')
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_id': gym_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update route color type
        :param request:
        :return: response
        """
        color_obj = ColorType.objects.filter(id=request.data.get('id')).first()
        if not color_obj:
            return Response(get_custom_error(message=validation_message.get('INVALID_COLOR_TYPE_ID'),
                                             error_location=validation_message.get('GYM_COLOR_TYPE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=color_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym route color type listing.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id')
        color_type_obj = ColorType.objects.filter(gym=gym_id).order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(color_type_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(color_type_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class ManualRouteType(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Route Type listing, add, update
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': StaffRouteTypeSerializer,
        'update': StaffRouteTypeSerializer,
        'list': StaffRouteTypeSerializer,
    }

    def create(self, request):
        gym_id = request.GET.get('gym_id')
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_id': gym_id})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update route type
        :param request:
        :return: response
        """
        route_obj = RouteType.objects.filter(id=request.data.get('id')).first()
        if not route_obj:
            return Response(get_custom_error(message=validation_message.get('INVALID_ROUTE_TYPE_ID'),
                                             error_location=validation_message.get('GYM_ROUTE_TYPE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=route_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym route type listing.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id')
        route_type_obj = RouteType.objects.filter(gym=gym_id).order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(route_type_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(route_type_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class StaffRouteViewSet(viewsets.ViewSet):
    """
    StaffRouteViewSet
        This class combines the logic of CRUD operations for gym staff routes. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    action_serializers = {
        'list': GradeTypeSerializer,
        'create': StaffRouteSerializer,
        'perform_update': StaffRouteSerializer,
        'retrieve': StaffRouteDetailSerializer
    }

    def list(self, request):
        """
        list method used for grade type listing.
            :param request:
            :return: response
        """
        section_wall = request.GET.get('wall_id')
        # We can use gym_id here as well instead of section wall id.
        section_instance = SectionWall.objects.filter(id=section_wall).first()
        if not section_instance:
            return Response(get_custom_error(message=validation_message.get('INVALID_WALL_ID'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        category = section_instance.gym_layout.category
        if category == GymLayout.ClimbingType.ROPE_CLIMBING:
            sub_category = request.user.user_details.home_gym.RopeClimbing
        else:
            sub_category = request.user.user_details.home_gym.Bouldering
        route_tag = GradeType.objects.filter(grading_system=category, sub_category=sub_category)
        if route_tag:
            serializer = self.action_serializers.get(self.action)(route_tag, many=True)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse([], status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add route.
        :param request:
        :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            update method used to update route details.
        :param request:
        :return: response
        """
        route_id = request.GET.get('route_id')
        if not route_id:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        wall_route_detail = WallRoute.objects.filter(id=route_id).first()
        if not wall_route_detail:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_NOT_FOUND'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(wall_route_detail, data=request.data,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, route_id):
        """
        retrieve method used for route details.
            :param request:
            :param route_id:
            :return: response
        """
        route_tag = WallRoute.objects.select_related('section_wall', 'grade', 'color',).filter(id=route_id).first()
        if route_tag:
            serializer = self.action_serializers.get(self.action)(route_tag, context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def perform_delete(self, request):
        """
            delete method used to delete the route.
        :param request:
        :return: response
        """
        route_id = request.GET.get('route_id')
        if not route_id:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        WallRoute.objects.filter(id=route_id).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get("ROUTE_DELETED_SUCCESSFULLY")},
                               status=status_code.HTTP_200_OK)


class StaffListingViewset(viewsets.ViewSet):
    """
    StaffListingViewset
        This class combines the logic of CRUD operations for gym staff listing. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for gym staff listing.
            :param request:
            :return: response
        """
        requested_user = request.user.user_details.home_gym.user
        users = User.objects.filter(user_role__name=Role.RoleType.GYM_STAFF, user_role__role_status=True,
                                    user_details__home_gym__user=requested_user).order_by('-email').\
            values('id', 'full_name', 'email')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(users, request)
        if page is not None:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(users, status=status_code.HTTP_200_OK)


class StaffGhostRouteViewSet(viewsets.ViewSet):
    """
    StaffGhostRouteViewSet
        This class combines the logic of CRUD operations for gym staff ghost routes. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)
    action_serializers = {
        'create': StaffGhostRouteSerializer,
        'perform_update': StaffGhostRouteSerializer,
        'retrieve': StaffGhostRouteDetailSerializer
    }

    def create(self, request):
        """
            post method used to add ghost route.
        :param request:
        :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            update method used to update ghost route details.
        :param request:
        :return: response
        """
        ghost_route_id = request.GET.get('ghost_route_id')
        if not ghost_route_id:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        wall_route_detail = GhostWallRoute.objects.filter(id=ghost_route_id).first()
        if not wall_route_detail:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_NOT_FOUND'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(wall_route_detail, data=request.data,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, ghost_route_id):
        """
        retrieve method used for ghost route details.
            :param request:
            :param ghost_route_id:
            :return: response
        """
        route_tag = GhostWallRoute.objects.select_related('section_wall', 'grade',).filter(id=ghost_route_id).first()
        if route_tag:
            serializer = self.action_serializers.get(self.action)(route_tag, context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class DeleteGymGhostRoute(viewsets.ViewSet):
    """
    DeleteGymGhostRoute
        This class combines the logic of CRUD operations for gym staff ghost routes. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppStaffPermission,)

    def update(self, request):
        """
            update method used to delete the ghost route.
        :param request:
        :return: response
        """
        ghost_route_ids = request.data.get('ghost_route_ids')
        section_wall = request.data.get('section_wall')
        if not ghost_route_ids:
            return Response(get_custom_error(message=validation_message.get('ROUTE_ID_REQUIRED'),
                                             error_location=validation_message.get('STAFF_ROUTE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        if ghost_route_ids and int(ghost_route_ids[0]) == 0:
            GhostWallRoute.all_objects.filter(section_wall=section_wall).update(is_deleted=True)
        else:
            GhostWallRoute.all_objects.filter(id__in=ghost_route_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get("ROUTE_DELETED_SUCCESSFULLY")},
                               status=status_code.HTTP_200_OK)


# Profile

class StaffDetailViewSet(viewsets.ViewSet):
    """
        StaffDetailViewSet to get the staff details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppStaffPermission,)
    serializer_class = StaffDetailSerializer

    def retrieve(self, request):
        """
        retrieve method used for the user details.
            :param request:
            :return: response
        """
        serializer = self.serializer_class(instance=request.user)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class PlanDetailViewSet(viewsets.ViewSet):
    """
        PlanDetailViewSet to get the staff details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppStaffPermission,)
    serializer_class = GymPlanSerializer

    def retrieve(self, request):
        """
        retrieve method used for the plan details.
            :param request:
            :return: response
        """
        gym_owner = User.all_objects.filter(id=request.user.user_details.home_gym.user.id).first()
        if gym_owner and gym_owner.user_subscription.plan:
            plan_detail = gym_owner.user_subscription
            serializer = self.serializer_class(instance=plan_detail)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({"is_active_subscription": False,
                               "message": "No active subscription of your home gym."},
                               status=status_code.HTTP_200_OK)

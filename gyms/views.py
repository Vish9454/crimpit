from datetime import date, datetime, timezone, timedelta
from itertools import chain

''' rest framework import '''
from django.contrib.gis.geos import GEOSGeometry
from rest_framework import status as status_code
from rest_framework import mixins, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend, FilterSet
from rest_framework import filters
from rest_framework.authtoken.models import Token

''' project level import '''
from accounts.models import User, Role, WallVisit, UserDetails, UserBiometricData, UserPreference, GymVisit
from accounts.serializers import GradeTypeSerializer
from gyms.models import GymDetails, GymLayout, LayoutSection, Event, SectionWall, WallRoute, GradeType, Announcement, \
    PreLoadedTemplate, GlobalSearch, OpenFeedback, WallType, ColorType, RouteType, GhostWallRoute
from core.exception import get_custom_error, CustomException
from core.messages import success_message, validation_message
from core.pagination import CustomPagination
from core.permissions import (AppClimberPermission, IsSubscribedAnnouncement, IsSubscribedUserProfile, )
from core.response import SuccessResponse
from core import utils as core_utils
from gyms.serializers import (GymOwnerSignUpSerializer, OwnerLogInSerializer, GymForgotPasswordSerializer,
                              GymResetPasswordSerializer, GymOwnerSignUpCompleteSerializer, GymOwnerListSerializer,
                              GymlayoutCreateSerializer, GymlayoutUpdateSerializer, GymlayoutRetrieveSerializer,
                              LayoutSectionSerializer, LayoutSectionRetrieveSerializer, GetGymOwnerProfileSerializer,
                              GymWallSerializer, GymWallRetrieveSerializer, GymEventSerializer, GymWallRouteSerializer,
                              GymWallRouteRetrieveSerializer, ListGymGradeTypeSerializer, GymAnnouncementSerializer,
                              PreLoadedTemplateSerializer, GymAnnouncementDetailSerializer, ChangePasswordSerializer,
                              GymWallRouteListSerializer, RouteTagListCommunityRGradeSerializer,
                              RouteTagListFeedbackListSerializer,
                              GymOwnerProfileUpdateSerializer, ListLayoutSerializer,
                              ListSectionSerializer, ListWallSerializer,
                              ListAllUsersSerializer, ListGymUsersSerializer, GymUserRouteFeedbackSerializer,
                              VerifyEmailSerializer, ResendEmailVerifyLinkSerializer,
                              ListSubscriptionSerializer, GlobalSearchKeywordSerializer, GymWallTypeSerializer,
                              GymColorTypeSerializer, GymRouteTypeSerializer, GymGhostWallSerializer,
                              GhostWallRouteSerializer, GhostWallRouteRetrieveSerializer, )
from accounts.models import UserRouteFeedback
from core.authentication import CustomTokenAuthentication
from core.permissions import IsGymOwner
from core.serializers import get_serialized_data
from django.db.models import Count, Avg, Max, FloatField, F, Q, ExpressionWrapper, IntegerField, Func
from django.db.models.functions import Greatest
from core.utils import (specific_route_details, route_progress_details, community_grade_route_details,
                        rating_range_output, validation_route_tag_list)
from admins.models import SubscriptionPlan

import logging
log = logging.getLogger(__name__)


class GymUserSignUp(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    GymUserSignUpViewSet
        This class combines the logic of CRUD operations for users. Only permitted gym owners can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    permission_classes = (AllowAny,)
    serializer_class = GymOwnerSignUpSerializer

    def create(self, request):
        """
                post method used for the signup.
            :param request:
            :return: response
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data,
                               status=status_code.HTTP_200_OK)


class GymUserSignUpComplete(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsGymOwner,)
    serializer_class = GymOwnerSignUpCompleteSerializer

    def update(self, request):
        user_id = request.data.get('user_id')
        gym_obj = GymDetails.objects.filter(user_id=user_id).first()
        serializer = self.serializer_class(
            instance=gym_obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('EMAIL_FOR_VERIFICATION_TO_ADMIN'),
                                }, status=status_code.HTTP_200_OK)


class GymOwnerLogIn(viewsets.ViewSet):
    """
        GymUserLogInViewSet class used to login the gym owner.
    """
    permission_classes = (AllowAny,)
    serializer_class = OwnerLogInSerializer

    def create(self, request):
        """
            post method used for the login authentication.
        :param request:
        :return:
        """
        user_obj = User.all_objects.filter(email=request.data.get('email').lower(),
                                           user_role__name__in=[Role.RoleType.GYM_OWNER, Role.RoleType.GYM_STAFF],
                                           user_role__role_status=True).first()
        if not user_obj:
            return Response(get_custom_error(message=validation_message.get('INVALID_CREDENTIAL'),
                                             error_location='gym', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        elif user_obj and not user_obj.is_active:
            return Response(get_custom_error(message=validation_message.get('ACCOUNT_DEACTIVATED'),
                                             error_location='gym', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)

        # user_obj = User.objects.filter(email=request.data.get('email').lower(),
        #                                user_role__name=Role.RoleType.GYM_OWNER, user_role__role_status=True).first()
        # if not user_obj:
        #     User.objects.filter(email=request.data.get('email').lower(),
        #                         user_role__name=Role.RoleType.GYM_STAFF, user_role__role_status=True).first()
        #     inactive_user = User.all_objects.filter(email=request.data.get('email').lower(),
        #                                             user_role__name=Role.RoleType.GYM_OWNER,
        #                                             user_role__role_status=True).first()
        #     if inactive_user and not inactive_user.is_active:
        #         return Response(get_custom_error(message=validation_message.get('ACCOUNT_DEACTIVATED'),
        #                                          error_location='gym', status=400),
        #                         status=status_code.HTTP_400_BAD_REQUEST)
        #     return Response(get_custom_error(message=validation_message.get('INVALID_CREDENTIAL'),
        #                                      error_location='gym', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        user_role_name = user_obj.user_role.first().name
        if user_role_name == Role.RoleType.GYM_OWNER:
            gym_obj = GymDetails.objects.filter(user_id=user_obj.id).first()
            if not gym_obj.is_profile_complete:
                data = {}
                data['id'] = user_obj.id
                data['token'] = core_utils.get_or_create_user_token(user_obj)
                data['is_profile_complete'] = user_obj.gym_detail_user.is_profile_complete
                data['gym_name'] = user_obj.gym_detail_user.gym_name
                data['user_role'] = Role.RoleType.GYM_OWNER
                return SuccessResponse(data, status=status_code.HTTP_200_OK)
            if not gym_obj.is_admin_approved:
                return Response(get_custom_error(message=validation_message.get('ADMIN_NOT_APPROVED'),
                                                 error_location='gym', status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.serializer_class(data=request.data, context={'user_role_name': user_role_name})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class GymForgotPasswordViewSet(viewsets.ViewSet):
    """
        GymForgotPasswordViewSet Class used to forgot password
    """
    permission_classes = (AllowAny,)
    serializer_class = GymForgotPasswordSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Remove during production
        forgot_password_url = serializer.validated_data.get("forgot_password_url")
        # Remove during production forgot_password_url key
        return SuccessResponse({"message": success_message.get('FORGOT_PASSWORD_LINK_SUCCESS_MESSAGE'),
                                "forgot_password_url": forgot_password_url}, status=status_code.HTTP_200_OK)


class GymResetPassword(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
        GymResetPasswordViewSet class used to change password on forgot password.
    """
    permission_classes = (AllowAny,)
    serializer_class = GymResetPasswordSerializer

    def create(self, request):
        """
            method used to call on Forgot Password.
        :param request:
        :return:
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        bool_val = serializer.save()
        if bool_val:
            return SuccessResponse({"message": success_message.get('PASSWORD_CHANGED'), "res_status": 1},
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse({"message": validation_message.get("FORGOT_PASS_LINK_ALREADY_VERIFIED"),
                                "res_status": 2},
                               status=status_code.HTTP_200_OK)


class GymOwnerList(mixins.ListModelMixin, viewsets.GenericViewSet):
    # list of the gym owners registered
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    list_serializer_class = GymOwnerListSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        page_size = request.GET.get('page_size', '')
        date = request.query_params.get('date')
        queryset = GymDetails.objects.filter(is_deleted=False).select_related('user').all()
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(queryset, request)
            if page is not None:
                serializer = self.list_serializer_class(page, many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.list_serializer_class(queryset, many=True)
        return SuccessResponse(serializer.data)


class GymlayoutView(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym layout create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymlayoutCreateSerializer,
        'update': GymlayoutUpdateSerializer,
        'retrieve': GymlayoutRetrieveSerializer,
        'list': GymlayoutRetrieveSerializer,
    }
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('title',)

    def create(self, request):
        gym_obj = GymDetails.objects.filter(id=request.data.get('gym')).first()
        if not gym_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location='layout', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
        put method used to update layout
        :param request:
        :return: response
        """
        layout_obj = GymLayout.objects.filter(id=request.data.get('id')).first()
        if not layout_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_LAYOUT_ID'),
                                             error_location='layout', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        if request.data.get('gym') or request.data.get('category'):
            return Response(get_custom_error(message=validation_message.get('CANNOT_UPDATE'),
                                             error_location='layout', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=layout_obj,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, layout_id):
        """
        retrieve method used to get gym layout
            :param request:
            :param layout_id:
            :return: response
        """
        layout_obj = GymLayout.all_objects.filter(id=layout_id).first()
        if layout_obj:
            serializer = self.action_serializers.get(self.action)(layout_obj,
                                                                  context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym layout list.
            :param request:
            :return: response
        """
        page_size = request.GET.get('page_size', '')
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user
        else:
            requested_user_gym = request.user.user_details.home_gym.user
        gym_obj = GymDetails.objects.filter(user=requested_user_gym).select_related('user').first()
        ##
        # token = request.META.get('HTTP_AUTHORIZATION')
        # word, token = token.split(" ")
        # token_obj = Token.objects.filter(key=token).first()
        # gym_ids = GymDetails.objects.filter(user_id=token_obj.user_id).all()
        gym_ids = GymDetails.objects.filter(user=requested_user_gym).all()
        category_val = request.query_params.get('category')
        if category_val == "0" or category_val == "1":
            layout_obj = GymLayout.all_objects.filter(gym_id__in=gym_ids, category=int(category_val)
                                                      ).all().select_related(
                'gym', 'gym__user'
            ).order_by('created_at')
            layout_obj = self.filter_queryset(layout_obj)
        else:
            return SuccessResponse({}, status=status_code.HTTP_200_OK)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(layout_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(layout_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class DeleteGymLayout(viewsets.ViewSet):
    """
        Gym layout soft delete
    """
    permission_classes = (IsGymOwner,)
    authentication_classes = (CustomTokenAuthentication,)

    def update(self, request):
        layout_ids = request.data.get('layout_ids')
        GymLayout.all_objects.filter(id__in=layout_ids).update(is_deleted=True)
        LayoutSection.all_objects.filter(gym_layout_id__in=layout_ids).update(is_deleted=True)
        wall_objs = SectionWall.objects.filter(gym_layout_id__in=layout_ids).values_list('id', flat=True)
        WallRoute.objects.filter(section_wall_id__in=wall_objs).update(is_deleted=True)
        SectionWall.all_objects.filter(gym_layout_id__in=layout_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DELETE_SUCCESS'),
                                }, status=status_code.HTTP_200_OK)


class GymLayoutSection(viewsets.ViewSet):
    """
        Gym layout create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': LayoutSectionSerializer,
        'update': LayoutSectionSerializer,
        'retrieve': LayoutSectionRetrieveSerializer,
        'list': LayoutSectionRetrieveSerializer,
    }

    def create(self, request):
        layout_obj = GymLayout.objects.filter(id=request.data.get('gym_layout')).first()
        if not layout_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_LAYOUT_ID'),
                                             error_location='section', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        serializer = get_serialized_data(
            obj=obj,
            serializer=LayoutSectionRetrieveSerializer,
            fields=request.query_params.get("fields"),
        )
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update layout
        :param request:
        :return: response
        """
        layout_section_obj = LayoutSection.objects.filter(id=request.data.get('id')).first()
        if not layout_section_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_LAYOUT_SECTION_ID'),
                                             error_location='section', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=layout_section_obj)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        serializer = get_serialized_data(
            obj=obj,
            serializer=LayoutSectionRetrieveSerializer,
            fields=request.query_params.get("fields"),
        )
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, section_id):
        """
        retrieve method used to get gym layout section
            :param request:
            :param section_id:
            :return: response
        """
        section_obj = LayoutSection.all_objects.filter(id=section_id).select_related('gym_layout',
                                                                                     'gym_layout__gym',
                                                                                     'gym_layout__gym__user').first()
        if section_obj:
            serializer = self.action_serializers.get(self.action)(section_obj)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym sections list for particular layout.
            :param request:
            :return: response
        """
        gym_layout_id = request.query_params.get('gym_layout_id')
        section_obj = LayoutSection.objects.filter(gym_layout_id=gym_layout_id).select_related('gym_layout',
                                                                                               'gym_layout__gym',
                                                                                               'gym_layout__gym__user'
                                                                                               ).all().order_by(
            '-created_at')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(section_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(section_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class DeleteGymSection(viewsets.ViewSet):
    """
        Gym layout soft delete
    """
    permission_classes = (IsGymOwner,)
    authentication_classes = (CustomTokenAuthentication,)

    def update(self, request):
        section_ids = request.data.get('section_ids')
        wall_objs = SectionWall.objects.filter(layout_section_id__in=section_ids).values_list('id', flat=True)
        WallRoute.objects.filter(section_wall_id__in=wall_objs).update(is_deleted=True)
        SectionWall.all_objects.filter(layout_section_id__in=section_ids).update(is_deleted=True)
        LayoutSection.all_objects.filter(id__in=section_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DELETE_SUCCESS'),
                                }, status=status_code.HTTP_200_OK)


class GetGymOwnerProfile(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    serializer_class = GetGymOwnerProfileSerializer

    def retrieve(self, request):
        # Add for gym staff
        requested_user = request.user
        role_name = request.user.user_role.first().name
        if role_name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user
        else:
            requested_user_gym = requested_user.user_details.home_gym.user
        gym_obj = GymDetails.objects.filter(user=requested_user_gym).select_related('user').first()

        if gym_obj:
            serializer = self.serializer_class(gym_obj, context={'role_name': role_name})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class GymWall(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Wall create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymWallSerializer,
        'update': GymWallSerializer,
        'retrieve': GymWallRetrieveSerializer,
        'list': GymWallRetrieveSerializer,
    }
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('name',)

    def create(self, request):
        section_obj = LayoutSection.objects.filter(id=request.data.get('layout_section')).first()
        if not section_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_SECTION_ID'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # To add subscription restrictions
        # requested_user = request.user
        # bool_val, msg = core_utils.is_subscription_access_wall(requested_user)
        # if not bool_val:
        #     return Response(get_custom_error(message=msg, error_location='add staff member', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        # bool_val1, msg1 = core_utils.is_subscription_wall_number(requested_user)
        # if not bool_val1:
        #     return Response(get_custom_error(message=msg1, error_location='add staff member', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        #
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request,
                                                                                          'section_obj': section_obj})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update wall
        :param request:
        :return: response
        """
        wall_obj = SectionWall.objects.filter(id=request.data.get('id')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=wall_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, wall_id):
        """
        retrieve method used to get gym wall
            :param request:
            :param wall_id:
            :return: response
        """
        wall_obj = SectionWall.all_objects.filter(id=wall_id).select_related('layout_section',
                                                                             'layout_section__gym_layout',
                                                                             'layout_section__gym_layout__gym',
                                                                             'layout_section__gym_layout__gym__user').first()
        if wall_obj:
            serializer = self.action_serializers.get(self.action)(wall_obj)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym sections list for particular layout.
            :param request:
            :return: response
        """
        gym_layout_id = request.query_params.get('gym_layout_id')
        wall_obj = SectionWall.objects.filter(gym_layout_id=gym_layout_id).\
            select_related('gym_layout', 'layout_section', 'layout_section__gym_layout', 'gym_layout__gym',
                           'layout_section__gym_layout__gym__user', 'gym_layout__gym__user', 'wall_type'
                           ).all().order_by('-created_at')
        wall_obj = self.filter_queryset(wall_obj)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(wall_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(wall_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class DeleteGymWall(viewsets.ViewSet):
    """
        delete wall soft delete
    """
    permission_classes = (IsGymOwner,)
    authentication_classes = (CustomTokenAuthentication,)

    def update(self, request):
        wall_ids = request.data.get('wall_ids')
        WallRoute.objects.filter(section_wall_id__in=wall_ids).update(is_deleted=True)
        SectionWall.all_objects.filter(id__in=wall_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DELETE_SUCCESS'),
                                }, status=status_code.HTTP_200_OK)


class GymGhostWall(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Ghost Wall create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'update': GymGhostWallSerializer,
    }

    def update(self, request):
        wall_obj = SectionWall.objects.filter(id=request.data.get('wall_id')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=wall_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)



class WallResetTimer(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Wall reset
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        """
            get method used to get wall reset timer detail
        :param request:
        :return: response
        """
        wall_id = request.GET.get('wall_id')
        wall_obj = SectionWall.objects.filter(id=wall_id).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        return SuccessResponse({"wall_id": wall_id, "reset_timer": wall_obj.reset_timer},
                               status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to create/update wall reset timer
        :param request:
        :return: response
        """
        wall_id = request.data.get('wall_id')
        reset_timer =  request.data.get('reset_timer')
        wall_obj = SectionWall.objects.filter(id=wall_id).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        wall_obj.reset_timer = reset_timer
        wall_obj.save()
        return SuccessResponse({"message": success_message.get("RESET_TIMER_ADDED")},
                               status=status_code.HTTP_200_OK)

    def destroy(self, request):
        wall_id = request.GET.get('wall_id')
        wall_obj = SectionWall.objects.filter(id=wall_id).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_NOT_FOUND'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        wall_obj.reset_timer = None
        wall_obj.save()
        return SuccessResponse({"message": success_message.get("RESET_TIMER_DELETED")},
                               status=status_code.HTTP_200_OK)


class ManualWallType(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Wall Type listing, add, update
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymWallTypeSerializer,
        'update': GymWallTypeSerializer,
        'list': GymWallTypeSerializer,
    }

    def create(self, request):
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_obj': gym_obj})
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
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        wall_type_obj = WallType.objects.filter(gym=gym_obj).order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(wall_type_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(wall_type_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class GymWallStats(viewsets.ViewSet):
    """
        Gym Wall Stats Retrieve
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)

    def retrieve(self, request, wall_id):
        """
        retrieve method used to get gym wall stats
            :param request:
            :param wall_id:
            :return: response
        """
        wall_detail = SectionWall.all_objects.filter(id=wall_id).first()
        if wall_detail:
            visit_instance = WallVisit.objects.filter(wall=wall_detail).first()
            count_data = core_utils.get_round_completed_data(wall_detail, visit_instance)
            return SuccessResponse(count_data, status=status_code.HTTP_200_OK)
        count_data = {'round_attempted': 0, 'round_completed': 0, 'wall_popularity': 0, 'wall_visit': 0}
        return SuccessResponse(count_data, status=status_code.HTTP_200_OK)


#  Announcements and Events


class PreLoadedTemplateViewSet(viewsets.ViewSet):
    """
    PreLoadedTemplateViewSet
        This class combines the logic of CRUD operations for pre-loaded template. Only permitted gym owners can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    # permission_classes = (IsGymOwner, IsSubscribedAnnouncement,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': PreLoadedTemplateSerializer,
        # 'create': GymEventSerializer,
    }

    def list(self, request):
        """
        list method used for pre-loaded template list.
            :param request:
            :return: response
        """
        templates = PreLoadedTemplate.objects.all().order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(templates, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(templates, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update announcement priority.
        :param request:
        :return: response
        """
        list_id = request.data.get('list_id')
        list_priority = request.data.get('list_priority')
        announcement_objs = Announcement.all_objects.filter(id__in=list_id).all()
        sorted_announcement = sorted(announcement_objs, key=lambda x: list_id.index(x.id))
        core_utils.update_announcement_priority(sorted_announcement, list_priority)
        return SuccessResponse({"message": success_message.get('PRIORITY_UPDATED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class GymAnnouncementViewSet(viewsets.ViewSet, viewsets.GenericViewSet):
    """
    GymAnnouncementViewSet
        This class combines the logic of CRUD operations for announcements. Only permitted gym owners can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    # permission_classes = (IsGymOwner, IsSubscribedAnnouncement,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': GymAnnouncementDetailSerializer,
        'create': GymAnnouncementSerializer,
        'update': GymAnnouncementSerializer,
        'retrieve': GymAnnouncementDetailSerializer,
    }
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('created_at__date',)

    def get_queryset(self, *args, **kwargs):
        query = Announcement.all_objects.all()
        return self.filter_queryset(query)

    # def list(self, request):
    #     """
    #     list method used for announcement list.
    #         :param request:
    #         :return: response
    #     """
    #     gym_id = request.GET.get('gym_id', '')
    #     filter_by = request.GET.get('filter_by', '')
    #     if not gym_id:
    #         return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
    #                                          error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
    #                         status=status_code.HTTP_400_BAD_REQUEST)
    #     bool_val, announcements_1, announcements_2, priority = core_utils.manage_announcement_list_filter(gym_id,
    #                                                                                                       filter_by)
    #     if not bool_val:
    #         return Response(get_custom_error(message="Please choose valid filter.",
    #                                          error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
    #                         status=status_code.HTTP_400_BAD_REQUEST)
    #     serialize_data_final = core_utils.serialize_all_data(self.action_serializers.get(self.action),
    #                                                          announcements_1, announcements_2, priority)
    #     return SuccessResponse(serialize_data_final, status=status_code.HTTP_200_OK)

    def list(self, request, *args, **kwargs):
        """
        list method used for announcement list.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        filter_by = request.GET.get('filter_by', '')
        queryset = self.get_queryset()
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        if not filter_by or int(filter_by) == 0:
            # announcements = Announcement.all_objects.filter(gym=gym_id).order_by('-is_active', '-priority')
            announcements = queryset.filter(gym=gym_id).order_by('-is_active', '-priority')
        # elif int(filter_by) == 1:
        #     today_date_time = datetime.now(timezone.utc)
        #     announcements = Announcement.all_objects.filter(gym=gym_id, created_at__lt=today_date_time).\
        #         order_by('-is_active', '-priority')
        elif int(filter_by) == 1:
            # announcements = Announcement.objects.filter(gym=gym_id).order_by('-priority')
            announcements = queryset.filter(gym=gym_id, is_active=True).order_by('-priority')
        elif int(filter_by) == 2:
            # announcements = Announcement.all_objects.filter(gym=gym_id, is_active=False).order_by('-priority')
            announcements = queryset.filter(gym=gym_id, is_active=False).order_by('-priority')
        else:
            return Response(get_custom_error(message="Please choose valid filter.",
                                             error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        priority = announcements.values_list('priority', flat=True)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(announcements, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            serialize_data = {"announcement_data": pagination_class.get_paginated_response(serializer.data).data,
                              "priority_data": priority}
            return SuccessResponse(serialize_data, status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(announcements, many=True)
        serialize_data = {"announcement_data": serializer.data, "priority_data": priority}
        return SuccessResponse(serialize_data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add announcement.
        :param request:
        :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request, announcement_id):
        """
            put method used to edit announcement.
        :param request:
        :param announcement_id:
        :return: response
        """
        announcement = Announcement.all_objects.filter(id=announcement_id).first()
        if not announcement:
            return Response(get_custom_error(message=validation_message.get('NO_ANNOUNCEMENT_FOUND'),
                                             error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(instance=announcement, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, announcement_id):
        """
        retrieve method used to get announcement detail by id.
            :param request:
            :param announcement_id:
            :return: response
        """
        announcement_detail = Announcement.all_objects.select_related('template').filter(id=announcement_id).first()
        if not announcement_detail:
            return Response(get_custom_error(message=validation_message.get('NO_ANNOUNCEMENT_FOUND'),
                                             error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(announcement_detail)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def destroy(self, request, announcement_id):
        """
        retrieve method used to delete/active/inactive announcement.
            :param request:
            :param announcement_id:
            :return: response
        """
        option_val = request.GET.get('option_value', '100')
        announcement_detail = Announcement.all_objects.filter(id=announcement_id)
        if not announcement_detail:
            return Response(get_custom_error(message=validation_message.get('NO_ANNOUNCEMENT_FOUND'),
                                             error_location=validation_message.get('GYM_ANNOUNCEMENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        message = core_utils.active_delete_announcement(announcement_detail, int(option_val))
        return SuccessResponse({"message": message}, status=status_code.HTTP_200_OK)


class GymEventViewSet(viewsets.ViewSet, viewsets.GenericViewSet):
    """
    GymEventViewSet
        This class combines the logic of CRUD operations for events. Only permitted gym owners can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    # permission_classes = (IsGymOwner, IsSubscribedAnnouncement,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': GymEventSerializer,
        'create': GymEventSerializer,
        'update': GymEventSerializer,
        'retrieve': GymEventSerializer,
    }
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ('title', 'description', 'start_date',)

    def list(self, request):
        """
        list method used for event list.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        filter_by = request.GET.get('filter_by', '')
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location=validation_message.get('GYM_EVENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        all_events = self.filter_queryset(Event.all_objects.all())
        if not filter_by or int(filter_by) == 0:
            # events = Event.all_objects.filter(gym=gym_id).order_by('-is_active', '-created_at')
            events = all_events.filter(gym=gym_id).order_by('-is_active', '-created_at')
        elif int(filter_by) == 1:
            today_date_time = datetime.now(timezone.utc)
            # events = Event.all_objects.filter(gym=gym_id, start_date__lt=today_date_time).order_by('-is_active',
            #                                                                                        '-created_at')
            events = all_events.filter(gym=gym_id, start_date__lt=today_date_time).order_by('-is_active',
                                                                                                   '-created_at')
        elif int(filter_by) == 2:
            today_date_time = datetime.now(timezone.utc)
            # events = Event.objects.filter(gym=gym_id, start_date__gte=today_date_time).order_by('-created_at')
            events = all_events.filter(gym=gym_id, is_active=True, start_date__gte=today_date_time).order_by('-created_at')
        elif int(filter_by) == 3:
            # events = Event.all_objects.filter(gym=gym_id, is_active=False).order_by('-created_at')
            events = all_events.filter(gym=gym_id, is_active=False).order_by('-created_at')
        else:
            return Response(get_custom_error(message="Please choose valid filter.",
                                             error_location=validation_message.get('GYM_EVENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(events, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(events, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add event.
        :param request:
        :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request, event_id):
        """
            put method used to edit event.
        :param request:
        :param event_id:
        :return: response
        """
        event = Event.all_objects.filter(id=event_id).first()
        if not event:
            return Response(get_custom_error(message=validation_message.get('NO_EVENT_FOUND'),
                                             error_location=validation_message.get('GYM_EVENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(instance=event, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, event_id):
        """
        retrieve method used to get event detail by id.
            :param request:
            :param event_id:
            :return: response
        """
        event_detail = Event.all_objects.filter(id=event_id).first()
        if not event_detail:
            return Response(get_custom_error(message=validation_message.get('NO_EVENT_FOUND'),
                                             error_location=validation_message.get('GYM_EVENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(event_detail)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def destroy(self, request, event_id):
        """
        retrieve method used to delete/active/inactive event.
            :param request:
            :param event_id:
            :return: response
        """
        option_val = request.GET.get('option_value', '100')
        event_detail = Event.all_objects.filter(id=event_id)
        if not event_detail:
            return Response(get_custom_error(message=validation_message.get('NO_EVENT_FOUND'),
                                             error_location=validation_message.get('GYM_EVENT'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        message = core_utils.active_delete_event(event_detail, int(option_val))
        return SuccessResponse({"message": message}, status=status_code.HTTP_200_OK)


class GymWallRoute(viewsets.ViewSet):
    """
        Gym Wall create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymWallRouteSerializer,
        'update': GymWallRouteSerializer,
        'retrieve': GymWallRouteRetrieveSerializer,
        'list': GymWallRouteListSerializer,
    }

    def create(self, request):
        wall_obj = SectionWall.objects.filter(id=request.data.get('section_wall')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_SECTION_ID'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update wall route
        :param request:
        :return: response
        """
        route_obj = WallRoute.objects.filter(id=request.data.get('id')).first()
        if not route_obj:
            return Response(get_custom_error(message=validation_message.get("ROUTE_ID_NOT_FOUND"),
                                             error_location='wallroute', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=route_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, route_id):
        """
        retrieve method used to get gym wall route
            :param request:
            :param route_id:
            :return: response
        """
        route_obj = WallRoute.all_objects.select_related('color', 'route_type').filter(id=route_id).first()
        if route_obj:
            serializer = self.action_serializers.get(self.action)(route_obj)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym wall route list for particular section.
            :param request:
            :return: response
        """
        section_id = request.query_params.get('section_id')
        route_obj = WallRoute.objects.filter(section_wall=section_id).select_related('section_wall',
                                                                                     'grade', 'color',
                                                                                     'route_type', 'created_by'
                                                                                     ).all().order_by(
            '-created_at')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(route_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(route_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class DeleteGymRoute(viewsets.ViewSet):
    """
        delete route soft delete
    """
    permission_classes = (IsGymOwner,)
    authentication_classes = (CustomTokenAuthentication,)

    def update(self, request):
        route_ids = request.data.get('route_ids')
        WallRoute.all_objects.filter(id__in=route_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DELETE_SUCCESS'),
                                }, status=status_code.HTTP_200_OK)


class GymStaffListing(viewsets.ViewSet):
    """
        Gym Staff Listing
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for gym staff listing.
            :param request:
            :return: response
        """
        # Add for gym staff
        user = request.user
        if user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user = user
        else:
            requested_user = user.user_details.home_gym.user
        ##
        users = User.objects.filter(user_role__name=Role.RoleType.GYM_STAFF, user_role__role_status=True,
                                    user_details__home_gym__user=requested_user).order_by('-email').\
            values('id', 'full_name', 'email')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(users, request)
        if page is not None:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(users, status=status_code.HTTP_200_OK)


class GymGhostWallRoute(viewsets.ViewSet):
    """
        Gym Ghost Wall Route create
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GhostWallRouteSerializer,
        'update': GhostWallRouteSerializer,
        'retrieve': GhostWallRouteRetrieveSerializer,
        'list': GhostWallRouteRetrieveSerializer,
    }

    def create(self, request):
        wall_obj = SectionWall.objects.filter(id=request.data.get('section_wall')).first()
        if not wall_obj:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_SECTION_ID'),
                                             error_location='wall', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            put method used to update wall route
        :param request:
        :return: response
        """
        route_obj = GhostWallRoute.objects.filter(id=request.data.get('id')).first()
        if not route_obj:
            return Response(get_custom_error(message=validation_message.get("ROUTE_ID_NOT_FOUND"),
                                             error_location='wallroute', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=route_obj)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, ghost_route_id):
        """
        retrieve method used to get gym ghost wall route
            :param request:
            :param ghost_route_id:
            :return: response
        """
        route_obj = GhostWallRoute.all_objects.select_related('assigned_to', 'created_by', 'grade'
                                                              ).filter(id=ghost_route_id).first()
        if route_obj:
            serializer = self.action_serializers.get(self.action)(route_obj)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def list(self, request):
        """
        list method used for gym ghost wall route list for particular section.
            :param request:
            :return: response
        """
        ghost_wall_id = request.query_params.get('ghost_wall_id')
        route_obj = GhostWallRoute.objects.filter(section_wall=ghost_wall_id).select_related('assigned_to', 'created_by',
                                                                                             'grade').all().order_by(
            '-created_at')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(route_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(route_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class DeleteGymGhostRoute(viewsets.ViewSet):
    """
        delete ghost route soft delete
    """
    permission_classes = (IsGymOwner,)
    authentication_classes = (CustomTokenAuthentication,)

    def update(self, request):
        ghost_route_ids = request.data.get('ghost_route_ids')
        section_wall = request.data.get('section_wall')
        if ghost_route_ids and int(ghost_route_ids[0]) == 0:
            GhostWallRoute.all_objects.filter(section_wall=section_wall).update(is_deleted=True)
        else:
            GhostWallRoute.all_objects.filter(id__in=ghost_route_ids).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DELETE_SUCCESS'),
                                }, status=status_code.HTTP_200_OK)


class ListGymGradeType(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    serializer_class = ListGymGradeTypeSerializer

    def list(self, request):
        """
        list method used for gym grade type
            :param request:
            :return: response
        """
        if not request.query_params.get('grading_system') or not request.query_params.get('sub_category'):
            grade_obj = GradeType.objects.filter().all().order_by('created_at')
        else:
            grade_obj = core_utils.grade_listing_conditions(request)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(grade_obj, request)
        if page is not None:
            serializer = self.serializer_class(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.serializer_class(grade_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class RouteTagList(viewsets.ViewSet, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    # search_fields = ("name", "section_wall__name", "section_wall__category", "section_wall__layout_section__name",
    #                  "avg_rating", "grade__sub_category_value", "route_type", "created_by__full_name")
    # search_fields = ("name", "grade__sub_category_value", "created_by__full_name",)
    search_fields = ("name",)

    def create(self, request):
        """
        create method used for RouteTagList in Gym Owner Panel
            :param request:
            :return: response
        """
        class Round(Func):
            function = 'ROUND'
            arity = 2
        # layout_ids = request.query_params.get('layout_ids')
        # section_ids = request.query_params.get('section_ids')
        # wall_ids = request.query_params.get('wall_ids')
        # category = request.query_params.get('category')
        # type_r_b = request.query_params.get('type')
        # grade = request.query_params.get('grade')
        # rating = request.query_params.get('rating')
        # created_by = request.query_params.get('created_by')
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user
        else:
            requested_user_gym = request.user.user_details.home_gym.user
        ##
        layout_ids = request.data.get('layout_ids')
        section_ids = request.data.get('section_ids')
        wall_ids = request.data.get('wall_ids')
        category = request.data.get('category')
        type_r_b = request.data.get('type')
        grade = request.data.get('grade')
        rating = request.data.get('rating')
        created_by = request.data.get('created_by')
        gym_owner = GymDetails.objects.filter(user=requested_user_gym).first()
        layout = GymLayout.objects.filter(gym_id=gym_owner.id).values_list('id', flat=True)
        section = SectionWall.objects.filter(gym_layout_id__in=layout).values_list('id', flat=True)
        queryset = WallRoute.all_objects.filter(section_wall_id__in=section)
        # for simplicity ,we are taking array for every request params except rating , rating will be in integer
        queryset = validation_route_tag_list(layout_ids, section_ids, wall_ids, category,
                                             type_r_b, grade, created_by, queryset)
        queryset = queryset.select_related('section_wall',
                                           "section_wall__layout_section",
                                           "section_wall__layout_section__gym_layout",
                                           "section_wall__layout_section__gym_layout__gym",
                                           "section_wall__layout_section__gym_layout__gym__user"
                                           ).prefetch_related('route_feedback'). \
            values('id', 'name',
                   "section_wall__id",
                   'section_wall__name',
                   "section_wall__layout_section__id",
                   "section_wall__layout_section__name",
                   "section_wall__layout_section__gym_layout__id",
                   "section_wall__layout_section__gym_layout__title",
                   "section_wall__layout_section__gym_layout__category",
                   "section_wall__layout_section__gym_layout__gym",
                   "section_wall__layout_section__gym_layout__gym__user",
                   "section_wall__wall_type__name",
                   "grade__sub_category",
                   'grade__sub_category_value',
                   'route_type__name',
                   "created_by__id",
                   'created_by__full_name',
                   'route_feedback__route'
                   ).annotate(
            submitted_count=Count('route_feedback'),
            avg_rating=Round(Avg('route_feedback__rating',
                                 filter=~Q(route_feedback__route_progress=UserRouteFeedback.RouteProgressType.PROJECTING)), 1),
            count_rating=Count('route_feedback__rating',
                               filter=~Q(route_feedback__route_progress=UserRouteFeedback.RouteProgressType.PROJECTING)),
            last_updated=Max('updated_at')).all(
        ).order_by('-last_updated')
        if rating:
            queryset = rating_range_output(rating, queryset)
        pagination_class = self.pagination_class()
        queryset = self.filter_queryset(queryset)
        page = pagination_class.paginate_queryset(queryset, request)
        if page is not None:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(queryset, status=status_code.HTTP_200_OK)


class ChangePassword(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    """View to update password"""
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)

    def update(self, request):
        """method for change password"""
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        response = {
            "message": success_message.get('PASSWORD_CHANGED'),
            "token": serializer.validated_data.get("token"),
        }
        return SuccessResponse(response, status=status_code.HTTP_200_OK)


class RouteTagListScreen2FeedbackList(viewsets.ViewSet, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    serializer_class = RouteTagListFeedbackListSerializer

    def list(self, request, route_id):
        """
        list method used for RouteTagListScreen2FeedbackList
            :param request:
            :return: response
        """
        feedbacks = UserRouteFeedback.objects.select_related('user', 'route', 'route__grade'). \
            filter(route_id=route_id).all().order_by('-updated_at')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(feedbacks, request)
        if page is not None:
            serializer = self.serializer_class(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.serializer_class(feedbacks, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class RouteTagListScreen2RouteDetail(viewsets.ViewSet, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)

    def retrieve(self, request, route_id):
        route_obj = WallRoute.all_objects.select_related(
            'section_wall', 'grade', 'color', 'created_by', 'created_by__gym_detail_user').\
            prefetch_related('route_feedback').filter(id=route_id)
        if not route_obj:
            return Response(get_custom_error(message=validation_message.get("ROUTE_ID_NOT_FOUND"),
                                             error_location='wallroute', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)

        # count_of_objects = UserRouteFeedback.objects.filter(route_id=route_id).count()
        count_of_objects = UserRouteFeedback.objects.filter(route_id=route_id)
        # count_of_objects = UserRouteFeedback.objects.filter(route_id=route_id).count()
        count_of_objects_with_grade = UserRouteFeedback.objects.filter(route_id=route_id, grade__isnull=False)
        # count_of_objects_with_grade = UserRouteFeedback.objects.filter(route_id=route_id, grade__isnull=False).count()
        # we will get the specific route details
        route_details_obj = specific_route_details(route_id, route_obj, )
        # Here we will get the route progress details
        projecting_level, users_count_rp = route_progress_details(route_id, route_obj,
                                                                  count_of_objects)
        # Here we will get the Community grade route details
        # grade_level, users_count_cgr, grade_value = community_grade_route_details(route_id, route_obj,
        #                                                                           count_of_objects)
        grade_level, users_count_cgr, grade_value = community_grade_route_details(route_id, route_obj,
                                                                                  count_of_objects_with_grade)
        return SuccessResponse({"route_details": route_details_obj,
                                "route_progress": {"users_count": users_count_rp,
                                                   "projecting_level": projecting_level,
                                                   },
                                "community_grade_route": {"users_count": users_count_cgr,
                                                          "grade_value": grade_value,
                                                          "grade_level": grade_level,
                                                          }
                                },
                               status=status_code.HTTP_200_OK)


class GymOwnerProfileUpdate(mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = (IsGymOwner,)
    serializer_class = GymOwnerProfileUpdateSerializer

    def update(self, request, gym_owner_id):
        gym_obj = GymDetails.objects.filter(id=gym_owner_id).first()
        serializer = self.serializer_class(
            instance=gym_obj, data=request.data, partial=True, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serialize_data = serializer.data
        # Remove during production
        serialize_data.update({'email_verification_token': serializer.validated_data.get('email_verification_token')})
        return SuccessResponse(serialize_data, status=status_code.HTTP_200_OK)


class ListRouteWallSectionLayout(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for List of Route -> Wall -> Section -> Layout
            :param request:
            :return: response
        """
        # layout_ids = request.query_params.get('layout_ids')
        # section_ids = request.query_params.get('section_ids')
        # wall_ids = request.query_params.get('wall_ids')
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user
        else:
            requested_user_gym = request.user.user_details.home_gym.user
        ##
        layout_ids = request.data.get('layout_ids')
        section_ids = request.data.get('section_ids')
        wall_ids = request.data.get('wall_ids')
        if layout_ids:
            queryset = GymLayout.objects.filter(id__in=layout_ids).prefetch_related('gym_layout_section',
                                                                   'gym_layout_section__section_wall',
                                                                   ).all()
            calling_serializer = ListLayoutSerializer
        if section_ids:
            queryset = LayoutSection.objects.filter(id__in=section_ids).prefetch_related('section_wall',
                                                                       ).all()
            calling_serializer = ListSectionSerializer
        if wall_ids:
            queryset = SectionWall.objects.filter(id__in=wall_ids).all()
            calling_serializer = ListWallSerializer
        if not layout_ids and not section_ids and not wall_ids:
            gym_owner = GymDetails.objects.filter(user=requested_user_gym).first()
            queryset = GymLayout.objects.filter(gym_id=gym_owner.id).prefetch_related('gym_layout_section',
                                                                                      'gym_layout_section__section_wall',
                                                                                      ).all()
            calling_serializer = ListLayoutSerializer
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(queryset, request)
        if page is not None:
            serializer = calling_serializer(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = calling_serializer(queryset, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class WallListBasedOnSection(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    list_serializer_class = GymWallRetrieveSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        page_size = request.GET.get('page_size', '')
        section_id = request.GET.get('section_id', '')
        queryset = SectionWall.all_objects.select_related('wall_type').filter(layout_section=section_id).all()
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(queryset, request)
            if page is not None:
                serializer = self.list_serializer_class(page, fields=('id', 'category', 'image', 'image_size', 'name', 'wall_type', 'wall_height',
                  'created_at', 'updated_at',), many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.list_serializer_class(queryset, fields=('id', 'category', 'image', 'image_size', 'name', 'wall_type', 'wall_height',
                'created_at', 'updated_at',), many=True)
        return SuccessResponse(serializer.data)


class ListAllUsers(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    list_serializer_class = ListAllUsersSerializer
    pagination_class = CustomPagination

    def list(self, request, *args, **kwargs):
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user
        else:
            requested_user_gym = request.user.user_details.home_gym.user
        ##
        page_size = request.GET.get('page_size', '')
        gym_detail = GymDetails.objects.filter(user=requested_user_gym).first()
        layout = GymLayout.objects.filter(gym_id=gym_detail.id).values_list('id', flat=True)
        section = SectionWall.objects.filter(gym_layout_id__in=layout).values_list('id', flat=True)
        route_created_by = WallRoute.all_objects.filter(section_wall_id__in=section).values_list('created_by',
                                                                                                 flat=True)

        queryset = User.objects.filter(id__in=route_created_by, is_deleted=False).prefetch_related('user_role').all()
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(queryset, request)
            if page is not None:
                serializer = self.list_serializer_class(page, many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.list_serializer_class(queryset, many=True)
        return SuccessResponse(serializer.data)


class ManualColorType(viewsets.ViewSet, viewsets.GenericViewSet):
    """
        Gym Color Type listing, add, update
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymColorTypeSerializer,
        'update': GymColorTypeSerializer,
        'list': GymColorTypeSerializer,
    }

    def create(self, request):
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_obj': gym_obj})
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
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        color_type_obj = ColorType.objects.filter(gym=gym_obj).order_by('id')
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
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination
    action_serializers = {
        'create': GymRouteTypeSerializer,
        'update': GymRouteTypeSerializer,
        'list': GymRouteTypeSerializer,
    }

    def create(self, request):
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'gym_obj': gym_obj})
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
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        gym_obj = requested_user_gym
        route_type_obj = RouteType.objects.filter(gym=gym_obj).order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(route_type_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(route_type_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class RouteGradeViewet(viewsets.ViewSet):
    """
    RouteGradeViewet
        This class combines the logic of CRUD operations for gym route grade. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    action_serializers = {
        'list': GradeTypeSerializer,
    }

    def list(self, request):
        """
        list method used for grade type listing.
            :param request:
            :return: response
        """
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
        else:
            requested_user_gym = request.user.user_details.home_gym
        ##
        section_wall = request.GET.get('wall_id')
        # We can use gym_id here as well instead of section wall id.
        layout_instance = GymLayout.objects.filter(gym_layout_wall=section_wall).first()
        if not layout_instance:
            return Response(get_custom_error(message=validation_message.get('INVALID_WALL_ID'),
                                             error_location=validation_message.get('GYM_ROUTE_GRADE'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        category = layout_instance.category
        if category == GymLayout.ClimbingType.ROPE_CLIMBING:
            sub_category = requested_user_gym.RopeClimbing
        else:
            sub_category = requested_user_gym.Bouldering
        route_tag = GradeType.objects.filter(grading_system=category, sub_category=sub_category)
        if route_tag:
            serializer = self.action_serializers.get(self.action)(route_tag, many=True)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse([], status=status_code.HTTP_200_OK)


#  Members
class ListGymUser1(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    list_serializer_class = ListGymUsersSerializer
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ['full_name', 'email']

    def get_queryset(self, *args, **kwargs):
        gym_detail_user = self.request.user.gym_detail_user
        query = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
            filter(user_details__home_gym=gym_detail_user)
        return self.filter_queryset(query), gym_detail_user

    def list(self, request, *args, **kwargs):
        ordering = request.GET.get('order_by', '')
        age_range = request.query_params.get('age_range')
        gender = request.query_params.get('gender')
        submitted_route = request.query_params.get('submitted_route')
        queryset, gym_detail_user = self.get_queryset()
        queryset = core_utils.filter_on_member_list(queryset, age_range, gender)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.list_serializer_class(page, many=True, context={'request': gym_detail_user})
            serializer_data = core_utils.compare_updated_at(serializer.data, ordering)
            filter_serializer_data = core_utils.filter_submitted_route(serializer_data, submitted_route)
            return SuccessResponse(pagination_class.get_paginated_response(filter_serializer_data).data)
        serializer = self.list_serializer_class(queryset, many=True, context={'request': gym_detail_user})
        serializer_data = core_utils.compare_updated_at(serializer.data)
        filter_serializer_data = core_utils.filter_submitted_route(serializer_data, submitted_route)
        return SuccessResponse(filter_serializer_data)


class TotalMemberCount(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)

    def list(self, request):
        """
        list method used for total users count grade type
            :param request:
            :return: response
        """
        # Add for gym staff
        requested_user = request.user
        if request.user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user_gym = requested_user.gym_detail_user
            requested_user_date = requested_user.created_at.date()
        else:
            requested_user_gym = request.user.user_details.home_gym
            requested_user_date = requested_user_gym.user.created_at.date()
        ##
        # Calculating increase or decrease count based on comparison between last week and this week
        today = date.today()
        last_week_date1 = today - timedelta(days=14)
        last_week_date2 = today - timedelta(days=7)
        # last_week_date = today - timedelta(days=7)
        users = User.objects.select_related('user_details').filter(
        # users = User.all_objects.select_related('user_details').filter(
            user_details__home_gym=requested_user_gym)
        user_count = users.count()
        # added to count last week data only if gym is created before last week
        if requested_user_date >= last_week_date2:
            last_week_user_count = 0
        else:
            # last_week_user_count = users.filter(user_details__home_gym_added_on__date__gte=last_week_date).count()
            last_week_user_count1 = users.filter(user_details__home_gym_added_on__date__gte=last_week_date1,
                                                 user_details__home_gym_added_on__date__lt=last_week_date2).count()
            last_week_user_count2 = users.filter(user_details__home_gym_added_on__date__gte=last_week_date2).count()
            last_week_user_count = last_week_user_count2 - last_week_user_count1
        return SuccessResponse({"total_user_count": user_count, "last_week_user_count": last_week_user_count},
                               status=status_code.HTTP_200_OK)


class ListGymUser(mixins.ListModelMixin, viewsets.GenericViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    list_serializer_class = ListGymUsersSerializer
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter)
    search_fields = ['full_name', 'email']

    def get_queryset(self, *args, **kwargs):
        # ordering = self.request.GET.get('order_by', '-last_updated')
        ordering = self.request.GET.get('order_by', '-user_details__home_gym_added_on')
        # Add for gym staff
        requested_user = self.request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_detail_user = requested_user.gym_detail_user
        else:
            gym_detail_user = requested_user.user_details.home_gym
        ##
        query = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
            prefetch_related('user_route_feedback', 'user_route_feedback__route'). \
            filter(user_details__home_gym=gym_detail_user).values(
            'id', 'full_name', 'email', 'user_details__user_avatar', 'user_biometric__birthday', 'user_biometric__gender',
            'user_preference__bouldering', 'user_preference__top_rope', 'user_preference__lead_climbing', ). \
            annotate(
            submitted=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                            user_route_feedback__route__is_deleted=False)),
            last_updated=Max('user_route_feedback__updated_at', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                         user_route_feedback__route__is_deleted=False))).all().order_by(ordering)
                     # last_updated=Greatest('updated_at', 'user_details__updated_at', 'user_biometric__updated_at',
                     #                       'user_preference__updated_at')).all().order_by(ordering)
        return self.filter_queryset(query), gym_detail_user

    def list(self, request, *args, **kwargs):
        climbing_level = request.query_params.get('climbing_level')
        age_range = request.query_params.get('age_range')
        gender = request.query_params.get('gender')
        search_submitted_route = request.query_params.get('search_submitted_route')
        queryset, gym_detail_user = self.get_queryset()
        queryset = core_utils.filter_on_member_list(queryset, climbing_level, age_range, gender,
                                                    search_submitted_route, gym_detail_user)
        queryset = core_utils.update_age_calculation(queryset)
        if age_range:
            a = int(age_range.split('-')[0])
            b = int(age_range.split('-')[1])
            queryset = [each for each in queryset if each['age'] and a <= each['age'] <= b]
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(queryset, request)
        if page is not None:
            page = core_utils.update_date_format(page)
            return SuccessResponse(pagination_class.get_paginated_response(page).data)
        queryset = core_utils.update_date_format(queryset)
        return SuccessResponse(queryset)

    def destroy(self, request, *args, **kwargs):
        user_id = request.GET.get('user_id')
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_detail_user = requested_user.gym_detail_user
        else:
            gym_detail_user = requested_user.user_details.home_gym
        ##
        gym_detail_user.blocked_user.add(user_id)
        user_instance = UserDetails.objects.filter(user=user_id)
        user_instance.update(home_gym=None)
        core_utils.delete_staff_role_for_user(user_instance.first().user)
        return SuccessResponse({'message': success_message.get('USER_BLOCKED_SUCCESSFULLY')})


class AddAsStaffMember(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)

    def update(self, request, user_id):
        choice_val = request.GET.get('action_key')
        user_obj = User.objects.filter(id=user_id).first()
        if not user_obj:
            return Response(get_custom_error(message=validation_message.get("USER_NOT_FOUND"),
                                             error_location='member', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # Add for gym staff
        # requested_user = request.user
        # if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
        #     gym_detail_user = requested_user
        # else:
        #     gym_detail_user = requested_user.user_details.home_gym.user
        ##
        if choice_val == 'ADD':
            # To add subscription restrictions
            # requested_user = request.user
            # bool_val, msg = core_utils.is_subscription_access_staff(requested_user)
            # if not bool_val:
            #     return Response(get_custom_error(message=msg, error_location='add staff member', status=400),
            #                     status=status_code.HTTP_400_BAD_REQUEST)
            # bool_val1, msg1 = core_utils.is_subscription_staff_number(requested_user)
            # if not bool_val1:
            #     return Response(get_custom_error(message=msg1, error_location='add staff member', status=400),
            #                     status=status_code.HTTP_400_BAD_REQUEST)
            #
            core_utils.create_user_staff_role(user_obj, Role.RoleType.GYM_STAFF)
            return SuccessResponse({"message": success_message.get('STAFF_MEMBER_ADDED_SUCCESSFULLY')},
                                   status=status_code.HTTP_200_OK)
        elif choice_val == 'REMOVE':
            if request.user.user_role.first().name != Role.RoleType.GYM_OWNER and user_obj == request.user:
                return Response(get_custom_error(message=validation_message.get("CAN_NOT_DELETE_HIMSELF"),
                                                 error_location='member', status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
            core_utils.delete_staff_role_for_user(user_obj)
            return SuccessResponse({"message": success_message.get('STAFF_MEMBER_REMOVED_SUCCESSFULLY')},
                                   status=status_code.HTTP_200_OK)
        else:
            return Response(get_custom_error(message=validation_message.get("INVALID_ACTION_KEY"),
                                             error_location='member', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)


class MemberProfile(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    action_serializers = {
        'list': GymUserRouteFeedbackSerializer,
    }
    pagination_class = CustomPagination

    def list(self, request):
        """
        user_id = request.GET.get('user_id')
        # To add subscription restrictions
        count, msg = core_utils.is_subscription_feedback(request.user)
        if count == -1:
            return Response(get_custom_error(message=msg, error_location='member_feedback', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        elif not count:
            user_route_feedback = UserRouteFeedback.objects.select_related(
                'route', 'route__section_wall', 'route__grade').filter(
                user__id=user_id, gym__user=request.user).order_by('-created_at')
        else:
            user_route_feedback = UserRouteFeedback.objects.select_related(
                'route', 'route__section_wall', 'route__grade').filter(
                user__id=user_id, gym__user=request.user).order_by('-created_at')[:int(count)]
        #
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(user_route_feedback, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(user_route_feedback, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        """

        # Without subscription restrictions
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_detail_user = requested_user
        else:
            gym_detail_user = requested_user.user_details.home_gym.user
        ##
        user_id = request.GET.get('user_id')
        user_route_feedback = UserRouteFeedback.objects.select_related(
            'route', 'route__section_wall', 'route__grade').filter(
            # user__id=user_id, gym__user=request.user).order_by('-created_at')
            user__id=user_id, gym__user=gym_detail_user, route__is_deleted=False).order_by('-created_at')
        # #
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(user_route_feedback, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(page, many=True,
                                                                  context={'request': request.user})
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(user_route_feedback, many=True,
                                                              context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, user_id):
        """
        # To add subscription restrictions
        bool_val, msg, queryset, process = core_utils.is_subscription_user_profile(request.user, user_id)
        if not bool_val:
            return Response(get_custom_error(message=msg, error_location='member_profile', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        #
        gym_detail_user = request.user.gym_detail_user
        queryset = queryset. \
            annotate(total_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user)),
                     projecting_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                            user_route_feedback__route_progress=0)),
                     red_point_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                           user_route_feedback__route_progress=1)),
                     flash_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                       user_route_feedback__route_progress=2)),
                     on_sight_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                          user_route_feedback__route_progress=3))
                     )
        if queryset:
            queryset = core_utils.update_age_calculation(queryset)
            if process == 1:
                queryset[0]['is_access_to_signup_info'] = True
                queryset[0]['is_access_to_biometric_data'] = True
            elif process == 2:
                queryset[0]['is_access_to_signup_info'] = False
                queryset[0]['is_access_to_biometric_data'] = True
            elif process == 3:
                queryset[0]['is_access_to_signup_info'] = True
                queryset[0]['is_access_to_biometric_data'] = False
            is_gym_staff = False
            if Role.objects.filter(user=user_id, name=Role.RoleType.GYM_STAFF, role_status=True):
                is_gym_staff = True
            queryset[0]['is_gym_staff'] = is_gym_staff
        return SuccessResponse(queryset, status=status_code.HTTP_200_OK)
        """
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_detail_user = requested_user.gym_detail_user
        else:
            gym_detail_user = requested_user.user_details.home_gym
        ##
        queryset = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
            prefetch_related('user_route_feedback', 'user_gym_visit').filter(id=user_id).values(
            'id', 'full_name', 'email', 'created_at', 'user_details__user_avatar',
            'user_biometric__gender', 'user_preference__prefer_climbing', 'user_preference__bouldering',
            'user_preference__top_rope', 'user_preference__lead_climbing', 'user_biometric__shoe_size',
            'user_biometric__weight', 'user_biometric__hand_size', 'user_biometric__height',
            'user_biometric__birthday', 'user_biometric__wingspan', 'user_biometric__ape_index'). \
            annotate(total_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user)),
                     projecting_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                            user_route_feedback__route_progress=0)),
                     red_point_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                           user_route_feedback__route_progress=1)),
                     flash_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                       user_route_feedback__route_progress=2)),
                     on_sight_count=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                          user_route_feedback__route_progress=3)),
                     route_attempted=Count('user_route_feedback', filter=Q(user_route_feedback__gym=gym_detail_user,
                                                                           user_route_feedback__route_progress=0)),
                     route_completed=F('total_count')-F('route_attempted'),
                     )
        if queryset:
            queryset = core_utils.update_age_calculation_on_single(queryset)
            is_gym_staff = False
            if Role.objects.filter(user=user_id, name=Role.RoleType.GYM_STAFF, role_status=True):
                is_gym_staff = True
            queryset[0]['is_gym_staff'] = is_gym_staff
            # Add gym visit this week, gym visit last week, route attempted, route completed
            gym_visit, gym_visit_last_week = core_utils.get_gym_visit(user_id, gym_detail_user)
            queryset[0]['gym_visit'] = gym_visit
            queryset[0]['gym_visit_last_week'] = gym_visit_last_week
        return SuccessResponse(queryset, status=status_code.HTTP_200_OK)


class MemberFeedbackOpen(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def retrieve(self, request, feedback_id):
        try:
            # Add for gym staff
            requested_user = request.user
            if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
                gym_detail_user = requested_user
            else:
                gym_detail_user = requested_user.user_details.home_gym.user
            ##
            # To add subscription restrictions
            count, msg, sub_start = core_utils.is_new_subscription_feedback(gym_detail_user)
            if count == -1:
                return Response(get_custom_error(message=msg, error_location='member_feedback', status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
            elif not count:
                pass
            else:
                open_feedback_count = OpenFeedback.objects.filter(gym_user=gym_detail_user, open_at__gte=sub_start).count()
                # print(open_feedback_count)
                # print(count)
                if open_feedback_count == int(count):
                    return Response(get_custom_error(message=validation_message.get("UPGRADE_YOUR_PLAN"), error_location='member_feedback', status=400),
                                    status=status_code.HTTP_400_BAD_REQUEST)

            OpenFeedback.objects.create(gym_user=gym_detail_user, feedback_id=feedback_id)
            message = "Success"
        except Exception as e:
            message = e
        return SuccessResponse({"message": message}, status=status_code.HTTP_200_OK)


class AllRouteFeedbackCount(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        # To get all route feedback count
        # Add for gym staff
        requested_user = request.user
        if requested_user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_detail_user = requested_user.gym_detail_user
        else:
            gym_detail_user = requested_user.user_details.home_gym
        ##
        feedbacks_count = UserRouteFeedback.objects.filter(gym=gym_detail_user)
        projecting_count = feedbacks_count.filter(route_progress=0).count()
        redpoint_count = feedbacks_count.filter(route_progress=1).count()
        flash_count = feedbacks_count.filter(route_progress=2).count()
        onsight_count = feedbacks_count.filter(route_progress=3).count()
        dict_data = {
            'projecting_count': projecting_count,
            'redpoint_count': redpoint_count,
            'flash_count': flash_count,
            'onsight_count': onsight_count
        }
        return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)


class VerifyEmailAddress(viewsets.ViewSet):
    """
        VerifyEmailAddress class used to verify user email.
    """
    permission_classes = (AllowAny,)
    serializer_class = VerifyEmailSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        bool_val = serializer.save()
        if bool_val:
            return SuccessResponse({"message": success_message.get('EMAIL_VERIFIED'), "res_status": 1},
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse({"message": validation_message.get("EMAIL_ALREADY_VERIFIED"), "res_status": 2},
                               status=status_code.HTTP_200_OK)


class ResendEmailVerifyLink(viewsets.ViewSet):
    """
        ResendEmailVerifyLink class used to resend email verification link.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    serializer_class = ResendEmailVerifyLinkSerializer

    def create(self, request):
        email = request.query_params.get('email')
        serializer = self.serializer_class(data=request.data, context={'request': request.user, 'email': email})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('RESEND_EMAIL_VERIFY_LINK')},
                               status=status_code.HTTP_200_OK)


class DashboardViewSet(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        # Add for gym staff
        if request.user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user = request.user
        else:
            requested_user = request.user.user_details.home_gym.user
        ##
        # gym_detail = request.user.gym_detail_user
        today = date.today()
        last_week_date1 = today - timedelta(days=14)
        last_week_date2 = today - timedelta(days=7)

        wall_count = core_utils.get_wall_count_for_dashboard(requested_user, last_week_date1, last_week_date2)
        route_attempt_count = core_utils.get_route_attempt_count_for_dashboard(requested_user)
        total_member_count = core_utils.get_total_member_count_for_dashboard(requested_user,
                                                                             last_week_date1, last_week_date2)
        total_wall_visit = core_utils.get_total_wall_visit_for_dashboard(requested_user, last_week_date1, last_week_date2)

        # added to count last week data only if gym is created before last week
        if request.user.created_at.date() >= last_week_date2:
            wall_count["las_week_wall_count"] = 0
            route_attempt_count["last_week_attempts_count"] = 0
            total_member_count["last_week_member_count"] = 0
            total_wall_visit["last_week_wall_vist"] = 0

        rope_bouldering_graph = core_utils.get_rope_bouldering_graph(requested_user)
        return SuccessResponse({"wall_count": wall_count, "route_attempt_count": route_attempt_count,
                                "total_member_count": total_member_count, "total_wall_visit": total_wall_visit,
                                "rope_bouldering_graph": rope_bouldering_graph},
                               status=status_code.HTTP_200_OK)


class Dashboard1ViewSet(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner,)
    pagination_class = CustomPagination

    def list(self, request):
        # Add for gym staff
        if request.user.user_role.first().name == Role.RoleType.GYM_OWNER:
            requested_user = request.user
            gym_detail = requested_user.gym_detail_user
        else:
            gym_detail = request.user.user_details.home_gym
            requested_user = gym_detail.user
        ##
        user_route_feedback = core_utils.get_dashboard_all_type_feedback_data(requested_user)
        route_type_count = core_utils.get_dashboard_all_route_type_data(requested_user)
        range_data = core_utils.get_dashboard_all_type_range_data(requested_user, gym_detail)

        # yds_climbing_level_range = UserPreference.objects.filter(
        #     user__is_deleted=False, rope_grading="YDS Scale").values('rope_grading', 'top_rope', 'lead_climbing'). \
        #     annotate(count=Count('id'))
        # francia_climbing_level_range = UserPreference.objects.filter(
        #     user__is_deleted=False, rope_grading="Francia").values('rope_grading', 'top_rope', 'lead_climbing'). \
        #     annotate(count=Count('id'))
        # v_system_climbing_level_range = UserPreference.objects.filter(
        #     user__is_deleted=False, bouldering_grading="V System").values('bouldering_grading', 'bouldering'). \
        #     annotate(count=Count('id'))
        # fontainebleau_climbing_level_range = UserPreference.objects.filter(
        #     user__is_deleted=False, bouldering_grading="Fontainebleau").values('bouldering_grading', 'bouldering'). \
        #     annotate(count=Count('id'))
        # climbing_level_range = {'yds': yds_climbing_level_range,
        #                         'francia': francia_climbing_level_range,
        #                         'v_system': v_system_climbing_level_range,
        #                         'fontainebleau': fontainebleau_climbing_level_range}
        # range_data = {'climbing_level_range': climbing_level_range,
        #               'height_range': height_range_updated, 'wingspan_range': wingspan_range_updated,
        #               }
        return SuccessResponse({"range_data": range_data, "user_route_feedback": user_route_feedback,
                                "route_type_count": route_type_count }, status=status_code.HTTP_200_OK)

        # return SuccessResponse({"range_data": range_data, "user_route_feedback": user_route_feedback,
        #                         "route_type_count": route_type_count}, status=status_code.HTTP_200_OK)


class PlansSubscriptionGymOwner(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner, )
    pagination_class = CustomPagination
    action_serializers = {
        'list': ListSubscriptionSerializer,
        'retrieve': ListSubscriptionSerializer,
    }

    def list(self, request):
        """
        list method used for subscription plan
            :param request:
            :return: response
        """
        sub_obj = SubscriptionPlan.objects.filter().all().order_by('created_at')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(sub_obj, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(sub_obj, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, subscription_plan_id):
        subscription_plan_obj = SubscriptionPlan.objects.filter(id=subscription_plan_id).first()
        if subscription_plan_obj:
            serializer = self.action_serializers.get(self.action)(subscription_plan_obj,
                                                                  context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class GlobalSearchKeyword(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner, )
    action_serializers = {
        'list': GlobalSearchKeywordSerializer,
    }
    pagination_class = CustomPagination

    def list(self, request):
        """
        list method used for global search keywords list
            :param request:
            :return: response
        """
        keywords = request.data.get('keywords')
        all_search_data = GlobalSearch.objects.all()
        # search_data = all_search_data.filter(Q(parent__icontains=keywords) | Q(child__icontains=keywords) |
        #                                      Q(sub_child__icontains=keywords)).all().values('parent').distinct()
        search_data1 = all_search_data.filter(parent__icontains=keywords).all().values('parent').distinct()
        search_data2 = all_search_data.filter(child__icontains=keywords).all().values('parent', 'child').distinct()
        search_data3 = all_search_data.filter(sub_child__icontains=keywords).all().values('parent', 'child',
                                                                                          'sub_child').distinct()
        search_data4 = all_search_data.filter(sub_child_1__icontains=keywords).all().values(
            'parent', 'child', 'sub_child', 'sub_child_1').distinct()
        final_data = list(chain(search_data1, search_data2, search_data3, search_data4))
        li = []
        for each in final_data:
            if each.get('sub_child_1'):
                li.append(each.get('parent') + " > " + each.get('child') + " > " + each.get('sub_child') + " > "
                          + each.get('sub_child_1'))
            elif each.get('sub_child'):
                li.append(each.get('parent') + " > " + each.get('child') + " > " + each.get('sub_child'))
            elif each.get('child'):
                li.append(each.get('parent') + " > " + each.get('child'))
            else:
                li.append(each.get('parent'))
        li.sort()
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(final_data, request)
        if page is not None:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        # return SuccessResponse(final_data, status=status_code.HTTP_200_OK)
        return SuccessResponse(li, status=status_code.HTTP_200_OK)


class OptionalClimbing(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner, )
    # action_serializers = {
    #     'list': OptionalClimbingSe,
    # }

    def list(self, request):
        """
        list method used for optional climbing list
            :param request:
            :return: response
        """
        # Add for gym staff
        user = request.user
        if user.user_role.first().name == Role.RoleType.GYM_OWNER:
            gym_data = user.gym_detail_user
        else:
            gym_data = user.user_details.home_gym
        ##
        # gym_data = request.user.gym_detail_user
        rope = gym_data.RopeClimbing
        boul = gym_data.Bouldering
        # if rope and boul:
        #     data = [{'RopeClimbing': rope}, {'Bouldering': boul}]
        # elif rope:
        #     data = [{'RopeClimbing': rope}, {'Bouldering': boul}]
        # elif boul:
        #     data = [{'RopeClimbing': rope}, {'Bouldering': boul}]
        data = [{'RopeClimbing': rope}, {'Bouldering': boul}]
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class CheckGymOwnerViewset(viewsets.ViewSet):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsGymOwner, )

    def list(self, request):
        """
        list method used to check login user is gym owner or not
            :param request:
            :return: response
        """
        if request.user.user_role.first().name == Role.RoleType.GYM_OWNER:
            is_gym_owner = True
        else:
            is_gym_owner = False
        return SuccessResponse({"is_gym_owner": is_gym_owner}, status=status_code.HTTP_200_OK)

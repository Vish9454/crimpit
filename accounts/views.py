from datetime import datetime, timezone

''' rest framework import '''
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import Avg, Count, Sum, Q, Value, CharField, OuterRef, Exists, Subquery
from rest_framework import status as status_code, filters
from rest_framework import mixins, views, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.authtoken.models import Token

''' project level import '''
from accounts.models import UserPreference, ListCategory, RouteSaveList, UserRouteFeedback, SavedEvent, \
    UserBiometricData, UserDetailPercentage, WallVisit, UserDetails, QuestionAnswer, Role, User
from accounts.serializers import (UserSignUpSerializer, VerifyEmailSerializer, ResendEmailVerifyLinkSerializer,
                                  LogInSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
                                  UserDetailUpdateSerializer, AddClimbingPreferenceSerializer,
                                  ClimbingPreferenceSerializer, MarkHomeGymSerializer,
                                  GetHomeGymSerializer, UnmarkHomeGymSerializer, ClimberHomeListSerializer,
                                  ClimberHomeDetailSerializer, ResendForgotPasswordLinkSerializer,
                                  ListCategorySerializer, RouteIntoCategorySerializer, RouteFeedbackSerializer,
                                  RouteFeedbackDetailSerializer, ClimberEventDetailSerializer,
                                  ClimberSaveEventSerializer, ClimberAnnounceDetailSerializer,
                                  SaveEventDetailSerializer, BiometricDataSerializer, BiometricDataDetailSerializer,
                                  PercentageDetailSerializer, GymLayoutDetailSerializer, LayoutSectionDetailSerializer,
                                  OnlyLayoutSectionDetailSerializer, WallRouteDetailSerializer,
                                  SectionWallDetailSerializer,
                                  OnlyWallRouteDetailSerializer, WallRouteWithCategoryInfoSerializer,
                                  NotFoundGymSerializer, ClimbingInfoSerializer, ClimbingInfoDetailSerializer,
                                  QuestionAnswerSerializer, )
from core.authentication import CustomTokenAuthentication
from core.exception import get_custom_error, CustomException
from core.messages import success_message, validation_message
from core.pagination import CustomPagination
from core.permissions import (CheckUserRoleStatusPermission,
                              UserEmailVerifiedPermission, AppClimberPermission)
from core.response import SuccessResponse
from core import utils as core_utils
from gyms.models import GymDetails, GymLayout, LayoutSection, WallRoute, SectionWall, Event, Announcement


def common_block_gym_fun(request_user, gym_detail):
    boo_val = core_utils.check_gym_is_blocked(request_user, gym_detail)
    if not boo_val:
        raise CustomException(status_code=301, message=validation_message.get('BLOCK_BY_GYM'),
                              location=validation_message.get('CLIMBER_HOME'),)
    return True


class UserSignUpViewSet(viewsets.ViewSet):
    """
    UserSignUpViewSet
        This class combines the logic of CRUD operations for users. Only permitted users can
        perform respective operations.

        Inherits: BaseUserViewSet
    """
    permission_classes = (AllowAny,)
    serializer_class = UserSignUpSerializer

    def create(self, request):
        """
                post method used for the signup.
            :param request:
            :return: response
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serialize_data = serializer.data
        # Remove during production
        serialize_data.update({'email_verification_token': serializer.validated_data.get('email_verification_token')})
        return SuccessResponse(serialize_data, status=status_code.HTTP_200_OK)


class VerifyEmailAddressViewSet(viewsets.ViewSet):
    """
        VerifyEmailAddress class used to verify user email.
    """
    permission_classes = (AllowAny,)
    serializer_class = VerifyEmailSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        bool_val = serializer.save()
        if bool_val:
            return SuccessResponse({"message": success_message.get('EMAIL_VERIFIED'), "res_status": 1},
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse({"message": validation_message.get("EMAIL_ALREADY_VERIFIED"), "res_status": 2},
                               status=status_code.HTTP_200_OK)



class ResendEmailVerifyLinkViewSet(viewsets.ViewSet):
    """
        ResendEmailVerifyLink class used to resend email verification link.
    """
    permission_classes = (IsAuthenticated,
                          CheckUserRoleStatusPermission,)
    serializer_class = ResendEmailVerifyLinkSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('RESEND_EMAIL_VERIFY_LINK')},
                               status=status_code.HTTP_200_OK)


class LogInViewSet(viewsets.ViewSet):
    """
        LogInViewSet class used to login the app user.
    """
    permission_classes = (AllowAny,)
    serializer_class = LogInSerializer

    def create(self, request):
        """
            post method used for the login authentication.
        :param request:
        :return:
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class ForgotPasswordViewSet(viewsets.ViewSet):
    """
        ForgotPasswordViewSet Class used to forgot password
    """
    permission_classes = (AllowAny,)
    serializer_class = ForgotPasswordSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Remove during production
        forgot_password_url = serializer.validated_data.get("forgot_password_url")
        # Remove during production forgot_password_url key
        return SuccessResponse({"message": success_message.get('FORGOT_PASSWORD_LINK_SUCCESS_MESSAGE'),
                                "forgot_password_url": forgot_password_url}, status=status_code.HTTP_200_OK)


class OldResetPasswordViewSet(viewsets.ViewSet):
    """
        ResetPasswordViewSet class used to change password on forgot password.
    """
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

    def create(self, request):
        """
            method used to call on Forgot Password.
        :param request:
        :return:
        """
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        bool_val, seq_id = serializer.validated_data
        if seq_id == 1:
            message = success_message.get('FORGOT_PASSWORD_LINK_VERIFIED')
        else:
            message = success_message.get('PASSWORD_CHANGED')
        return SuccessResponse({"message": message}, status=status_code.HTTP_200_OK)


class ResetPasswordViewSet(viewsets.ViewSet):
    """
        ResetPasswordViewSet class used to change password on forgot password.
    """
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

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


class ResendForgotPasswordLinkViewSet(viewsets.ViewSet):
    """
        ResendForgotPasswordLinkViewSet class used to resend forgot password link.
    """
    permission_classes = (AllowAny,)
    serializer_class = ResendForgotPasswordLinkSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('RESEND_FORGOT_PASSWORD_LINK')},
                               status=status_code.HTTP_200_OK)


# After login APIs

class ClimbingPreferenceViewSet(viewsets.ViewSet):
    """
        ClimbingPreferenceViewSet used to get and add the climbing preference.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    action_serializers = {
        'list': ClimbingPreferenceSerializer,
        'perform_update': AddClimbingPreferenceSerializer
    }

    def list(self, request):
        queryset = UserPreference.objects.filter(user=request.user).first()
        if not queryset:
            return Response(get_custom_error(message='No climbing preference exist for this user.',
                                             error_location='climbing preference', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(instance=queryset)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        user_preference, created = UserPreference.objects.get_or_create(user=request.user)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=user_preference)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class NotFoundGymViewSet(viewsets.ViewSet):
    """
        NotFoundGymViewSet class used to send not found gym info to admin.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppClimberPermission)
    serializer_class = NotFoundGymSerializer

    def create(self, request):
        """
            post method used to not-gym-found.
            :param request:
            :return: response
        """
        serializer = self.serializer_class(data=request.data, context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('GYM_DETAIL_SEND_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class UserDetailViewSet(viewsets.ViewSet):
    """
        UserDetailViewSet to get/update the climber details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppClimberPermission,)
    serializer_class = UserDetailUpdateSerializer

    def list(self, request):
        """
                post method used for the signup.
            :param request:
            :return: response
        """
        serializer = self.serializer_class(instance=request.user)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def perform_update(self, request):
        """
            method used to update the climber details.
        :param request:
        :return:
        """
        serializer = self.serializer_class(data=request.data, instance=request.user)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serialize_data = serializer.data
        # Remove during production
        serialize_data.update({'email_verification_token': serializer.validated_data.get('email_verification_token')})
        return SuccessResponse(serialize_data, status=status_code.HTTP_200_OK)


class UpdateUserImageViewSet(viewsets.ViewSet):
    """
        UpdateUserImageViewSet to update the climber profile image.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppClimberPermission,)

    def perform_update(self, request):
        """
            method used to update the climber profile image.
        :param request:
        :return:
        """
        user_detail_instance = request.user.user_details
        user_detail_instance.user_avatar = request.data.get('user_avatar', '')
        user_detail_instance.save()
        return SuccessResponse({'message': success_message.get('IMAGE_CHANGED_SUCCESSFULLY'),
                                'user_avatar': user_detail_instance.user_avatar}, status=status_code.HTTP_200_OK)


class MarkHomeGymViewSet(viewsets.ViewSet):
    """
        MarkHomeGymViewSet class used to add the gym as home-gym.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppClimberPermission)
    pagination_class = CustomPagination
    action_serializers = {
        'list': GetHomeGymSerializer,
        'create': MarkHomeGymSerializer
    }

    def list(self, request):
        """
            method used to get the home-gym list.
        :param request:
        :return:
        """
        page_size = request.GET.get('page_size', '')
        mark_gym = GymDetails.objects.filter(user_home_gym=request.user.user_details)
            # filter(user__is_active=True, user_home_gym=request.user.user_details)
        # For block gym
        if mark_gym:
            common_block_gym_fun(request.user, mark_gym.first())
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(mark_gym, request)
            if page is not None:
                serializer = self.action_serializers.get(self.action)(instance=mark_gym, many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.action_serializers.get(self.action)(instance=mark_gym, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to mark home-gym.
            :param request:
            :return: response
        """
        requested_user_detail = request.user.user_details
        # For block gym
        mark_gym = GymDetails.objects.filter(id=request.data.get('gym_id'))
        if mark_gym:
            common_block_gym_fun(request.user, mark_gym.first())
        serializer = self.action_serializers.get(self.action)(data=request.data,
                                                              context={'user_detail': requested_user_detail})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # If user change the home gym and he is also staff member for any gym, delete the staff role for that user.
        core_utils.delete_staff_role_for_user(request.user)
        return SuccessResponse({"message": success_message.get('HOME_GYM_MARKED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class UnMarkHomeGymViewSet(viewsets.ViewSet):
    """
        UnMarkHomeGymViewSet class used to unmark gym from home-gym.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,
                          AppClimberPermission)
    serializer_class = UnmarkHomeGymSerializer

    def perform_update(self, request):
        # For block gym
        mark_gym = GymDetails.objects.filter(id=request.data.get('gym_id'))
        if mark_gym:
            common_block_gym_fun(request.user, mark_gym.first())
        serializer = self.serializer_class(instance=request.user.user_details, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # If user change the home gym and he is also staff member for any gym, delete the staff role for that user.
        core_utils.delete_staff_role_for_user(request.user)
        return SuccessResponse({"message": success_message.get('HOME_GYM_UNMARKED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class ClimberHomeDecisionViewSet(viewsets.ViewSet):
    """
        ClimberHomeDecisionViewSet class used to check Climber has home gym or not.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)

    def list(self, request):
        """
            list method used to check user home gym.
        :param request:
        :return: response
        """
        has_home_gym = request.user.user_details.home_gym
        dict_data = dict()
        if has_home_gym:
            dict_data.update({'has_home_gym': True, 'gym_detail': {'id': has_home_gym.id, 'gym_name': has_home_gym.gym_name}})
        else:
            dict_data.update({'has_home_gym': False, 'gym_detail': {}})
        return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)


class OldClimberHomeViewSet(viewsets.ViewSet):
    """
        ClimberHomeViewSet class used to handle the Climber home api.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    list_serializer_class = ClimberHomeListSerializer
    detail_serializer_class = ClimberHomeDetailSerializer
    pagination_class = CustomPagination

    def list(self, request):
        """
                post method used for the gym list.
            :param request:
            :return: response
        """
        page_size = request.GET.get('page_size', '')
        zipcode = request.GET.get('zipcode', '')
        if not zipcode:
            return Response(get_custom_error(message='Please provide the zipcode.',
                                             error_location=validation_message.get('CLIMBER_HOME'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        gyms = GymDetails.objects.select_related('user', 'user__user_details').filter(
            user__is_active=True, zipcode=zipcode, is_admin_approved=True).order_by("user_home_gym")
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(gyms, request)
            if page is not None:
                serializer = self.list_serializer_class(page, many=True,
                                                        context={'home_gym_v': request.user.user_details.home_gym})
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.list_serializer_class(gyms, many=True,
                                                context={'home_gym_v': request.user.user_details.home_gym})
        return SuccessResponse(serializer.data)

    def retrieve(self, request, gym_id):
        """
                post method used for the gym info.
            :param request:
            :param gym_id:
            :return: response
        """
        floor_id = request.GET.get('floor_id', '')
        category_id = request.GET.get('category_id', '')
        gym_detail = GymDetails.objects.select_related('user', 'user__user_details', 'user__user_preference').\
            filter(id=gym_id, user__is_active=True, is_admin_approved=True).first()
        if not gym_detail:
            return Response(get_custom_error(message='Gym details is not found.',
                                             error_location=validation_message.get('CLIMBER_HOME'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        user_preference = getattr(request.user, 'user_preference', None)
        if user_preference:
            user_preference_val = user_preference.prefer_climbing
            category = user_preference_val if user_preference_val in [0, 1] else 0
        else:
            user_preference_val = None
            category = 0
        if category_id:
            category = int(category_id)
        user_data = {'user_preference': user_preference_val}

        serializer = self.detail_serializer_class(gym_detail,
                                                  context={'home_gym_v': request.user.user_details.home_gym})

        gym_layout = GymLayout.objects.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
            filter(gym=gym_id, category=category).all()
        if gym_layout:
            if floor_id:
                get_floor_id = floor_id
            else:
                get_floor_id = gym_layout.first().id
            # To show floor list only
            floor_list = core_utils.get_is_selected_floor(gym_layout.values('id', 'title'), get_floor_id)
            gym_layout_data = {'floor_list': floor_list}
            floor_gym_layout = gym_layout.filter(id=get_floor_id).first()

            # To get all section point only
            only_layout_section = LayoutSection.objects.filter(gym_layout=floor_gym_layout)
            only_layout_serialized_data = OnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
            gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})

            # To get section + its wall details
            serialized_data = GymLayoutDetailSerializer(floor_gym_layout)
            gym_layout_data.update(serialized_data.data)
            return SuccessResponse({'user_data': user_data, 'gym_data': serializer.data,
                                    'gym_layout_data': gym_layout_data, 'category': category}, status=status_code.HTTP_200_OK)
        gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": []}
        return SuccessResponse({'user_data': user_data, 'gym_data': serializer.data,
                                'gym_layout_data': gym_layout_data, 'category': category}, status=status_code.HTTP_200_OK)


class ClimberHomeViewSet(viewsets.ViewSet):
    """
        ClimberHomeViewSet class used to handle the Climber home api.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    list_serializer_class = ClimberHomeListSerializer
    detail_serializer_class = ClimberHomeDetailSerializer
    pagination_class = CustomPagination

    def list(self, request):
        """
                post method used for the gym list.
            :param request:
            :return: response
        """
        page_size = request.GET.get('page_size', '')
        zipcode = request.GET.get('zipcode', '')
        if not zipcode:
            return Response(get_custom_error(message='Please provide the zipcode or gym name.',
                                             error_location=validation_message.get('CLIMBER_HOME'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        gyms = GymDetails.objects.filter(
            (Q(zipcode=zipcode) | Q(gym_name__icontains=zipcode)), user__is_active=True,
            is_admin_approved=True).order_by("-id")
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(gyms, request)
            if page is not None:
                serializer = self.list_serializer_class(page, many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = self.list_serializer_class(gyms, many=True)
        return SuccessResponse(serializer.data)

    def retrieve(self, request, gym_id):
        """
                post method used for the gym info.
            :param request:
            :param gym_id:
            :return: response
        """
        gym_detail = GymDetails.objects.filter(id=gym_id, user__is_active=True, is_admin_approved=True).first()
        if not gym_detail:
            return Response(get_custom_error(message='Gym details not found.',
                                             error_location=validation_message.get('CLIMBER_HOME'), status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # For block gym
        common_block_gym_fun(request.user, gym_detail)
        serializer = self.detail_serializer_class(gym_detail,
                                                  context={'home_gym_v': request.user.user_details.home_gym})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


# class ClimberHomeMoreViewSet(viewsets.ViewSet):
#     """
#         ClimberHomeMoreViewSet class used to handle the Climber home layout detail.
#     """
#     authentication_classes = (CustomTokenAuthentication,)
#     permission_classes = (IsAuthenticated, AppClimberPermission,)
#     detail_serializer_class = ClimberHomeDetailSerializer
#
#     def retrieve(self, request, gym_id):
#         """
#             retrieve method used for the gym info.
#         :param request:
#         :param gym_id:
#         :return: response
#         """
#         # For block gym
#         gym_detail = GymDetails.objects.filter(id=gym_id).first()
#         if gym_detail:
#             common_block_gym_fun(request.user, gym_detail)
#         floor_id = request.GET.get('floor_id', '')
#         category_id = request.GET.get('category_id', '')
#         user_preference = getattr(request.user, 'user_preference', None)
#         if user_preference:
#             user_preference_val = user_preference.prefer_climbing
#             category = user_preference_val if user_preference_val in [0, 1] else 0
#         else:
#             user_preference_val = None
#             category = 0
#         if category_id:
#             category = int(category_id)
#         user_data = {'user_preference': user_preference_val}
#
#         gym_layout = GymLayout.objects.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
#             filter(gym=gym_id, category=category).all()
#
#         ''' If only gym_layout required having atleast one wall in any section '''
#         '''
#         gym_layout = GymLayout.objects.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
#             filter(gym=gym_id, category=category, gym_layout_section__section_wall__isnull=False,
#                    gym_layout_section__section_wall__is_active=True,
#                    gym_layout_section__section_wall__is_deleted=False).all().distinct()
#         '''
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
#             only_layout_serialized_data = OnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
#             gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})
#
#             ''' If only section required having atleast one wall '''
#             '''
#             only_layout_section = LayoutSection.objects.filter(gym_layout=floor_gym_layout,
#                                                                section_wall__isnull=False, section_wall__is_active=True, section_wall__is_deleted=False).distinct()
#             only_layout_serialized_data = OnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
#             gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})
#             '''
#
#             # To get section + its wall details
#             serialized_data = GymLayoutDetailSerializer(floor_gym_layout)
#             gym_layout_data.update(serialized_data.data)
#             return SuccessResponse({'user_data': user_data, 'gym_layout_data': gym_layout_data,
#                                     'category': category}, status=status_code.HTTP_200_OK)
#         gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": []}
#         return SuccessResponse({'user_data': user_data, 'gym_layout_data': gym_layout_data,
#                                 'category': category}, status=status_code.HTTP_200_OK)


# CR
class ClimberHomeMoreViewSet(viewsets.ViewSet):
    """
        ClimberHomeMoreViewSet class used to handle the Climber home layout detail.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    detail_serializer_class = ClimberHomeDetailSerializer

    def retrieve(self, request, gym_id):
        """
            retrieve method used for the gym info.
        :param request:
        :param gym_id:
        :return: response
        """
        # For block gym
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        if gym_detail:
            common_block_gym_fun(request.user, gym_detail)

        # Cr
        r = gym_detail.RopeClimbing
        b = gym_detail.Bouldering
        if r and b:
            rb = [0, 1]
        elif r:
            rb = [0]
        else:
            rb = [1]

        floor_id = request.GET.get('floor_id', '')
        category_id = request.GET.get('category_id', '')
        user_preference = getattr(request.user, 'user_preference', None)
        if user_preference:
            user_preference_val = user_preference.prefer_climbing
            category = user_preference_val if user_preference_val in rb else rb[0]
        else:
            user_preference_val = None
            category = rb[0]
        if category_id:
            category = int(category_id)
        user_data = {'user_preference': user_preference_val, 'gym_preference': rb}

        gym_layout = GymLayout.objects.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
            filter(gym=gym_id, category=category).all()

        ''' If only gym_layout required having atleast one wall in any section '''
        '''
        gym_layout = GymLayout.objects.prefetch_related('gym_layout_section', 'gym_layout_section__section_wall'). \
            filter(gym=gym_id, category=category, gym_layout_section__section_wall__isnull=False, 
                   gym_layout_section__section_wall__is_active=True, 
                   gym_layout_section__section_wall__is_deleted=False).all().distinct()
        '''
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
            only_layout_serialized_data = OnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
            gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})

            ''' If only section required having atleast one wall '''
            '''
            only_layout_section = LayoutSection.objects.filter(gym_layout=floor_gym_layout,
                                                               section_wall__isnull=False, section_wall__is_active=True, section_wall__is_deleted=False).distinct()
            only_layout_serialized_data = OnlyLayoutSectionDetailSerializer(only_layout_section, many=True)
            gym_layout_data.update({'only_layout_section': only_layout_serialized_data.data})
            '''

            # To get section + its wall details
            serialized_data = GymLayoutDetailSerializer(floor_gym_layout)
            gym_layout_data.update(serialized_data.data)
            return SuccessResponse({'user_data': user_data, 'gym_layout_data': gym_layout_data,
                                    'category': category}, status=status_code.HTTP_200_OK)
        gym_layout_data = {'floor_list': [], "only_layout_section": [], "gym_layout_section": []}
        return SuccessResponse({'user_data': user_data, 'gym_layout_data': gym_layout_data,
                                'category': category}, status=status_code.HTTP_200_OK)


class ClimberHomeSectionViewSet(viewsets.ViewSet):
    """
        ClimberHomeSectionViewSet class used to handle the gym layout SECTION.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    list_serializer_class = SectionWallDetailSerializer

    def list(self, request):
        """
        list method used for wall routes.
            :param request:
            :return: response
        """
        # Currently not using, it can be used to get data of wall on click section on home page

        # section_id = request.GET.get('section_id', '')
        # if not section_id:
        #     return Response(get_custom_error(message='Please provide the section id.',
        #                                      error_location='wall route', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        # wall_detail = SectionWall.objects.filter(layout_section=section_id).first()
        # serializer = self.list_serializer_class(wall_detail)
        # return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({'a': "Success"})


class WallRouteViewSet(viewsets.ViewSet):
    """
        WallRouteViewSet class used to handle the wall route tags.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    list_serializer_class = SectionWallDetailSerializer
    detail_serializer_class = OnlyWallRouteDetailSerializer

    def list(self, request):
        """
        list method used for wall routes.
            :param request:
            :return: response
        """
        wall_id = request.GET.get('wall_id', '')
        if not wall_id:
            return Response(get_custom_error(message=validation_message.get('WALL_ID_REQUIRED'),
                                             error_location='wall route', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        wall_detail = SectionWall.objects.filter(id=wall_id).first()
        if wall_detail:
            # For block gym
            common_block_gym_fun(request.user, wall_detail.gym_layout.gym)
            serializer = self.list_serializer_class(wall_detail, context={'request': request.user,
                                                                          'section_wall': wall_detail})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)

    # def list(self, request):
    #     """
    #     list method used for wall routes.
    #         :param request:
    #         :return: response
    #     """
    #     wall_id = request.GET.get('wall_id', '')
    #     if not wall_id:
    #         return Response(get_custom_error(message=validation_message.get('WALL_ID_REQUIRED'),
    #                                          error_location='wall route', status=400),
    #                         status=status_code.HTTP_400_BAD_REQUEST)
    #     wall_detail = SectionWall.objects.prefetch_related('section_wall_route').filter(id=wall_id).first()
    #     if wall_detail:
    #         serializer = self.list_serializer_class(wall_detail, context={'request': request.user})
    #         dict_data = dict()
    #         dict_data.update(serializer.data)
    #         # To show list of route tags
    #         route_tags = WallRoute.objects.prefetch_related('route_save_list', 'route_save_list__list_category'). \
    #             filter(section_wall=wall_detail)
    #
    #         pagination_class = self.pagination_class()
    #         page = pagination_class.paginate_queryset(route_tags, request)
    #         if page is not None:
    #             route_serializer = WallRouteWithCategoryInfoSerializer(page, many=True,
    #                                                                    context={'request': request.user})
    #             result_data = pagination_class.get_paginated_response(route_serializer.data).data
    #         else:
    #             route_serializer = WallRouteWithCategoryInfoSerializer(route_tags, many=True,
    #                                                                    context={'request': request.user})
    #             result_data = route_serializer.data
    #         dict_data.update({"route_data": result_data})
    #         return SuccessResponse(dict_data, status=status_code.HTTP_200_OK)
    #     return SuccessResponse({}, status=status_code.HTTP_200_OK)

    def retrieve(self, request, route_id):
        """
                get method used for the route info.
            :param request:
            :param route_id:
            :return: response
        """
        route_tag = WallRoute.objects.select_related('section_wall', 'grade', 'color', 'route_type',).filter(id=route_id).first()
        if route_tag:
            # For block gym
            common_block_gym_fun(request.user, route_tag.section_wall.gym_layout.gym)
            serializer = self.detail_serializer_class(route_tag, context={'user': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        # return SuccessResponse({}, status=status_code.HTTP_200_OK)
        return Response(get_custom_error(message=validation_message.get('ROUTE_IS_DELETED'),
                                         error_location='wall_route', status=400),
                        status=status_code.HTTP_400_BAD_REQUEST)


class WallRouteFeedbackViewSet(viewsets.ViewSet):
    """
        WallRouteFeedbackViewSet class used to handle the wall route progress feedback.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    detail_serializer_class = OnlyWallRouteDetailSerializer
    pagination_class = CustomPagination

    def retrieve(self, request, route_id):
        """
            get method used for the route progress feedback info.
        :param request:
        :param route_id:
        :return: response
        """
        page_size = request.GET.get('page_size', '')
        # For block gym
        route_tag = WallRoute.objects.filter(id=route_id).first()
        if route_tag:
            common_block_gym_fun(request.user, route_tag.section_wall.gym_layout.gym)
        else:
            return Response(get_custom_error(message=validation_message.get('ROUTE_IS_DELETED'),
                                             error_location='wall_route', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        route_feedback = UserRouteFeedback.objects.filter(user=request.user, route=route_id).all().\
            order_by('-created_at')
        projecting_update = route_feedback.filter(route_progress=UserRouteFeedback.RouteProgressType.PROJECTING
                                                  ).update(first_time_read=True, second_time_read=True)
        second_read = route_feedback.filter(first_time_read=True, second_time_read=False).update(second_time_read=True)
        first_read = route_feedback.filter(first_time_read=False, second_time_read=False).update(first_time_read=True)
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(route_feedback, request)
            if page is not None:
                serializer = RouteFeedbackDetailSerializer(
                    page, fields=('id', 'route_progress', 'attempt_count', 'route_note',
                                  'climb_count', 'grade', 'rating', 'feedback', 'created_at',
                                  'first_time_read', 'second_time_read',), many=True)
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data)
        serializer = RouteFeedbackDetailSerializer(
                route_feedback, fields=('id', 'route_progress', 'attempt_count', 'route_note',
                                        'climb_count', 'grade', 'rating', 'feedback', 'created_at',
                                        'first_time_read', 'second_time_read',), many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class ListCategoryViewSet(viewsets.ViewSet):
    """
        ListCategoryViewSet class used to add/get the list category.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': ListCategorySerializer,
        'create': ListCategorySerializer
    }

    def list(self, request):
        """
        list method used for categories list.
            :param request:
            :return: response
        """
        page_size = request.GET.get('page_size', '')
        gym_id = request.GET.get('gym_id', '')
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location='list category', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        ## For New CR
        # common_category_list = ListCategory.objects.filter(is_common=True).order_by('id')
        # category_list = ListCategory.objects.filter(user=request.user, gym=gym_id).order_by('id')
        category = ListCategory.objects.filter(user=request.user).order_by('id')
        ## For New CR
        # category = common_category_list | category_list
        # category = category_list
        if page_size:
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(category, request)
            if page is not None:
                serializer = self.action_serializers.get(self.action)(instance=page, many=True,
                                                                      context={'request': request.user})
                return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                       status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(category, many=True,
                                                              context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add category.
            :param request:
            :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data,
                                                              context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            update method used to delete category.
            :param request:
            :return: response
        """
        category_ids = request.data.get('category_ids')
        list_category = ListCategory.objects.filter(id__in=category_ids)
        if list_category:
            # list_category.update(is_active=False)
            # list_category.update(is_deleted=True)
            list_categories = list_category.values_list('id', flat=True)
            RouteSaveList.objects.filter(list_category__in=list_categories).delete()
            list_category.delete()
        return SuccessResponse({"message": success_message.get('CATEGORY_DELETED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class RouteIntoCategoryViewSet(viewsets.ViewSet):
    """
        RouteIntoCategoryViewSet class used to add/list the route into category.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    create_serializer_class = RouteIntoCategorySerializer

    def list(self, request):
        """
        list method used for categories list.
            :param request:
            :return: response
        """
        # gym_id = request.GET.get('gym_id', '')
        # category_id = request.GET.get('category_id', '')
        # if not gym_id or not category_id:
        #     return Response(get_custom_error(message='Please provide the gym id and category id.',
        #                                      error_location='route into category', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        # # Only Active, Not Deleted and Order by Recently Added Route
        # wall_route = WallRoute.objects.select_related('section_wall').prefetch_related('route_save_list').\
        #     filter(route_save_list__user=request.user, route_save_list__gym=gym_id, route_save_list__user=
        #     request.user).order_by('section_wall')

        category_id = request.GET.get('category_id', '')
        if not category_id:
            return Response(get_custom_error(message='Please provide the category id.',
                                             error_location='route into category', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # Only Active, Not Deleted and Order by Recently Added Route
        # wall_route = WallRoute.objects.select_related('section_wall', 'grade').prefetch_related('route_save_list').\
        #     filter(route_save_list__list_category=category_id, route_save_list__user=request.user).\
        #     order_by('-route_save_list')
            # order_by('section_wall')

        # To annotate for gym details instead of get gym detail in serializer
        gym_details = GymDetails.objects.filter(gym_layout__gym_layout_wall__section_wall_route=OuterRef('pk'))
        wall_route = WallRoute.objects.select_related('section_wall', 'grade', 'color', 'route_type',).prefetch_related('route_save_list').\
            filter(route_save_list__list_category=category_id, route_save_list__user=request.user).\
            annotate(gym_id=Subquery(gym_details.values('id')[:1]),
                     gym_name=Subquery(gym_details.values('gym_name')[:1])).order_by('-route_save_list')

        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(wall_route, request)
        if page is not None:
            serializer = WallRouteDetailSerializer(instance=page, fields=(
                'id', 'name', 'grade', 'color', 'section_wall', 'gym_id', 'gym_name',), many=True)
            # work_data = core_utils.modify_data_group_by_wall(serializer.data)
            # return SuccessResponse(pagination_class.get_paginated_response(work_data).data,
            #                        status=status_code.HTTP_200_OK)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = WallRouteDetailSerializer(wall_route, fields=(
            'id', 'name', 'grade', 'color', 'section_wall', 'gym_id', 'gym_name',), many=True)
        # work_data = core_utils.modify_data_group_by_wall(serializer.data)
        # return SuccessResponse(work_data, status=status_code.HTTP_200_OK)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add category.
            :param request:
            :return: response
        """
        # For block gym
        gym_detail = GymDetails.objects.filter(id=request.data.get('gym')).first()
        if gym_detail:
            common_block_gym_fun(request.user, gym_detail)
        serializer = self.create_serializer_class(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get('ROUTE_ADDED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)

    @staticmethod
    def update(request):
        """
                put method used to remove route from category.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        route_id = request.GET.get('route_id', '')
        if not gym_id or not route_id:
            return Response(get_custom_error(message='Please provide gym id and route id.',
                                             error_location='route into category', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        route_tag = RouteSaveList.objects.filter(user=request.user, gym=gym_id, route=route_id).first()
        if route_tag:
            # For block gym
            gym_detail = GymDetails.objects.filter(id=gym_id).first()
            if gym_detail:
                common_block_gym_fun(request.user, gym_detail)
            route_tag.route.remove(route_id)
        return SuccessResponse({"message": success_message.get('ROUTE_REMOVED_SUCCESSFULLY')},
                               status=status_code.HTTP_200_OK)


class RouteFeedbackViewSet(viewsets.ViewSet):
    """
        RouteFeedbackViewSet class used to add/list/retrieve the route feedback.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': RouteFeedbackDetailSerializer,
        'create': RouteFeedbackSerializer,
        'retrieve': RouteFeedbackDetailSerializer
    }

    # # WITHOUT CR
    # def list(self, request):
    #     """
    #     list method used for route feedback list.
    #         :param request:
    #         :return: response
    #     """
    #     # gym_id = request.GET.get('gym_id', '')
    #     # if not gym_id:
    #     #     return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
    #     #                                      error_location='route feedback', status=400),
    #     #                     status=status_code.HTTP_400_BAD_REQUEST)
    #     # feedbacks = UserRouteFeedback.objects.select_related('route', 'route__section_wall').\
    #     #     filter(user=request.user, route__section_wall__gym_layout__gym=gym_id).\
    #     #     order_by('-id')
    #     # Only not deleted feedbacks will show
    #     feedbacks = UserRouteFeedback.objects.select_related('gym', 'route', 'route__section_wall', 'route__grade',
    #                                                          'route__color', 'route__route_type',). \
    #         filter(user=request.user, route__is_deleted=False).order_by('-id')
    #     # In future, can also add is_added_to_category field to show, is it added into a category
    #     pagination_class = self.pagination_class()
    #     page = pagination_class.paginate_queryset(feedbacks, request)
    #     if page is not None:
    #         serializer = self.action_serializers.get(self.action)(instance=page, many=True,
    #                                                               context={'request': request.user})
    #         return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
    #                                status=status_code.HTTP_200_OK)
    #     serializer = self.action_serializers.get(self.action)(feedbacks, many=True,
    #                                                           context={'request': request.user})
    #     return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    # CR
    def list(self, request):
        """
        list method used for route feedback list.
            :param request:
            :return: response
        """
        # Only not deleted feedbacks will show
        # feedbacks_queryset = UserRouteFeedback.objects.filter(user=request.user).order_by('-id').\
        #     values('id', 'route_id')
        feedbacks_queryset = UserRouteFeedback.objects.filter(user=request.user, route__is_deleted=False).order_by('-id').\
            values('id', 'route_id')
        feedbacks = core_utils.show_latest_unique_feedback(feedbacks_queryset)
        updated_feedbacks = UserRouteFeedback.objects.select_related('gym', 'route', 'route__section_wall', 'route__grade',
                                                                     'route__color', 'route__route_type',). \
            filter(id__in=feedbacks).order_by('-id')
        # In future, can also add is_added_to_category field to show, is it added into a category
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(updated_feedbacks, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True,
                                                                  context={'request': request.user})
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(updated_feedbacks, many=True,
                                                              context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add route feedback.
            :param request:
            :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, feedback_id):
        """
        retrieve method used to get route feedback detail by id.
            :param request:
            :param feedback_id:
            :return: response
        """
        feedback_detail = UserRouteFeedback.objects.select_related(
            'route', 'route__section_wall', 'route__grade', 'route__color',).filter(id=feedback_id).first()
        # In future, can also add is_added_to_category field to show, is it added into a category
        # # To add delete route or delete wall custom message
        # if feedback_detail and feedback_detail.route.is_deleted:
        #     return Response(get_custom_error(message=validation_message.get('ROUTE_IS_DELETED'),
        #                                      error_location='route_feedback', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        # elif feedback_detail and feedback_detail.route.section_wall.is_deleted:
        #     return Response(get_custom_error(message=validation_message.get('WALL_IS_DELETED'),
        #                                      error_location='route_feedback', status=400),
        #                     status=status_code.HTTP_400_BAD_REQUEST)
        if feedback_detail:
            serializer = self.action_serializers.get(self.action)(feedback_detail,
                                                                  context={'request': request.user})
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class AnnouncementViewSet(viewsets.ViewSet):
    """
        AnnouncementViewSet class used to list/retrieve the announcements.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': ClimberAnnounceDetailSerializer,
        'retrieve': ClimberAnnounceDetailSerializer,
    }

    def list(self, request):
        """
        list method used for announcement list.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location='announcement', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # For block gym
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        if gym_detail:
            common_block_gym_fun(request.user, gym_detail)
        # announcements = Announcement.objects.filter(gym=gym_id).order_by('-created_at')
        announcements = Announcement.objects.select_related('template').filter(gym=gym_id).order_by('-priority')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(announcements, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(announcements, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def retrieve(self, request, announcement_id):
        """
        retrieve method used to get announcement detail by id.
            :param request:
            :param announcement_id:
            :return: response
        """
        announcement_detail = Announcement.objects.select_related('template').filter(id=announcement_id).first()
        if announcement_detail:
            # For block gym
            common_block_gym_fun(request.user, announcement_detail.gym)
            serializer = self.action_serializers.get(self.action)(announcement_detail)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class EventViewSet(viewsets.ViewSet):
    """
        EventViewSet class used to list the events and add as favourite list.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': ClimberEventDetailSerializer,
        'create': ClimberSaveEventSerializer,
        'retrieve': ClimberEventDetailSerializer,
    }

    def list(self, request):
        """
        list method used for event list.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location='event', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        # For block gym
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        if gym_detail:
            common_block_gym_fun(request.user, gym_detail)
        today_date_time = datetime.now(timezone.utc)
        events = Event.objects.filter(gym=gym_id, start_date__gte=today_date_time).order_by('start_date')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(events, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True,
                                                                  context={'request': request.user})
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(events, many=True, context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to saved/remove event.
        :param request:
        :return: response
        """
        event_detail = Event.objects.filter(id=request.data.get('save_event')).first()
        # For block gym
        if event_detail:
            common_block_gym_fun(request.user, event_detail.gym)
        check_event, msg = core_utils.check_event_delete_or_pass_status(event_detail)
        if not check_event:
            return Response(get_custom_error(message=msg, error_location='event', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, context={'request': request.user})
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
        event_detail = Event.objects.filter(id=event_id).first()
        # For block gym
        if event_detail:
            common_block_gym_fun(request.user, event_detail.gym)
        check_event, msg = core_utils.check_event_delete_or_pass_status(event_detail)
        if not check_event:
            return Response(get_custom_error(message=msg, error_location='event', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(event_detail, context={'request': request.user})
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class PercentageDetailViewSet(viewsets.ViewSet):
    """
        PercentageDetailViewSet class used to retrieve user percentage detail.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    serializer_class = PercentageDetailSerializer

    def retrieve(self, request):
        """
        retrieve method used to get user percentage data.
            :param request:
            :return: response
        """
        percentage_data = UserDetailPercentage.objects.filter(user=request.user).first()
        if percentage_data:
            serializer = self.serializer_class(percentage_data)
            return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)
        return SuccessResponse({}, status=status_code.HTTP_200_OK)


class ClimbingInfoViewSet(viewsets.ViewSet):
    """
        ClimbingInfoViewSet class used to list/update user climbing details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    action_serializers = {
        'retrieve': ClimbingInfoDetailSerializer,
        'update': ClimbingInfoSerializer,
    }

    def retrieve(self, request):
        """
        retrieve method used to get user climbing data.
            :param request:
            :return: response
        """
        climbing_info = UserPreference.objects.filter(user=request.user).first()
        serializer = self.action_serializers.get(self.action)(climbing_info)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            post method used to update climbing info.
        :param request:
        :return: response
        """
        instance = UserPreference.objects.filter(user=request.user).first()
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=instance,
                                                              context={'request': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class BiometricDataViewSet(viewsets.ViewSet):
    """
        BiometricDataViewSet class used to list/create/update user biometric details.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    action_serializers = {
        'retrieve': BiometricDataDetailSerializer,
        'update': BiometricDataSerializer,
    }

    def retrieve(self, request):
        """
        retrieve method used to get user biometric data.
            :param request:
            :return: response
        """
        biometric_instance = getattr(request.user, 'user_biometric', None)
        data_for_serialize = biometric_instance
        if not biometric_instance:
            data_for_serialize = UserBiometricData.objects.create(user=request.user)
        serializer = self.action_serializers.get(self.action)(data_for_serialize)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
            post method used to update biometric data.
        :param request:
        :return: response
        """
        instance = UserBiometricData.objects.filter(user=request.user).first()
        if not instance:
            return Response(get_custom_error(message=validation_message.get('USER_NOT_FOUND'),
                                             error_location='biometric data', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        serializer = self.action_serializers.get(self.action)(data=request.data, instance=instance)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class SavedEventViewSet(viewsets.ViewSet):
    """
        SavedEventViewSet class used to list the saved events.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': SaveEventDetailSerializer,
    }

    def list(self, request):
        """
        list method used to get event list.
            :param request:
            :return: response
        """
        gym_id = request.GET.get('gym_id', '')
        if not gym_id:
            return Response(get_custom_error(message=validation_message.get('PROVIDE_GYM_ID'),
                                             error_location='saved event', status=400),
                            status=status_code.HTTP_400_BAD_REQUEST)
        today_date_time = datetime.now(timezone.utc)
        saved_events = SavedEvent.objects.select_related('save_event').\
            filter(user=request.user, is_saved=True, save_event__gym=gym_id, save_event__is_active=True,
                   save_event__is_deleted=False, save_event__start_date__gte=today_date_time).order_by('save_event__start_date')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(saved_events, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(saved_events, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class QuestionAnswerViewSet(viewsets.ViewSet):
    """
        QuestionAnswerViewSet class used to list the question/answer.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)
    pagination_class = CustomPagination
    serializer_class = QuestionAnswerSerializer

    def list(self, request):
        """
        list method used to get question/answer list.
            :param request:
            :return: response
        """
        question_answer = QuestionAnswer.objects.all().order_by('id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(question_answer, request)
        if page is not None:
            serializer = self.serializer_class(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.serializer_class(question_answer, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class CheckClimberIsStaff(viewsets.ViewSet):
    """
        CheckClimberIsStaff class used to get climber is staff or not for any gym.
    """
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated, AppClimberPermission,)

    def list(self, request):
        """
        list method used to get climber is staff or not.
            :param request:
            :return: response
        """
        check_staff_user = User.objects.filter(user_role__user=request.user, user_role__name=Role.RoleType.GYM_STAFF,
                                               user_role__role_status=True,
                                               user_details__home_gym__isnull=False).first()
        is_staff_user = False
        if check_staff_user:
            is_staff_user = True
        return SuccessResponse({"is_staff_user": is_staff_user}, status=status_code.HTTP_200_OK)

import os
import uuid
from datetime import datetime, timezone
from itertools import chain
from multiprocessing import Process

import pandas as pd
import xlsxwriter

from django.db.models import Sum, CharField, Value

from admins.serializers import (AdminLoginSerializer, AdminForgetPasswordSerializer,
                                AdminResetPasswordSerializer, AdminResetPasswordSerializer, ListOfUserSerializer,
                                SpecificUserDetailSerializer,
                                CustomEmailSerializer, SpecificUserDetailSerializer, ClimberProfileSerializer,
                                GymProfileSerializer, ListOfReviewSerializer, PaymentGraphSerializer,
                                UserSubscriptionSerializer, DetailReviewSerializer, UserSerializer, DomainSerializer)
from accounts.models import User, Role, UserSubscription, SavedEvent
from accounts.models import User,Role,WallVisit, UserDetails, UserRouteFeedback
from core.views import upload_payment_report
from gyms.models import GymDetails, WallRoute, SectionWall, WallRoute, LayoutSection, Event, Announcement, \
    ChangeRequestGymDetails, GymLayout
from accounts.models import User, Role, UserSubscription
from accounts.models import User, Role, WallVisit, UserSubscription
from gyms.models import GymDetails, WallRoute,SectionWall
from rest_framework import viewsets, mixins, filters
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from rest_framework import status as status_code
from core.response import SuccessResponse
from core.messages import success_message,validation_message
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from rest_framework import generics
from django.shortcuts import get_object_or_404
from core.permissions import CheckAdminRoleStatusPermission
from admins.serializers import (ListSubscriptionSerializer,)
from admins.models import SubscriptionPlan, Domain
from core.exception import get_custom_error, CustomException
from core.messages import success_message, validation_message
from core.pagination import CustomPagination
from core.response import SuccessResponse
from core import utils as core_utils
from payments.models import Transaction
from payments.stripe_functions import stripe_plan_create, plan_amount_change, update_users_for_subscription
from django.core.mail import EmailMessage
from config.local import ADMIN_MAIL
from django.core.mail import EmailMessage
from core.response import SuccessResponse
from django_filters.rest_framework import DjangoFilterBackend
from django.views import generic


class AdminLoginViewSet(viewsets.ViewSet):

    """
        AdminLoginViewSet to Login the admin panel
    """

    permission_classes = (AllowAny,)
    serializer_class = AdminLoginSerializer

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status_code.HTTP_200_OK)


class AdminForgetPasswordViewSet(viewsets.ViewSet):
    serializer_class = AdminForgetPasswordSerializer
    permission_classes = (AllowAny,)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # Remove during production
        forgot_password_url = serializer.validated_data.get("forgot_password_url")
        # Remove during production forgot_password_url key
        return SuccessResponse({"message": success_message.get('FORGOT_PASSWORD_LINK_SUCCESS_MESSAGE'),
                                "forgot_password_url": forgot_password_url}, status=status_code.HTTP_200_OK)


class AdminResetPasswordViewSet(viewsets.ViewSet):
    serializer_class = AdminResetPasswordSerializer
    permission_classes = (AllowAny,)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        bool_val = serializer.save()
        if bool_val:
            return SuccessResponse({"message": success_message.get('PASSWORD_CHANGED'), "res_status": 1},
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse({"message": validation_message.get("FORGOT_PASS_LINK_ALREADY_VERIFIED"),
                                "res_status": 2},
                               status=status_code.HTTP_200_OK)


class PlansSubscriptionAdmin(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission, )
    pagination_class = CustomPagination
    action_serializers = {
        'list': ListSubscriptionSerializer,
        'retrieve': ListSubscriptionSerializer,
    }

    def create(self, request):
        """
        post method used for the Subscription.
            :param request:
            :return: response
        """
        try:
            plan_obj = SubscriptionPlan.objects.filter(amount=request.data.get('amount'),
                                                       currency=request.data.get('currency')).first()
            if plan_obj:
                return Response(get_custom_error(message=validation_message.get('PLAN_EXISTS'),
                                                 error_location=validation_message.get('SUBSCRIPTION_PLAN'), status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
            stripe_plan = stripe_plan_create(request)
            SubscriptionPlan.objects.create(plan_id=stripe_plan.id,
                                            product=stripe_plan.product,
                                            amount=request.data['amount'],
                                            currency=request.data['currency'],
                                            title=request.data['title'],
                                            interval=request.data['interval'],
                                            access_to_wall_pics=request.data['access_to_wall_pics'],
                                            uploaded_wall_number=request.data['uploaded_wall_number'],
                                            access_feedback_per_month=request.data.get('access_feedback_per_month'),
                                            access_to_gym_staff=request.data['access_to_gym_staff'],
                                            active_gymstaff_number=request.data['active_gymstaff_number'],
                                            announcements_create=request.data['announcements_create'],
                                            access_to_biometric_data=request.data['access_to_biometric_data'],
                                            access_to_sign_up_info=request.data['access_to_sign_up_info'],
                                            )
            return SuccessResponse({"message": success_message.get('PLAN_SUCCESSFUL')},status=status_code.HTTP_200_OK)
        except Exception as ex:
            print(ex)
            msg = core_utils.create_exception_message(ex)
            raise CustomException(status_code=400, message=msg, location="Plan creation")

    def update(self, request):
        """
        put method used for updating subscription
        :param request:
        :return: response
        """
        try:
            id = request.data.get('id')
            amount = request.data.get('amount')
            plan_obj = SubscriptionPlan.objects.filter(id=id).first()
            if not plan_obj or SubscriptionPlan.objects.filter(amount=amount).exists():
                return Response(get_custom_error(message=validation_message.get('PLAN_UPDATE'),
                                                 error_location=validation_message.get('SUBSCRIPTION_PLAN'), status=400),
                                status=status_code.HTTP_400_BAD_REQUEST)
            try:
                plan_id = plan_obj.plan_id
                new_stripe_plan = plan_amount_change(plan_id, amount)
                # new stripe plan adding to the Subscription plan for amount change
                plan_obj.plan_id = new_stripe_plan.id
                plan_obj.amount = amount
                plan_obj.save()
                # Update all users to new subscription related to this plan
                subscribed_users = UserSubscription.objects.filter(plan=plan_obj)
                update_users_for_subscription(subscribed_users, new_stripe_plan)
                # Mail will also send to the user i.e. price has been changed
                subscribed_users = subscribed_users.values_list('user__email', flat=True)
                core_utils.send_html_mail_to_multiple_user(subject="Plan Updated", email_list=subscribed_users,
                                                           html_template="plan_updated.html", ctx_dict={})
            except Exception as ex:
                print(ex)
                msg = core_utils.create_exception_message(ex)
                raise CustomException(status_code=400, message=msg, location="Plan update")
            return SuccessResponse({"message": success_message.get('PLAN_UPDATE_SUCCESS')}, status=status_code.HTTP_200_OK)
        except Exception as ex:
            print(ex)
            msg = core_utils.create_exception_message(ex)
            raise CustomException(status_code=400, message=msg, location="Plan update")

    def list(self, request):
        """
        list method used for sunbscription plan
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

    def retrieve(self, request, plan_id):
        """
        retrieve method used for subscription plan
            :param request:
            :param plan_id:
            :return: response
        """
        sub_obj = SubscriptionPlan.objects.filter(id=plan_id).first()
        data = {}
        if sub_obj:
            serializer = self.action_serializers.get(self.action)(sub_obj)
            data = serializer.data
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class StaffMemberCountViewSet(viewsets.ViewSet):
    """
        Dashboard stats
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def list(self, request):
        user_data = User.all_objects.all()
        staff_member_count = user_data.filter(user_role__name=Role.RoleType.GYM_STAFF,
                                              user_role__role_status=True).count()
        gym_registered = user_data.filter(gym_detail_user__isnull=False).count()
        # climber_count = user_data.filter(user_details__isnull=False).count()
        climber_count = user_data.filter(user_role__name=Role.RoleType.CLIMBER,
                                         user_role__role_status=True).count()
        wall_count = SectionWall.all_objects.filter(layout_section__gym_layout__gym__isnull=False).count()
        route_count = WallRoute.all_objects.filter(section_wall__layout_section__gym_layout__gym__isnull=False).count()
        content = {
            'total_no_of_staff_members': staff_member_count,
            'total_gym_registered': gym_registered,
            'total_no_of_climbers': climber_count,
            'total_numbers_of_walls': wall_count,
            'total_numbers_of_routes': route_count
        }
        return SuccessResponse(content, status=status_code.HTTP_200_OK)


class ListUserViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = ListOfUserSerializer
    pagination_class = CustomPagination
    queryset = User.all_objects.all()
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    # filterset_fields = ['user_role__name', 'is_active']
    search_fields = ('full_name', 'email', 'user_details__home_gym__gym_name', 'gym_detail_user__gym_name',)

    def get_queryset(self, *args, **kwargs):
        is_active = self.request.data.get('is_active', 'no_key')
        user_role = self.request.data.get('user_role__name', '')
        query = super(ListUserViewSet, self).get_queryset()
        query = query.prefetch_related('user_role', 'user_details', 'user_details__home_gym',
                                       'gym_detail_user').filter(is_superuser=False).order_by('-id')
        if is_active != 'no_key':
            query = query.filter(is_active=is_active)
        if user_role:
            query = query.filter(user_role__name=user_role, user_role__role_status=True)
        return query
        # return self.filter_queryset(query)

    def create(self, request, *args, **kwargs):
        response = super().list(self, request, *args, **kwargs)
        return SuccessResponse(response.data, status=status_code.HTTP_200_OK)


class SpecificUserDetailViewSet(viewsets.ViewSet):

    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = SpecificUserDetailSerializer

    def retrieve(self, request, user_id):
        user_details = User.objects.get(id=user_id)
        serializer = self.serializer_class(user_details, many=False)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)


class GetGymUserViewset(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    pagination_class = CustomPagination

    def list(self, request):
        user = User.objects.filter(gym_detail_user__isnull=False).order_by('id').values('id', 'email',
                                                                                        'gym_detail_user__gym_name')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(user, request)
        if page:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(user, status=status_code.HTTP_200_OK)


class GetFilteredUserViewset(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = CustomEmailSerializer
    pagination_class = CustomPagination

    def create(self, request):
        gym_data = request.data.get('gym_user')
        user_data = request.data.get('other_user')
        if gym_data == '':
            gym = None
        elif gym_data == 'ALL_GYM':
            gym = User.objects.filter(gym_detail_user__isnull=False)
        else:
            gym = User.objects.filter(id__in=gym_data, gym_detail_user__isnull=False)
        data = core_utils.get_filtered_user_common_fun(gym, user_data)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(data, request)
        if page:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class CustomEmailViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = CustomEmailSerializer
    pagination_class = CustomPagination

    # def list(self, request):
    #     user = User.objects.filter(gym_detail_user__isnull=False).order_by('id').values('id', 'email',
    #                                                                                     'gym_detail_user__gym_name')
    #     pagination_class = self.pagination_class()
    #     page = pagination_class.paginate_queryset(user, request)
    #     if page:
    #         return SuccessResponse(pagination_class.get_paginated_response(page).data,
    #                                status=status_code.HTTP_200_OK)
    #     return SuccessResponse(user, status=status_code.HTTP_200_OK)

    def create(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse({"message": success_message.get("CUSTOM_MAIL_SEND")}, status=status_code.HTTP_200_OK)


# class GlobalSearchView(generics.ListAPIView):
#     queryset=User.objects.all()
#     serializer_class=GlobalSearchSerializer


# class DeleteUserViewSet(viewsets.ViewSet):
#     def destroy(self,request,user_id):
#         user=User.objects.get(id=user_id)
#         user.is_deleted=True
#         user.save()
#         return Response("User deleted")


class ClimberProfileViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = ClimberProfileSerializer

    def list(self, request, user_id):
        user = User.all_objects.filter(id=user_id).first()
        try:
            if user.user_role.filter(name=3, role_status=True).exists():
                is_associated_to_gym = True
                associated_gym = user.user_details.home_gym.gym_name
            else:
                is_associated_to_gym = False
                associated_gym = None
        except:
            is_associated_to_gym = False
            associated_gym = None
        serializer = self.serializer_class(user)
        saved_event_count = SavedEvent.objects.filter(user=user_id, is_saved=True).count()
        route_feedbacks = UserRouteFeedback.objects.filter(user=user_id).order_by('-created_at')
        route_feedbacks_count = route_feedbacks.count()
        route_feedbacks_last_updated = route_feedbacks.first().created_at if route_feedbacks else None
        climb_count = sum(UserRouteFeedback.objects.filter(user=user_id).exclude(
            route_progress=UserRouteFeedback.RouteProgressType.PROJECTING).values_list('climb_count', flat=True))
        b_detail_dict = serializer.data
        b_detail_dict.update({'is_associated_to_gym': is_associated_to_gym, 'associated_gym': associated_gym})
        data = {}
        data.update({
            "basic_details": b_detail_dict,
            "last_updated": route_feedbacks_last_updated,
            "saved_event_count": saved_event_count,
            "no_of_climbs": climb_count,
            "feedback_count": route_feedbacks_count
        })
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class GymProfileViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = GymProfileSerializer

    def list(self, request, gym_user_id):
        user = GymDetails.objects.select_related('user').filter(user__id=gym_user_id).first()
        serializer = self.serializer_class(user)
        subscription = UserSubscription.objects.select_related('plan').filter(user=gym_user_id).first()
        subscription_serializer = UserSubscriptionSerializer(subscription) if subscription else None
        no_of_members = UserDetails.objects.filter(home_gym__user=gym_user_id, user__user_role__name=3,
                                                   user__user_role__role_status=True).count()
        layout_count = GymLayout.all_objects.filter(gym__user=gym_user_id).count()
        section_count = LayoutSection.all_objects.filter(gym_layout__gym__user=gym_user_id).count()
        wall_count = SectionWall.all_objects.filter(layout_section__gym_layout__gym__user=gym_user_id).count()
        route_count = WallRoute.all_objects.filter(section_wall__layout_section__gym_layout__gym__user=gym_user_id).count()
        announcement_count = Announcement.all_objects.filter(gym__user=gym_user_id).count()
        event_count = Event.all_objects.filter(gym__user=gym_user_id).count()
        data = {}
        data.update({
            "basic_details": serializer.data,
            "subscription_details": subscription_serializer.data if subscription_serializer else None,
            "no_of_members": no_of_members,
            "layout_count": layout_count,
            "section_count": section_count,
            "route_count": route_count,
            "wall_count": wall_count,
            "announcement_count": announcement_count,
            "event_count": event_count,
        })
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class DeleteBulkUserViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def update(self, request):
        action_type = request.data.get('action_type')
        user_ids = request.data.get('user_ids')
        msg = "Invalid action type"
        print(action_type)
        if action_type == "ACTIVATE":
            User.all_objects.filter(id__in=user_ids).update(is_active=True)
            msg = success_message.get("BULK_USER_ACTIVATED")
        elif action_type == "DEACTIVATE":
            User.all_objects.filter(id__in=user_ids).update(is_active=False)
            msg = success_message.get("BULK_USER_DEACTIVATED")
        return SuccessResponse({"message": msg}, status=status_code.HTTP_200_OK)


class DeleteSingleUserViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def destroy(self,request,user_id):

        user = User.objects.filter(id=user_id)
        if user:
            user.update(is_active=False)
        return Response("Selected User has been deleted")


class ListOfReviewViewSet(viewsets.ViewSet, viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = DetailReviewSerializer
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend, filters.SearchFilter,)
    search_fields = ('user__email', 'gym_name', 'address',)

    def list(self, request):
        """
        # Using for approve and change request
            user = GymDetails.objects.filter(is_admin_approved=False, user__is_active=True).order_by('-updated_at').values(
                'id', 'updated_at', 'gym_name', 'user__email', 'address').\
                annotate(review_type=Value('Approve', output_field=CharField()))
            change_request = ChangeRequestGymDetails.objects.all().order_by('-updated_at').values(
                'gym_detail__id', 'updated_at', 'gym_name', 'email', 'gym_detail__address').\
                annotate(review_type=Value('Change Request', output_field=CharField()))
            intersection = sorted(list(chain(user, change_request)), key=lambda instance: instance['updated_at'],
                                  reverse=True)
            pagination_class = self.pagination_class()
            page = pagination_class.paginate_queryset(intersection, request)
            if page:
                return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                       status=status_code.HTTP_200_OK)
            return SuccessResponse(intersection, status=status_code.HTTP_200_OK)
        """
        gym_details = GymDetails.objects.filter(is_admin_approved=False, is_profile_complete=True,
                                                user__is_active=True).order_by('-created_at').\
            values('id', 'created_at', 'gym_name', 'user__email', 'address')
        gym_details = self.filter_queryset(gym_details)
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(gym_details, request)
        if page is not None:
            return SuccessResponse(pagination_class.get_paginated_response(page).data,
                                   status=status_code.HTTP_200_OK)
        return SuccessResponse(gym_details, status=status_code.HTTP_200_OK)

    def retrieve(self, request, gym_id):
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        data = {}
        if gym_detail:
            serializer = self.serializer_class(gym_detail)
            data = serializer.data
        return SuccessResponse(data, status=status_code.HTTP_200_OK)


class ApproveViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def update(self,request):
        """
        # Using for approve and change request
        gym_id = request.GET.get('gym_id')
        review_type = request.GET.get('review_type')
        user_detail = User.all_objects.filter(gym_detail_user=gym_id)
        gym_detail = GymDetails.objects.filter(id=gym_id).first()
        # to_mail = user_detail.first().email
        to_mail = 'shivagupta086@gmail.com'
        if int(review_type) == 1:
            user_detail.update(is_active=True)
            gym_detail.is_admin_approved = True
            gym_detail.save()
        elif int(review_type) == 2:
            cr = gym_detail.gym_change_request
            update_email = cr.email
            update_gym_name = cr.gym_name
            update_easy_direction_link = cr.easy_direction_link
            update_website_link = cr.website_link
            if update_email:
                user_detail.update(email=update_email)
            if update_gym_name:
                gym_detail.gym_name = update_gym_name
            if update_easy_direction_link:
                gym_detail.easy_direction_link = update_easy_direction_link
            if update_website_link:
                gym_detail.website_link = update_website_link
            gym_detail.save()
            ChangeRequestGymDetails.objects.filter(gym_detail=gym_id).delete()
        core_utils.send_html_mail_to_single_user('Review Status Changed', to_mail, 'acception_mail.html',
                                                 {'email': to_mail})
        return SuccessResponse({"message": success_message.get("ADMIN_APPROVED")}, status=status_code.HTTP_200_OK)
        """
        gym_id = request.GET.get('gym_id')
        gym_detail = GymDetails.objects.filter(id=gym_id)
        if gym_detail:
            gym_detail.update(is_admin_approved=True)
            user = User.objects.filter(gym_detail_user=gym_id)
            user.update(is_active=True)
            to_mail = user.first().email
            # send approval mail to gym user
            p = Process(target=core_utils.send_html_mail_to_single_user,
                        args=('Review Status Changed', to_mail, 'acception_mail.html', {'email': to_mail}))
            p.start()
        return SuccessResponse({"message": success_message.get("ADMIN_APPROVED")}, status=status_code.HTTP_200_OK)


class RejectViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)

    def update(self, request):
        """
        # Using for approve and change request
        gym_id = request.GET.get('gym_id')
        review_type = request.GET.get('review_type')
        user_detail = User.all_objects.filter(gym_detail_user=gym_id)
        # to_mail = user_detail.first().email
        to_mail = 'shivagupta086@gmail.com'
        if int(review_type) == 1:
            user_detail.update(is_active=False)
        elif int(review_type) == 2:
            ChangeRequestGymDetails.objects.filter(gym_detail=gym_id).delete()
        core_utils.send_html_mail_to_single_user('Review Status Changed', to_mail, 'rejection_mail.html',
                                                 {'email': to_mail})
        return SuccessResponse({"message": success_message.get("ADMIN_REJECTION")}, status=status_code.HTTP_200_OK)
        """
        gym_id = request.GET.get('gym_id')
        user_detail = User.all_objects.filter(gym_detail_user=gym_id)
        if user_detail:
            to_mail = user_detail.first().email
            user_detail.update(is_active=False)
            # send rejection mail to gym user
            p = Process(target=core_utils.send_html_mail_to_single_user,
                        args=('Review Status Changed', to_mail, 'rejection_mail.html', {'email': to_mail}))
            p.start()
        return SuccessResponse({"message": success_message.get("ADMIN_REJECTION")}, status=status_code.HTTP_200_OK)


class PaymentGraphViewSet(viewsets.ViewSet):
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    serializer_class = PaymentGraphSerializer
    pagination_class = CustomPagination

    def list(self, request):
        year = request.GET.get('year', '')
        if not year:
            year = datetime.utcnow().year
        payments = Transaction.objects.filter(transaction_time__date__year=year).values(
            'transaction_time__date__month', 'transaction_time__date__year',).\
            annotate(amount=Sum('total_amount')).order_by('transaction_time__date__month')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(payments, request)
        if page:
            return SuccessResponse(pagination_class.get_paginated_response(page).data)
        return SuccessResponse(payments, status=status_code.HTTP_200_OK)


class PaymentReportViewSet(viewsets.ViewSet):
    """
        PaymentReportViewSet class used to export the payment report
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission)

    def list(self, request):
        """
            method to list the payment report by month
        """
        from_date = request.GET.get('month_start_date')
        to_date = request.GET.get('month_last_date')
        if not from_date or not to_date:
            return Response(get_custom_error(message='Please provide month start and last date.',
                                             error_location='payment report',
                                             status=status_code.HTTP_400_BAD_REQUEST),
                            status=status_code.HTTP_400_BAD_REQUEST)

        payments = Transaction.objects.filter(transaction_time__date__range=[from_date, to_date]).values(
            'transaction_time__date').annotate(amount=Sum('total_amount')).order_by('transaction_time__date')
        updated_payments = core_utils.update_payments_based_on_date(payments, from_date, to_date)

        df = pd.DataFrame(updated_payments)
        file_name = "{}_{}_{}".format(uuid.uuid4(), datetime.now(timezone.utc).timestamp(), 'data.xlsx')

        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'others/downloads/'+file_name)
        writer = pd.ExcelWriter(data_path, engine='xlsxwriter')
        df.to_excel(writer, sheet_name="payment_report", index=False)
        # Indicate workbook and worksheet for formatting
        worksheet = writer.sheets['payment_report']
        # Iterate through each column and set the width == the max length in that column. A padding length of 2 is also added.
        for i, col in enumerate(df.columns):
            # find length of column i
            column_len = df[col].astype(str).str.len().max()
            # Setting the length if the column header is larger
            # than the max column value length
            column_len = max(column_len, len(col)) + 2
            # set the column length
            worksheet.set_column(i, i, column_len)
        writer.save()
        # To upload file on aws
        bool_val, url_data = upload_payment_report(file_name, data_path)
        if not bool_val:
            os.remove(data_path)
            return SuccessResponse(url_data, status=status_code.HTTP_400_BAD_REQUEST)
        os.remove(data_path)
        return SuccessResponse(url_data, status=status_code.HTTP_200_OK)
        # return SuccessResponse(updated_payments, status=status_code.HTTP_200_OK)


class DomainViewSet(viewsets.ViewSet):
    """
        DomainViewSet class used to list, add, remove the domains.
    """
    permission_classes = (IsAuthenticated, CheckAdminRoleStatusPermission,)
    pagination_class = CustomPagination
    action_serializers = {
        'list': DomainSerializer,
        'create': DomainSerializer,
    }

    def list(self, request):
        """
        list method used for domain list.
            :param request:
            :return: response
        """
        domains = Domain.objects.filter(is_deleted=False).order_by('-id')
        pagination_class = self.pagination_class()
        page = pagination_class.paginate_queryset(domains, request)
        if page is not None:
            serializer = self.action_serializers.get(self.action)(instance=page, many=True)
            return SuccessResponse(pagination_class.get_paginated_response(serializer.data).data,
                                   status=status_code.HTTP_200_OK)
        serializer = self.action_serializers.get(self.action)(domains, many=True)
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def create(self, request):
        """
            post method used to add domain.
        :param request:
        :return: response
        """
        serializer = self.action_serializers.get(self.action)(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return SuccessResponse(serializer.data, status=status_code.HTTP_200_OK)

    def update(self, request):
        """
        update method used to delete domain.
            :param request:
            :return: response
        """
        domain_id = request.data.get('domain_id')
        Domain.objects.filter(id=domain_id).update(is_deleted=True)
        return SuccessResponse({"message": success_message.get('DOMAIN_DELETED')},
                               status=status_code.HTTP_200_OK)

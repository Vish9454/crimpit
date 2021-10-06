from django.db.models import Q
from rest_framework.permissions import BasePermission
from accounts.models import Role
from core.exception import CustomException
from core.messages import variables, validation_message
from rest_framework.authtoken.models import Token


class CheckUserRoleStatusPermission(BasePermission):
    """
        CheckUserRoleStatusPermission class used to check User Role Status Is active or not.
    """
    message = variables.get("PERMISSION_MESSAGE")

    def has_permission(self, request, view):
        role_exist = Role.objects.filter((Q(name=Role.RoleType.CLIMBER) | Q(name=Role.RoleType.GYM_STAFF)),
                                         user=request.user, role_status=True).exists()
        if role_exist:
            return True
        return False


class AppClimberPermission(BasePermission):
    """
        AppClimberPermission class used to check the requested data is climber user.
    """
    message = variables.get("PERMISSION_MESSAGE")

    def has_permission(self, request, view):
        if Role.objects.filter(user__email=request.user.email, name=Role.RoleType.CLIMBER,
                               role_status=True).exists():
            return True
        return False


class AppStaffPermission(BasePermission):
    """
        AppStaffPermission class used to check the requested data is gym-staff user.
    """
    # message = variables.get("PERMISSION_MESSAGE")
    message = variables.get("STAFF_PERMISSION_MESSAGE")

    def has_permission(self, request, view):
        if Role.objects.filter(user__email=request.user.email, name=Role.RoleType.GYM_STAFF,
                               role_status=True).exists():
            return True
        return False


class CheckRestaurantRoleStatusPermission(BasePermission):
    """
        CheckRestaurantRoleStatusPermission class used to check Restaurant Role Status Is active or not.
    """
    message = "Permission is allowed only to restaurant user."

    def has_permission(self, request, view):
        if Role.objects.filter(user=request.user, name=Role.RoleType.RESTAURANT_USER,
                               role_status=True).exists():
            return True
        return False


class CheckRestaurantEmployeeRoleStatusPermission(BasePermission):
    """
        CheckRestaurantEmployeeRoleStatusPermission class used to check Restaurant Employee Role Status Is active or not.
    """
    message = "Permission is allowed only to restaurant employee user."

    def has_permission(self, request, view):
        if Role.objects.filter(user=request.user, name=Role.RoleType.EMPLOYEE_USER,
                               role_status=True).exists():
            return True
        return False


class CheckAdminRoleStatusPermission(BasePermission):
    """
        CheckAdminRoleStatusPermission class used to check Admin Role Status Is active or not.
    """
    message = "Permission is allowed only to admin user."

    def has_permission(self, request, view):
        if Role.objects.filter(user=request.user, name=Role.RoleType.ADMIN_USER,
                               role_status=True).exists():
            return True
        return False


class UserEmailVerifiedPermission(BasePermission):
    """
        UserEmailVerifiedPermission class used to check user email is verified or not.
    """
    message = "User email is not verified."

    def has_permission(self, request, view):
        if request.user.is_email_verified:
            return True
        return False


# class IsGymOwner(BasePermission):
#     """
#         Gym owner permission class
#     """
#     message = variables.get("PERMISSION_MESSAGE")
#
#     def has_permission(self, request, view):
#         try:
#             # token = request.META.get('HTTP_AUTHORIZATION')
#             # word, token = token.split(" ")
#             # token_obj = Token.objects.filter(key=token).first()
#             if Role.objects.filter(user__email=request.user.email,name=Role.RoleType.GYM_OWNER,
#                                    role_status=True).exists():
#                 return True
#             else:
#                 return False
#         except Exception:
#             return False


class IsGymOwner(BasePermission):
    """
        Gym owner permission class
    """
    message = variables.get("PERMISSION_MESSAGE")

    def has_permission(self, request, view):
        try:
            # token = request.META.get('HTTP_AUTHORIZATION')
            # word, token = token.split(" ")
            # token_obj = Token.objects.filter(key=token).first()
            # if Role.objects.filter(user__email=request.user.email,name=Role.RoleType.GYM_OWNER,
            #                        role_status=True).exists():
            if Role.objects.filter(user__email=request.user.email.lower(),
                                   name__in=[Role.RoleType.GYM_OWNER, Role.RoleType.GYM_STAFF],
                                   role_status=True).exists():
                return True
            else:
                return False
        except Exception:
            return False


class IsSubscribedAnnouncement(BasePermission):
    """ permission class for user to check subscription"""
    message = ''

    def has_permission(self, request, view):
        # """
        data = request.user.user_subscription
        if data.is_subscribed and data.plan:
            if data.plan.announcements_create:
                return True
            else:
                # self.message = validation_message.get("UPGRADE_YOUR_PLAN")
                message = validation_message.get("UPGRADE_YOUR_PLAN")
        else:
            # self.message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
            message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
        raise CustomException(status_code=400, message=message, location=validation_message.get("LOCATION"))
        # return False
    # """
    #     return True


class IsSubscribedUserProfile(BasePermission):
    """ permission class for user to check subscription"""
    message = ''

    def has_permission(self, request, view):
        """
        kwargs_data = request.__dict__['parser_context']['kwargs']
        data = request.user.user_subscription
        if kwargs_data:
            if data.is_subscribed:
                if data.plan.access_to_biometric_data and data.plan.access_to_sign_up_info:
                    return True
                else:
                    self.message = validation_message.get("UPGRADE_YOUR_PLAN")
            else:
                self.message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
            return False
        else:
            # Check access to feedback
            return True
            # if data.is_subscribed:
            #     if data.plan.access_to_biometric_data and data.plan.access_to_sign_up_info:
            #         return True
            #     else:
            #         self.message = validation_message.get("UPGRADE_YOUR_PLAN")
            # else:
            #     self.message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
            # return False

    """
        return True

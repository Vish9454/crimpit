"""
    file contains project level methods
"""
import os
import secrets
import uuid
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
import random
import sendgrid
from math import ceil
from multiprocessing import Process

from django.contrib.gis.geos import Point
from django.db.models import Count, Max, Sum, Q, ExpressionWrapper, Func
from django.template.loader import render_to_string
from django.utils import timezone
from fcm_django.models import FCMDevice
from python_http_client import HTTPError
from rest_framework.authtoken.models import Token
from sendgrid.helpers.mail import Content, Email, Mail, To

from accounts.models import AccountVerification, Role, UserDetails, UserPreference, UserRouteFeedback, WallVisit, User, \
    UserDetailPercentage, UserSubscription, GymVisit, UserBiometricData
from config.local import (FROM_EMAIL, SEND_GRID_API_KEY, emailverification_url, ADMIN_MAIL)
from core.exception import CustomException
from core.messages import validation_message, success_message
from core.messages import variables
from rest_framework import serializers
from gyms.models import GradeType, Announcement, GymDetails, WallType, ColorType, RouteType
from rest_framework.response import Response
from core.exception import get_custom_error, CustomException
from rest_framework import status as status_code
from gyms.models import WallRoute
from django.db.models import Count, Avg, Max, DecimalField, FloatField, F
from django.db.models.functions import Cast
from gyms.models import GymLayout,LayoutSection,SectionWall

import logging
log = logging.getLogger(__name__)


def get_the_week_day_mapping(week_day_name):
    """
        method used to get the week day number
    :param week_day_name:
    :return:
    """
    mapping = {
        'MONDAY': 1,
        'TUESDAY': 2,
        'WEDNESDAY': 3,
        'THURSDAY': 4,
        'FRIDAY': 5,
        'SATURDAY': 6,
        'SUNDAY': 7
    }
    return mapping[week_day_name]


def get_date_object_from_date(date):
    date_obj = datetime.strptime(date, "%d-%m-%Y")
    return date_obj


def get_date_object_from_date_updated(date):
    date_obj = datetime.strptime(date, variables.get("TIME_FORMAT"))
    return date_obj


def get_week_day_name_from_date_updated(date=None):
    if date is None:
        week_day_name = datetime.today().strftime('%A').upper()
    else:
        week_day_name = get_date_object_from_date_updated(date).strftime('%A').upper()
    # get the week day number from the week_day_name
    return get_the_week_day_mapping(week_day_name)


def get_current_date_time_object():
    """
        method used to get the current date time objects.
    :return: current_date_time_object
    """
    current_date_time_object = timezone.now()
    return current_date_time_object


def create_random_number():
    """
        method used to create random number.
    :return:
    """

    random_number = 1234  # secrets.choice(range(1000, 9999))
    return random_number


def save_user_coordinate(instance, latitude, longitude) -> object:
    """
        method used to save the user coordinates
    :param instance:
    :param latitude:
    :param longitude:
    :return:
    """
    point = Point(x=longitude, y=latitude, srid=4326)
    instance.coordinate = point
    return instance


def get_latitude_from_obj(instance):
    """
        method used to get the latitude of the address
    :param instance:
    :return:
    """
    try:
        latitude = instance.geo_point.y
    except Exception:
        latitude = 0
    return latitude


def get_longitude_from_obj(instance):
    """
        method used to get the longitude of the address
    :param instance:
    :return:
    """
    try:
        longitude = instance.geo_point.x
    except Exception:
        longitude = 0
    return longitude


def get_or_create_user_token(instance):
    """
        method used to create the user toke
    :param instance:
    :return: token key
    """
    try:
        token, created = Token.objects.get_or_create(user=instance)
    except Exception as e:
        print(e)
    return token.key


def update_or_create_fcm_detail(user, registration_id, device_type):
    """
        method used to save the fcm device token details
    :param user:
    :param device_type:
    :param registration_id:
    :return:
    """
    # FCMDevice.objects.update_or_create(user=user, type=device_type, defaults={
    #     "registration_id": registration_id,
    #     "active": True
    # })
    # To delete all previous registered fcm token for this user
    FCMDevice.objects.filter(user=user, type=device_type).delete()
    FCMDevice.objects.update_or_create(registration_id=registration_id, type=device_type, defaults={
        "user": user,
        "active": True
    })
    return True


def send_plain_mail_to_single_user(subject, email, message):
    """
            method used to send the token to email for email verification
        :param subject:
        :param email:
        :param message:
        :return:
        """
    email_body = message
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    to_email = To(email)
    mail_subject = subject
    content = Content(variables.get("PLAIN_EMAIL_CONTENT_TYPE"), email_body)
    mail = Mail(from_email, to_email, mail_subject, content)
    try:
        send_grid.client.mail.send.post(request_body=mail.get())
    except Exception:
        print(validation_message.get("ERROR_IN_SENDING_MAIL"))
    return True


def send_plain_mail_to_multiple_user(subject, email_list, message):
    """
        method used to send the restaurant employee credentials to email.
        :param subject:
        :param email_list:
        :param message:
        :return:
        """
    email_body = message
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    to_list = sendgrid.Personalization()
    for each in email_list:
        to_list.add_to(To(each))
    mail_subject = subject
    content = Content(variables.get("PLAIN_EMAIL_CONTENT_TYPE"), email_body)
    mail = Mail(from_email, None, mail_subject, content)
    mail.add_personalization(to_list)
    try:
        send_grid.client.mail.send.post(request_body=mail.get())
    except Exception:
        print(validation_message.get("ERROR_IN_SENDING_MAIL"))
    return True


def send_html_mail_to_single_user(subject, email, html_template, ctx_dict):
    """
        method used to send the restaurant employee credentials to email.
        :param subject:
        :param email:
        :param html_template:
        :param ctxt_dict:
        :return:
        """
    email_body = render_to_string(html_template, ctx_dict)
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    to_email = To(email)
    mail_subject = subject
    content = Content(variables.get("HTML_EMAIL_CONTENT_TYPE"), email_body)
    mail = Mail(from_email, to_email, mail_subject, content)
    try:
        send_grid.client.mail.send.post(request_body=mail.get())
        print("success")
    except Exception:
        print(validation_message.get("ERROR_IN_SENDING_MAIL"))
    return True


def send_html_mail_to_multiple_user(subject, email_list, html_template, ctx_dict):
    """
        method used to send the restaurant employee credentials to email.
        :param subject:
        :param email_list:
        :param html_template:
        :param ctxt_dict:
        :return:
        """
    """
    email_body = render_to_string(html_template, ctx_dict)
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    to_list = sendgrid.Personalization()
    for each in email_list:
        to_list.add_to(To(each))
    mail_subject = subject
    content = Content(variables.get("HTML_EMAIL_CONTENT_TYPE"), email_body)
    mail = Mail(from_email, None, mail_subject, content)
    mail.add_personalization(to_list)
    try:
        send_grid.client.mail.send.post(request_body=mail.get())
    except Exception:
        print(validation_message.get("ERROR_IN_SENDING_MAIL"))
    return True
    """
    email_body = render_to_string(html_template, ctx_dict)
    send_grid = sendgrid.SendGridAPIClient(api_key=SEND_GRID_API_KEY)
    from_email = Email(FROM_EMAIL)
    # To send bulk email in small pieces of 50
    size_limit = 50
    loop_size = ceil(len(email_list) / size_limit)
    for i in range(loop_size):
        to_list = sendgrid.Personalization()
        min_val = i * size_limit
        max_val = (i * size_limit) + size_limit
        for each in email_list[min_val:max_val]:
            to_list.add_to(To(each))
        mail_subject = subject
        content = Content(variables.get("HTML_EMAIL_CONTENT_TYPE"), email_body)
        mail = Mail(from_email, None, mail_subject, content)
        mail.add_personalization(to_list)
        try:
            send_grid.client.mail.send.post(request_body=mail.get())
        except HTTPError as e:
            print(e.to_dict)
            log.info(e.to_dict)
            log.info(validation_message.get("ERROR_IN_SENDING_MAIL"))
            print(validation_message.get("ERROR_IN_SENDING_MAIL"))
    return True


def create_user_role(instance, role_type):
    """
        method used to the user role
    :param instance:
    :param role_type:
    :return:
    """
    Role.objects.get_or_create(user=instance, name=role_type)
    # Change to make deleted user True
    # Role.objects.create(user=instance, name=role_type)
    return True


def create_user_staff_role(instance, role_type):
    """
        method used to the user staff role
    :param instance:
    :param role_type:
    :return:
    """
    role_instance, created = Role.objects.get_or_create(user=instance, name=role_type)
    if not created:
        role_instance.role_status = True
        role_instance.save()
    return True


def check_file_size(file_obj):
    try:
        file_obj_size = file_obj.size
        file_in_mb = file_obj_size / 1000000
        # if file_in_mb <= 2:
        if file_in_mb <= 10:
            return True
        return False
    except Exception:
        return False


def generate_verification_token(instance, verification_type):
    """
        method used to generate the verification type
    :param instance:
    :param verification_type:
    :return:
    """
    # create random number of 6 digit
    token = uuid.uuid4().hex
    user_token = AccountVerification.objects.filter(user=instance.id,
                                                    verification_type=verification_type).only('id').first()
    if user_token:
        user_token.delete()
    token_expired_at = timezone.now() + timedelta(hours=variables.get('OTP_EXPIRATION_TIME'))
    user_token = AccountVerification.objects.create(token=token, verification_type=verification_type,
                                                    user=instance, expired_at=token_expired_at)
    return user_token


def generate_admin_verification_token(instance, verification_type):
    """
        method used to generate the verification type for the restaurant
    :param instance:
    :param verification_type:
    :return:
    """
    # create random number of 6 digit
    token = str(uuid.uuid4())
    user_token = AccountVerification.objects.filter(user=instance.id,
                                                    verification_type=verification_type).only('id').first()
    if user_token:
        user_token.delete()
    token_expired_at = timezone.now() + timedelta(minutes=variables.get('OTP_EXPIRATION_TIME'))
    user_token = AccountVerification.objects.create(token=token,
                                                    verification_type=verification_type,
                                                    user=instance,
                                                    expired_at=token_expired_at)
    return user_token


def generate_restaurant_verification_token(instance, verification_type):
    """
        method used to generate the verification type for the restaurant
    :param instance:
    :param verification_type:
    :return:
    """
    # create random number of 6 digit
    token = str(uuid.uuid4())
    user_token = AccountVerification.objects.filter(user=instance.id,
                                                    verification_type=verification_type).only('id').first()
    if user_token:
        user_token.delete()
    token_expired_at = timezone.now() + timedelta(minutes=variables.get('OTP_EXPIRATION_TIME'))
    user_token = AccountVerification.objects.create(token=token,
                                                    verification_type=verification_type,
                                                    user=instance,
                                                    expired_at=token_expired_at)
    return user_token


def send_notification_bulk(user_ids, title, message, data):
    try:
        devices = FCMDevice.objects.select_related('user').filter(user__in=user_ids, active=True)
        result = devices.send_message(title=title, body=message, data=data, sound=True)
        return result
    except Exception:
        pass
    return True


def send_notification_to_gym_staff(users, title, message, data):
    """
        method used to send notification to staff.
    :param users:
    :param title:
    :param message:
    :param data:
    :return:
    """
    try:
        send_notification_bulk(users, title=title, message=message, data=data)
    except Exception:
        print('Send notification exception.')
    return True


def create_user_details_instance(instance, user_role_check):
    """
        method used to create used details instance.
    :param instance:
    :return:
    """
    try:
        user_detail_instance, created = UserDetails.objects.get_or_create(user=instance)
        if user_role_check.first().name == Role.RoleType.CLIMBER:
            user_detail_instance.login_count = user_detail_instance.login_count + 1
            user_detail_instance.save()
    except Exception:
        pass
    return True


def send_verification_link_to_email(email, verification_link):
    """
        method used to send email verification link to email.
    :param email:
    :param verification_link:
    :return:
    """
    subject = 'Email Verification'
    html_template = 'verify_mail.html'
    ctx_dict = {'email': email, 'verification_link': verification_link}
    send_html_mail_to_single_user(subject, email, html_template, ctx_dict)


def send_forgot_password_link_to_email(email, forgot_password_link):
    """
        method used to send forgot password link to email.
    :param email:
    :param verification_link:
    :return:
    """
    subject = 'Forgot Password'
    html_template = 'forgot_password.html'
    ctx_dict = {'email': email, 'forgot_password_link': forgot_password_link}
    send_html_mail_to_single_user(subject, email, html_template, ctx_dict)


def resend_email_verify_link(instance):
    """
        method used to send forgot password link to email.
    :param instance:
    :return:
    """
    verification_token = generate_verification_token(instance, AccountVerification.VerificationType.
                                                     EMAIL_VERIFICATION)
    email_verification_url = emailverification_url + verification_token.token + "/"
    # send verification token to email
    p = Process(target=send_verification_link_to_email,
                args=(instance.email, email_verification_url,))
    p.start()
    return True


def send_not_found_gym_to_admin(data):
    """
        method used to send not found gym detail to admin.
    :param data:
    :return:
    """
    subject = 'Gym Not Found'
    email = ADMIN_MAIL
    html_template = 'gym_not_found.html'
    ctx_dict = {'email': data['email'], 'gym_name': data['gym_name'], 'gym_location': data['gym_location']}
    p = Process(target=send_html_mail_to_single_user,
                args=(subject, email, html_template, ctx_dict,))
    p.start()
    return True


def create_user_preference(instance):
    """
        method used to send forgot password link to email.
    :param instance:
    :return:
    """
    try:
        user_preference = UserPreference.objects.filter(user=instance)
        if user_preference:
            user_preference.delete()
        UserPreference.objects.create(user=instance)
    except Exception:
        pass
    return True


def get_is_selected_floor(dict_val, floor_id):
    """
        method used to check which floor is selected at gym detail.
    :param dict_val:
    :param floor_id:
    :return:
    """
    try:
        for each in dict_val:
            if each['id'] == int(floor_id):
                each.update({'is_selected': True})
            else:
                each.update({'is_selected': False})
    except Exception:
        for each in dict_val:
            each.update({'is_selected': False})
    return dict_val


def delete_staff_role_for_user(instance):
    """
        method used to delete staff role of user if have.
    :param instance:
    :return:
    """
    try:
        user_role = instance.user_role.filter(name=Role.RoleType.GYM_STAFF, role_status=True)
        if user_role.exists():
            user_role.update(role_status=False)
    except Exception as e:
        print(e)
        pass
    return True


def get_basic_percentage(instance, percentage_data):
    """
        method used to get percentage from basic data.
    :param instance:
    :param percentage_data:
    :return:
    """
    try:
        total_count, data_count = 4, 0
        if instance.user_details.user_avatar:
            data_count += 1
        if instance.full_name:
            data_count += 1
        if instance.email:
            data_count += 1
        # if instance.phone_number:
        #     data_count += 1
        if instance.user_preference.prefer_climbing in [0, 1, 2]:
            data_count += 1
        calculate_per = (data_count / total_count) * 100
        percentage_data.basic_detail = calculate_per
        percentage_data.save()
    except Exception:
        pass
    return percentage_data


def get_climbing_percentage(preference_instance, validated_data=None):
    """
        method used to get percentage from climbing info.
    :param preference_instance:
    :param validated_data:
    :return:
    """
    try:
        total_count, data_count = 7, 5
        if validated_data:
            # if validated_data['strength']:
            if validated_data['strength_hold'] or validated_data['strength_move']:
                data_count += 1
            if validated_data['weakness_hold'] or validated_data['weakness_move']:
                data_count += 1
            calculate_per = (data_count / total_count) * 100

            # user_detail_percentage
            UserDetailPercentage.objects.filter(user=preference_instance.user).update(climbing_detail=calculate_per)
        else:
            climbing_instance = preference_instance.user.user_details
            # if climbing_instance.strength:
            if climbing_instance.strength_hold or climbing_instance.strength_move:
                data_count += 1
            if climbing_instance.weakness_hold or climbing_instance.weakness_move:
                data_count += 1
            calculate_per = (data_count / total_count) * 100

            # user_detail_percentage
            UserDetailPercentage.objects.update_or_create(user=preference_instance.user,
                                                          defaults={'climbing_detail': calculate_per})
    except Exception:
        pass
    return True


def get_biometric_percentage(data):
    """
        method used to get percentage from biometric data.
    :param data:
    :return:
    """
    try:
        user_id = data.pop('user') if 'user' in data else ''
        total_count, data_count = 0, 0
        for each in data:
            if (each == 'gender' and data[each] != 0) or data[each]:
                data_count += 1
            elif data[each]:
                data_count += 1
            total_count += 1
        calculate_per = (data_count / total_count) * 100
        data['user'] = user_id
        return calculate_per
    except Exception:
        return 0


def get_sequence_data(query_data):
    """
        method used to get sequence data.
    :param query_data:
    :return:
    """
    grade_count1, grade_count2, grade_count3 = 0, 0, 0
    try:
        emp_dict = [{'grade': 0, 'grade_count': 0},
                    {'grade': 1, 'grade_count': 0},
                    {'grade': 2, 'grade_count': 0}]
        for ind, each in enumerate(query_data):
            if each['grade'] == 0:
                emp_dict[0]['grade_count'] = each['grade_count']
            elif each['grade'] == 1:
                emp_dict[1]['grade_count'] = each['grade_count']
            elif each['grade'] == 2:
                emp_dict[2]['grade_count'] = each['grade_count']
        grade_count1 = emp_dict[0]['grade_count']
        grade_count2 = emp_dict[1]['grade_count']
        grade_count3 = emp_dict[2]['grade_count']
    except Exception:
        pass
    return grade_count1, grade_count2, grade_count3


def get_percentage_from_grade_count(grade_count_list):
    """
        method used to get percentage from grade count.
    :param grade_count_list:
    :return:
    """
    try:
        total_sum = sum(grade_count_list)
        data_dict = dict()
        negative = round((grade_count_list[0] / total_sum) * 100, 2)
        normal = round((grade_count_list[1] / total_sum) * 100, 2)
        positive = round((grade_count_list[2] / total_sum) * 100, 2)
        data_dict['NEGATIVE'] = negative
        data_dict['NORMAL'] = normal
        data_dict['POSITIVE'] = positive
    except Exception:
        data_dict = {}
    return data_dict


def get_round_completed_data(obj, visit_instance):
    """
        method used to get round completed details.
    :param obj:
    :param visit_instance:
    :return:
    """
    round_attempted_count = User.all_delete_objects.filter(
        user_route_feedback__route__section_wall=obj, user_route_feedback__route_progress=0).distinct().count()
    round_completed_count = User.all_delete_objects.filter(
        user_route_feedback__route__section_wall=obj, user_route_feedback__route_progress__in=[1, 2, 3]). \
        distinct().count()
    wall_popularity_count = round_attempted_count + round_completed_count

    if visit_instance:
        # wall_visit_count = visit_instance.user.all().only('id').count()
        wall_visit_count = WallVisit.objects.filter(wall=obj).only('id').count()
    else:
        wall_visit_count = 0
    data = {
        'round_attempted': round_attempted_count,
        'round_completed': round_completed_count,
        'wall_popularity': wall_popularity_count,
        'wall_visit': wall_visit_count
    }
    return data


def check_event_delete_or_pass_status(event_detail):
    """
        method used to check event deactivated or deleted or has been passed.
    :param event_detail:
    :return:
    """
    if not event_detail:
        return False, validation_message.get('EVENT_NOT_FOUND')
    today_date_time = datetime.now(timezone.utc)
    bool_val = event_detail.start_date >= today_date_time
    if not bool_val:
        return False, validation_message.get('EVENT_HAS_BEEN_PASSED')
    return True, 'Success'


def modify_data_group_by_wall(data):
    try:
        main_dict = dict()
        for each in data:
            route_data_dict = {
                "id": each['id'],
                "name": each['name'],
                "grade": each['grade'],
                "color": each['color']
            }
            wall_id = each['section_wall']['id']
            if wall_id not in main_dict.keys():
                main_dict[wall_id] = {
                    'wall_name': each['section_wall']['name'],
                    'route_list': [route_data_dict]
                }
            else:
                main_dict[wall_id]['route_list'].append(route_data_dict)
    except Exception:
        main_dict = {}
    return main_dict


def update_route_category_data(serialized_data, user):
    try:
        for each in serialized_data:
            each['route_save_list'] = [j for j in each['route_save_list'] if j['user'] == user.id
                                       and not j['list_category_is_deleted']]
            # for i, j in enumerate(each['route_save_list']):
            #     if j['user'] != user.id:
            #         del each['route_save_list'][i]
    except Exception:
        pass
    return serialized_data


def active_delete_announcement(announcement_detail, option_val):
    # is_active, is_deleted = True, False
    msg = "Please enter valid option value."
    if option_val == 0:
        is_active, is_deleted = False, False
        msg = success_message.get('ANNOUNCEMENT_DEACTIVATED_SUCCESSFULLY')
    elif option_val == 1:
        is_active, is_deleted = True, False
        msg = success_message.get('ANNOUNCEMENT_ACTIVATED_SUCCESSFULLY')
    elif option_val == 2:
        is_active, is_deleted = True, True
        msg = success_message.get('ANNOUNCEMENT_DELETED_SUCCESSFULLY')
    try:
        announcement_detail.update(is_active=is_active, is_deleted=is_deleted)
    except Exception:
        pass
    return msg


def active_delete_event(event_detail, option_val):
    msg = "Please enter valid option value."
    if option_val == 0:
        is_active, is_deleted = False, False
        msg = success_message.get('EVENT_DEACTIVATED_SUCCESSFULLY')
    elif option_val == 1:
        is_active, is_deleted = True, False
        msg = success_message.get('EVENT_ACTIVATED_SUCCESSFULLY')
    elif option_val == 2:
        is_active, is_deleted = True, True
        msg = success_message.get('EVENT_DELETED_SUCCESSFULLY')
    try:
        event_detail.update(is_active=is_active, is_deleted=is_deleted)
    except Exception:
        pass
    return msg


def grade_listing_conditions(request):
    grading_system = int(request.query_params.get('grading_system'))
    sub_category = int(request.query_params.get('sub_category'))
    r = GradeType.ClimbingType.ROPE_CLIMBING
    b = GradeType.ClimbingType.BOULDERING
    # 0 and 1
    if grading_system == r and sub_category == GradeType.SubCategoryType.YDSSCALE:
        grade_obj = GradeType.objects.filter(grading_system=r, sub_category=GradeType.SubCategoryType.YDSSCALE
                                             ).all().order_by('created_at')
    # 0 and 2
    elif grading_system == r and sub_category == GradeType.SubCategoryType.FRANCIA:
        grade_obj = GradeType.objects.filter(grading_system=r, sub_category=GradeType.SubCategoryType.FRANCIA
                                             ).all().order_by('created_at')
    # 1 and 10
    elif grading_system == b and sub_category == GradeType.SubCategoryType.V_SYSTEM:
        grade_obj = GradeType.objects.filter(grading_system=b, sub_category=GradeType.SubCategoryType.V_SYSTEM
                                             ).all().order_by('created_at')
    # 1 and 11
    elif grading_system == b and sub_category == GradeType.SubCategoryType.FONTAINEBLEAU:
        grade_obj = GradeType.objects.filter(grading_system=b, sub_category=GradeType.SubCategoryType.FONTAINEBLEAU
                                             ).all().order_by('created_at')
    else:
        raise CustomException(message=validation_message.get("WRONG_COMBINATION"),
                              location='wallroute', status_code=400)
    return grade_obj


def map_with_category(gym_layout_category):
    """
        method used to map category with it's name.
    :param event_detail:
    :return:
    """
    emp_li = list()
    if gym_layout_category:
        for each in gym_layout_category:
            if each['category'] == 0 and each['gym__RopeClimbing']:
                emp_li.append({'id': 0, 'title': 'Rope Climbing'})
            elif each['category'] == 1 and each['gym__Bouldering']:
                emp_li.append({'id': 1, 'title': 'Bouldering'})
    return emp_li


def update_announcement_priority(announcement_objs, priority):
    """
        method used to update announcement priority.
    :param announcement_objs:
    :param priority:
    :return:
    """
    user_bulk_update_list = list()
    for i, j in zip(announcement_objs, priority):
        i.priority = j
        user_bulk_update_list.append(i)
    Announcement.objects.bulk_update(user_bulk_update_list, ['priority'])
    return True


def manage_announcement_list_filter(gym_id, filter_by):
    """
        method used to manage announcement list filter.
    :param gym_id:
    :param filter_by:
    :return:
    """
    bool_val = True
    if not filter_by or int(filter_by) == 0:
        announcements_1 = Announcement.objects.select_related('template').filter(gym=gym_id). \
            order_by('-is_active', '-priority')
        announcements_2 = Announcement.all_objects.select_related('template').filter(gym=gym_id, is_active=False). \
            order_by('-is_active', '-priority')
        priority = list(announcements_1.values_list('priority', flat=True)) + list(
            announcements_2.values_list('priority', flat=True))
    elif int(filter_by) == 1:
        announcements_1 = Announcement.objects.select_related('template').filter(gym=gym_id). \
            order_by('-priority')
        announcements_2 = []
        priority = list(announcements_1.values_list('priority', flat=True)) + announcements_2
    elif int(filter_by) == 2:
        announcements_1 = []
        announcements_2 = Announcement.all_objects.select_related('template').filter(
            gym=gym_id, is_active=False).order_by('-priority')
        priority = announcements_1 + list(announcements_2.values_list('priority', flat=True))
    else:
        bool_val = False
        announcements_1 = []
        announcements_2 = []
        priority = []
    return bool_val, announcements_1, announcements_2, priority


def serialize_all_data(serializer_name, announcements_1, announcements_2, priority):
    """
        method used to serialize all data.
    :param serializer_name:
    :param announcements_1:
    :param announcements_2:
    :param priority:
    :return:
    """
    serializer_1 = serializer_name(announcements_1, many=True)
    serializer_2 = serializer_name(announcements_2, many=True)
    serialize_data_1 = {"active_announcement": serializer_1.data, "inactive_announcement": serializer_2.data}
    serialize_data_final = {"announcement_data": serialize_data_1, "priority_data": priority}
    return serialize_data_final


def specific_route_details(route_id, route_obj):
    class Round(Func):
        function = 'ROUND'
        arity = 2

    route_details_obj = route_obj.values('id', 'name', 'color__name', 'color__hex_value', 'grade__sub_category_value',
                                         'created_at', 'created_by__full_name', 'created_by__gym_detail_user__gym_name',
                                         "section_wall__image", "section_wall__name",
                                         ).annotate(avg_rating=Round(Avg('route_feedback__rating', filter=~Q(
                                                                             route_feedback__route_progress=UserRouteFeedback.RouteProgressType.PROJECTING)), 1),
                                                    count_climbers=Count('route_feedback__user', distinct=True,
                                                                         filter=~Q(
                                                                             route_feedback__route_progress=UserRouteFeedback.RouteProgressType.PROJECTING)
                                                    # count_climbers=Count('route_feedback__rating'
                                                                         )).first()
    return route_details_obj


def route_progress_details(route_id, route_obj, count_of_objects):
    count_of_objects_unique = count_of_objects.values_list('user_id', flat=True).distinct().count()
    # count_of_objects = count_of_objects.count()
    try:
        update_data = route_obj.values(
            "route_feedback__route_progress"
        ).annotate(users_count=Count("route_feedback__user", distinct=True))
        sum_data = sum(each['users_count'] for each in update_data)
        if sum_data != 0:
        # if count_of_objects != 0:
            feedback_objs =route_obj.values(
                "route_feedback__route_progress"
            ).annotate(users_count=Count("route_feedback__user", distinct=True),
                       percentage=Cast(Count("route_feedback__user", distinct=True
                                             ) * 100, FloatField(),
                                       ) / sum_data
                       ).all()
                       # users_count = Count("route_feedback__route_progress"),
                       # percentage=Cast(Count("route_feedback__route_progress",
                       #                       ) * 100, FloatField(),
                       #                 ) / count_of_objects
                       # ).all()
        else:
            feedback_objs = [
                {
                    "route_feedback__route_progress": None,
                    "users_count": 0,
                    "percentage": 0
                }
                ]
    except Exception as e:
        print(e)
        feedback_objs = [
            {
                "route_feedback__route_progress": None,
                "users_count": 0,
                "percentage": 0
            }
        ]
    return feedback_objs, count_of_objects_unique
    # return feedback_objs, count_of_objects


def community_grade_route_details(route_id, route_obj, count_of_objects):
    count_of_objects_unique = count_of_objects.values_list('user_id', flat=True).distinct().count()
    # count_of_objects = count_of_objects.count()
    try:
        update_data = route_obj.filter(route_feedback__grade__isnull=False).values(
            "route_feedback__grade",
        ).annotate(users_count=Count("route_feedback__user", distinct=True))
        sum_data = sum(each['users_count'] for each in update_data)
        # if count_of_objects != 0:
        if sum_data != 0:
            # feedback_objs = route_obj.values(
            feedback_objs = route_obj.filter(route_feedback__grade__isnull=False).values(
                "route_feedback__grade",
            ).annotate(users_count=Count("route_feedback__user", distinct=True),
                       percentage=Cast(Count("route_feedback__user", distinct=True
                                             ) * 100, FloatField(),
                                       ) / sum_data
                       ).all()
            # users_count = Count("route_feedback__grade"),
            # percentage = Cast(Count("route_feedback__grade"
            #                         ) * 100, FloatField(),
            #                   ) / count_of_objects
            # ).all()
        else:
            feedback_objs = [
                {
                    "route_feedback__grade": None,
                    "users_count": 0,
                    "percentage": 0
                }]
    except Exception as e:
        print(e)
        feedback_objs = [
                {
                    "route_feedback__grade": None,
                    "users_count": 0,
                    "percentage": 0
                }]
    return feedback_objs, count_of_objects_unique, route_obj.first().grade.sub_category_value
    # return feedback_objs, count_of_objects, route_obj.first().grade.sub_category_value

def rating_range_output(rating,queryset):
    if int(rating) == 1:
        queryset = queryset.filter(avg_rating__lte=1)
    if int(rating) == 2:
        queryset = queryset.filter(avg_rating__gt=1,avg_rating__lte=2)
    if int(rating) == 3:
        queryset = queryset.filter(avg_rating__gt=2,avg_rating__lte=3)
    if int(rating) == 4:
        queryset = queryset.filter(avg_rating__gt=3,avg_rating__lte=4)
    if int(rating) == 5:
        queryset = queryset.filter(avg_rating__gt=4,avg_rating__lte=5)
    return queryset

def validation_route_tag_list(layout_ids=None, section_ids=None, wall_ids=None, category=None,
                              type_r_b=None, grade=None, created_by=None, queryset=None):
    if layout_ids:
        # gym_wall_ids = SectionWall.objects.filter(gym_layout_id__in=eval(layout_ids))
        gym_wall_ids = SectionWall.objects.filter(gym_layout_id__in=layout_ids)
        queryset = queryset.filter(section_wall_id__in=gym_wall_ids.values_list(
            'id', flat="True"))
    if section_ids:
        # gym_section_ids = LayoutSection.objects.filter(id__in=eval(section_ids))
        gym_section_ids = LayoutSection.objects.filter(id__in=section_ids)
        gym_wall_ids = SectionWall.objects.filter(layout_section__in=gym_section_ids.values_list(
            'id', flat="True"))
        queryset = queryset.filter(section_wall_id__in=gym_wall_ids.values_list(
            'id', flat="True"))
    if wall_ids:
        # gym_wall_ids = SectionWall.objects.filter(id__in=eval(wall_ids))
        gym_wall_ids = SectionWall.objects.filter(id__in=wall_ids)
        queryset = queryset.filter(section_wall_id__in=gym_wall_ids.values_list(
            'id', flat="True"))
    if category:
        # queryset = queryset.filter(section_wall__layout_section__gym_layout__category__in=eval(category))
        queryset = queryset.filter(section_wall__layout_section__gym_layout__category__in=category)
    if type_r_b:
        # queryset = queryset.filter(route_type__in=eval(type_r_b))
        queryset = queryset.filter(route_type__in=type_r_b)
    if grade:
        # queryset = queryset.filter(grade__sub_category__in=eval(grade))
        queryset = queryset.filter(grade__sub_category__in=grade)
    if created_by:
        # queryset = queryset.filter(created_by__id__in=eval(created_by))
        queryset = queryset.filter(created_by__id__in=created_by)
    return queryset


def compare_updated_at(serialized_data, ordering):
    """
        method used to compare updated_at date.
    :param serialized_data:
    :param ordering:
    :return:
    """
    for index, each in enumerate(serialized_data):
        date1 = each['updated_at']
        date2 = each['user_details']['updated_at']
        try:
            date3 = each['user_biometric']['updated_at']
        except Exception:
            date3 = "0000-00-00T00:00:00Z"
        date4 = each['user_preference']['updated_at']
        final_date = max(date1, date2, date3, date4)
        serialized_data[index]['updated_at'] = final_date
    order_serialized_data = serialized_data
    if ordering in ['submitted', '-submitted']:
        data = 'submitted_route'
        if '-' in ordering:
            reverse = True
        else:
            reverse = False
        order_serialized_data = sorted(serialized_data, reverse=reverse, key=lambda x: x[data])
    elif ordering in ['last_updated', '-last_updated']:
        data = 'updated_at'
        if '-' in ordering:
            reverse = True
        else:
            reverse = False
        order_serialized_data = sorted(serialized_data, reverse=reverse, key=lambda x: x[data])
    return order_serialized_data


def update_copy_queryset_for_submitted_count(copy_queryset, queryset):
    updated_queryset = [each_1 for each in queryset for each_1 in copy_queryset if each_1['id'] == each['id']]
    return updated_queryset


def update_age_calculation(query_data):
    print("11111")
    today = datetime.today().date()
    for each in query_data:
        birthday = each['user_biometric__birthday']
        if birthday:
            each['age'] = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        else:
            each['age'] = None
        print(each)
    return query_data


def update_age_calculation_on_single(query_data):
    if query_data:
        today = datetime.today().date()
        birthday = query_data[0]['user_biometric__birthday']
        if birthday:
            query_data[0]['user_details__age'] = today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day))
        else:
            query_data[0]['user_details__age'] = None
    return query_data


def filter_on_member_list(queryset, climbing_level=None, age_range=None, gender=None,
                          search_submitted_route=None, gym_detail_user=None):
    if climbing_level:
        # climbing_level = climbing_level.split(',')
        # print(climbing_level)
        if climbing_level == str(1):
        # if str(1) in climbing_level:
            queryset = queryset.filter(user_preference__rope_grading='YDS Scale')
        elif climbing_level == str(2):
        # if str(2) in climbing_level:
            queryset = queryset.filter(user_preference__rope_grading='Francia')
        elif climbing_level == str(10):
        # if str(10) in climbing_level:
            queryset = queryset.filter(user_preference__bouldering_grading='V System')
        elif climbing_level == str(11):
        # if str(11) in climbing_level:
            queryset = queryset.filter(user_preference__bouldering_grading='Fontainebleau')
    queryset = update_age_calculation(queryset)
    # if age_range:
    #     print(queryset)
    #     queryset = queryset.filter(user_details__age__range=age_range.split('-'))
    if gender:
        queryset = queryset.filter(user_biometric__gender=gender)
    copy_queryset = queryset
    if search_submitted_route:
        queryset = queryset.filter(user_route_feedback__gym=gym_detail_user,
                                   user_route_feedback__route__name__icontains=search_submitted_route)
        queryset = update_copy_queryset_for_submitted_count(copy_queryset, queryset)
    return queryset


def update_date_format(query_data):
    for each in query_data:
        if each['last_updated']:
            each['last_updated'] = each['last_updated'].strftime('%Y-%m-%dT%H:%M:%SZ')
    return query_data


# make changes for count
def filter_submitted_route(serialize_data, submitted_route=None):
    if submitted_route:
        serialize_data = [each for each in serialize_data if each['submitted_route'] == int(submitted_route)]
    return serialize_data


def check_gym_is_blocked(request_user, gym_detail):
    if request_user in gym_detail.blocked_user.all():
        return False
    return True


def check_dashboard_attempts_total(route_progress=None, last_week=False):
    today = date.today()
    # last_week_date = today - timedelta(days=7)
    last_week_date1 = today - timedelta(days=14)
    last_week_date2 = today - timedelta(days=7)
    if last_week:
        # Calculating increase or decrease count based on comparison between last week and this week
        # count_val = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress=route_progress,
        #                                                  gym_route_feedback__created_at__date__gte=last_week_date))
        count_val1 = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress__in=route_progress,
                                                          gym_route_feedback__created_at__date__gte=last_week_date1,
                                                          gym_route_feedback__created_at__date__lt=last_week_date2))
        count_val2 = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress__in=route_progress,
                                                          gym_route_feedback__created_at__date__gte=last_week_date2))
        count_val = count_val2 - count_val1
    else:
        count_val = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress__in=route_progress))
    return count_val


def check_dashboard_feedback_total(route_progress=None, total=False, last_week=False):
    today = date.today()
    # last_week_date = today - timedelta(days=7)
    last_week_date1 = today - timedelta(days=14)
    last_week_date2 = today - timedelta(days=7)
    if total:
        count_val = Count('gym_route_feedback', filter=~Q(gym_route_feedback__route_progress=route_progress))
    elif last_week:
        # Calculating increase or decrease count based on comparison between last week and this week
        # count_val = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress=route_progress,
        #                                                  gym_route_feedback__created_at__date__gte=last_week_date))
        count_val1 = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress=route_progress,
                                                          gym_route_feedback__created_at__date__gte=last_week_date1,
                                                          gym_route_feedback__created_at__date__lt=last_week_date2))
        count_val2 = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress=route_progress,
                                                          gym_route_feedback__created_at__date__gte=last_week_date2))
        count_val = count_val2 - count_val1
    else:
        count_val = Count('gym_route_feedback', filter=Q(gym_route_feedback__route_progress=route_progress))
    return count_val


def check_dashboard_route_type_total(route_type=None, total=False, percentage=False, v1=None, route_count=0):
    try:
        if total:
            count_val = Count('gym_layout__gym_layout_wall__section_wall_route',
                              filter=Q(gym_layout__gym_layout_wall__section_wall_route__is_deleted=False))
        elif percentage:
            if route_count != 0:
                count_val = (ExpressionWrapper(F(v1) * 100.0 / F('total_route_count'), output_field=FloatField()))
            else:
                count_val = Count('gym_layout__gym_layout_wall__section_wall_route',
                                  filter=Q(gym_layout__gym_layout_wall__section_wall_route__is_deleted=False))
        else:
            count_val = Count('gym_layout__gym_layout_wall__section_wall_route',
                              filter=Q(gym_layout__gym_layout_wall__section_wall_route__route_type=route_type,
                                       gym_layout__gym_layout_wall__section_wall_route__is_deleted=False))
    except Exception as e:
        print(e)
        count_val = 0
    return count_val


def get_total_members(users):
    # Calculating increase or decrease count based on comparison between last week and this week
    today = date.today()
    last_week_date1 = today - timedelta(days=14)
    last_week_date2 = today - timedelta(days=7)
    # last_week_date = today - timedelta(days=7)

    user_count = users.count()

    # last_week_user_count = users.filter(user_details__home_gym_added_on__date__gte=last_week_date).count()
    last_week_user_count1 = users.filter(user_details__home_gym_added_on__date__gte=last_week_date1,
                                         user_details__home_gym_added_on__date__lt=last_week_date2).count()
    last_week_user_count2 = users.filter(user_details__home_gym_added_on__date__gte=last_week_date2).count()
    last_week_user_count = last_week_user_count2 - last_week_user_count1

    member_count = {"user_count": user_count, "last_week_user_count": last_week_user_count}
    return member_count


def convert_height_to_range(height_range):
    height_range_dict = [
        {"key": "0-1", "value": 0},
        {"key": "1.1-2", "value": 0},
        {"key": "2.1-3", "value": 0},
        {"key": "3.1-4", "value": 0},
        {"key": "4.1-5", "value": 0},
        ]
    for each in height_range:
        each['height'] = each['height'] * 0.0254
        if 0 < each['height'] < 1:
            height_range_dict[0]["value"] += each['height_range_count']
        elif 1 < each['height'] <= 2:
            height_range_dict[1]["value"] += each['height_range_count']
        elif 2 < each['height'] <= 3:
            height_range_dict[2]["value"] += each['height_range_count']
        elif 3 < each['height'] <= 4:
            height_range_dict[3]["value"] += each['height_range_count']
        elif 4 < each['height'] <= 5:
            height_range_dict[4]["value"] += each['height_range_count']
    # height_range_dict = {
    #         "0-1": 0,
    #         "1.1-2": 0,
    #         "2.1-3": 0,
    #         "3.1-4": 0,
    #         "4.1-5": 0
    #     }
    # for each in height_range:
    #     each['height'] = each['height'] * 0.0254
    #     if 0 < each['height'] < 1:
    #         height_range_dict["0-1"] += each['height_range_count']
    #     elif 1 < each['height'] <= 2:
    #         height_range_dict["1.1-2"] += each['height_range_count']
    #     elif 2 < each['height'] <= 3:
    #         height_range_dict["2.1-3"] += each['height_range_count']
    #     elif 3 < each['height'] <= 4:
    #         height_range_dict["3.1-4"] += each['height_range_count']
    #     elif 4 < each['height'] <= 5:
    #         height_range_dict["4.1-5"] += each['height_range_count']
    return height_range_dict


def convert_wingspan_to_range( wingspan_range):
    wingspan_range_dict = [
        {"key": "0-1", "value": 0},
        {"key": "1.1-2", "value": 0},
        {"key": "2.1-3", "value": 0},
        {"key": "3.1-4", "value": 0},
        {"key": "4.1-5", "value": 0},
    ]
    for each in wingspan_range:
        each['wingspan'] = each['wingspan'] * 0.0254
        if 0 < each['wingspan'] < 1:
            wingspan_range_dict[0]["value"] += each['wingspan_range_count']
        elif 1 < each['wingspan'] <= 2:
            wingspan_range_dict[1]["value"] += each['wingspan_range_count']
        elif 2 < each['wingspan'] <= 3:
            wingspan_range_dict[2]["value"] += each['wingspan_range_count']
        elif 3 < each['wingspan'] <= 4:
            wingspan_range_dict[3]["value"] += each['wingspan_range_count']
        elif 4 < each['wingspan'] <= 5:
            wingspan_range_dict[4]["value"] += each['wingspan_range_count']

    # wingspan_range_dict = {
    #         "0-1": 0,
    #         "1.1-2": 0,
    #         "2.1-3": 0,
    #         "3.1-4": 0,
    #         "4.1-5": 0
    #     }
    # for each in wingspan_range:
    #     each['wingspan'] = each['wingspan'] * 0.0254
    #     if 0 < each['wingspan'] < 1:
    #         wingspan_range_dict["0-1"] += each['wingspan_range_count']
    #     elif 1 < each['wingspan'] <= 2:
    #         wingspan_range_dict["1.1-2"] += each['wingspan_range_count']
    #     elif 2 < each['wingspan'] <= 3:
    #         wingspan_range_dict["2.1-3"] += each['wingspan_range_count']
    #     elif 3 < each['wingspan'] <= 4:
    #         wingspan_range_dict["3.1-4"] += each['wingspan_range_count']
    #     elif 4 < each['wingspan'] <= 5:
    #         wingspan_range_dict["4.1-5"] += each['wingspan_range_count']
    return wingspan_range_dict


def create_rope_bouldering_graph_for_value(request_user, grading_system, sub_category):
    count_data = GradeType.objects.filter(grading_system=grading_system, sub_category=sub_category).order_by('id').\
        values('sub_category_value').annotate(
        count=Count('route_grade', filter=Q(route_grade__section_wall__gym_layout__gym__user=request_user,
                                            route_grade__is_deleted=False))
    )
    total_count = sum([each['count'] for each in count_data])
    return count_data, total_count


def create_exception_message(ex):
    if hasattr(ex, 'user_message'):
        msg = ex.user_message
    else:
        msg = "Something went wrong please try again later."
    return msg


def is_subscription_user_profile(requested_user, user_id):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        if data.plan.access_to_biometric_data and data.plan.access_to_sign_up_info:
            queryset = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
                    prefetch_related('user_route_feedback').filter(id=user_id).values(
                    'id', 'full_name', 'email', 'created_at', 'user_details__user_avatar', 'user_biometric__birthday',
                    'user_biometric__gender', 'user_preference__prefer_climbing', 'user_preference__bouldering',
                    'user_preference__top_rope', 'user_preference__lead_climbing', 'user_biometric__shoe_size',
                    'user_biometric__birthday', 'user_biometric__weight', 'user_biometric__hand_size',
                    'user_biometric__height', 'user_biometric__wingspan', 'user_biometric__ape_index')
            return True, '', queryset, 1
        elif data.plan.access_to_biometric_data and not data.plan.access_to_sign_up_info:
            queryset = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
                prefetch_related('user_route_feedback').filter(id=user_id).values(
                'id', 'user_biometric__birthday', 'user_biometric__gender', 'user_biometric__shoe_size',
                'user_biometric__weight', 'user_biometric__hand_size', 'user_biometric__height',
                'user_biometric__wingspan', 'user_biometric__ape_index')
            return True, '', queryset, 2
        elif not data.plan.access_to_biometric_data and data.plan.access_to_sign_up_info:
            queryset = User.objects.prefetch_related('user_details', 'user_biometric', 'user_preference'). \
                prefetch_related('user_route_feedback').filter(id=user_id).values(
                'id', 'full_name', 'email', 'created_at', 'user_details__user_avatar', 'user_biometric__birthday',
                'user_preference__prefer_climbing', 'user_preference__bouldering', 'user_preference__top_rope',
                'user_preference__lead_climbing',)
            return True, '', queryset, 3
        message = validation_message.get("UPGRADE_YOUR_PLAN")
        return False, message, [], 0
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return False, message, [], 0


def is_subscription_feedback(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        message = ''
        return data.plan.access_feedback_per_month, message
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return -1, message


def is_new_subscription_feedback(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        message = ''
        return data.plan.access_feedback_per_month, message, data.subscription_start
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return -1, message, None


def is_subscription_access_staff(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        if data.plan.access_to_gym_staff:
            message = ''
            return True, message
        message = validation_message.get("UPGRADE_YOUR_PLAN")
        return False, message
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return False, message


def is_subscription_staff_number(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        staff_user_count = Role.objects.filter(name=Role.RoleType.GYM_STAFF, role_status=True,
                                               user__user_details__home_gym=requested_user.gym_detail_user
                                               ).count()
        data_count = int(data.plan.active_gymstaff_number)
        if staff_user_count < data_count:
            message = ''
            return True, message
        message = 'Upgrade your plan to add more staff member (Current limit -> '+str(data_count)+').'
        return False, message
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return False, message


def is_subscription_access_wall(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        if data.plan.access_to_wall_pics:
            message = ''
            return True, message
        message = validation_message.get("UPGRADE_YOUR_PLAN")
        return False, message
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return False, message


def is_subscription_wall_number(requested_user):
    data = requested_user.user_subscription
    if data.is_subscribed and data.plan:
        wall_count = SectionWall.all_objects.filter(
            layout_section__gym_layout__gym__user=requested_user,
            created_at__gte=data.subscription_start).count()
        data_count = int(data.plan.uploaded_wall_number)
        if wall_count < data_count:
            message = ''
            return True, message
        message = 'Upgrade your plan to add more walls (Current limit -> '+str(data_count)+').'
        return False, message
    message = validation_message.get("NOT_ACTIVE_SUBSCRIPTION")
    return False, message


def get_wall_slot_left(gym_id):
    print(gym_id)
    user_subscription = UserSubscription.objects.filter(user__gym_detail_user=gym_id).first()
    user_plan = user_subscription.plan
    if not user_plan:
        return "NO ACTIVE PLAN"
    wall_count = SectionWall.all_objects.filter(layout_section__gym_layout__gym=gym_id,
                                                created_at__gte=user_subscription.subscription_start).count()
    data_count = int(user_plan.uploaded_wall_number)
    diff_count = data_count - wall_count
    data = diff_count if diff_count > 0 else 0
    return data


def date_list_based_on_month(from_date, to_date):
    from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
    to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    delta = to_date - from_date
    return [from_date + timedelta(days=i) for i in range(delta.days + 1)]


def update_payments_based_on_date(payments, from_date, to_date):
    date_list = date_list_based_on_month(from_date, to_date)
    d = dict((i['transaction_time__date'], i['amount']) for i in payments)
    payments_val = [{'Transaction Date': each, 'Amount': '$'+str(d[each])} if each in d else
                    {'Transaction Date': each, 'Amount': '$0.0'} for each in date_list]
    return payments_val


def send_custom_mail_to_gyms(gym_user_ids, subject, message):
    """
        method used to send custom email to gym users by admin.
    :param gym_user_ids:
    :param subject:
    :param message:
    :return:
    """
    subject = subject
    html_template = 'admin_custom_mail.html'
    ctx_dict = {"title": subject, "message_content": message}
    # send custom mail to gym users
    try:
        send_html_mail_to_multiple_user(subject, gym_user_ids, html_template, ctx_dict)
        # p = Process(target=send_html_mail_to_multiple_user,
        #             args=(subject, gym_user_ids, html_template, ctx_dict))
        # p.start()
    except Exception as e:
        print(e)
    return True


def show_latest_unique_feedback(queryset):
    emp_dict1, emp_dict2 = list(), list()
    for each in queryset:
        if each['route_id'] not in emp_dict1:
            emp_dict1.append(each['route_id'])
            emp_dict2.append(each['id'])
    return emp_dict2


def track_gym_visit_by_user(user_instance, route_instance, feedback_id):
    try:
        gym_detail = route_instance.section_wall.layout_section.gym_layout.gym
        today = date.today()
        GymVisit.objects.get_or_create(user=user_instance, gym=gym_detail, updated_at__date=today,
                                       defaults={'route_feedback': feedback_id})
    except Exception as e:
        print(e)
    return True


def get_gym_visit(user_id, gym_detail_user):
    today = date.today()
    last_week_date1 = today - timedelta(days=14)
    last_week_date2 = today - timedelta(days=7)
    gym_visit_all = GymVisit.objects.filter(user=user_id, gym=gym_detail_user)
    gym_visit = gym_visit_all.filter(updated_at__date__gte=last_week_date2).count()
    gym_visit_last_week = gym_visit_all.filter(updated_at__date__gte=last_week_date1,
                                               updated_at__date__lt=last_week_date2).count()
    return gym_visit, gym_visit_last_week


def get_dashboard_all_type_feedback_data(requested_user):
    user_route_feedback = GymDetails.objects.prefetch_related('gym_route_feedback'). \
        filter(user=requested_user, gym_route_feedback__route__is_deleted=False).values('id').annotate(
        # filter(user=request.user).values('id').annotate(
        projecting_count=check_dashboard_feedback_total(0),
        last_week_projecting_count=check_dashboard_feedback_total(0, last_week=True),
        total_rfo_count=check_dashboard_feedback_total(0, total=True),
        red_point_count=check_dashboard_feedback_total(1),
        last_week_red_point_count=check_dashboard_feedback_total(1, last_week=True),
        flash_count=check_dashboard_feedback_total(2),
        last_week_flash_count=check_dashboard_feedback_total(2, last_week=True),
        on_sight_count=check_dashboard_feedback_total(3),
        last_week_on_sight_count=check_dashboard_feedback_total(3, last_week=True),
    ).first()
    if not user_route_feedback:
        user_route_feedback = {
            "projecting_count": 0,
            "last_week_projecting_count": 0,
            "total_rfo_count": 0,
            "red_point_count": 0,
            "last_week_red_point_count": 0,
            "flash_count": 0,
            "last_week_flash_count": 0,
            "on_sight_count": 0,
            "last_week_on_sight_count": 0
        }

    # added to count last week data only if gym is created before last week
    today = date.today()
    last_week_date2 = today - timedelta(days=7)
    if requested_user.created_at.date() >= last_week_date2:
        user_route_feedback["last_week_projecting_count"] = 0
        user_route_feedback["last_week_red_point_count"] = 0
        user_route_feedback["last_week_flash_count"] = 0
        user_route_feedback["last_week_on_sight_count"] = 0
    return user_route_feedback


# def get_dashboard_all_route_type_data(requested_user):
#     route_type_count_before = GymDetails.objects.prefetch_related('gym_layout__gym_layout_wall__section_wall_route'). \
#         filter(user=requested_user).values('id'). \
#         annotate(total_route_count_val=Count('gym_layout__gym_layout_wall__section_wall_route',
#                                              filter=Q(
#                                                  gym_layout__gym_layout_wall__section_wall_route__is_deleted=False)))
#     before_route = route_type_count_before[0]['total_route_count_val']
#     route_type_count = GymDetails.objects.prefetch_related('gym_layout__gym_layout_wall__section_wall_route'). \
#         filter(user=requested_user).values('id').annotate(
#         total_route_count=check_dashboard_route_type_total(total=True),
#         endurance_count=check_dashboard_route_type_total(0),
#         endurance_percentage=check_dashboard_route_type_total(
#             percentage=True, v1='endurance_count', route_count=before_route),
#         strength_count=check_dashboard_route_type_total(1),
#         strength_percentage=check_dashboard_route_type_total(
#             percentage=True, v1='strength_count', route_count=before_route),
#         training_count=check_dashboard_route_type_total(2),
#         training_percentage=check_dashboard_route_type_total(
#             percentage=True, v1='training_count', route_count=before_route),
#         competition_count=check_dashboard_route_type_total(3),
#         competition_percentage=check_dashboard_route_type_total(
#             percentage=True, v1='competition_count', route_count=before_route)
#     ).first()
#
#     route_type_count['endurance_percentage'] = round(route_type_count['endurance_percentage'], 2)
#     route_type_count['strength_percentage'] = round(route_type_count['strength_percentage'], 2)
#     route_type_count['training_percentage'] = round(route_type_count['training_percentage'], 2)
#     route_type_count['competition_percentage'] = round(route_type_count['competition_percentage'], 2)
#     return route_type_count


def get_dashboard_all_route_type_data(requested_user):
    try:
        all_route_type_count = WallRoute.objects. \
            filter(section_wall__layout_section__gym_layout__gym__user=requested_user, is_deleted=False,
                   route_type__isnull=False).count()
        route_type_count = WallRoute.objects.filter(
            section_wall__layout_section__gym_layout__gym__user=requested_user, is_deleted=False,
            route_type__isnull=False).values('route_type__id', 'route_type__name').order_by('route_type__id').\
            annotate(specific_route_count=Count('id'))
        all_route_type_total = RouteType.objects.filter(gym__user=requested_user).order_by('id')
        all_route_type = all_route_type_total.values_list('id', flat=True)
        updated_route_type_count = [{'route_type__id': each.id, 'route_type__name': each.name, 'specific_route_count': 0, 'specific_route_percentage': 0} for each in all_route_type_total]
        for ind, each in enumerate(all_route_type):
            for each1 in route_type_count:
                if each == each1['route_type__id']:
                    updated_route_type_count[ind]['route_type__id'] = each1['route_type__id']
                    updated_route_type_count[ind]['route_type__name'] = each1['route_type__name']
                    updated_route_type_count[ind]['specific_route_count'] = each1['specific_route_count']
                    updated_route_type_count[ind]['specific_route_percentage'] = round(
                        each1['specific_route_count'] * 100 / all_route_type_count, 2)
                    break
        route_type_data = {"total_route_count": all_route_type_count, "specific_route_count": updated_route_type_count}
    except:
        route_type_data = {"total_route_count": 0, "specific_route_count": []}
    return route_type_data


def get_dashboard_all_type_range_data(requested_user, gym_detail):
    ## To get height range
    height_range = UserBiometricData.objects.filter(user__is_deleted=False,
                                                    user__is_active=True,
                                                    user__user_details__home_gym=gym_detail,
                                                    height__isnull=False).values('height'). \
        annotate(height_range_count=Count('height')).order_by('height')
    # To convert normal data into range data
    height_range_updated = convert_height_to_range(height_range)

    ## To get wingspan range
    wingspan_range = UserBiometricData.objects.filter(user__is_deleted=False,
                                                      user__is_active=True,
                                                      user__user_details__home_gym=gym_detail,
                                                      wingspan__isnull=False).values('wingspan'). \
        annotate(wingspan_range_count=Count('wingspan')).order_by('wingspan')
    # To convert normal data into range data
    wingspan_range_updated = convert_wingspan_to_range(wingspan_range)

    ## To get climbing level range
    climbing_level_range1 = None
    climbing_level_range1a = None
    climbing_level_range2 = None
    key_data1 = None
    key_data2 = None
    gym_details = GymDetails.objects.filter(user=requested_user).first()
    if gym_details.RopeClimbing == 1:
        climbing_level_range1 = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            rope_grading="YDS Scale").values('rope_grading', 'top_rope'). \
            annotate(count=Count('id'))
        climbing_level_range1a = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            rope_grading="YDS Scale").values('rope_grading', 'lead_climbing'). \
            annotate(count=Count('id'))
        key_data1 = 'YDS_Scale_Or_Francia'
        grading_name1 = 'YDS Scale'
    elif gym_details.RopeClimbing == 2:
        climbing_level_range1 = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            rope_grading="Francia").values('rope_grading', 'top_rope'). \
            annotate(count=Count('id'))
        climbing_level_range1a = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            rope_grading="Francia").values('rope_grading', 'lead_climbing'). \
            annotate(count=Count('id'))
        key_data1 = 'YDS_Scale_Or_Francia'
        grading_name1 = 'Francia'
    if gym_details.Bouldering == 10:
        climbing_level_range2 = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            bouldering_grading="V System").values('bouldering_grading', 'bouldering'). \
            annotate(count=Count('id'))
        key_data2 = 'V_System_Or_Fontainebleau'
        grading_name2 = 'V System'
    elif gym_details.Bouldering == 11:
        climbing_level_range2 = UserPreference.objects.filter(
            user__is_deleted=False, user__is_active=True, user__user_details__home_gym=gym_details,
            bouldering_grading="Fontainebleau").values('bouldering_grading', 'bouldering'). \
            annotate(count=Count('id'))
        key_data2 = 'V_System_Or_Fontainebleau'
        grading_name2 = 'Fontainebleau'
    climbing_level_range = dict()
    if gym_details.RopeClimbing:
        climbing_level_range[key_data1] = {
            'grading_name': grading_name1,
            'top_rope': climbing_level_range1,
            'lead_climbing': climbing_level_range1a}
    if gym_details.Bouldering:
        climbing_level_range2_data = climbing_level_range2 if climbing_level_range2 else []
        climbing_level_range[key_data2] = {
                                              'grading_name': grading_name2,
                                              'level_data': climbing_level_range2_data
                                          }
    range_data = {'climbing_level_range': climbing_level_range,
                  'height_range': height_range_updated, 'wingspan_range': wingspan_range_updated,
                  }
    return range_data


def create_wall_type(gym_obj):
    li = ['OVERHANG', 'SLAB', 'CAVE']
    wall_li = [WallType(gym=gym_obj, name=each) for each in li]
    WallType.objects.bulk_create(wall_li)
    return True


def create_color_type(gym_obj):
    li = [('ORANGE', '#FFA500'), ('RED', '#FF0000'), ('GREEN', '#00FF00'), ('BLUE', '#0000FF'), ('PURPLE', '#800080'),
          ('PINK', '#FFC0CB'), ('BROWN', '#964B00'), ('GRAY', '#808080')]
    color_li = [ColorType(gym=gym_obj, name=each[0], hex_value=each[1]) for each in li]
    ColorType.objects.bulk_create(color_li)
    return True


def create_route_type(gym_obj):
    li = ['ENDURANCE', 'STRENGTH', 'TRAINING', 'COMPETITION']
    route_li = [RouteType(gym=gym_obj, name=each) for each in li]
    RouteType.objects.bulk_create(route_li)
    return True


def get_wall_count_for_dashboard(requested_user, last_week_date1, last_week_date2):
    wall_count = SectionWall.all_objects.filter(gym_layout__gym__user=requested_user). \
        values('id').aggregate(
        wall_count=Count('id'),
        las_week_wall_count=
        Count('id', filter=Q(created_at__date__gte=last_week_date2)) -
        Count('id', filter=Q(created_at__date__gte=last_week_date1, created_at__date__lt=last_week_date2)))
    return wall_count


def get_route_attempt_count_for_dashboard(requested_user):
    route_attempt_count = GymDetails.objects.prefetch_related('gym_route_feedback'). \
        filter(user=requested_user, gym_route_feedback__route__is_deleted=False).values('id').annotate(
        # filter(user=request.user).values('id').annotate(
        attempts_count=check_dashboard_attempts_total([0, 1, 2, 3]),
        last_week_attempts_count=check_dashboard_attempts_total([0, 1, 2, 3], last_week=True)).first()
    if not route_attempt_count:
        route_attempt_count = {
            "attempts_count": 0,
            "last_week_attempts_count": 0
        }
    return route_attempt_count


def get_total_member_count_for_dashboard(requested_user, last_week_date1, last_week_date2):
    # total_member_count = User.all_objects.select_related('user_details').filter(
    total_member_count = User.objects.select_related('user_details').filter(
        user_details__home_gym=requested_user.gym_detail_user).values('id').aggregate(
        member_count=Count('id'),
        last_week_member_count=
        Count('id', filter=Q(user_details__home_gym_added_on__date__gte=last_week_date2)) -
        Count('id', filter=Q(user_details__home_gym_added_on__date__gte=last_week_date1,
                             user_details__home_gym_added_on__date__lt=last_week_date2)))
    return total_member_count


def get_total_wall_visit_for_dashboard(requested_user, last_week_date1, last_week_date2):
    total_wall_visit = WallVisit.objects.filter(wall__gym_layout__gym__user=requested_user). \
        values('id').aggregate(
        wall_visit=Count('id'),
        last_week_wall_vist=
        Count('id', filter=Q(created_at__date__gte=last_week_date2)) -
        Count('id', filter=Q(created_at__date__gte=last_week_date1, created_at__date__lt=last_week_date2)))
    return total_wall_visit


def get_rope_bouldering_graph(requested_user):
    gym_details = GymDetails.objects.filter(user=requested_user).first()
    rope_climbing_data, bouldering_data = None, None
    total_count1, total_count2 = 0, 0
    if gym_details.RopeClimbing == GymDetails.RopeClimbingOptions.YDSSCALE:
        rope_climbing_data, total_count1 = create_rope_bouldering_graph_for_value(
            request_user=requested_user, grading_system=GymLayout.ClimbingType.ROPE_CLIMBING,
            sub_category=GymDetails.RopeClimbingOptions.YDSSCALE)
    elif gym_details.RopeClimbing == GymDetails.RopeClimbingOptions.FRANCIA:
        rope_climbing_data, total_count1 = create_rope_bouldering_graph_for_value(
            request_user=requested_user, grading_system=GymLayout.ClimbingType.ROPE_CLIMBING,
            sub_category=GymDetails.RopeClimbingOptions.FRANCIA)
    if gym_details.Bouldering == GymDetails.BoulderingOptions.V_SYSTEM:
        bouldering_data, total_count2 = create_rope_bouldering_graph_for_value(
            request_user=requested_user, grading_system=GymLayout.ClimbingType.BOULDERING,
            sub_category=GymDetails.BoulderingOptions.V_SYSTEM)
    elif gym_details.Bouldering == GymDetails.BoulderingOptions.FONTAINEBLEAU:
        bouldering_data, total_count2 = create_rope_bouldering_graph_for_value(
            request_user=requested_user, grading_system=GymLayout.ClimbingType.BOULDERING,
            sub_category=GymDetails.BoulderingOptions.FONTAINEBLEAU)
    rope_bouldering_graph = dict()
    if rope_climbing_data:
        rope_bouldering_graph['total_rope_climbing_count'] = total_count1
        rope_bouldering_graph['rope_climbing_data'] = rope_climbing_data
    else:
        rope_bouldering_graph['total_rope_climbing_count'] = -1
        rope_bouldering_graph['rope_climbing_data'] = None
    if bouldering_data:
        rope_bouldering_graph['total_bouldering_count'] = total_count2
        rope_bouldering_graph['bouldering_data'] = bouldering_data
    else:
        rope_bouldering_graph['total_bouldering_count'] = -1
        rope_bouldering_graph['bouldering_data'] = None
    return rope_bouldering_graph


def get_filtered_user_common_fun(gym, user_data):
    if gym is None:
        # user = User.objects.filter(user_details__isnull=False)
        user = User.objects.filter(user_role__name__in=[Role.RoleType.CLIMBER, Role.RoleType.GYM_STAFF],
                                   user_role__role_status=True).distinct()
        if user_data == "":
            data = []
        elif int(user_data) == 1:
            data2 = user.extra(select={'gym_detail_user__gym_name': 'full_name'}).values(
                'id', 'email',
                'gym_detail_user__gym_name')
            data = list(data2)
        elif int(user_data) == 2:
            data2 = user.filter(user_role__name=3, user_role__role_status=True).values(
                'id', 'email', 'full_name',)
            data = list(data2)
        elif int(user_data) == 3:
            data2 = user.filter(user_role__name=1, user_role__role_status=True).values(
                'id', 'email', 'full_name',)
            data = list(data2)
        else:
            data = User.objects.filter(gym_detail_user__isnull=False).order_by('id').values(
                'id', 'email', 'gym_detail_user__gym_name')
    else:
        data1 = gym.values(
            'id', 'email', 'gym_detail_user__gym_name')
        if user_data == "":
            data = list(data1)
        elif int(user_data) == 1:
            data2 = gym.filter(gym_detail_user__user_home_gym__user__isnull=False,
                               gym_detail_user__user_home_gym__user__is_active=True).values(
                'id', 'email', 'gym_detail_user__gym_name', 'gym_detail_user__user_home_gym__user__id',
                'gym_detail_user__user_home_gym__user__full_name', 'gym_detail_user__user_home_gym__user__email')
            data = list(data1) + list(data2)
        elif int(user_data) == 2:
            data2 = gym.filter(gym_detail_user__user_home_gym__user__isnull=False,
                               gym_detail_user__user_home_gym__user__is_active=True,
                               gym_detail_user__user_home_gym__user__user_role__name=3,
                               gym_detail_user__user_home_gym__user__user_role__role_status=True).values(
                'id', 'email', 'gym_detail_user__gym_name', 'gym_detail_user__user_home_gym__user__id',
                'gym_detail_user__user_home_gym__user__full_name', 'gym_detail_user__user_home_gym__user__email')
            data = list(data1) + list(data2)
        elif int(user_data) == 3:
            data2 = gym.filter(gym_detail_user__user_home_gym__user__isnull=False,
                               gym_detail_user__user_home_gym__user__is_active=True,
                               gym_detail_user__user_home_gym__user__user_role__name=1,
                               gym_detail_user__user_home_gym__user__user_role__role_status=True).values(
                'id', 'email', 'gym_detail_user__gym_name', 'gym_detail_user__user_home_gym__user__id',
                'gym_detail_user__user_home_gym__user__full_name', 'gym_detail_user__user_home_gym__user__email')
            data = list(data1) + list(data2)
        else:
            data = list(data1)
    return data

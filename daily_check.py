import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
from django.conf import settings
from django.utils import timezone

django.setup()
from datetime import datetime, timedelta
import pytz
from accounts.models import User, UserSubscription
from core import utils as core_utils


# To save datetime in cronjobreport
print("Today running on (UTC) : " + str(datetime.utcnow()))

# # Fetching all users in Database.
user_obj = UserSubscription.objects.filter(user__user_role__name=2)
#
# '''
#     We will be looping through all the users and checking whether.
#     1. Free trial is over then send notification and remove free access.
#     2. Subscription is going to end and they didn't subscribed to any plan send notification and
#        remove subscription.
# '''
print(user_obj)
for users in user_obj:
    # Checking for free trial
    try:
        if users.is_subscribed and users.subscription_end.replace(tzinfo=pytz.UTC) < datetime.utcnow().replace(
                tzinfo=pytz.UTC):  # and not CustomerSubscriptions.objects.filter(user=users).exists():
            try:
                user_email = users.user.email
                core_utils.send_html_mail_to_single_user(
                    subject="Subscription ended", email=user_email,
                    html_template="subscription_ended.html", ctx_dict={'email': user_email})
            except Exception:
                pass
            users.is_subscribed = False
            users.subscription_status = UserSubscription.INACTIVE
            users.subscription_interval = "subscription expired"
            users.subscription_id = None
            users.plan = None
            users.save()
            print("%s:-ending subscription" % (str(datetime.utcnow().date())), users)
    except Exception:
        print("Error in users.subscription_end.replace(tzinfo=pytz.UTC)")

print("#############################")
print("\n\n")

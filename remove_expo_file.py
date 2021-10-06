import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import boto3
from datetime import datetime, timezone
from config.settings import AWS_STORAGE_BUCKET_NAME, AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY
from core.models import ExpoPaymentUrl


# SETUP THIS CRON ON SERVER
def delete_junky_image():
    """
        It will delete all expo temp file of past date from aws.
    """
    print("DELETE JUNKY IMAGES AT: {}".format(str(datetime.utcnow())))
    s3 = boto3.resource('s3',
                        aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
    current_utc_date = datetime.now(timezone.utc).date()
    all_aws_url = ExpoPaymentUrl.objects.filter(created_at__date__lt=current_utc_date).all()
    for key in all_aws_url:
        try:
            s3.Object(AWS_STORAGE_BUCKET_NAME, key.name).delete()
            key.delete()
        except Exception:
            pass


def delete_downloads_file():
    """
        It will delete all expo temp file of past date from local.
    """
    try:
        print("DELETE JUNKY IMAGES AT: {}".format(str(datetime.utcnow())))
        # data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        #                          'downloads/')
        data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 'others/downloads/')
        list_dir = os.listdir(data_path)
        for file_name in list_dir:
            try:
                file_extension = os.path.splitext(file_name)[-1]
                if file_extension != '.txt':
                    time_stamp = file_name.split('_')[1]
                    file_date = datetime.utcfromtimestamp(float(time_stamp)).date()
                    if file_date < datetime.now(timezone.utc).date():
                        os.remove(os.path.join(data_path, file_name))
                        print(file_name)
            except Exception:
                pass
    except Exception:
        pass


delete_junky_image()
delete_downloads_file()
print("\n##########################\n")

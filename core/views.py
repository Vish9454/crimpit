import boto3
from io import BytesIO
import sys
import uuid

from core.models import ExpoPaymentUrl

''' project level imports '''
from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import status as status_code
from rest_framework import views
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status as status_code
from core.exception import get_custom_error
from core.messages import variables
from core.response import SuccessResponse
from config.settings import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
from core import utils as core_utils


class UploadFileView(views.APIView):
    """
        UploadFileView
            This class contains the logic of file upload into the S3 bucket. Only authenticated users can
        perform respective operation.

        Inherits: APIView
    """
    parser_classes = (MultiPartParser,)
    image_content = "file"
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        """
                post method used to upload file into S3 bucket.
            :param request:
            :return: response
        """
        upload = request.data.get(self.image_content, None)
        if not upload:
            return Response(get_custom_error(message='No file data found',
                                             error_location='file upload.', status=status_code.HTTP_400_BAD_REQUEST),
                            status=status_code.HTTP_400_BAD_REQUEST)
        s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
                            aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
        import os
        file_name, file_extension = os.path.splitext(upload.name)
        file_full_name = upload.name
        updated_filename = file_full_name.replace(' ', '_')
        if file_extension.lower() in variables["IMAGE_TYPE"]:
            path_key = "image/{}_{}".format(uuid.uuid4(), updated_filename)
        elif file_extension.lower() in variables["DOCS_TYPE"]:
            path_key = "docs/{}_{}".format(uuid.uuid4(), updated_filename)
        else:
            return Response(get_custom_error(message='Please provide valid file.',
                                             error_location=variables.get('LOCATION_FILE_UPLOAD'),
                                             status=status_code.HTTP_400_BAD_REQUEST),
                            status=status_code.HTTP_400_BAD_REQUEST)
        bool_val = core_utils.check_file_size(upload)
        if not bool_val:
            # return Response(get_custom_error(message='File size must be less than or equal to 2 MB.',
            #                                  error_location=variables.get('LOCATION_FILE_UPLOAD'),
            #                                  status=status_code.HTTP_400_BAD_REQUEST),
            #                 status=status_code.HTTP_400_BAD_REQUEST)
            return Response(get_custom_error(message='File size must be less than or equal to 10 MB.',
                                             error_location=variables.get('LOCATION_FILE_UPLOAD'),
                                             status=status_code.HTTP_400_BAD_REQUEST),
                            status=status_code.HTTP_400_BAD_REQUEST)
        try:
            s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_fileobj(upload, path_key)
        except Exception:
            return Response(get_custom_error(message='Something went wrong during file uploading.',
                                             error_location=variables.get('LOCATION_FILE_UPLOAD'),
                                             status=status_code.HTTP_400_BAD_REQUEST),
                            status=status_code.HTTP_400_BAD_REQUEST)
        created_url = 'https://'+AWS_STORAGE_BUCKET_NAME+'.s3.amazonaws.com/'+path_key
        return Response({'name': path_key, 'url': created_url}, status=status_code.HTTP_200_OK)


class GetAWSKeyView(views.APIView):
    """API to return encrypted AWS keys."""

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        import base64
        from config.local import AWS_S3_ACCESS_KEY_ID, AWS_S3_SECRET_ACCESS_KEY, AWS_STORAGE_BUCKET_NAME
        random_num = request.data.get('num')
        if not random_num:
            return SuccessResponse({"message": "Please provide num"}, status=400)
        if random_num < 2:
            return SuccessResponse({"message": "Invalid num"}, status=400)
        temp_dict = {
            'access_key': AWS_S3_ACCESS_KEY_ID.encode('utf-8'),
            'secret_key': AWS_S3_SECRET_ACCESS_KEY.encode('utf-8'),
            'bucket_name': AWS_STORAGE_BUCKET_NAME.encode('utf-8')
        }
        for _ in range(random_num):
            access_key = base64.encodebytes(temp_dict['access_key'])
            secret_key = base64.encodebytes(temp_dict['secret_key'])
            bucket_name = base64.encodebytes(temp_dict['bucket_name'])
            temp_dict['access_key'] = access_key
            temp_dict['secret_key'] = secret_key
            temp_dict['bucket_name'] = bucket_name

        response = {
            "access_key": base64.b64encode(temp_dict['access_key']),
            "secret_key": base64.b64encode(temp_dict['secret_key']),
            "bucket_name": base64.b64encode(temp_dict['bucket_name'])
        }
        return SuccessResponse(response, status=status_code.HTTP_200_OK)


def upload_payment_report(filename, file_path):
    path_key = "export_data/{}".format(filename)
    s3 = boto3.resource('s3', aws_access_key_id=AWS_S3_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_S3_SECRET_ACCESS_KEY)
    try:
        s3.Bucket(AWS_STORAGE_BUCKET_NAME).upload_file(file_path, path_key)
    except Exception:
        data = {
             "message": 'Something went wrong during file uploading.',
             "error_location": 'export temp upload function.',
        }
        return False, data
    created_url = 'https://' + AWS_STORAGE_BUCKET_NAME + '.s3.amazonaws.com/' + path_key
    # To save data into ExpoTempUrl model
    expo_temp_data = {
        "name": path_key,
        "full_url": created_url
    }
    ExpoPaymentUrl.objects.create(**expo_temp_data)
    data = {'name': path_key, 'url': created_url}
    return True, data

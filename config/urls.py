"""config URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import include, path

from core.views import UploadFileView, GetAWSKeyView

urlpatterns = [
    path('crimpit/superadmin/', admin.site.urls),
    path('crimpit/user/', include('accounts.urls')),
    path('crimpit/gym/', include('gyms.urls')),
    path('crimpit/gym_staff/', include('staffs.urls')),
    url('crimpit/upload-file', UploadFileView.as_view()),
    url('crimpit/aws-key', GetAWSKeyView.as_view()),
    url('crimpit/admin/',include('admins.urls')),
    url('crimpit/payments/',include('payments.urls')),

]

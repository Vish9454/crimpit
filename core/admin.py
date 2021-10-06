from django.contrib import admin
from core.models import ExpoPaymentUrl

# Register your models here.


@admin.register(ExpoPaymentUrl)
class ExpoPaymentUrlAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'full_url')

from django.contrib import admin

# Register your models here.
from admins.models import Domain


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'is_active',)

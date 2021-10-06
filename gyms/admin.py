from django.contrib import admin
from gyms.models import GymDetails, ChangeRequestGymDetails, GymLayout, LayoutSection, SectionWall, WallRoute, \
    PreLoadedTemplate, Announcement, Event, OpenFeedback, WallType, ColorType, RouteType


# Register your models here.


@admin.register(GymDetails)
class GymDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym_name', 'zipcode', 'is_admin_approved')


@admin.register(ChangeRequestGymDetails)
class ChangeRequestGymDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym_detail', 'gym_name',)


admin.site.register(GymLayout)
admin.site.register(LayoutSection)


@admin.register(SectionWall)
class SectionWallAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym_layout', 'name', 'created_by', 'created_at',)


@admin.register(WallRoute)
class WallRouteAdmin(admin.ModelAdmin):
    list_display = ('id', 'section_wall', 'name', 'grade', 'route_type', 'created_by',)


@admin.register(OpenFeedback)
class OpenFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym_user', 'feedback', 'open_at',)


@admin.register(WallType)
class WallTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym', 'name',)


@admin.register(ColorType)
class ColorTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym', 'name', 'hex_value',)


@admin.register(RouteType)
class RouteTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym', 'name',)


admin.site.register(PreLoadedTemplate)


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('id', 'gym', 'priority', 'is_active',)


admin.site.register(Event)

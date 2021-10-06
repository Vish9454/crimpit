from django.contrib import admin
from accounts.models import User, AccountVerification, Role, UserDetails, UserPreference, ListCategory, \
    RouteSaveList, UserRouteFeedback, SavedEvent, UserBiometricData, UserDetailPercentage, WallVisit, \
    QuestionAnswer, UserSubscription, GymVisit


# Register your models here.


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'user_preference',)


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user',)


@admin.register(GymVisit)
class GymVisitAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'gym', 'route_feedback', 'updated_at',)


admin.site.register(AccountVerification)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'name', 'role_status',)


@admin.register(UserDetails)
class UserDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'home_gym',)


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'rope_grading', 'bouldering_grading', 'bouldering', 'top_rope',
                    'lead_climbing',)


@admin.register(ListCategory)
class ListCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'image', 'is_active',)


@admin.register(RouteSaveList)
class RouteSaveListAdmin(admin.ModelAdmin):
    list_display = ('id', 'list_category', 'user', 'created_at',)


@admin.register(UserRouteFeedback)
class UserRouteFeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'gym', 'route', 'route_progress', 'grade', 'created_at', 'updated_at',)


@admin.register(UserBiometricData)
class UserBiometricDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'height', 'wingspan', 'created_at',)


@admin.register(WallVisit)
class UserBiometricDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'wall', 'user', 'created_at',)


@admin.register(SavedEvent)
class SavedEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'save_event', 'is_going', 'is_saved',)


admin.site.register(UserDetailPercentage)
admin.site.register(QuestionAnswer)

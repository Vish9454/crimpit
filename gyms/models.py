from django.contrib.postgres.search import SearchVectorField

from accounts.models import ActiveUserManager, ActiveObjectsManager, User
from core.models import BaseModel
from django.contrib.gis.db import models
from django.contrib.gis.geos import Polygon
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.indexes import GinIndex
from multiselectfield import MultiSelectField


# Create your models here.


class GymDetails(BaseModel):
    """
    GymDetail models used for the Gym Details fields.
     Inherit : BaseModel
    """

    class WeekDays(models.IntegerChoices):
        SUNDAY = 1
        MONDAY = 2
        TUESDAY = 3
        WEDNESDAY = 4
        THURSDAY = 5
        FRIDAY = 6
        SATURDAY = 7

    class RopeClimbingOptions(models.IntegerChoices):
        YDSSCALE = 1
        FRANCIA = 2

    class BoulderingOptions(models.IntegerChoices):
        V_SYSTEM = 10
        FONTAINEBLEAU = 11

    class DocumentChoices(models.IntegerChoices):
        PENDING = 1
        VERIFIED = 2
        REJECTED = 3

    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name='gym_detail_user')
    gym_name = models.CharField(max_length=100, verbose_name='Gym Name')
    gym_avatar = models.CharField(max_length=255, blank=True, null=True, verbose_name='Gym Image')
    gym_phone_number = models.CharField(max_length=25, verbose_name='Gym Phone Number')
    week_day = MultiSelectField("week days", choices=WeekDays.choices, blank=True, null=True)
    start_time = models.TimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    end_time = models.TimeField(auto_now=False, auto_now_add=False, null=True, blank=True)
    address = models.CharField(max_length=300, blank=True, null=True, verbose_name='Address')
    zipcode = models.CharField(max_length=20, blank=True, null=True, verbose_name='Zipcode')
    geo_point = models.PointField(blank=True, null=True, verbose_name='Site coordinate')
    easy_direction_link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Easy Directions Link')
    website_link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Website Link')
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name='Description')
    RopeClimbing = models.IntegerField(choices=RopeClimbingOptions.choices, blank=True, null=True,
                                       verbose_name='Rope Climbing')
    Bouldering = models.IntegerField(choices=BoulderingOptions.choices, blank=True, null=True,
                                     verbose_name='Bouldering')
    blocked_user = models.ManyToManyField('accounts.User', related_name='blocked_user_by_gym')
    is_active = models.BooleanField('Active', default=True)
    is_admin_approved = models.BooleanField('Is Admin Approved', default=False)
    is_profile_complete = models.BooleanField('Is Profile Complete', default=False)
    documents = ArrayField(models.CharField(max_length=200), blank=True, null=True)
    temp_documents = ArrayField(models.CharField(max_length=200), blank=True, null=True)
    document_state = models.IntegerField(choices=DocumentChoices.choices, blank=True, null=True,
                                         verbose_name='Document State')

    class Meta:
        verbose_name = 'GymDetail'
        verbose_name_plural = 'GymDetails'


class ChangeRequestGymDetails(BaseModel):
    """
    ChangeRequestGymDetails models used for the Gym Details change request.
     Inherit : BaseModel
    """
    gym_detail = models.OneToOneField("gyms.GymDetails", on_delete=models.CASCADE, related_name='gym_change_request')
    email = models.EmailField(max_length=80, blank=True, null=True, verbose_name='Email')
    gym_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Gym Name')
    easy_direction_link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Easy Directions Link')
    website_link = models.CharField(max_length=500, blank=True, null=True, verbose_name='Website Link')

    class Meta:
        verbose_name = 'ChangeRequestGymDetail'
        verbose_name_plural = 'ChangeRequestGymDetails'


class GymLayout(BaseModel):
    class ClimbingType(models.IntegerChoices):
        """
            ClimbingType Models used for the climbing type
        """
        ROPE_CLIMBING, BOULDERING, BOTH = 0, 1, 2

    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_layout')
    category = models.IntegerField(choices=ClimbingType.choices, null=True, verbose_name='Climbing Category')
    layout_image = models.CharField(max_length=255, blank=True, null=True, verbose_name='Gym Layout Image')
    image_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Image Size')
    title = models.CharField(max_length=50, blank=True, null=True, verbose_name='Gym Title')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'GymLayout'
        verbose_name_plural = 'GymLayouts'
        ordering = ['id']


class LayoutSection(BaseModel):
    gym_layout = models.ForeignKey(GymLayout, null=True, on_delete=models.SET_NULL, related_name='gym_layout_section')
    name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Gym Name')
    section_point = models.PolygonField(blank=False, null=False, verbose_name='Section Point')
    image_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Image Size')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'LayoutSection'
        verbose_name_plural = 'LayoutSections'
        ordering = ['id']


class WallType(BaseModel):
    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_wall_type')
    name = models.CharField(max_length=50, verbose_name='Wall Type Name')

    class Meta:
        verbose_name = 'WallType'
        verbose_name_plural = 'WallTypes'


class SectionWall(BaseModel):
    class ClimbingType(models.IntegerChoices):
        """
            ClimbingType Models used for the climbing type
        """
        ROPE_CLIMBING, BOULDERING, BOTH = 0, 1, 2

    # class WallType(models.IntegerChoices):
    #     """
    #         WallType Models used for the wall type
    #     """
    #     OVERHANG, SLAB, CAVE = 0, 1, 2
    #     # STRENGTH, TRAIN, BOTH = 0, 1, 2

    category = models.IntegerField(choices=ClimbingType.choices, null=True, verbose_name='Climbing Category')
    gym_layout = models.ForeignKey(GymLayout, null=True, on_delete=models.SET_NULL, related_name='gym_layout_wall')
    layout_section = models.ForeignKey(LayoutSection, null=True, on_delete=models.SET_NULL, related_name='section_wall')
    image = models.CharField(max_length=255, blank=True, null=True, verbose_name='Wall Image')
    image_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Image Size')
    name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Wall Name')
    # wall_type = models.IntegerField(choices=WallType.choices, null=True, verbose_name='Wall Type')
    wall_type = models.ForeignKey(WallType, null=True, on_delete=models.SET_NULL, verbose_name='Wall Type')
    wall_height = models.CharField(max_length=50, blank=True, null=True, verbose_name='Wall Height')
    reset_timer = models.DateTimeField(null=True, verbose_name='Reset Timer')
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                   related_name='created_by_wall')
    ghost_wall_image = models.CharField(max_length=255, blank=True, null=True, verbose_name='Ghost Wall Image')
    ghost_wall_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Ghost Image Size')
    ghost_wall_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Ghost Wall Name')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'SectionWall'
        verbose_name_plural = 'SectionWalls'
        ordering = ['id']


class GradeType(BaseModel):
    class ClimbingType(models.IntegerChoices):
        """
            ClimbingType Models used for the climbing type
        """
        ROPE_CLIMBING, BOULDERING = 0, 1

    class SubCategoryType(models.IntegerChoices):
        """
            SubCategoryType Models used for the sub-category type
        """
        YDSSCALE, FRANCIA, V_SYSTEM, FONTAINEBLEAU = 1, 2, 10, 11

    grading_system = models.IntegerField(choices=ClimbingType.choices,
                                         verbose_name='Grading System')
    sub_category = models.IntegerField(choices=SubCategoryType.choices,
                                       verbose_name='Sub Category')
    sub_category_value = models.CharField(max_length=20, verbose_name='Sub-Category Value')

    def __str__(self):
        return "Grading: " + str(self.grading_system) + " Sub Category: " + str(self.sub_category) + \
               " Value: " + str(self.sub_category_value)


class ColorType(BaseModel):
    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_color_type')
    name = models.CharField(max_length=50, verbose_name='Wall Type Name')
    hex_value = models.CharField(max_length=100, verbose_name='Hex Value')

    class Meta:
        verbose_name = 'ColorType'
        verbose_name_plural = 'ColorTypes'


class RouteType(BaseModel):
    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_route_type')
    name = models.CharField(max_length=50, verbose_name='Route Type Name')

    class Meta:
        verbose_name = 'RouteType'
        verbose_name_plural = 'RouteTypes'


class WallRoute(BaseModel):
    # class GradeType(models.IntegerChoices):
    #     """
    #         GradeType Models used for the grade type
    #     """
    #     v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11, v12, v13, v14, v15 = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

    # class ColorType(models.IntegerChoices):
    #     """
    #         ColorType Models used for the color type
    #     """
    #     ORANGE, RED, GREEN, BLUE, PURPLE, PINK, BROWN, GRAY = 1, 2, 3, 4, 5, 6, 7, 8

    # class RouteType(models.IntegerChoices):
    #     """
    #         RouteType Models used for the route type
    #     """
    #     ENDURANCE, STRENGTH, TRAINING, COMPETITION = 0, 1, 2, 3

    section_wall = models.ForeignKey(SectionWall, null=True, on_delete=models.SET_NULL,
                                     related_name='section_wall_route')
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Route Name')
    # grade = models.IntegerField(choices=GradeType.choices, null=True, verbose_name='Route Grade')
    grade = models.ForeignKey(GradeType, null=True, on_delete=models.SET_NULL, related_name='route_grade')
    # color = models.IntegerField(choices=ColorType.choices, null=True, verbose_name='Route Color')
    color = models.ForeignKey(ColorType, null=True, on_delete=models.SET_NULL, related_name='route_Color')
    # route_type = models.IntegerField(choices=RouteType.choices, null=True, verbose_name='Route Type')
    route_type = models.ForeignKey(RouteType, null=True, on_delete=models.SET_NULL, related_name='route_type')
    setter_tip = models.CharField(max_length=200, blank=True, null=True, verbose_name='Route Setter Tip')
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                   related_name='created_by_route')
    image_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Image Size')
    tag_point = ArrayField(models.FloatField())
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'WallRoute'
        verbose_name_plural = 'WallRoutes'
        ordering = ['id']


class GhostWallRoute(BaseModel):
    section_wall = models.ForeignKey(SectionWall, null=True, on_delete=models.SET_NULL,
                                     related_name='ghost_wall_route')
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Route Name')
    assigned_to = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                    related_name='assigned_to_route')
    grade = models.ForeignKey(GradeType, null=True, on_delete=models.SET_NULL, related_name='ghost_route_grade')
    created_by = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                   related_name='ghost_created_by_route')
    image_size = ArrayField(models.FloatField(), blank=True, null=True, verbose_name='Image Size')
    tag_point = ArrayField(models.FloatField())
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'GhostWallRoute'
        verbose_name_plural = 'GhostWallRoutes'
        ordering = ['id']


class PreLoadedTemplate(BaseModel):
    uploaded_template = models.CharField(max_length=255, verbose_name='Uploaded Template')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'PreLoadedTemplate'
        verbose_name_plural = 'PreLoadedTemplates'


class Announcement(BaseModel):
    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_announcement')
    banner = models.CharField(max_length=255, blank=True, null=True, verbose_name='Banner')
    template = models.ForeignKey(PreLoadedTemplate, null=True, on_delete=models.SET_NULL,
                                 related_name='template_announcement')
    template_type = models.IntegerField(default=0, verbose_name='Template Type')
    picture = models.CharField(max_length=255, blank=True, null=True, verbose_name='Picture')
    title = models.CharField(max_length=300, blank=True, null=True, verbose_name='Title')
    sub_title = models.CharField(max_length=300, blank=True, null=True, verbose_name='Subtitle')
    priority = models.IntegerField(default=0)
    is_active = models.BooleanField('Is Active', default=True)
    search = SearchVectorField(null=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    def save(self, *args, **kwargs):
        try:
            if not self.pk:
                super(Announcement, self).save(*args, **kwargs)
            if self.priority == 0:
                self.priority = self.pk
                self.save()
                # super(Announcement, self).save(*args, **kwargs)
            else:
                super(Announcement, self).save(*args, **kwargs)
        except Exception:
            pass

    class Meta:
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'
        indexes = [
            GinIndex(fields=['search']),
        ]


class Event(BaseModel):
    gym = models.ForeignKey(GymDetails, null=True, on_delete=models.SET_NULL, related_name='gym_event')
    thumbnail = models.CharField(max_length=255, verbose_name='Thumbnail')
    title = models.CharField(max_length=200, verbose_name='Title')
    start_date = models.DateTimeField(verbose_name='Start Date')
    description = models.CharField(max_length=500, blank=True, null=True, verbose_name='Description')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'


class OpenFeedback(BaseModel):
    gym_user = models.ForeignKey('accounts.User', null=True, on_delete=models.SET_NULL,
                                 related_name='open_feedback_user')
    feedback = models.ForeignKey('accounts.UserRouteFeedback', null=True, on_delete=models.SET_NULL,
                                 related_name='open_feedback')
    open_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Open Feedback'
        verbose_name_plural = 'Open Feedbacks'


class GlobalSearch(BaseModel):
    parent = models.CharField(max_length=100, blank=False, null=False, verbose_name='Parent')
    child = models.CharField(max_length=100, blank=True, null=True, verbose_name='Child')
    sub_child = models.CharField(max_length=100, blank=True, null=True, verbose_name='Sub Child')
    sub_child_1 = models.CharField(max_length=100, blank=True, null=True, verbose_name='Sub Child 1 Level More')
    is_active = models.BooleanField('Is Active', default=True)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'Global Search'
        verbose_name_plural = 'Global Searchs'

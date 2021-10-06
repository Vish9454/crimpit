from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import (AbstractBaseUser, UserManager)
from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField

from core.models import BaseModel
from multiselectfield import MultiSelectField

from admins.models import SubscriptionPlan
# Create your models here.


class MyUserManager(BaseUserManager):
    """
    Inherits: BaseUserManager class
    """

    def create_user(self, email, password=None):
        """
        Create user with given email and password.
        :param email:
        :param password:
        :return:
        """
        if not email:
            raise ValueError('Users must have an email address')
        user = self.model(email=self.normalize_email(email))
        # set_password is used set password in encrypted form.
        user.set_password(password)
        user.is_active = True
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password):
        """
        Create and save the super user with given email and password.
        :param email:
        :param password:
        :return: user
        """
        user = self.create_user(email, password=password)
        user.is_superuser = True
        user.username = ""
        user.is_staff = True
        user.is_active = True
        user.save(using=self._db)
        return user


class ActiveUserManager(UserManager):
    """
        ActiveUserManager class to filter the deleted user.
    """
    def get_queryset(self):
        return super(ActiveUserManager, self).get_queryset().filter(is_active=True, is_deleted=False)


class ActiveObjectsManager(UserManager):
    """
        ActiveObjectsManager class to filter the deleted objs
    """
    def get_queryset(self):
        return super(ActiveObjectsManager, self).get_queryset().filter(is_deleted=False)


class User(AbstractBaseUser, BaseModel):
    """
    MyUser models used for the authentication process and it contains basic
     fields.
     Inherit : AbstractBaseUser, PermissionMixin, BaseModel
    """
    username = models.CharField(max_length=50, blank=True, null=True, verbose_name='User Name')
    first_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='First Name')
    last_name = models.CharField(max_length=50, blank=True, null=True, verbose_name='Last Name')
    full_name = models.CharField(max_length=120, blank=True, null=True, verbose_name='Full Name')
    email = models.EmailField(max_length=80, unique=True, blank=False, null=False, verbose_name='Email')
    phone_number = models.CharField(max_length=25, unique=False, blank=True, null=True,
                                    verbose_name='Phone Number')
    is_email_verified = models.BooleanField('Email Verified', default=False)
    is_phone_verified = models.BooleanField('Phone Verified', default=False)
    is_active = models.BooleanField('Active', default=True)
    is_staff = models.BooleanField('Is Staff', default=False)
    is_superuser = models.BooleanField('SuperUser', default=False)

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()
    all_delete_objects = UserManager()
    my_user_manager = MyUserManager()
    USERNAME_FIELD = 'email'

    def has_perm(self, perm, obj=None):
        """
        has_perm method used to give permission to the user.
        :param perm:
        :param obj:
        :return: is_staff
        """
        return self.is_staff

    def has_module_perms(self, app_label):
        """
        method to give module permission to the superuser.
        :param app_label:
        :return: is_superuser
        """
        return self.is_superuser

    def __str__(self):
        """
        :return: email
        """
        return self.email

    def get_short_name(self):
        return self.email

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['id']
        index_together = ["email", "phone_number", "updated_at"]


class AccountVerification(BaseModel):
    """
        AccountVerification models to save the account verification details.
    """

    class VerificationType(models.IntegerChoices):
        """
            VerificationType Models used for the token_type
        """
        EMAIL_VERIFICATION = 1
        FORGOT_PASSWORD = 2
        OTHER = 3

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_token')
    token = models.CharField(blank=False, max_length=100, verbose_name='Token')
    expired_at = models.DateTimeField(blank=False, verbose_name='Expired At')
    is_used = models.BooleanField('IsUsed', default=False)
    verification_type = models.IntegerField(choices=VerificationType.choices, blank=False,
                                            verbose_name='Verification Type')

    class Meta:
        verbose_name = 'AccountVerification'
        verbose_name_plural = 'AccountVerifications'


class Role(BaseModel):
    """ Role
            Defines the model used to store the User's roles.
        Inherits : `BaseModel`
    """
    class RoleType(models.IntegerChoices):
        """
            VerificationType Models used for the token_type
        """
        CLIMBER = 1
        GYM_OWNER = 2
        GYM_STAFF = 3
        ADMIN_USER = 4

    name = models.IntegerField(choices=RoleType.choices, blank=False, verbose_name="Name")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='user_role',
                             blank=True, null=True)
    role_status = models.BooleanField(default=True, verbose_name='Role Status')

    class Meta:
        verbose_name = 'Role'
        verbose_name_plural = 'Roles'


class UserSettings(BaseModel):
    """
        UserSettings model used to save the UserSetting.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_settings',
                                null=True)
    is_notification_allowed = models.BooleanField(default=True,
                                                  verbose_name='Is notification allowed')
    is_location_allowed = models.BooleanField(default=True, verbose_name='Is location allowed')


class UserDetails(BaseModel):
    """
        UserDetails model used to save the UserDetails.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_details')
    user_avatar = models.CharField(max_length=255, blank=True, null=True, verbose_name='User Image')
    home_gym = models.ForeignKey('gyms.GymDetails', null=True, on_delete=models.SET_NULL, related_name='user_home_gym')
    home_gym_added_on = models.DateTimeField(blank=True, null=True, verbose_name='Home Gym Addition Date')
    age = models.CharField(max_length=3, blank=True, null=True, verbose_name='Age')
    # strength = ArrayField(models.CharField(max_length=1000, blank=True, null=True), blank=True, null=True,
    #                       verbose_name='Strength')
    strength_hold = ArrayField(models.CharField(max_length=1000, blank=True, null=True), blank=True, null=True,
                               verbose_name='Strength Holds')
    strength_move = ArrayField(models.CharField(max_length=1000, blank=True, null=True), blank=True, null=True,
                               verbose_name='Strength Moves')
    weakness_hold = ArrayField(models.CharField(max_length=1000, blank=True, null=True), blank=True, null=True,
                               verbose_name='Weakness Holds')
    weakness_move = ArrayField(models.CharField(max_length=1000, blank=True, null=True), blank=True, null=True,
                               verbose_name='Weakness Moves')
    login_count = models.IntegerField(default=0, verbose_name='Login Count')

    class Meta:
        verbose_name = 'UserDetail'
        verbose_name_plural = 'UserDetails'


class UserBiometricData(BaseModel):
    """
        UserBiometricData model used to save the User Biometric Details.
    """
    class GenderType(models.IntegerChoices):
        """
            GenderType Models used for the gender_type
        """
        NOT_SELECTED = 0
        MALE = 1
        FEMALE = 2
        TRANSGENDER = 3

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_biometric')
    height = models.FloatField(null=True, verbose_name='Height (in inch)')
    wingspan = models.FloatField(null=True, verbose_name='Wingspan (in inch)')
    ape_index = models.FloatField(null=True, verbose_name='Ape Index')
    gender = models.IntegerField(choices=GenderType.choices, default=0, verbose_name='Gender')
    birthday = models.DateField(null=True, verbose_name='Birthday')
    weight = models.FloatField(null=True, verbose_name='Wingspan (in lbs)')
    shoe_size = models.FloatField(null=True, verbose_name='Shoe Size (Us)')
    hand_size = models.FloatField(null=True, verbose_name='Shoe Size (in inch)')

    class Meta:
        verbose_name = 'UserBiometricData'
        verbose_name_plural = 'UserBiometricDatas'


class UserDetailPercentage(BaseModel):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_detail_percentage')
    basic_detail = models.DecimalField(default=0, max_digits=5, decimal_places=2,
                                       verbose_name='Basic Detail Percentage')
    climbing_detail = models.DecimalField(default=0, max_digits=5, decimal_places=2,
                                          verbose_name='Climbing Detail Percentage')
    biometric_detail = models.DecimalField(default=0, max_digits=5, decimal_places=2,
                                           verbose_name='Biometric Detail Percentage')
    overall_detail = models.DecimalField(default=0, max_digits=5, decimal_places=2,
                                         verbose_name='Overall Detail Percentage')

    def save(self, *args, **kwargs):
        sum_data = float(self.basic_detail) + float(self.climbing_detail) + float(self.biometric_detail)
        self.overall_detail = (sum_data / 300) * 100
        super(UserDetailPercentage, self).save(*args, **kwargs)

    class Meta:
        verbose_name = 'UserDetailPercentage'
        verbose_name_plural = 'UserDetailPercentages'


"""
    GradingType Models used for the grading type
"""
GRADING_CHOICES = (('R0', 'YDS_SCALE'),
               ('R1', 'FRANCIA'),
               ('R2', 'UIAA'),
               ('R3', 'AUS'),
               ('R4', 'LIVELLO'),
               ('B0', 'V_SYSTEM'),
               ('B1', 'FONTAINEBLEAU'))


class UserPreference(BaseModel):
    """
        UserPreference model used to save the user climbing preference.
    """

    class ClimbingType(models.IntegerChoices):
        """
            ClimbingType Models used for the climbing type
        """
        ROPE_CLIMBING, BOULDERING, BOTH = 0, 1, 2

    class BoulderingType(models.IntegerChoices):
        """
            ClimbingType Models used for the climbing type
        """
        V0, V1, V2, V3, V4, V5, V6, V7, V8, V9 = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9

    class TopRopeType(models.IntegerChoices):
        """
            TopRopeType Models used for the top rope type
        """
        a, b, c, d, e = 0, 1, 2, 3, 4

    class LeadClimbingType(models.IntegerChoices):
        """
            LeadClimbingType Models used for the lead climbing type
        """
        a, b, c, d, e = 0, 1, 2, 3, 4

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='user_preference')
    prefer_climbing = models.IntegerField(choices=ClimbingType.choices, blank=True, null=True,
                                          verbose_name='Prefer Climbing')
    rope_grading = models.CharField(max_length=30, blank=True, null=True, verbose_name='Rope Grading')
    bouldering_grading = models.CharField(max_length=30, blank=True, null=True, verbose_name='Bouldering Grading')
    bouldering = models.CharField(max_length=20, blank=True, null=True, verbose_name='Bouldering')
    top_rope = models.CharField(max_length=20, blank=True, null=True, verbose_name='Top Rope')
    lead_climbing = models.CharField(max_length=20, blank=True, null=True, verbose_name='Lead Climbing')
    # grading = MultiSelectField(choices=GRADING_CHOICES, verbose_name='Grading')
    # bouldering = models.IntegerField(choices=BoulderingType.choices, blank=True, null=True, verbose_name='Bouldering')
    # top_rope = models.IntegerField(choices=TopRopeType.choices, blank=True, null=True, verbose_name='Top Rope')
    # lead_climbing = models.IntegerField(choices=LeadClimbingType.choices, blank=True, null=True,
    # verbose_name='Lead Climbing')

    class Meta:
        verbose_name = 'UserPreference'
        verbose_name_plural = 'UserPreferences'


class UserSubscription(BaseModel):
    """
        UserSubscription model used to save the User Subscription Detail.
    """
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name='user_subscription',
                                null=True)
    is_stripe_customer = models.BooleanField('StripeCustomer', default=False)
    is_subscribed = models.BooleanField('Subscribed User', default=False)
    subscription_start = models.DateTimeField(null=True, blank=True, verbose_name='Subscription Start')
    subscription_end = models.DateTimeField(null=True, blank=True, verbose_name='Subscription End')
    subscription_interval = models.CharField(max_length=20, null=True, blank=True, verbose_name='Subscription Interval')
    ACTIVE = 1
    INACTIVE = 2
    SUBSCRIPTION_STATUS_C = (
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    )
    subscription_status = models.IntegerField('Subscription status', choices=SUBSCRIPTION_STATUS_C, default=INACTIVE)
    is_free = models.BooleanField('Free Access', default=False)
    is_trial = models.BooleanField('Trial Access', default=False)
    trial_end = models.DateTimeField(null=True, blank=True, verbose_name='Trial End')
    subscription_id = models.CharField(max_length=30, null=True, blank=True)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, related_name="subscription_plan", null=True, blank=True)

    class Meta:
        verbose_name = 'UserSubscription'
        verbose_name_plural = 'UserSubscriptions'


class WallVisit(BaseModel):
    """
        WallVisit model used to save the wall visit user history.
    """
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_wall_visit')
    wall = models.ForeignKey('gyms.SectionWall', null=True, on_delete=models.SET_NULL, related_name='wall_visit')

    class Meta:
        verbose_name = 'WallVisit'
        verbose_name_plural = 'WallVisits'


class ListCategory(BaseModel):
    """
        ListCategory model used to save the list name.
    """
    name = models.CharField(max_length=50, verbose_name='List Name')
    image = models.CharField(max_length=255, blank=True, null=True, verbose_name='List Name')
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_list_category')
    gym = models.ForeignKey('gyms.GymDetails', null=True, on_delete=models.SET_NULL, related_name='gym_list_category')
    # is_common = models.BooleanField(default=False, verbose_name='Is Common')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')

    objects = ActiveUserManager()
    all_objects = ActiveObjectsManager()

    class Meta:
        verbose_name = 'ListCategory'
        verbose_name_plural = 'ListCategories'


class RouteSaveList(BaseModel):
    """
        RouteSaveList model used to save the route into a particular list.
    """
    list_category = models.ForeignKey(ListCategory, on_delete=models.CASCADE, related_name='list_category_route')
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_route_list')
    gym = models.ForeignKey('gyms.GymDetails', null=True, on_delete=models.SET_NULL, related_name='gym_route_list')
    route = models.ManyToManyField('gyms.WallRoute', related_name='route_save_list')

    class Meta:
        verbose_name = 'RouteSaveList'
        verbose_name_plural = 'RouteSaveLists'


class UserRouteFeedback(BaseModel):
    """
        UserRouteFeedback model used to save the user route feedback.
    """
    class RouteProgressType(models.IntegerChoices):
        """
            RouteProgressType Models used for the route progress type
        """
        PROJECTING, RED_POINT, FLASH, ON_SIGHT = 0, 1, 2, 3

    class CommunityGradeType(models.IntegerChoices):
        """
            CommunityGradeType Models used for the community grade type
        """
        NEGATIVE, NORMAL, POSITIVE = 0, 1, 2

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_route_feedback')
    gym = models.ForeignKey('gyms.GymDetails', null=True, on_delete=models.SET_NULL,
                            related_name='gym_route_feedback')
    route = models.ForeignKey('gyms.WallRoute', null=True, on_delete=models.SET_NULL, related_name='route_feedback')
    route_progress = models.IntegerField(choices=RouteProgressType.choices, null=True, verbose_name='Route Progress')
    attempt_count = models.IntegerField(default=0, verbose_name='No. of Attempts')
    route_note = models.CharField(max_length=500, blank=True, null=True, verbose_name='Route Notes')
    # for red point, flash, on sight
    climb_count = models.IntegerField(default=0, verbose_name='Climb Count')
    grade = models.IntegerField(choices=CommunityGradeType.choices, null=True, verbose_name='Route Progress')
    rating = models.IntegerField(default=0, verbose_name='Route Rating')
    feedback = models.CharField(max_length=500, blank=True, null=True, verbose_name='Route Feedback')
    first_time_read = models.BooleanField(default=False, verbose_name='First Time Read')
    second_time_read = models.BooleanField(default=False, verbose_name='Second Time Read')

    class Meta:
        verbose_name = 'UserRouteFeedback'
        verbose_name_plural = 'UserRouteFeedbacks'


class SavedEvent(BaseModel):
    class GoingType(models.IntegerChoices):
        """
            GoingType Models used for the going confirmation
        """
        NOT_SELECTED, YES, NO, MAY_BE = 0, 1, 2, 3

    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_saved_event')
    save_event = models.ForeignKey('gyms.Event', null=True, on_delete=models.SET_NULL, related_name='mark_event')
    is_going = models.IntegerField(choices=GoingType.choices, default=0, verbose_name='Is Going')
    is_saved = models.BooleanField(default=False, verbose_name='Is Saved')

    class Meta:
        verbose_name = 'SavedEvent'
        verbose_name_plural = 'SavedEvents'


class QuestionAnswer(BaseModel):
    question = models.TextField(verbose_name='Question')
    answer = models.TextField(verbose_name='Answer')
    priority = models.IntegerField(default=0, verbose_name='Question Priority')

    class Meta:
        verbose_name = 'QuestionAnswer'
        verbose_name_plural = 'QuestionAnswers'


class GymVisit(BaseModel):
    user = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, related_name='user_gym_visit')
    gym = models.ForeignKey('gyms.GymDetails', null=True, on_delete=models.SET_NULL, related_name='g_gym_visit')
    route_feedback = models.IntegerField(verbose_name='Route Feedback Id')

    class Meta:
        verbose_name = 'GymVisit'
        verbose_name_plural = 'GymVisits'

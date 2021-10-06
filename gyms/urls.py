"""gym owner related routes """
from django.conf.urls import url
from gyms import views as gym_views
from django.urls import path

urlpatterns = [
    url('^signup$', gym_views.GymUserSignUp.as_view({'post': 'create'}), name='gym-owner-create'),
    url('signupcomplete', gym_views.GymUserSignUpComplete.as_view({'put': 'update'}),
        name='gym-owner-update'),
    url('^login$', gym_views.GymOwnerLogIn.as_view({'post': 'create'}), name='gym-owner-log-in'),
    url('^forgot_password$', gym_views.GymForgotPasswordViewSet.as_view({'post': 'create'}),
        name='gym-owner-forgot-password'),
    url('^reset_password$', gym_views.GymResetPassword.as_view({'post': 'create'}),
        name='reset-owner-change-password'),
    url('^gymownerlist', gym_views.GymOwnerList.as_view({'get': 'list'}), name='gym-owner-list'),
    path('gymownerprofile', gym_views.GetGymOwnerProfile.as_view({'get': 'retrieve'}),
         name='gym-owner-profile'),

    # Layout
    url('^gymlayout$', gym_views.GymlayoutView.as_view({'post': 'create','put': 'update','get': 'list'
                                                    }), name='gym-layout'),
    path('gymlayout/<int:layout_id>', gym_views.GymlayoutView.as_view({'get': 'retrieve'}), name='gym-layout-retrieve'),
    url('deletelayout', gym_views.DeleteGymLayout.as_view({'put': 'update'}),
        name='gym-layout-update'),

    # Section
    url('^gymsectionlayout$', gym_views.GymLayoutSection.as_view({'post': 'create','put': 'update','get': 'list'
                                                                  }), name='gym-section-layout'),
    path('gymsectionlayout/<int:section_id>', gym_views.GymLayoutSection.as_view({'get': 'retrieve'}),
         name='gym-section-retrieve'),
    url('deletegymsection', gym_views.DeleteGymSection.as_view({'put': 'update'}),
        name='gym-section-update'),

    # Wall
    url('^gymwall', gym_views.GymWall.as_view({'post': 'create','put': 'update','get': 'list'
                                               }), name='gym-wall'),
    path('retrievegymwall/<int:wall_id>', gym_views.GymWall.as_view({'get': 'retrieve'}),
         name='gym-wall-retrieve'),
    url('deletegymwall', gym_views.DeleteGymWall.as_view({'put': 'update'}),
        name='gym-wall-update'),
    path('gym_wall_stats/<int:wall_id>', gym_views.GymWallStats.as_view({'get': 'retrieve'}),
         name='gym-wall-stats'),
    url('^wall_reset_timer', gym_views.WallResetTimer.as_view({
        'get': 'list', 'put': 'update', 'delete': 'destroy'}), name='gym-wall-reset-timer'),
    url('^wall_type', gym_views.ManualWallType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='gym-wall-type'),
    url('^gym_ghost_wall', gym_views.GymGhostWall.as_view({'put': 'update'}), name='gym-ghost-wall'),

    # Events & Announcements
    url('^pre_loaded_template$', gym_views.PreLoadedTemplateViewSet.as_view({'get': 'list', 'put': 'update'}),
        name='pre-loaded-template-view-set'),
    url('^gym_announcement$', gym_views.GymAnnouncementViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='gym-announcement-view-set'),
    path('gym_announcement/<int:announcement_id>', gym_views.GymAnnouncementViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='gym-announcement-view-set'),
    url('^gym_event$', gym_views.GymEventViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='gym-event-view-set'),
    path('gym_event/<int:event_id>', gym_views.GymEventViewSet.as_view(
        {'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='gym-event-view-set'),

    url('^gymgrade$', gym_views.ListGymGradeType.as_view({'get': 'list'}),name='gym-grade'),

    # Gym Route API
    url('^color_type', gym_views.ManualColorType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='gym-color-type'),
    url('^route_type', gym_views.ManualRouteType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='gym-route-type'),
    url('^route_grade', gym_views.RouteGradeViewet.as_view({'get': 'list'}), name='gym-route-grade'),
    url('^gymroute', gym_views.GymWallRoute.as_view({'post': 'create','put': 'update','get': 'list'}),
        name='gym-route'),
    path('retrievegymroute/<int:route_id>', gym_views.GymWallRoute.as_view({'get': 'retrieve'}),
         name='gym-route-retrieve'),
    url('deletegymroute', gym_views.DeleteGymRoute.as_view({'put': 'update'}),
        name='gym-route-update'),
    url('staff_listing', gym_views.GymStaffListing.as_view({'get': 'list'}), name='gym-staff-list'),
    url('^gym_ghost_route', gym_views.GymGhostWallRoute.as_view({'post': 'create','put': 'update','get': 'list'}),
        name='gym-ghost-route'),
    path('retrieve_ghost_route/<int:ghost_route_id>', gym_views.GymGhostWallRoute.as_view({'get': 'retrieve'}),
         name='ghost-route-retrieve'),
    url('delete_ghost_route', gym_views.DeleteGymGhostRoute.as_view({'put': 'update'}),
        name='ghost-route-update'),


    url('^routetaglist', gym_views.RouteTagList.as_view({'post': 'create'}), name='gym-routetag-list'),

    path("changepassword",gym_views.ChangePassword.as_view({"put": "update"}),
        name="change_password",),

    # Dashboard
    path("dashboard", gym_views.DashboardViewSet.as_view({"get": "list"}), name="dashboard-view-set"),
    path("dashboard1", gym_views.Dashboard1ViewSet.as_view({"get": "list"}), name="dashboard1-view-set"),


    path('feedbacklist/<int:route_id>', gym_views.RouteTagListScreen2FeedbackList.as_view({'get': 'list'}),
         name='gym-route-retrieve'),
    path('routedetails/<int:route_id>', gym_views.RouteTagListScreen2RouteDetail.as_view({'get': 'retrieve'}),
         name='gym-route-details'),
    path("profileupdate/<int:gym_owner_id>", gym_views.GymOwnerProfileUpdate.as_view({"put": "update"}),
         name="rofile-update", ),
    path('listsubsection', gym_views.ListRouteWallSectionLayout.as_view({'get': 'list'}),
         name='gym-list-subsection'),
    path('wall_based_on_section', gym_views.WallListBasedOnSection.as_view({'get': 'list'}),
         name='wall-based-on-section'),
    path('listallusers', gym_views.ListAllUsers.as_view({'get': 'list'}),
         name='list-allusers'),

    # Members
    url('^all_users_count', gym_views.TotalMemberCount.as_view({'get': 'list'}), name='all-users-count'),
    url('^all_gym_users', gym_views.ListGymUser.as_view({'get': 'list', 'delete': 'destroy'}), name='all-gym-users'),
    path("add_remove_staff_member/<int:user_id>", gym_views.AddAsStaffMember.as_view({"put": "update"}),
         name="member-update"),
    path('member_profile_detail', gym_views.MemberProfile.as_view({'get': 'list'}), name='member-profile-detail'),
    path('member_profile_detail/<int:user_id>', gym_views.MemberProfile.as_view({'get': 'retrieve'}),
         name='retrieve-member-profile-detail'),
    path('open_feedback/<int:feedback_id>', gym_views.MemberFeedbackOpen.as_view({'get': 'retrieve'}),
         name='retrieve-member-feedback-open'),
    url('^all_route_feedback_count', gym_views.AllRouteFeedbackCount.as_view({'get': 'list'}),
         name='all-route-feedback-count'),

    # Profile
    url('^verifyemail$', gym_views.VerifyEmailAddress.as_view({'post': 'create'}),
         name='gym-verify-email$'),
    url('^resendverifyemail$', gym_views.ResendEmailVerifyLink.as_view({'post': 'create'}),
         name='gym-resend-verify-email$'),

    # Subscription
    path('listsubplan', gym_views.PlansSubscriptionGymOwner.as_view({'get': 'list'}), name='subscription-plan'),
    path('retrievesubplan/<int:subscription_plan_id>', gym_views.PlansSubscriptionGymOwner.as_view(
        {'get': 'retrieve'}), name='subscription-plan'),

    # Global Search
    url('^global_search$', gym_views.GlobalSearchKeyword.as_view({'get': 'list'}), name='gym-global-search'),

    # CR for Optional Climbing Level
    url('^optional_climbing$', gym_views.OptionalClimbing.as_view({'get': 'list'}), name='gym-optional-climbing'),

    # Check staff member
    url('^check_gym_owner$', gym_views.CheckGymOwnerViewset.as_view({'get': 'list'}), name='check-gym-owner-viewset'),
]

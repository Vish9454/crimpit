from django.conf.urls import url
from admins import views as admin_views
from django.urls import path
urlpatterns =[
    # Onboarding
    url('^admin_login$', admin_views.AdminLoginViewSet.as_view({'post': 'create'}), name='Admin-login'),
    url('^forget_password$', admin_views.AdminForgetPasswordViewSet.as_view({'post': 'create'}),
        name='Admin-forget-password'),
    url('^reset_password$', admin_views.AdminResetPasswordViewSet.as_view({'post': 'create'}),
        name='Admin-reset-password'),

    # Dashboard
    url('^user_count$', admin_views.StaffMemberCountViewSet.as_view({'get': 'list'}), name='User-count'),
    url('^payment_graph$', admin_views.PaymentGraphViewSet.as_view({'get': 'list'}), name='payment-graph'),
    url('^payment_report$', admin_views.PaymentReportViewSet.as_view({'get': 'list'}), name='payment-report'),

    # User Management
    url('^list_of_user$',admin_views.ListUserViewSet.as_view({'post': 'create'}),
        name='List-of-User'),
    path('climber_profile/<int:user_id>', admin_views.ClimberProfileViewSet.as_view({'get': 'list'}),
         name='Climber-Profile-ViewSet'),
    path('gym_profile/<int:gym_user_id>', admin_views.GymProfileViewSet.as_view({'get': 'list'}),
         name='Gym-Profile-ViewSet'),
    url('^delete_multiple_user$', admin_views.DeleteBulkUserViewSet.as_view({'put': 'update'}),
        name='delete-user-bulk'),
    # path('user_detail/<int:user_id>',admin_views.SpecificUserDetailViewSet.as_view({'get':'retrieve'}),
    #      name='Specific-User-Details'),
    # path('delete_single_user/<int:user_id>',admin_views.DeleteSingleUserViewSet.as_view({'delete':'destroy'}),name='Delete-single-user-ViewSet'),

    # Review Details Management
    url('^list_of_review$', admin_views.ListOfReviewViewSet.as_view({'get': 'list'}), name='List-Of-Review-ViewSet'),
    path('list_of_review/<int:gym_id>', admin_views.ListOfReviewViewSet.as_view({'get': 'retrieve'}),
         name='List-Of-Review-ViewSet'),
    url('^gym_approve$', admin_views.ApproveViewSet.as_view({'put': 'update'}), name='Approve-ViewSet'),
    url('^gym_reject$', admin_views.RejectViewSet.as_view({'put': 'update'}), name='Reject-ViewSet'),

    # Subscription
    url('^plan_subscription$', admin_views.PlansSubscriptionAdmin.as_view({
        'post': 'create', 'put': 'update', 'get': 'list'}), name='subscription-plan'),
    path('plan_subscription/<int:plan_id>', admin_views.PlansSubscriptionAdmin.as_view({'get': 'retrieve'}),
         name='subscription-plan'),

    # Mail
    url('^get_gym_user$', admin_views.GetGymUserViewset.as_view({'get': 'list'}), name='Gym-User-ViewSet'),
    url('^get_filtered_user$', admin_views.GetFilteredUserViewset.as_view({'post': 'create'}), name='Filtered-User-ViewSet'),
    url('^send_custom_email$', admin_views.CustomEmailViewSet.as_view({'post': 'create'}), name='Send-Email-ViewSet'),

    # Global Search
    # url('^global_search/',admin_views.GlobalSearchView.as_view(),name='Global-search'),

    # Domain
    url('^gym_domain$', admin_views.DomainViewSet.as_view({'get': 'list', 'post': 'create',
                                                           'put': 'update'}), name='Domain-ViewSet'),
]



"""gym staff related routes """
from django.conf.urls import url
from django.urls import path
from staffs import views as staff_views

urlpatterns = [
    url('^staff_home_gym_check$', staff_views.StaffHomeGymCheckViewSet.as_view({'get': 'retrieve'}),
        name='staff-home-gym-view-set'),
    path('staff_home/<int:gym_id>', staff_views.StaffHomeViewSet.as_view({'get': 'retrieve'}),
         name='staff-home-view-set'),
    url('^staff_wall$', staff_views.StaffWallViewSet.as_view(
        {'get': 'list', 'post': 'create', 'put': 'perform_update', 'delete': 'perform_delete'}),
        name='staff-wall-view-set'),
    path('staff_wall/<int:wall_id>', staff_views.StaffWallViewSet.as_view({'get': 'retrieve'}),
         name='staff-wall-view-set'),
    path('only_staff_wall_detail/<int:wall_id>', staff_views.OnlyStaffWallDetailViewSet.as_view({'get': 'retrieve'}),
         name='only-staff-wall-detail-view-set'),
    url('^wall_type', staff_views.StaffManualWallType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='staff-wall-type'),
    url('^staff_ghost_wall$', staff_views.StaffGhostWallViewSet.as_view(
        {'get': 'list', 'put': 'update'}), name='staff-ghost-wall-view-set'),
    url('^color_type', staff_views.ManualColorType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='gym-color-type'),
    url('^route_type', staff_views.ManualRouteType.as_view({'get': 'list', 'post': 'create', 'put': 'update'}),
        name='gym-route-type'),
    url('^staff_route$', staff_views.StaffRouteViewSet.as_view(
        {'get': 'list', 'post': 'create', 'put': 'perform_update', 'delete': 'perform_delete'}),
        name='staff-route-view-set'),
    path('staff_route/<int:route_id>', staff_views.StaffRouteViewSet.as_view({'get': 'retrieve'}),
         name='staff-route-view-set'),
    url('staff_listing', staff_views.StaffListingViewset.as_view({'get': 'list'}), name='staff-list'),
    url('^staff_ghost_route$', staff_views.StaffGhostRouteViewSet.as_view(
        {'post': 'create', 'put': 'perform_update'}), name='staff-route-view-set'),
    path('staff_ghost_route/<int:ghost_route_id>', staff_views.StaffGhostRouteViewSet.as_view({'get': 'retrieve'}),
         name='staff-route-view-set'),
    url('delete_ghost_route', staff_views.DeleteGymGhostRoute.as_view({'put': 'update'}),
        name='ghost-route-delete'),

    # Profile
    url('^staff_detail$', staff_views.StaffDetailViewSet.as_view({'get': 'retrieve'}), name='user-detail-view-set'),
    url('^plan_detail$', staff_views.PlanDetailViewSet.as_view({'get': 'retrieve'}), name='plan-detail-view-set'),

    # FCM Token
    url('^update_device_detail$', staff_views.UpdateDeviceDetailViewSet.as_view({
        'get': 'retrieve', 'put': 'perform_update', 'delete': 'perform_destroy'}), name='update-device-detail'),
]

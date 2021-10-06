from django.conf.urls import url
from payments import views as payment_views
from django.urls import path

urlpatterns = [
    url('^customercreate$', payment_views.CreateStripeCustomer.as_view({'post': 'create'}), name='stripe-customer'),
    url('^card', payment_views.Card.as_view({'post': 'create', 'get': 'list', 'delete': 'destroy'}),
        name='stripe-customer'),
    path("subscription", payment_views.Subscription.as_view({"get": "list",
                                                             "post": "create", "delete": "destroy"}),
         name="subscription"),
    path('stripewebhook',payment_views.StripeWebhook.as_view(),name="stripe_webhook_success"),
]

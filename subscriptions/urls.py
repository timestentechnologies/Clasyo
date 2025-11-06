from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('plans/', views.SubscriptionPlansView.as_view(), name='plans'),
    path('subscribe/<slug:plan_slug>/', views.SubscribeView.as_view(), name='subscribe'),
    path('payment/<uuid:payment_id>/', views.PaymentView.as_view(), name='payment'),
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment_success'),
    path('payment/failed/', views.PaymentFailedView.as_view(), name='payment_failed'),
    path('my-subscription/', views.MySubscriptionView.as_view(), name='my_subscription'),
    path('renew/', views.RenewSubscriptionView.as_view(), name='renew'),
    path('cancel/', views.CancelSubscriptionView.as_view(), name='cancel'),
    path('apply-coupon/', views.ApplyCouponView.as_view(), name='apply_coupon'),
]

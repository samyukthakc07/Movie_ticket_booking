from django.urls import path
from .views import create_razorpay_order, razorpay_webhook, verify_payment

urlpatterns = [
    path('create-razorpay-order/', create_razorpay_order),
    path('webhook/', razorpay_webhook),
    path('verify-payment/', verify_payment),
]
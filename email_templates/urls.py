from django.urls import path
from .views import *

urlpatterns = [
    path("", EmailViewSet.ApplicationApproved, name='app_approved')
]
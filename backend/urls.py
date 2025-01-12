"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework import routers
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from adopters.views import AdopterViewSet
from appointment_bases.views import AppointmentBaseViewSet
from appointments.views import AppointmentViewSet
from pending_adoptions.views import PendingAdoptionViewSet
from closed_dates.views import ClosedDateViewSet
from users.views import UserProfileViewSet

router = routers.DefaultRouter()
router.register(r'Adopters', AdopterViewSet)
router.register(r'Appointments', AppointmentViewSet)
router.register(r'ClosedDates', ClosedDateViewSet)
router.register(r'PendingAdoptions', PendingAdoptionViewSet)
router.register(r'TemplateAppointments', AppointmentBaseViewSet)
router.register(r'UserProfiles', UserProfileViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('', include('email_templates.urls')),
    path('auth/token/', TokenObtainPairView.as_view()),
    path('auth/token/refresh/', TokenRefreshView.as_view()),
    path('auth/token/verify/', TokenVerifyView.as_view()),
    path('api/', include('rest_framework.urls', namespace='rest_framework'))
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

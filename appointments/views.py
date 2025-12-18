import datetime

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action

from adopters.models import Adopter
from appointment_bases.models import AppointmentBase, AppointmentTypes
from appointments.enums import OutcomeTypes
from bookings.models import Booking, BookingStatus
from closed_dates.models import ClosedDate
from email_templates.views import EmailViewSet
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from users.enums import SecurityLevels
from users.models import UserProfile
from utils.DateTimeUtils import DateTimeUtils

from .models import Appointment
from .serializers import AppointmentSerializer

# Create your views here.
class AppointmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Appointment.objects.all().order_by("instant", "type")
    serializer_class = AppointmentSerializer

    @action(detail=False, methods=["GET"], url_path="GetContextForDate")
    def GetContextForDate(self, request: HttpRequest, *args, **kwargs):
        date = DateTimeUtils.Parse(request.query_params["forDate"], "JSON").date()
        exceptions = []
        user = None

        # Get logged-in adopter's appointment or exceptions (if applicable)
        if "forUserID" in request.query_params:
            try:
                user = UserProfile.objects.get(pk=int(request.query_params["forUserID"]))

                if user.adopter_profile == None:
                    raise Exception
                
                if user.adoption_completed:
                    exceptions.append("adoptionCompleted")
                
                if user.requested_access:
                    exceptions.append("requestedAccess")

                if user.requested_surrender:
                    exceptions.append("requestedSurrender")

                user_current_appt = Booking.objects.get(
                    adopter=user.adopter_profile,
                    status=BookingStatus.ACTIVE
                ).appointment
                
                user_current_appt = AppointmentSerializer(user_current_appt).data
            except Exception:
                user_current_appt = None
        else:
            user_current_appt = None

        # See if date is closed
        try:
            closed_date = ClosedDate.objects.get(date=date).id
        except:
            closed_date = None

        # Load appointments for date
        appointments = Appointment.objects.filter(
            instant__range=DateTimeUtils.GetRangeForDate(date),
            soft_deleted=False
        )

        appointment_dict = {}
        for appointment in appointments:
            serialized = AppointmentSerializer(appointment).data
            instant_str = str(appointment.instant)
            if instant_str not in appointment_dict:
                appointment_dict[instant_str] = []
            appointment_dict[instant_str].append(serialized)
        
        adopter_flags = []
        if user and user.security_level > SecurityLevels.ADOPTER:
            adopters = [a.get_current_booking().adopter for a in appointments if a.get_current_booking()]
            
            for adopter in adopters:
                flags = adopter.get_flags()
                if len(flags) > 0:
                    adopter_flags.append({
                        "name": adopter.user_profile.full_name,
                        "summary": flags
                    })
                    # adopter_flags.append({adopter.user_profile.full_name, flags))
            
        return JsonResponse(
            {
                "adopterFlags": adopter_flags,
                "closedDateID": closed_date,
                "appointments": appointment_dict,
                "emptyDates": self.GetDatesWithNoAppointments(),
                "missingOutcomes": [AppointmentSerializer(appt).data for appt in Appointment.get_appts_missing_outcomes()],
                "userCurrentAppointment": user_current_appt,
                "userExceptions": exceptions,
            }
        )
    
    @action(detail=False, methods=["POST"], url_path="SoftDeleteAppointment")
    def SoftDeleteAppointment(self, request: HttpRequest, *args, **kwargs):
        id = request.data["appointmentID"]
        appointment = Appointment.objects.get(pk=id)
        appointment.soft_delete()

        if appointment.type == AppointmentTypes.PAPERWORK:
            try:
                adoption = PendingAdoption.objects.get(paperwork_appointment=appointment)
                adoption.paperwork_appointment = None
                adoption.save()
            except Exception as e:
                pass

        return JsonResponse(
            AppointmentSerializer(appointment).data, 
            status=status.HTTP_202_ACCEPTED
        )
    
    @action(detail=False, methods=["POST"], url_path="CancelAppointment")
    def CancelAppointment(self, request: HttpRequest, *args, **kwargs):
        # Get the appointment and booking objects
        id = request.data["appointmentID"]
        appointment = Appointment.objects.get(pk=id)
        booking = Booking.objects.get(
            appointment=appointment,
            status=BookingStatus.ACTIVE
        )

        # Email the adopter
        EmailViewSet().AppointmentCanceled(appointment)

        # Process the cancellation
        booking.mark_status(BookingStatus.CANCELLED)

        # Create short notice notification

        return JsonResponse({}, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=["POST"], url_path="CreateBatchForDate")
    def CreateBatchForDate(self, request, *args, **kwargs):
        date = DateTimeUtils.Parse(request.data["forDate"], "JSON", isUTC=True)
        template_objs = AppointmentBase.objects.filter(weekday=date.weekday())
        created_appts = []

        if template_objs.count() == 0:
            return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        for object in template_objs:
            date = date.replace(
                hour=object.time.hour, 
                minute=object.time.minute,
                second=0,
                microsecond=0
            )
            
            appointment = Appointment.objects.create(
                type=object.type,
                instant=date,        
            )
            
            created_appts.append(AppointmentSerializer(appointment).data)

        return JsonResponse({ "appointments": created_appts }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="CreateAppointment")
    def CreateAppointment(self, request, *args, **kwargs):
        date = DateTimeUtils.Parse(request.data["instant"], "JSON", isUTC=True)
        appointment = Appointment.objects.create(
            locked=request.data["locked"],
            # subtype=(request.data["subtype"] if "subtype" in request.data else None),
            type=request.data["type"],
            instant=date,
            appointment_notes=request.data["appointmentNotes"],
            surrendered_dog=request.data["surrenderedDog"],
            surrendered_dog_fka=request.data["surrenderedDogFka"]
        )

        if appointment.type == AppointmentTypes.PAPERWORK:
            adoption = PendingAdoption.objects.get(pk=request.data["paperworkAdoptionID"])
            adoption.paperwork_appointment = appointment
            adoption.save()

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_201_CREATED    
        )
    
    @action(detail=False, methods=["POST"], url_path="ToggleLock")
    def ToggleLock(self, request, *args, **kwargs):
        id = request.data["appointmentID"]

        appointment = Appointment.objects.get(pk=id)
        appointment.toggle_lock()

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_201_CREATED    
        )
        
    @action(detail=False, methods=["POST"], url_path="MarkTemplateSent")
    def MarkTemplateSent(self, request, *args, **kwargs):
        id = request.data["appointmentID"]
        template_id = request.data["templateID"]
        appointment = Appointment.objects.get(pk=id)
        booking = appointment.get_current_booking()

        booking.mark_template_sent(template_id)

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_200_OK    
        )
    
    @action(detail=False, methods=["POST"], url_path="CheckInAppointment")
    def CheckInAppointment(self, request, *args, **kwargs):
        id = request.data["appointmentID"]
        clothing = request.data["clothingDescription"]
        counselor = request.data["counselor"] if "counselor" in request.data else None

        appointment = Appointment.objects.get(pk=id)
        appointment.check_in(clothing, counselor)

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_200_OK    
        )
    
    @action(detail=False, methods=["POST"], url_path="CheckOutAppointment")
    def CheckOutAppointment(self, request, *args, **kwargs):
        id = request.data["appointmentID"]
        outcome = request.data["outcome"]
        dog = request.data["dog"] if "dog" in request.data else ""
        host_weekend = request.data["hostWeekend"] if "hostWeekend" in request.data else False

        appointment = Appointment.objects.get(pk=id)
        appointment.check_out(outcome, dog)

        if outcome == OutcomeTypes.CHOSEN:
            pending_adoption, created = PendingAdoption.objects.get_or_create(
                source_appointment=appointment,
                adopter=appointment.get_current_booking().adopter,
                dog=dog,
                circumstance=CircumstanceOptions.APPOINTMENT,
                status=PendingAdoptionStatus.CHOSEN,
                defaults={
                    "created_instant": timezone.now(),
                }
            )

            if created:
                EmailViewSet().DogChosen(appointment)
                appointment.get_current_booking().adopter.restrict_calendar()
        elif outcome == OutcomeTypes.NO_DECISION:
            try:
                pending_adoption = PendingAdoption.objects.get_or_create(
                    source_appointment=appointment
                )
                pending_adoption.status = PendingAdoptionStatus.CANCELED
                pending_adoption.save()
            except:
                pass

            EmailViewSet().NoDecision(appointment, host_weekend)
        elif outcome in [OutcomeTypes.ADOPTION, OutcomeTypes.FTA]:
            appointment.get_current_booking().adopter.restrict_calendar()

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_200_OK    
        )
        
    @action(detail=False, methods=["POST"], url_path="MarkNoShow")
    def MarkNoShow(self, request, *args, **kwargs):
        id = request.data["appointmentID"]

        appointment = Appointment.objects.get(pk=id)
        appointment.no_show()

        return JsonResponse(
            {
                "appointment": AppointmentSerializer(appointment).data
            },
            status=status.HTTP_200_OK    
        )
  
    @action(detail=False, methods=["POST"], url_path="ToggleLockForAll")
    def ToggleLockForAll(self, request, *args, **kwargs):
        isUnlock = request.data["isUnlock"]
        date = DateTimeUtils.Parse(request.data["forDate"], "JSON")

        appointments = Appointment.objects.filter(
            instant__range=DateTimeUtils.GetRangeForDate(date)
        )

        response = []

        for appointment in appointments:
            appointment.locked = not isUnlock # if isUnlock = true, then locked should be false
            appointment.save()
            response.append(AppointmentSerializer(appointment).data)
        
        return JsonResponse(
            {"appointments": response}
        )
    
    @action(detail=False, methods=["GET"], url_path="GetAppointmentsMissingOutcomes")
    def GetAppointmentsMissingOutcomes(self, request, *args, **kwargs):
        appointments = Appointment.objects.filter(
            instant__range=DateTimeUtils.GetRangeForDate(DateTimeUtils.GetToday(), backdateDays=14)
            #filter further for bookings awaiting outcomes
        )

        response = [AppointmentSerializer(appointment).data for appointment in appointments]
        
        return JsonResponse(
            {"appointments": response}
        ) 

    def GetDatesWithNoAppointments(self):
        # Loop through next two weeks to find dates where no appointments exist
        dateOffset = 0
        emptyDates = []

        while (dateOffset <= 14):
            testDate = DateTimeUtils.GetToday() + datetime.timedelta(days=dateOffset)
            dateRange = DateTimeUtils.GetRangeForDate(testDate)
            appointments = Appointment.objects.filter(instant__range=dateRange)

            if appointments.count() == 0:
                try:
                    closedDate = ClosedDate.objects.get(date=testDate)
                except ObjectDoesNotExist:
                    if testDate.weekday() < 6:
                        emptyDates.append(testDate)
            
            dateOffset += 1

        return emptyDates

    @action(detail=False, methods=["POST"], url_path="ScheduleAppointment")
    def ScheduleAppointment(self, request, *args, **kwargs):
        # Fetch the appointment and adopter
        appointment = Appointment.objects.get(pk=request.data["appointmentID"])
        adopter = Adopter.objects.get(pk=request.data["adopterID"])
        
        # Update the adopter demographics
        adopter.update_from_booking(request.data)

        if appointment.get_current_booking() is not None:
            appointment

            return JsonResponse(
                {}, 
                status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION
            )

        # Create a new booking
        booking = Booking.objects.create(
            adopter=adopter,
            appointment=appointment,
            status=BookingStatus.ACTIVE,
            created=timezone.now()
        )

        # Send email to the adopter
        EmailViewSet().AppointmentScheduled(appointment)

        # TODO: If short notice, create a short notice notification
        # NOTE: This is mostly done, but needs testing on a weekday night
        # if ShortNoticeNotification.is_short_notice(appointment.instant):
            # print("SHORT NOTICE!")
            # short_notice = ShortNoticeNotification.objects.create(
            #     target_booking=booking,
            #     type=ShortNoticeNotificationTypes.ADD,
            # )

        # TODO: Email the short notice to adoptions

        # Return success status.
        return JsonResponse({}, status=status.HTTP_201_CREATED)

    def RescheduleAppointment(self, request: HttpRequest, *args, **kwargs):
        return
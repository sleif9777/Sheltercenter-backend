import datetime
import io
from typing import Optional

from requests import Response

from adopters.enums import ApprovalStatus
from adopters.models import Adopter
from adopters.serializers import AdopterContactInfoSerializer
from appointment_bases.enums import AppointmentTypes
from appointment_bases.models import AppointmentBase
from appointments.enums import OutcomeTypes
from appointments.services import ContinuityAccessSpreadsheetService
from bookings.enums import BookingMessageTemplate
from bookings.models import Booking, BookingStatus
from closed_dates.models import ClosedDate
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from email_templates.views import EmailViewSet
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from rest_framework import status, viewsets
from rest_framework.decorators import action
from utils import DateTimeUtils
from users.enums import SecurityLevel
from users.models import UserProfile

from .mapper import AppointmentHashMapper
from .models import Appointment
from .serializers import *


# from rest_framework.response import Response


# Create your views here.
class AppointmentViewSet(viewsets.ModelViewSet):
    queryset = Appointment.objects.all().order_by("instant", "type")

    # Static methods
    @staticmethod
    def GetAppointmentFromAppointmentIDRequest(data):
        query = AppointmentIDRequestSerializer(data=data)
        query.is_valid(raise_exception=True)

        appt_id: int = int(query.validated_data["apptID"])
        appt = Appointment.objects.get(pk=appt_id)

        return appt

    @staticmethod
    def GetISODateFromISODateRequest(request) -> tuple[datetime.date, str]:
        date_key = request["isoDate"]
        query = ISODateRequestSerializer(data=request)
        query.is_valid(raise_exception=True)

        return (query.validated_data["isoDate"], date_key)

    # GET commands

    @action(detail=False, methods=["GET"], url_path="GetAppointmentCardData")
    def GetAppointmentCardData(self, request):
        appointment = self.GetAppointmentFromAppointmentIDRequest(request.query_params)

        serializer = AppointmentCardDataSerializer(appointment)

        return JsonResponse({"cardData": serializer.data}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetAppointmentsMissingOutcomes")
    def GetAppointmentsMissingOutcomes(self, request):

        appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(
                DateTimeUtils.get_today() - datetime.timedelta(days=1), backdate_days=13
            ),
            outcome=None,
        )

        serialized_appts = [
            AppointmentMissingOutcomeSerializer(appt).data
            for appt in appts
            if appt.has_current_booking
        ]

        return JsonResponse(
            {"appts": serialized_appts},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetContextForDate")
    def GetContextForDate(self, request):
        date, date_key = AppointmentViewSet.GetISODateFromISODateRequest(request.query_params)

        appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(date), soft_deleted=False
        )

        appt_hash = AppointmentHashMapper.map_appointments(appts) if appts.count() > 0 else None
        has_available_appts = (
            len(
                [
                    appt
                    for appt in appts
                    if appt.is_adoption_appointment and not appt.has_current_booking
                ]
            )
            > 0
        )
        is_closed_date = ClosedDate.exists_for_date(date)

        return JsonResponse(
            {
                "apptHash": appt_hash,
                "hasAvailableAppts": has_available_appts,
                "isClosedDate": is_closed_date,
                "isoDate": date_key,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetContinuityAccessSpreadsheet")
    def GetContinuityAccessSpreadsheet(self, request):
        date, _ = AppointmentViewSet.GetISODateFromISODateRequest(request.query_params)
        service = ContinuityAccessSpreadsheetService(date)
        spreadsheet = service.create_schedule_export()

        # Return as downloadable file
        response = HttpResponse(
            spreadsheet.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="schedule_export_{DateTimeUtils.get_iso_date(DateTimeUtils.get_now())}.xlsx"'
        )

        return response

    @action(detail=False, methods=["GET"], url_path="GetEmptyDates")
    def GetEmptyDates(self, request):
        emptyDates: list[str] = []
        today = DateTimeUtils.get_today()

        for offset in range(15):
            testDate = today + datetime.timedelta(days=offset)
            dateRange = DateTimeUtils.get_range_for_date(testDate)

            hasAppointments = Appointment.objects.filter(instant__range=dateRange).exists()

            isClosed = ClosedDate.objects.filter(date=testDate).exists()

            if not hasAppointments and not isClosed and testDate.weekday() < 6:
                emptyDates.append(testDate.isoformat())

        return JsonResponse(
            {
                "emptyDates": emptyDates,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["GET"], url_path="GetRecentAdoptions")
    def GetRecentAdoptions(self, request):
        adoption_outcome_appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(timezone.now(), backdate_days=10),
            outcome__in=[OutcomeTypes.ADOPTION, OutcomeTypes.FTA],
            soft_deleted=False,
        )

        paperwork_appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(timezone.now(), backdate_days=10),
            type=AppointmentTypes.PAPERWORK,
            soft_deleted=False,
        )

        all_serialized_adoptions = [
            {
                "instant": appt.iso_date,
                "adopter": (
                    AdopterContactInfoSerializer(appt.get_current_booking().adopter).data
                    if appt.is_adoption_appointment
                    else AdopterContactInfoSerializer(appt.paperwork_adoption.adopter).data
                ),
                "dog": (
                    appt.chosen_dog if appt.is_adoption_appointment else appt.paperwork_adoption.dog
                ),
            }
            for appt in (adoption_outcome_appts | paperwork_appts)
        ]

        all_serialized_adoptions = sorted(all_serialized_adoptions, key=lambda a: a["instant"])
        all_serialized_adoptions.reverse()

        return JsonResponse({"adoptions": all_serialized_adoptions}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetReportingAppointment")
    def GetReportingAppointment(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.query_params)

        if appt.is_adoption_appointment:
            serializer = ReportingAdoptionAppointmentSerializer(appt)
        else:
            serializer = ReportingAdminAppointmentSerializer(appt)

        return JsonResponse(
            {
                "apptData": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    # POST commands

    @action(detail=False, methods=["POST"], url_path="CancelAllAndClose")
    def CancelAllAndClose(self, request):
        date, _ = AppointmentViewSet.GetISODateFromISODateRequest(request.data)
        dateRange = DateTimeUtils.get_range_for_date(date)
        appts = Appointment.objects.filter(instant__range=dateRange)

        for appt in appts:
            booking = appt.get_current_booking()

            if booking:
                booking.mark_status(BookingStatus.CANCELLED)
                EmailViewSet().AppointmentCanceled(
                    appt
                )  # TODO: this should be a different email template for mass cancellations

            appt.soft_delete()

        ClosedDate.objects.get_or_create(date=date)

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="CancelAppointment")
    def CancelAppointment(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.data)
        booking = Booking.objects.get(appointment=appt, status=BookingStatus.ACTIVE)

        # Email the adopter
        EmailViewSet().AppointmentCanceled(appt)

        # Process the cancellation
        booking.mark_status(BookingStatus.CANCELLED)

        # Create short notice notification

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="CheckInAppointment")
    def CheckInAppointment(self, request):
        query = CheckInAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        id = query.validated_data["apptID"]

        appt: Appointment = Appointment.objects.get(pk=id)

        if not appt.get_current_booking():
            return JsonResponse({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        appt.check_in(query.validated_data)

        adopter: Adopter = appt.get_current_booking().adopter
        adopter.update_address(query.validated_data)

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="CheckOutAppointment")
    def CheckOutAppointment(self, request):
        query = CheckOutAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        id = query.validated_data["apptID"]
        outcome = query.validated_data["outcome"]
        dog = query.validated_data["dog"]
        send_sleepover_info = query.validated_data["sendSleepoverInfo"]

        if dog.isupper() or dog.islower():
            dog = (
                dog.title()
            )  # if dog is all upper or lower case, convert to title case for consistency

        appt = Appointment.objects.get(pk=id)
        appt.check_out(outcome, dog)

        if outcome == OutcomeTypes.CHOSEN:
            # create pending adoption
            pending_adoption, created = PendingAdoption.objects.update_or_create(
                source_appointment=appt,
                defaults={
                    "adopter": appt.get_current_booking().adopter,
                    "circumstance": CircumstanceOptions.APPOINTMENT,
                    "created_instant": timezone.now(),
                    "dog": dog,
                    "source_appointment": appt,
                    "status": PendingAdoptionStatus.CHOSEN,
                },
                create_defaults={
                    "adopter": appt.get_current_booking().adopter,
                    "circumstance": CircumstanceOptions.APPOINTMENT,
                    "created_instant": timezone.now(),
                    "dog": dog,
                    "source_appointment": appt,
                    "status": PendingAdoptionStatus.CHOSEN,
                },
            )

            # email confirmation and lock calendar
            if created:
                EmailViewSet().DogChosen(appt)
                appt.get_current_booking().adopter.restrict_calendar()
        elif outcome == OutcomeTypes.NO_DECISION:
            try:
                # find pending adoption and mark canceled
                pending_adoption = PendingAdoption.objects.get_or_create(source_appointment=appt)
                pending_adoption.status = PendingAdoptionStatus.CANCELED
                pending_adoption.save()

                # restore calendar access
                pending_adoption.adopter.restrict_calendar(restrict=False)
            except:
                pass

            EmailViewSet().NoDecision(appt, send_sleepover_info)
        elif outcome in [OutcomeTypes.ADOPTION, OutcomeTypes.FTA]:
            appt.get_current_booking().adopter.restrict_calendar()

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="CreateAppointment")
    def CreateAppointment(self, request):
        query = CreateAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        date = query.validated_data["isoDate"]
        hour = query.validated_data["hour"]
        minute = query.validated_data["minute"]
        instant = timezone.make_aware(
            datetime.datetime(
                date.year,
                date.month,
                date.day,
                hour,
                minute,
            )
        )

        type = query.validated_data["type"]
        notes = query.validated_data["notes"] if "notes" in query.validated_data else ""
        fka = query.validated_data["fka"] if "fka" in query.validated_data else ""
        locked = query.validated_data["locked"]
        pending_adoption_id = (
            query.validated_data["pendingAdoptionID"]
            if "pendingAdoptionID" in query.validated_data
            else 0
        )

        adoption = None
        is_paperwork_appt = type == AppointmentTypes.PAPERWORK

        if is_paperwork_appt and pending_adoption_id > 0:
            adoption = PendingAdoption.objects.get(pk=pending_adoption_id)

        appointment = Appointment.objects.create(
            locked=locked,
            type=type,
            instant=instant,
            appointment_notes=(
                notes
                if type in [AppointmentTypes.VISIT, AppointmentTypes.DONATION_DROP_OFF]
                else adoption.dog if is_paperwork_appt else ""
            ),
            surrendered_dog=(notes if type == AppointmentTypes.SURRENDER else ""),
            surrendered_dog_fka=(fka if type == AppointmentTypes.SURRENDER else ""),
        )

        if adoption:
            adoption.paperwork_appointment = appointment
            adoption.save()

        return JsonResponse({}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="CreateBatchForDate")
    def CreateBatchForDate(self, request):
        isoDate = request.data["isoDate"]
        [year, month, day] = [int(i) for i in isoDate.split("-")]

        weekday = datetime.date(year, month, day).weekday()
        template_objs = AppointmentBase.objects.filter(weekday=weekday)

        if template_objs.count() == 0:
            return JsonResponse({}, status=status.HTTP_200_OK)

        created_appts = []

        for object in template_objs:
            # Create a naive datetime first
            naive_dt = datetime.datetime(
                year=year,
                month=month,
                day=day,
                hour=object.time.hour,
                minute=object.time.minute,
                second=0,
                microsecond=0,
            )

            # Make it timezone-aware using Django's current timezone
            instant = timezone.make_aware(naive_dt)

            appointment = Appointment.objects.create(
                type=object.type,
                instant=instant,
            )

            created_appts.append(AppointmentCardDataSerializer(appointment).data)

        return JsonResponse({}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="CreateWalkIn")
    def CreateWalkIn(self, request):
        query = CreateWalkInRequestSerializer(data=request.data)
        try:
            query.is_valid(raise_exception=True)
        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

        adopter_id = query.validated_data.get("adopterID", "*")
        type = query.validated_data["type"]

        # TODO: this should probably be in the user factory classes
        if adopter_id == "*":
            adopter_email = query.validated_data.get("primaryEmail", "")
            adopter_first_name = query.validated_data.get("firstName", "")
            adopter_last_name = query.validated_data.get("lastName", "")

            if "" in [adopter_email, adopter_first_name, adopter_last_name]:
                return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)

            adopter, _ = Adopter.objects.update_or_create(
                primary_email=adopter_email.lower(),
                defaults={"status": ApprovalStatus.APPROVED},
                create_defaults={
                    "approved_until": Adopter.get_default_approval_date(),
                    "status": ApprovalStatus.APPROVED,
                },
            )

            UserProfile.objects.update_or_create(
                primary_email=adopter_email.lower(),
                defaults={
                    "first_name": adopter_first_name.title(),
                    "last_name": adopter_last_name.title(),
                    "archived": False,
                },
                create_defaults={
                    "adopter_profile": adopter,
                    "first_name": adopter_first_name.title(),
                    "last_name": adopter_last_name.title(),
                    "security_level": SecurityLevel.ADOPTER,
                },
            )
        else:
            adopter = Adopter.objects.get(pk=adopter_id)

        now = timezone.localtime(timezone.now())
        instant = now.replace(
            minute=(now.minute // 15) * 15,
            second=0,
            microsecond=0,
        )

        adopter.internal_notes = "Walk-in ({0})".format(instant.date().isoformat())
        adopter.save()

        appt = Appointment.objects.create(
            locked=True,
            type=type,
            instant=instant,
        )

        Booking.objects.create(
            adopter=adopter, appointment=appt, status=BookingStatus.ACTIVE, created=timezone.now()
        )

        return JsonResponse({}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="MarkNoShow")
    def MarkNoShow(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.data)
        appt.no_show()

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="MarkTemplateSent")
    def MarkTemplateSent(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.data)
        template_id: BookingMessageTemplate = request.data["templateID"]
        booking: Optional["Booking"] = appt.get_current_booking()

        booking.mark_template_sent(template_id)

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="ScheduleAppointment")
    def ScheduleAppointment(self, request):
        query = ScheduleAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        # Fetch the appointment and adopter
        appt = Appointment.objects.get(pk=request.data["apptID"])
        adopter = Adopter.objects.get(pk=request.data["adopterID"])

        # Update the adopter demographics
        if len(data.keys()) > 2:  # More than just apptID and adopterID
            adopter.update_preferences(data)

        if appt.get_current_booking() is not None:
            return JsonResponse({}, status=status.HTTP_203_NON_AUTHORITATIVE_INFORMATION)

        # Create a new booking
        Booking.objects.create(
            adopter=adopter, appointment=appt, status=BookingStatus.ACTIVE, created=timezone.now()
        )

        # Send email to the adopter
        EmailViewSet().AppointmentScheduled(appt)

        # TODO: If short notice, create a short notice notification
        # NOTE: This is mostly done, but needs testing on a weekday night
        # if ShortNoticeNotification.is_short_notice(appointment.instant):
        # short_notice = ShortNoticeNotification.objects.create(
        #     target_booking=booking,
        #     type=ShortNoticeNotificationTypes.ADD,
        # )

        # TODO: Email the short notice to adoptions

        # Return success status.
        return JsonResponse({}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["POST"], url_path="SoftDeleteAppointment")
    def SoftDeleteAppointment(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.data)
        appt.soft_delete()

        if appt.is_paperwork_appointment:
            try:
                adoption = PendingAdoption.objects.get(paperwork_appointment=appt)
                adoption.paperwork_appointment = None
                adoption.save()
            except:
                pass

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="ToggleLockForDate")
    def ToggleLockForDate(self, request):
        date_obj, _ = self.GetISODateFromISODateRequest(request.data)
        is_unlock: bool = request.data["isUnlock"]

        appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(date_obj)
        )

        for appt in appts:
            appt.toggle_lock(override=(not is_unlock))

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="ToggleLockForSingleAppt")
    def ToggleLockForSingleAppt(self, request):
        appt = self.GetAppointmentFromAppointmentIDRequest(request.data)
        appt.toggle_lock()

        return JsonResponse({}, status=status.HTTP_200_OK)

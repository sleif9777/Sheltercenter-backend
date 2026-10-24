import datetime
import io
import logging
from typing import Optional

from django.db.models import Count
from django.db.models.functions import ExtractWeekDay

logger = logging.getLogger(__name__)

from requests import Response

from adopters.enums import ApprovalStatus
from adopters.models import Adopter, AdopterUploadEvent
from adopters.serializers import AdopterContactInfoSerializer
from appointment_bases.enums import AppointmentTypes
from appointment_bases.models import AppointmentBase
from appointments.enums import NoDecisionEmailOption, OutcomeTypes
from appointments.services import ContinuityAccessSpreadsheetService, ReportingStatsExportService
from bookings.enums import BookingMessageTemplate
from bookings.models import Booking, BookingStatus
from closed_dates.models import ClosedDate
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from dogs.models import Dog
from email_templates.views import EmailViewSet
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from utils import DateTimeUtils
from users.enums import SecurityLevel
from users.models import UserProfile
from users.permissions import AnySecurityLevel, MinSecurityLevel

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

        serializer = AppointmentCardDataSerializer(appointment, context={"request": request})

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
            instant__range=DateTimeUtils.get_range_for_date(date),
            soft_deleted=False,
            primary_appointment__isnull=True,
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

    @action(detail=False, methods=["GET"], url_path="GetOpenAdoptionSlots", permission_classes=[AnySecurityLevel(SecurityLevel.ADMIN, SecurityLevel.SUPERUSER)])
    def GetOpenAdoptionSlots(self, request):
        date, date_key = AppointmentViewSet.GetISODateFromISODateRequest(request.query_params)

        appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(date),
            instant__gte=timezone.now(),
            soft_deleted=False,
        ).order_by("instant", "type")

        # One open appointment per type per timeslot, preferring an unlocked one
        slots: dict[int, dict] = {}
        for appt in appts:
            if not appt.is_adoption_appointment or appt.has_current_booking:
                continue

            local_dt = appt.local_dt
            key = (local_dt.hour * 100) + local_dt.minute
            slot = slots.setdefault(
                key, {"key": key, "label": appt.time_display.lstrip("0"), "appts": {}}
            )

            current = slot["appts"].get(appt.type)
            if current is None or (current["locked"] and not appt.locked):
                slot["appts"][appt.type] = {
                    "ID": appt.id,
                    "typeDisplay": appt.type_display,
                    "locked": appt.locked,
                }

        for slot in slots.values():
            slot["appts"] = list(slot["appts"].values())

        return JsonResponse(
            {"isoDate": date_key, "slots": list(slots.values())},
            status=status.HTTP_200_OK,
        )

    QUEUE_CUTOFF_KEY = 1600

    # Mirrors DateTime.IsClosedForBooking on the frontend
    ADOPTER_BOOKING_CUTOFF = datetime.timedelta(hours=2)

    @staticmethod
    def _get_queue_bookings_for_date(date: datetime.date) -> list[Booking]:
        """Active adoption bookings for the X-in-Queue email, in default queue order.

        The queue runs through the 4:00 PM slot, or the first slot after it when there
        is no 4:00 PM slot, or the last slot when the day ends earlier.
        """
        appts = [
            appt
            for appt in Appointment.objects.filter(
                instant__range=DateTimeUtils.get_range_for_date(date), soft_deleted=False
            ).order_by("instant")
            if appt.is_adoption_appointment
        ]

        def slot_key(appt: Appointment) -> int:
            return (appt.local_dt.hour * 100) + appt.local_dt.minute

        keys = sorted({slot_key(appt) for appt in appts})
        if not keys:
            return []

        later_keys = [k for k in keys if k >= AppointmentViewSet.QUEUE_CUTOFF_KEY]
        cutoff = later_keys[0] if later_keys else keys[-1]

        bookings = Booking.objects.filter(
            appointment__in=[appt for appt in appts if slot_key(appt) <= cutoff],
            status=BookingStatus.ACTIVE,
        ).select_related("appointment", "adopter__user_profile")

        return sorted(bookings, key=lambda b: (b.appointment.instant, b.created))

    @action(detail=False, methods=["GET"], url_path="GetQueueForDate", permission_classes=[AnySecurityLevel(SecurityLevel.ADMIN, SecurityLevel.SUPERUSER)])
    def GetQueueForDate(self, request):
        date, date_key = AppointmentViewSet.GetISODateFromISODateRequest(request.query_params)

        queue = [
            {
                "apptID": booking.appointment.id,
                "adopterName": booking.adopter.user_profile.full_name,
                "timeDisplay": booking.appointment.time_display.lstrip("0"),
                "typeDisplay": booking.appointment.type_display,
                "bookedDisplay": booking.created_display,
                "alreadySent": booking.sent_x_in_queue,
            }
            for booking in self._get_queue_bookings_for_date(date)
        ]

        return JsonResponse({"isoDate": date_key, "queue": queue}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetRecentAdoptions")
    def GetRecentAdoptions(self, request):
        adoption_outcome_appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(timezone.now(), backdate_days=10),
            outcome__in=[OutcomeTypes.ADOPTION, OutcomeTypes.FTA],
            soft_deleted=False,
        ).prefetch_related("bookings__adopter")

        paperwork_appts = Appointment.objects.filter(
            instant__range=DateTimeUtils.get_range_for_date(timezone.now(), backdate_days=10),
            type=AppointmentTypes.PAPERWORK,
            soft_deleted=False,
        ).select_related("paperwork_adoption__adopter")

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
        appts = Appointment.objects.filter(
            instant__range=dateRange, primary_appointment__isnull=True
        )

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

    @staticmethod
    def _get_active_booking_by_token(token: str) -> Optional[Booking]:
        try:
            return Booking.objects.select_related("appointment").get(
                cancel_token=token,
                status=BookingStatus.ACTIVE,
                cancel_token_expires_at__gt=timezone.now(),
            )
        except Booking.DoesNotExist:
            return None

    @action(detail=False, methods=["GET"], url_path="GetByToken", permission_classes=[AllowAny])
    def GetByToken(self, request):
        token = request.query_params.get("token")
        if not token:
            return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)

        booking = self._get_active_booking_by_token(token)
        if booking is None:
            return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        return JsonResponse(
            {"instantDisplay": booking.appointment.instant_display},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["POST"], url_path="CancelByToken", permission_classes=[AllowAny])
    def CancelByToken(self, request):
        token = request.data.get("token")
        if not token:
            return JsonResponse({}, status=status.HTTP_400_BAD_REQUEST)

        booking = self._get_active_booking_by_token(token)
        if booking is None:
            return JsonResponse({}, status=status.HTTP_404_NOT_FOUND)

        appt = booking.appointment
        EmailViewSet().AppointmentCanceled(appt)
        booking.mark_status(BookingStatus.CANCELLED)

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

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="CheckOutAppointment")
    @transaction.atomic
    def CheckOutAppointment(self, request):
        query = CheckOutAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        id = query.validated_data["apptID"]
        outcome = query.validated_data["outcome"]
        dogID = query.validated_data["dogID"]
        no_decision_email_option = query.validated_data["noDecisionEmailOption"]
        second_outcome = query.validated_data.get("secondOutcome")
        second_dog_id = query.validated_data.get("secondDogID")

        appt = Appointment.objects.get(pk=id)

        if appt.is_second_dog_appointment:
            return JsonResponse(
                {"detail": "Edit the second dog from the original appointment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_second_dog_appt = appt.get_second_dog_appointment()
        second_dog_adoption_canceled = False

        if (
            second_dog_id is not None
            and outcome == OutcomeTypes.NO_DECISION
            and existing_second_dog_appt is None
        ):
            return JsonResponse(
                {"secondDogID": [SECOND_DOG_NEEDS_DOG_CHOICE]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Remove a second dog that was unchecked before processing the first dog, so the
        # calendar-unlock check for the first dog doesn't see the second dog's adoption.
        if second_dog_id is None and existing_second_dog_appt is not None:
            second_dog_adoption_canceled = AppointmentViewSet._remove_second_dog_appointment(
                existing_second_dog_appt
            )

        AppointmentViewSet._check_out_with_outcome(
            appt,
            outcome,
            dogID,
            no_decision_email_option,
            adoption_canceled_elsewhere=second_dog_adoption_canceled,
        )

        if second_dog_id is not None:
            second_dog_appt = (
                existing_second_dog_appt or AppointmentViewSet._create_second_dog_appointment(appt)
            )
            AppointmentViewSet._check_out_with_outcome(
                second_dog_appt, second_outcome, second_dog_id, NoDecisionEmailOption.NO_EMAIL
            )

        return JsonResponse({}, status=status.HTTP_200_OK)

    @staticmethod
    def _check_out_with_outcome(
        appt: Appointment,
        outcome: int,
        dogID: Optional[int],
        no_decision_email_option: int,
        adoption_canceled_elsewhere: bool = False,
    ) -> None:
        dog = Dog.objects.get(pk=dogID).name if dogID else ""
        appt.check_out(outcome, dog, dogID)
        adopter = appt.get_current_booking().adopter

        if outcome == OutcomeTypes.CHOSEN:
            # create pending adoption
            pending_adoption, created = PendingAdoption.objects.update_or_create(
                source_appointment=appt,
                defaults={
                    "adopter": adopter,
                    "circumstance": CircumstanceOptions.APPOINTMENT,
                    "created_instant": timezone.now(),
                    "dog": dog,
                    "dogID": dogID,
                    "source_appointment": appt,
                    "status": PendingAdoptionStatus.CHOSEN,
                },
            )

            # email confirmation and lock calendar
            if created:
                EmailViewSet().DogChosen(appt)
                adopter.restrict_calendar()
        elif outcome == OutcomeTypes.NO_DECISION:
            # find pending adoption and mark canceled
            canceled = AppointmentViewSet._cancel_open_adoption(appt) or adoption_canceled_elsewhere

            # restore calendar access unless another dog is still pending
            if canceled and not PendingAdoption.adopter_has_open_adoption(adopter):
                adopter.restrict_calendar(restrict=False)

            if no_decision_email_option != NoDecisionEmailOption.NO_EMAIL:
                send_sleepover_info = no_decision_email_option == NoDecisionEmailOption.WITH_SLEEPOVER
                EmailViewSet().NoDecision(appt, send_sleepover_info)
        elif outcome in [OutcomeTypes.ADOPTION, OutcomeTypes.FTA]:
            adopter.restrict_calendar()

    @staticmethod
    def _cancel_open_adoption(appt: Appointment) -> bool:
        adoption = (
            PendingAdoption.objects.filter(source_appointment=appt)
            .exclude(status__in=[PendingAdoptionStatus.CANCELED, PendingAdoptionStatus.COMPLETED])
            .first()
        )

        if adoption is None:
            return False

        adoption.mark_status(PendingAdoptionStatus.CANCELED)
        return True

    @staticmethod
    def _create_second_dog_appointment(primary: Appointment) -> Appointment:
        second_dog_appt = Appointment.objects.create(
            type=primary.type,
            instant=primary.instant,
            locked=True,
            primary_appointment=primary,
            check_in_time=primary.check_in_time,
            clothing_description=primary.clothing_description,
            counselor=primary.counselor,
        )
        Booking.create_active(primary.get_current_booking().adopter, second_dog_appt)

        return second_dog_appt

    @staticmethod
    def _remove_second_dog_appointment(second_dog_appt: Appointment) -> bool:
        """Cancels the second dog's adoption and hides the placeholder.

        Returns True if an adoption was canceled.
        """
        canceled = AppointmentViewSet._cancel_open_adoption(second_dog_appt)

        booking = second_dog_appt.get_current_booking()
        if booking is not None:
            booking.mark_status(BookingStatus.CANCELLED)

        second_dog_appt.soft_delete()

        return canceled

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
        notes = query.validated_data.get("notes", "")
        fka = query.validated_data.get("fka", "")
        locked = query.validated_data["locked"]
        pending_adoption_id = query.validated_data.get("pendingAdoptionID", 0)
        surrender_dog_name = query.validated_data.get("surrenderDogName", "")

        adoption = None
        is_paperwork_appt = type == AppointmentTypes.PAPERWORK
        is_surrender_appt = type == AppointmentTypes.SURRENDER

        if is_paperwork_appt and pending_adoption_id > 0:
            adoption = PendingAdoption.objects.get(pk=pending_adoption_id)

        appointment = Appointment.objects.create(
            locked=locked,
            type=type,
            instant=instant,
            appointment_notes=(
                adoption.dog if (is_paperwork_appt and adoption is not None) else notes or ""
            ),
            surrendered_dog=(surrender_dog_name if is_surrender_appt else ""),
            surrendered_dog_fka=(fka if is_surrender_appt else ""),
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

            adopter, adopter_created = Adopter.objects.update_or_create(
                primary_email=adopter_email.lower(),
                defaults={"status": ApprovalStatus.APPROVED},
                create_defaults={
                    "approved_until": Adopter.get_default_approval_date(),
                    "status": ApprovalStatus.APPROVED,
                },
            )

            try:
                UserProfile.objects.update_or_create(
                    primary_email=adopter_email.lower(),
                    defaults={
                        "adopter_profile": adopter,
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
            except Exception:
                if adopter_created:
                    adopter.delete()
                return JsonResponse({}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            adopter = Adopter.objects.get(pk=adopter_id)

        if adopter.has_current_booking:
            return JsonResponse({}, status=status.HTTP_409_CONFLICT)

        appt_date = query.validated_data["isoDate"]
        hour = query.validated_data["hour"]
        minute = query.validated_data["minute"]
        instant = timezone.make_aware(
            datetime.datetime(appt_date.year, appt_date.month, appt_date.day, hour, minute, 0, 0)
        )

        adopter.internal_notes = "Walk-in ({0})".format(instant.date().isoformat())
        adopter.save()

        appt = Appointment.objects.create(
            locked=True,
            type=type,
            instant=instant,
        )

        Booking.create_active(adopter, appt)

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

    @action(detail=False, methods=["POST"], url_path="RescheduleAppointment", permission_classes=[AnySecurityLevel(SecurityLevel.ADMIN, SecurityLevel.SUPERUSER)])
    @transaction.atomic
    def RescheduleAppointment(self, request):
        query = RescheduleAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        # Lock both rows so the target slot can't be booked out from under us
        old_appt = Appointment.objects.select_for_update().get(pk=query.validated_data["apptID"])
        new_appt = Appointment.objects.select_for_update().get(
            pk=query.validated_data["newApptID"]
        )

        booking = Booking.objects.filter(appointment=old_appt, status=BookingStatus.ACTIVE).first()

        if booking is None or old_appt.check_in_time is not None or old_appt.outcome is not None:
            return JsonResponse(
                {"error": "This appointment can no longer be rescheduled."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            new_appt.pk == old_appt.pk
            or new_appt.soft_deleted
            or not new_appt.is_adoption_appointment
            or new_appt.instant < timezone.now()
            or new_appt.get_current_booking() is not None
        ):
            return JsonResponse(
                {"error": "That timeslot is no longer available."},
                status=status.HTTP_409_CONFLICT,
            )

        booking.reschedule_to(new_appt)

        EmailViewSet().AppointmentRescheduled(old_appt, new_appt)

        return JsonResponse({}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="SendQueueEmails", permission_classes=[AnySecurityLevel(SecurityLevel.ADMIN, SecurityLevel.SUPERUSER)])
    def SendQueueEmails(self, request):
        query = SendQueueEmailsRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)

        signature = request.user.full_name.strip() or "The Adoptions Team"
        sent, failed = 0, []

        for entry in query.validated_data["entries"]:
            appt = Appointment.objects.get(pk=entry["apptID"])
            booking = Booking.objects.filter(appointment=appt, status=BookingStatus.ACTIVE).first()

            if booking is None:
                failed.append(appt.description)
                continue

            try:
                EmailViewSet().XInQueue(appt, entry["position"], signature)
                booking.mark_template_sent(BookingMessageTemplate.X_IN_QUEUE)
                sent += 1
            except Exception:
                logger.exception("Failed to send X-in-Queue email for appointment %s", appt.id)
                failed.append(appt.description)

        return JsonResponse({"sent": sent, "failed": failed}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["POST"], url_path="ScheduleAppointment")
    @transaction.atomic
    def ScheduleAppointment(self, request):
        query = ScheduleAppointmentRequestSerializer(data=request.data)
        query.is_valid(raise_exception=True)
        data = query.validated_data

        # Fetch and lock the appointment and adopter rows to prevent concurrent bookings
        appt = Appointment.objects.select_for_update().get(pk=request.data["apptID"])
        adopter = Adopter.objects.select_for_update().get(pk=request.data["adopterID"])

        # Adopters can't book inside the cutoff window; staff may still book late walk-ups
        is_adopter = request.user.security_level == SecurityLevel.ADOPTER
        if is_adopter and appt.instant - timezone.now() < self.ADOPTER_BOOKING_CUTOFF:
            return JsonResponse(
                {
                    "error": "Appointments must be booked at least 2 hours in advance. "
                    "Please choose a later time."
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Update the adopter demographics
        if len(data.keys()) > 2:  # More than just apptID and adopterID
            adopter.update_preferences(data)

        if adopter.has_current_booking:
            return JsonResponse({}, status=status.HTTP_409_CONFLICT)

        if adopter.user_profile.adoption_completed:
            return JsonResponse({}, status=status.HTTP_403_FORBIDDEN)

        if appt.get_current_booking() is not None:
            return JsonResponse({}, status=status.HTTP_409_CONFLICT)

        # Create a new booking
        Booking.create_active(adopter, appt)

        # Send email to the adopter
        EmailViewSet().AppointmentScheduled(appt)

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
            except PendingAdoption.DoesNotExist:
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

    @staticmethod
    def _compute_reporting_stats() -> dict:
        today = DateTimeUtils.get_today()
        py_same_day = today.replace(year=today.year - 1)

        ranges = {
            "ytd": (datetime.date(today.year, 1, 1), today),
            "pytd": (datetime.date(today.year - 1, 1, 1), py_same_day),
            "prev_year": (datetime.date(today.year - 1, 1, 1), datetime.date(today.year - 1, 12, 31)),
            "current_month": (datetime.date(today.year, today.month, 1), today),
            "current_month_py": (
                datetime.date(today.year - 1, today.month, 1),
                datetime.date(today.year - 1, today.month, today.day),
            ),
        }

        adoption_types = [
            AppointmentTypes.ADULTS,
            AppointmentTypes.PUPPIES,
            AppointmentTypes.ALL_AGES,
            AppointmentTypes.FUN_SIZE,
        ]

        periods = {}
        for key, (start, end) in ranges.items():
            appts_qs = Appointment.objects.filter(
                type__in=adoption_types,
                soft_deleted=False,
                primary_appointment__isnull=True,
                outcome__isnull=False,
                instant__date__gte=start,
                instant__date__lte=end,
            )
            hw_qs = PendingAdoption.objects.filter(
                source_appointment__instant__date__gte=start,
                source_appointment__instant__date__lte=end,
            )
            visitors = (
                Booking.objects.filter(
                    status=BookingStatus.COMPLETED,
                    appointment__instant__date__gte=start,
                    appointment__instant__date__lte=end,
                )
                .values("adopter_id")
                .distinct()
                .count()
            )
            adopters_count = (
                Booking.objects.filter(
                    status=BookingStatus.COMPLETED,
                    appointment__outcome=OutcomeTypes.ADOPTION,
                    appointment__instant__date__gte=start,
                    appointment__instant__date__lte=end,
                )
                .values("adopter_id")
                .distinct()
                .count()
            )
            periods[key] = {
                "total": appts_qs.count(),
                "adoptions": appts_qs.filter(outcome=OutcomeTypes.ADOPTION).count(),
                "chosen": appts_qs.filter(outcome=OutcomeTypes.CHOSEN).count(),
                "fta": appts_qs.filter(outcome=OutcomeTypes.FTA).count(),
                "no_decision": appts_qs.filter(outcome=OutcomeTypes.NO_DECISION).count(),
                "no_show": appts_qs.filter(outcome=OutcomeTypes.NO_SHOW).count(),
                "hw_positive": hw_qs.filter(heartworm_positive=True).count(),
                "hw_negative": hw_qs.filter(heartworm_positive=False).count(),
                "applications": AdopterUploadEvent.objects.filter(
                    uploaded_at__date__gte=start,
                    uploaded_at__date__lte=end,
                ).count(),
                "visitors": visitors,
                "adopters": adopters_count,
            }

        adopted_adopter_ids = set(
            Booking.objects.filter(
                status=BookingStatus.COMPLETED,
                appointment__outcome=OutcomeTypes.ADOPTION,
            ).values_list("adopter_id", flat=True)
        )
        visit_counts = list(
            Booking.objects.filter(
                status=BookingStatus.COMPLETED,
                adopter_id__in=adopted_adopter_ids,
                appointment__primary_appointment__isnull=True,
            )
            .values("adopter_id")
            .annotate(count=Count("id"))
        )
        avg_visits = (
            round(sum(v["count"] for v in visit_counts) / len(visit_counts), 1) if visit_counts else 0.0
        )

        all_visitor_ids = set(
            Booking.objects.filter(status=BookingStatus.COMPLETED).values_list("adopter_id", flat=True)
        )
        visitors_never_adopted = len(all_visitor_ids - adopted_adopter_ids)

        return {
            "periods": periods,
            "global": {
                "avg_visits_before_adopting": avg_visits,
                "visitors_never_adopted": visitors_never_adopted,
            },
        }

    @action(detail=False, methods=["GET"], url_path="GetReportingStats", permission_classes=[MinSecurityLevel(SecurityLevel.ADMIN)])
    def GetReportingStats(self, request):
        return JsonResponse(AppointmentViewSet._compute_reporting_stats(), status=status.HTTP_200_OK)

    @action(detail=False, methods=["GET"], url_path="GetReportingStatsExport", permission_classes=[MinSecurityLevel(SecurityLevel.ADMIN)])
    def GetReportingStatsExport(self, request):
        stats = AppointmentViewSet._compute_reporting_stats()
        buffer = ReportingStatsExportService(stats["periods"], stats["global"]).build()
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = (
            f'attachment; filename="reporting_stats_{DateTimeUtils.get_iso_date(DateTimeUtils.get_now())}.xlsx"'
        )
        return response

    @action(detail=False, methods=["GET"], url_path="GetDayOfWeekStats", permission_classes=[MinSecurityLevel(SecurityLevel.ADMIN)])
    def GetDayOfWeekStats(self, request):
        adoption_types = [
            AppointmentTypes.ADULTS,
            AppointmentTypes.PUPPIES,
            AppointmentTypes.ALL_AGES,
            AppointmentTypes.FUN_SIZE,
        ]

        today = DateTimeUtils.get_today()
        py_same_day = today.replace(year=today.year - 1)

        date_ranges = {
            "ytd": (datetime.date(today.year, 1, 1), today),
            "pytd": (datetime.date(today.year - 1, 1, 1), py_same_day),
            "prev_year": (datetime.date(today.year - 1, 1, 1), datetime.date(today.year - 1, 12, 31)),
        }

        # Django's ExtractWeekDay: 1=Sunday, 2=Monday, ..., 7=Saturday
        DAY_NAMES = {1: "Sun", 2: "Mon", 3: "Tue", 4: "Wed", 5: "Thu", 6: "Fri", 7: "Sat"}

        periods = {}
        for period_key, (start, end) in date_ranges.items():
            base_qs = Appointment.objects.filter(
                type__in=adoption_types,
                soft_deleted=False,
                primary_appointment__isnull=True,
                outcome__isnull=False,
                instant__date__gte=start,
                instant__date__lte=end,
            ).annotate(dow=ExtractWeekDay("instant"))

            rows = {}
            for dow_num, day_name in DAY_NAMES.items():
                day_qs = base_qs.filter(dow=dow_num)
                rows[day_name] = {
                    "total": day_qs.count(),
                    "adoptions": day_qs.filter(outcome=OutcomeTypes.ADOPTION).count(),
                    "chosen": day_qs.filter(outcome=OutcomeTypes.CHOSEN).count(),
                    "fta": day_qs.filter(outcome=OutcomeTypes.FTA).count(),
                    "no_decision": day_qs.filter(outcome=OutcomeTypes.NO_DECISION).count(),
                    "no_show": day_qs.filter(outcome=OutcomeTypes.NO_SHOW).count(),
                }
            periods[period_key] = {"days": rows}

        return JsonResponse({"periods": periods}, status=status.HTTP_200_OK)

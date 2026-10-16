"""Shared fixtures for the smoke-test suite.

These tests exist to catch breakage from dependency and framework upgrades: every
test asserts that a real code path runs end to end and returns the expected status,
not the exact shape of each response. Network access is blocked and email uses
Django's in-memory backend, so nothing leaves the machine.
"""

import datetime
from unittest import mock

import requests
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from adopters.enums import ApprovalStatus
from adopters.models import Adopter
from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from bookings.models import Booking
from dogs.enums import DogSex, DogStatus
from dogs.models import Dog
from environment_settings.enums import EnvironmentType
from environment_settings.models import EnvironmentSettings
from pending_adoptions.enums import CircumstanceOptions, PendingAdoptionStatus
from pending_adoptions.models import PendingAdoption
from users.enums import SecurityLevel
from users.models import UserProfile


def _block_network(*args: object, **kwargs: object) -> None:
    raise AssertionError(f"Tests must not make network requests (attempted: {args[:2]})")


def local_instant(days_from_today: int, hour: int) -> datetime.datetime:
    day = timezone.localdate() + datetime.timedelta(days=days_from_today)
    return timezone.make_aware(datetime.datetime.combine(day, datetime.time(hour, 0)))


class SmokeTestCase(TestCase):
    adopter: Adopter
    adopter_user: UserProfile
    other_adopter: Adopter
    admin_user: UserProfile
    greeter_user: UserProfile
    dog: Dog
    other_dog: Dog
    booked_appt: Appointment
    open_appt: Appointment
    booking: Booking
    pending_adoption: PendingAdoption

    @classmethod
    def setUpTestData(cls) -> None:
        EnvironmentSettings.objects.create(
            pk=1,
            environment_type=EnvironmentType.DEVELOPMENT,
            default_sending_email="sender@example.invalid",
            test_recipient_email="test-recipient@example.invalid",
            email_host="smtp.example.invalid",
            last_dog_import=timezone.now(),
        )

        cls.adopter, cls.adopter_user = cls.make_adopter(
            "Avery", "Adopter", "avery@example.invalid"
        )
        cls.other_adopter, _ = cls.make_adopter("Blake", "Other", "blake@example.invalid")

        cls.admin_user = UserProfile.objects.create(
            first_name="Ada",
            last_name="Admin",
            primary_email="admin@example.invalid",
            security_level=SecurityLevel.SUPERUSER,
            is_staff=True,
            is_superuser=True,
        )
        cls.greeter_user = UserProfile.objects.create(
            first_name="Gale",
            last_name="Greeter",
            primary_email="greeter@example.invalid",
            security_level=SecurityLevel.GREETER,
        )

        cls.dog = Dog.objects.create(
            name="Biscuit",
            shelterluv_id=1001,
            sex=DogSex.FEMALE,
            status=DogStatus.AVAILABLE_NOW,
            publishable=True,
            age_months=24,
            weight=40,
            available_date=timezone.localdate(),
            last_updated=timezone.localdate(),
        )
        cls.other_dog = Dog.objects.create(
            name="Pepper",
            shelterluv_id=1002,
            sex=DogSex.MALE,
            status=DogStatus.HEALTHY_IN_HOME,
            publishable=True,
            age_months=4,
            weight=12,
            last_updated=timezone.localdate(),
        )

        cls.booked_appt = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=local_instant(1, 14)
        )
        cls.open_appt = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=local_instant(1, 15)
        )
        cls.booking = Booking.create_active(cls.adopter, cls.booked_appt)

        cls.pending_adoption = PendingAdoption.objects.create(
            circumstance=CircumstanceOptions.HOST_WEEKEND,
            dog=cls.other_dog.name,
            dogID=cls.other_dog.id,
            adopter=cls.other_adopter,
            status=PendingAdoptionStatus.CHOSEN,
        )

    @staticmethod
    def make_adopter(first: str, last: str, email: str) -> tuple[Adopter, UserProfile]:
        adopter = Adopter.objects.create(
            primary_email=email,
            status=ApprovalStatus.APPROVED,
            approved_until=timezone.localdate() + datetime.timedelta(days=60),
        )
        user = UserProfile.objects.create(
            first_name=first,
            last_name=last,
            primary_email=email,
            security_level=SecurityLevel.ADOPTER,
            adopter_profile=adopter,
        )
        return adopter, user

    def setUp(self) -> None:
        for target in ("requests.Session.request", "requests.request"):
            patcher = mock.patch(target, side_effect=_block_network)
            patcher.start()
            self.addCleanup(patcher.stop)
        assert requests  # imported so the patch targets resolve

    @staticmethod
    def make_staff(level: SecurityLevel) -> UserProfile:
        return UserProfile.objects.create(
            first_name="Staff",
            last_name=level.name.title(),
            primary_email=f"staff-{level.name.lower()}@example.invalid",
            security_level=level,
        )

    def client_for(self, user: UserProfile | None) -> APIClient:
        client = APIClient()
        if user is not None:
            client.force_authenticate(user)
        return client

    def assertStatus(self, response: object, expected: int) -> None:
        actual = getattr(response, "status_code")
        body = getattr(response, "content", b"")[:500]
        self.assertEqual(actual, expected, f"Expected {expected}, got {actual}: {body!r}")

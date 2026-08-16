from django.core.management.base import BaseCommand

from adopters.models import Adopter
from appointments.enums import OutcomeTypes
from appointments.models import Appointment
from bookings.enums import BookingStatus
from pending_adoptions.enums import PendingAdoptionStatus


class Command(BaseCommand):
    help = "Backfill adoption_completed=True for adopters with unreversed adoption outcomes."

    def add_arguments(self, parser: object) -> None:
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write changes to the database (default is dry-run).",
        )

    def handle(self, *args: object, **options: object) -> None:
        apply = options["apply"]

        # Appointments with adoption outcomes that were NOT later reversed via a canceled pending adoption
        unreversed_appts = Appointment.objects.filter(
            outcome__in=[OutcomeTypes.ADOPTION, OutcomeTypes.CHOSEN, OutcomeTypes.FTA]
        ).exclude(source_adoption__status=PendingAdoptionStatus.CANCELED)

        affected = Adopter.objects.filter(
            bookings__appointment__in=unreversed_appts,
            bookings__status=BookingStatus.COMPLETED,
            user_profile__adoption_completed=False,
        ).distinct()

        count = affected.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No adopters found needing backfill."))
            return

        self.stdout.write(f"{'DRY RUN — ' if not apply else ''}Found {count} adopter(s) to restrict:\n")

        for adopter in affected:
            self.stdout.write(f"  [{adopter.id}] {adopter.user_profile.disambiguated_name}")

        if apply:
            for adopter in affected:
                adopter.restrict_calendar()
            self.stdout.write(self.style.SUCCESS(f"\nRestricted {count} adopter(s)."))
        else:
            self.stdout.write(
                self.style.WARNING("\nDry run complete. Re-run with --apply to write changes.")
            )

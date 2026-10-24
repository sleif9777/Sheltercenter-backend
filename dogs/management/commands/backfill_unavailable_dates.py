import os
import time
from datetime import timedelta

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from dotenv import load_dotenv

from dogs.enums import DogStatus
from dogs.models import Dog
from dogs.shelterluv import SHELTERLUV_API_ROOT, fetch_adoption_date

# Stay under Shelterluv's ~300 requests/minute limit.
REQUEST_INTERVAL_SECONDS = 0.25


class Command(BaseCommand):
    help = (
        "One-time fix: reset unavailable_date on Healthy In Home dogs to their Shelterluv adoption "
        "date. Earlier imports derived it from LastUpdated, which moves on any record edit."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=90,
            help="Only check dogs whose current unavailable_date is within this many days. "
            "A corrected date can only move earlier, so older dates are already past every cutoff.",
        )
        parser.add_argument(
            "--dry-run", action="store_true", help="Report changes without saving them"
        )

    def handle(self, *args, **kwargs):
        load_dotenv()
        api_key = os.environ.get("SHELTERLUV_API_KEY")
        if not api_key:
            self.stdout.write(self.style.ERROR("API key not found!"))
            return
        headers = {"Authorization": f"Bearer {api_key}"}
        dry_run = kwargs["dry_run"]

        cutoff = timezone.localdate() - timedelta(days=kwargs["days"])
        dogs = {
            dog.shelterluv_id: dog
            for dog in Dog.objects.filter(status=DogStatus.HEALTHY_IN_HOME).filter(
                Q(unavailable_date__gte=cutoff) | Q(unavailable_date__isnull=True)
            )
        }
        self.stdout.write(f"Checking {len(dogs)} Healthy In Home dogs")
        if not dogs:
            return

        internal_ids = self._fetch_internal_ids(headers, set(dogs))
        if internal_ids is None:
            self.stdout.write(self.style.ERROR("Animal list fetch failed — nothing changed."))
            return

        changed = 0
        for shelterluv_id, dog in dogs.items():
            internal_id = internal_ids.get(shelterluv_id)
            if not internal_id:
                self.stdout.write(self.style.WARNING(f"  {dog}: not found in Shelterluv, skipped"))
                continue

            time.sleep(REQUEST_INTERVAL_SECONDS)
            adoption_date = fetch_adoption_date(internal_id, headers)
            if not adoption_date:
                self.stdout.write(self.style.WARNING(f"  {dog}: no adoption event, skipped"))
                continue
            if adoption_date == dog.unavailable_date:
                continue

            self.stdout.write(f"  {dog}: {dog.unavailable_date} -> {adoption_date}")
            changed += 1
            if not dry_run:
                dog.unavailable_date = adoption_date
                dog.save(update_fields=["unavailable_date"])

        verb = "Would update" if dry_run else "Updated"
        self.stdout.write(self.style.SUCCESS(f"Done! {verb} {changed} of {len(dogs)} dogs"))

    def _fetch_internal_ids(self, headers, wanted):
        # The events endpoint needs Shelterluv's Internal-ID, which we don't store, so map it
        # from the animal list.
        internal_ids = {}
        offset = 0
        while True:
            response = requests.get(
                f"{SHELTERLUV_API_ROOT}/animals",
                headers=headers,
                params={"offset": offset},
                timeout=30,
            )
            if response.status_code != 200:
                return None
            data = response.json()
            for animal in data.get("animals", []):
                try:
                    shelterluv_id = int(animal["ID"])
                except (KeyError, ValueError):
                    continue
                if shelterluv_id in wanted and animal.get("Internal-ID"):
                    internal_ids[shelterluv_id] = animal["Internal-ID"]
            if not data.get("has_more", False):
                return internal_ids
            offset += 100
            time.sleep(REQUEST_INTERVAL_SECONDS)

import requests
import os
import time

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from dogs.enums import DogStatus
from dogs.models import Dog
from dogs.mapper import map_dog, parse_status
from dotenv import load_dotenv
from email_templates.views import EmailViewSet
from environment_settings.models import EnvironmentSettings


class Command(BaseCommand):
    help = "Import dogs from Shelterluv API"
    base_url = "https://new.shelterluv.com/api/v1/animals"

    def handle(self, *args, **kwargs):
        load_dotenv()
        api_key = self._get_api_key()
        if not api_key:
            self.stdout.write(self.style.ERROR("API key not found!"))
            return

        self.headers = {"Authorization": f"Bearer {api_key}"}

        environment = EnvironmentSettings.objects.get(pk=1)
        is_first_run = environment.last_dog_import is None

        publishable_ids = self._fetch_all_ids(status_type="publishable")

        min_shelterluv_id = None if is_first_run else self._get_min_shelterluv_id()
        if not is_first_run and min_shelterluv_id is None:
            self.stdout.write(self.style.WARNING("No dogs in DB, treating as first run."))
            is_first_run = True

        imported_ids, total_imported, total_reactivated = self._import_all_animals(
            publishable_ids, is_first_run, min_shelterluv_id
        )
        deactivated = self._deactivate_missing_dogs(imported_ids)
        self._update_last_import_timestamp(environment)

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Imported: {total_imported - total_reactivated}, "
                f"Reactivated: {total_reactivated}, Deactivated: {deactivated}"
            )
        )

    def _get_api_key(self):
        return os.environ.get("SHELTERLUV_API_KEY")

    def _get_min_shelterluv_id(self):
        result = Dog.objects.aggregate(models.Min("shelterluv_id"))
        return result.get("shelterluv_id__min")

    def _fetch_page(self, offset, status_type=None):
        params = {"offset": offset}
        if status_type:
            params["status_type"] = status_type
        self.stdout.write(f"Fetching page at offset={offset} (status_type={status_type})...")
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Request failed: {response.status_code}"))
            return None
        return response.json()

    def _fetch_all_ids(self, status_type=None):
        ids = set()
        offset = 0
        while True:
            data = self._fetch_page(offset, status_type=status_type)
            if data is None:
                break
            for animal in data.get("animals", []):
                try:
                    ids.add(int(animal["ID"]))
                except (KeyError, ValueError):
                    pass
            if not data.get("has_more", False):
                break
            offset += 100
        return ids

    def _import_all_animals(self, publishable_ids, is_first_run, min_shelterluv_id):
        imported_ids = set()
        total_imported = 0
        total_reactivated = 0

        first_page = self._fetch_page(0)
        if first_page is None:
            return imported_ids, total_imported, total_reactivated

        total_count = first_page.get("total_count", 0)
        offsets = [0] + list(range(100, total_count, 100))

        requests_this_minute = 1
        minute_start = time.time()

        for offset in offsets:
            requests_this_minute += 1
            if requests_this_minute >= 290:
                elapsed = time.time() - minute_start
                if elapsed < 60:
                    self.stdout.write(f"Rate limit approaching, sleeping {60 - elapsed:.1f}s...")
                    time.sleep(60 - elapsed)
                requests_this_minute = 0
                minute_start = time.time()

            data = first_page if offset == 0 else self._fetch_page(offset)
            if data is None:
                break

            animals = data.get("animals", [])

            if is_first_run:
                animals = [a for a in animals if parse_status(a) not in [DogStatus.UNAVAILABLE, DogStatus.HEALTHY_IN_HOME]]
            else:
                animals = [a for a in animals if int(a.get("ID", 0)) >= min_shelterluv_id]

            page_imported, page_reactivated = self._process_animals(animals, imported_ids, publishable_ids, is_first_run)
            total_imported += page_imported
            total_reactivated += page_reactivated
            self.stdout.write(f"  Processed {len(animals)} animals.")

        return imported_ids, total_imported, total_reactivated

    def _process_animals(self, animals, imported_ids, publishable_ids, is_first_run):
        total_imported = 0
        total_reactivated = 0

        for animal_data in animals:
            parsed = map_dog(animal_data, is_first_run)
            if not parsed:
                self.stdout.write(
                    self.style.WARNING(f"Failed to parse animal {animal_data.get('ID')}")
                )
                continue

            parsed["publishable"] = parsed["shelterluv_id"] in publishable_ids
            shelterluv_id = parsed["shelterluv_id"]
            reactivated = self._upsert_dog(parsed)
            imported_ids.add(shelterluv_id)
            total_imported += 1
            if reactivated:
                total_reactivated += 1

        return total_imported, total_reactivated

    def _upsert_dog(self, parsed):
        shelterluv_id = parsed.pop("shelterluv_id")
        previous = Dog.objects.filter(shelterluv_id=shelterluv_id).first()
        was_inactive = previous and not previous.publishable
        unavailable_date = previous.unavailable_date if previous else None

        dog, created = Dog.objects.update_or_create(
            shelterluv_id=shelterluv_id, defaults=parsed
        )

        reactivated = not created and was_inactive and dog.publishable
        if reactivated:
            self._handle_reactivation(dog, unavailable_date)

        return reactivated

    def _handle_reactivation(self, dog, unavailable_date):
        if unavailable_date and (timezone.now().date() - unavailable_date).days > 90:
            dog.interest_adopters.clear()
        dog.unavailable_date = None
        dog.save()

    def _deactivate_missing_dogs(self, imported_ids):
        dogs_to_deactivate = (
            Dog.objects.filter(publishable=True)
            .exclude(shelterluv_id__in=imported_ids)
            .prefetch_related("interest_adopters")
        )

        for dog in dogs_to_deactivate:
            self._notify_interested_adopters(dog)

        return dogs_to_deactivate.update(
            publishable=False, unavailable_date=timezone.localdate()
        )

    def _notify_interested_adopters(self, dog):
        for adopter in dog.interest_adopters.all():
            EmailViewSet().DogNoLongerAvailable(adopter, dog.name)

    def _update_last_import_timestamp(self, environment):
        environment.last_dog_import = timezone.now()
        environment.save()
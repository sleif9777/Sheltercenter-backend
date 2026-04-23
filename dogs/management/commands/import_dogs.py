import requests
import os
import time

from django.core.management.base import BaseCommand
from django.utils import timezone
from adopters.models import Adopter
from dogs.enums import DogStatus
from dogs.models import Dog
from dogs.mapper import map_dog, parse_status
from dotenv import load_dotenv
from email_templates.views import EmailViewSet
from environment_settings.models import EnvironmentSettings


class Command(BaseCommand):
    help = "Import dogs from Shelterluv API"
    base_url = "https://new.shelterluv.com/api/v1/animals"
    is_test_env = False

    def add_arguments(self, parser):
        parser.add_argument(
            "--dog-id",
            type=int,
            help="Only process a single dog by Shelterluv ID (for testing)",
        )
        parser.add_argument(
            "--env-type",
            type=int,
            help="Only print debug output in a test environment",
        )

    def handle(self, *args, **kwargs):
        load_dotenv()
        self.test_dog_id = kwargs.get("dog_id")
        self.is_test_env = kwargs.get("env_type") == 1

        if self.test_dog_id:
            self._debug_output(self.style.WARNING(f"--- TEST MODE: only processing dog ID {self.test_dog_id} ---"))

        api_key = self._get_api_key()
        if not api_key:
            self._debug_output(self.style.ERROR("API key not found!"))
            return

        self.headers = {"Authorization": f"Bearer {api_key}"}

        environment = EnvironmentSettings.objects.get(pk=1)
        is_first_run = environment.last_dog_import is None
        self._debug_output(f"is_first_run={is_first_run}, last_dog_import={environment.last_dog_import}")

        publishable_ids = self._fetch_all_ids(status_type="publishable")
        self._debug_output(f"Fetched {len(publishable_ids)} publishable IDs from API")
        if self.test_dog_id:
            self._debug_output(f"Test dog {self.test_dog_id} in publishable_ids: {self.test_dog_id in publishable_ids}")

        imported_ids, total_imported, total_reactivated, total_created = self._import_all_animals(
            publishable_ids, is_first_run
        )
        deactivated = self._deactivate_missing_dogs(imported_ids)
        self._update_last_import_timestamp(environment)

        self._debug_output(
            self.style.SUCCESS(
                f"Done! Imported: {total_imported - total_reactivated}, "
                f"Reactivated: {total_reactivated}, Deactivated: {deactivated} "
                f"Created: {total_created}"
            )
        )

    def _get_api_key(self):
        return os.environ.get("SHELTERLUV_API_KEY")

    def _fetch_page(self, offset, status_type=None):
        params = {"offset": offset}
        if status_type:
            params["status_type"] = status_type
        self._debug_output(f"Fetching page at offset={offset} (status_type={status_type})...")
        response = requests.get(self.base_url, headers=self.headers, params=params)
        if response.status_code != 200:
            self._debug_output(self.style.ERROR(f"Request failed: {response.status_code}"))
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

    def _import_all_animals(self, publishable_ids, is_first_run):
        imported_ids = set()
        total_imported = 0
        total_reactivated = 0
        total_created = 0

        first_page = self._fetch_page(0)
        if first_page is None:
            return imported_ids, total_imported, total_reactivated, total_created

        total_count = first_page.get("total_count", 0)
        offsets = [0] + list(range(100, total_count, 100))
        self._debug_output(f"Total animals from API: {total_count}, pages to fetch: {len(offsets)}")

        requests_this_minute = 1
        minute_start = time.time()

        for offset in offsets:
            requests_this_minute += 1
            if requests_this_minute >= 290:
                elapsed = time.time() - minute_start
                if elapsed < 60:
                    self._debug_output(f"Rate limit approaching, sleeping {60 - elapsed:.1f}s...")
                    time.sleep(60 - elapsed)
                requests_this_minute = 0
                minute_start = time.time()

            data = first_page if offset == 0 else self._fetch_page(offset)
            if data is None:
                break

            animals = data.get("animals", [])

            if self.test_dog_id:
                animals = [a for a in animals if a.get("ID") == str(self.test_dog_id)]
                if animals:
                    self._debug_output(f"Found test dog {self.test_dog_id} in page at offset={offset}")

            if is_first_run:
                animals = [
                    a for a in animals
                    if parse_status(a) not in [DogStatus.UNAVAILABLE, DogStatus.HEALTHY_IN_HOME]
                ]

            page_imported, page_reactivated, page_created = self._process_animals(
                animals, imported_ids, publishable_ids
            )
            total_imported += page_imported
            total_reactivated += page_reactivated
            total_created += page_created

            if animals:
                self._debug_output(f"  Processed {len(animals)} animals at offset={offset}.")

        return imported_ids, total_imported, total_reactivated, total_created

    def _process_animals(self, animals, imported_ids, publishable_ids):
        total_imported = 0
        total_reactivated = 0
        total_created = 0

        for animal_data in animals:
            if animal_data.get("Type") != "Dog":
                continue

            parsed = map_dog(animal_data)
            if not parsed:
                self._debug_output(
                    self.style.WARNING(f"Failed to parse animal {animal_data.get('ID')}")
                )
                continue

            shelterluv_id = parsed["shelterluv_id"]
            parsed["publishable"] = shelterluv_id in publishable_ids

            self._debug_output(
                f"  Processing dog shelterluv_id={shelterluv_id}, "
                f"parsed publishable={parsed['publishable']}, "
                f"parsed status={parsed.get('status')}"
            )

            created, reactivated = self._upsert_dog(parsed)
            imported_ids.add(shelterluv_id)
            total_imported += 1
            if reactivated:
                total_reactivated += 1
            if created:
                total_created += 1

        return total_imported, total_reactivated, total_created

    def _upsert_dog(self, parsed):
        shelterluv_id = parsed.pop("shelterluv_id")
        previous = Dog.objects.filter(shelterluv_id=shelterluv_id).first()
        was_inactive = previous and not previous.publishable
        was_active = previous and previous.publishable
        unavailable_date = previous.unavailable_date if previous else None

        self._debug_output(
            f"  DB state before upsert: exists={previous is not None}, "
            f"was_active={was_active}, was_inactive={was_inactive}, "
            f"unavailable_date={unavailable_date}"
        )

        dog, created = Dog.objects.update_or_create(
            shelterluv_id=shelterluv_id, defaults=parsed
        )

        self._debug_output(
            f"  DB state after upsert: created={created}, "
            f"publishable={dog.publishable}, status={dog.status}"
        )

        reactivated = not created and was_inactive and dog.publishable
        if reactivated:
            self._debug_output(self.style.SUCCESS(f"  Dog {dog.name} ({shelterluv_id}) reactivated"))
            self._handle_reactivation(dog, unavailable_date)

        just_deactivated = not created and was_active and not dog.publishable
        self._debug_output(f"  just_deactivated={just_deactivated} (not created={not created}, was_active={was_active}, not publishable={not dog.publishable})")

        if just_deactivated:
            dog.unavailable_date = timezone.localdate()
            dog.save()
            dog = Dog.objects.prefetch_related("interest_adopters").get(pk=dog.pk)
            adopters = list(dog.interest_adopters.all())
            self._debug_output(
                self.style.WARNING(
                    f"  Dog {dog.name} ({shelterluv_id}) just deactivated, "
                    f"found {len(adopters)} interested adopters"
                )
            )
            for adopter in adopters:
                self._debug_output(f"    Adopter pk={adopter.pk}, adoption_completed={adopter.user_profile.adoption_completed}")
            self._notify_interested_adopters(dog)

        return created, reactivated

    def _handle_reactivation(self, dog, unavailable_date):
        if unavailable_date and (timezone.now().date() - unavailable_date).days > 90:
            dog.interest_adopters.clear()
        dog.unavailable_date = None
        dog.save()

    def _deactivate_missing_dogs(self, imported_ids):
        if self.test_dog_id:
            self._debug_output(self.style.WARNING("TEST MODE: skipping deactivate_missing_dogs"))
            return 0

        dogs_to_deactivate = list(
            Dog.objects.filter(publishable=True, unavailable_date__isnull=True)
            .exclude(shelterluv_id__in=imported_ids)
            .prefetch_related("interest_adopters")
        )

        self._debug_output(f"Dogs newly missing from API (to deactivate): {len(dogs_to_deactivate)}")
        for dog in dogs_to_deactivate:
            self._debug_output(f"  Deactivating dog {dog.name} (shelterluv_id={dog.shelterluv_id})")
            self._notify_interested_adopters(dog)

        deactivated_count = Dog.objects.filter(publishable=True).exclude(
            shelterluv_id__in=imported_ids
        ).update(publishable=False, unavailable_date=timezone.localdate())

        return deactivated_count

    def _notify_interested_adopters(self, dog):
        email_list: list[Adopter] = [
            adopter for adopter in dog.interest_adopters.all()
            if not adopter.user_profile.adoption_completed
        ]

        self._debug_output(f"  Notifying {len(email_list)} adopters for dog {dog.name}")

        for adopter in email_list:
            try:
                self._debug_output(f"    Sending email to adopter pk={adopter.pk}...")
                EmailViewSet().DogNoLongerAvailable(adopter, dog.name)
                self._debug_output(self.style.SUCCESS(f"    Email sent to adopter pk={adopter.pk}"))
            except Exception as e:
                self._debug_output(
                    self.style.WARNING(f"Failed to email adopter {adopter.pk} for {dog.name}: {e}")
                )

    def _update_last_import_timestamp(self, environment):
        environment.last_dog_import = timezone.now()
        environment.save()

    def _debug_output(self, message):
        if self.is_test_env:
            self.stdout.write(message)
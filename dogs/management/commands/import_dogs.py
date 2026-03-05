import requests
import os

from django.core.management.base import BaseCommand
from django.utils import timezone
from dogs.models import Dog
from dogs.mapper import map_dog
from dotenv import load_dotenv
from email_templates.views import EmailViewSet
from email_templates.services import EmailService
from environment_settings.models import EnvironmentSettings

from dotenv import load_dotenv, find_dotenv


class Command(BaseCommand):
    help = "Import dogs from Shelterluv API"

    def handle(self, *args, **kwargs):
        load_dotenv()
        shelterluv_api_key = os.environ.get("SHELTERLUV_API_KEY")
        base_url = "https://new.shelterluv.com/api/v1/animals"

        if shelterluv_api_key is None:
            self.stdout.write(self.style.ERROR("API key not found!"))
            return

        headers = {"Authorization": f"Bearer {shelterluv_api_key}"}

        offset = 0
        iteration = 0
        total_imported = 0
        total_reactivated = 0
        imported_shelterluv_ids = set()

        while True:
            params = {
                "status_type": "publishable",
                "offset": offset,
            }

            self.stdout.write(f"Fetching page {iteration + 1} (offset={offset})...")
            response = requests.get(base_url, headers=headers, params=params)

            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Request failed: {response.status_code}"))
                break

            data = response.json()
            animals = data.get("animals", [])

            for animal_data in animals:
                parsed = map_dog(animal_data)
                if parsed:
                    shelterluv_id = parsed.pop("shelterluv_id")

                    # Check previous state before updating
                    previous = Dog.objects.filter(shelterluv_id=shelterluv_id).first()

                    if previous:
                        was_inactive = previous and not previous.available_now
                        unavailable_date = previous.unavailable_date
                    else:
                        was_inactive = False
                        unavailable_date = None

                    dog, created = Dog.objects.update_or_create(
                        shelterluv_id=shelterluv_id, defaults=parsed
                    )

                    if not created and was_inactive and dog.available_now:
                        if unavailable_date and (timezone.now().date() - unavailable_date).days > 90:
                            dog.interest_adopters.clear()
                        total_reactivated += 1

                    imported_shelterluv_ids.add(shelterluv_id)
                    total_imported += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(f"Failed to parse animal {animal_data.get('ID')}")
                    )

            self.stdout.write(f"  Processed {len(animals)} animals.")

            if not data.get("has_more", False):
                break

            iteration += 1
            offset = iteration * 100

        # Fetch dogs being deactivated (still available_now) before updating them,
        # so we can notify interested adopters
        dogs_to_deactivate = (
            Dog.objects.filter(available_now=True)
            .exclude(shelterluv_id__in=imported_shelterluv_ids)
            .prefetch_related("interest_adopters")
        )

        for dog in dogs_to_deactivate:
            for adopter in dog.interest_adopters.all():
                EmailViewSet().DogNoLongerAvailable(adopter, dog.name)

        deactivated = dogs_to_deactivate.update(
            available_now=False, unavailable_date=timezone.localdate()
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Imported: {total_imported - total_reactivated}, Reactivated: {total_reactivated}, Deactivated: {deactivated}"
            )
        )

        environment = EnvironmentSettings.objects.get(pk=1)
        environment.last_dog_import = timezone.now()
        environment.save()

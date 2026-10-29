import sys

from django.core.management.base import BaseCommand, CommandError, CommandParser

from chatbot.models import PolicyEntry


class Command(BaseCommand):
    help = (
        "Create or update a chatbot policy entry by slug. The body is read from stdin, e.g. "
        "`heroku run --no-tty -- python manage.py upsert_policy visits --title 'Visits' < visits.md`."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("slug")
        parser.add_argument("--title", help="Required when creating a new entry.")
        parser.add_argument(
            "--deactivate", action="store_true", help="Hide the entry from the chatbot."
        )
        parser.add_argument(
            "--activate", action="store_true", help="Show a deactivated entry again."
        )

    def handle(self, *args: object, **options: object) -> None:
        slug = str(options["slug"])
        title = options["title"]
        entry = PolicyEntry.objects.filter(slug=slug).first()

        if options["deactivate"] or options["activate"]:
            if entry is None:
                raise CommandError(f"No policy entry with slug '{slug}'.")
            entry.is_active = bool(options["activate"])
            entry.save(update_fields=["is_active", "updated_instant"])
            state = "Activated" if entry.is_active else "Deactivated"
            self.stdout.write(self.style.SUCCESS(f"{state} '{slug}'."))
            return

        body = sys.stdin.read().strip()
        if not body:
            raise CommandError("Pipe the policy body in on stdin.")

        if entry is None:
            if not title:
                raise CommandError("--title is required for a new entry.")
            PolicyEntry.objects.create(slug=slug, title=str(title), body=body)
            self.stdout.write(self.style.SUCCESS(f"Created '{slug}'."))
            return

        entry.body = body
        if title:
            entry.title = str(title)
        entry.save()
        self.stdout.write(self.style.SUCCESS(f"Updated '{slug}'."))

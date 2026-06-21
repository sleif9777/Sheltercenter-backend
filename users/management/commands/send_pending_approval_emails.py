from django.core.management.base import BaseCommand

from adopters.enums import ApprovalStatus
from adopters.models import Adopter
from email_templates.views import EmailViewSet


class Command(BaseCommand):
    help = "Send approval emails to all approved adopters whose email has not yet been sent"

    def handle(self, *args, **options):
        pending = Adopter.objects.filter(status=ApprovalStatus.APPROVED, approval_emailed=False)
        self.stdout.write(f"Found {pending.count()} adopters needing approval emails")

        sent, failed = 0, 0
        for adopter in pending:
            try:
                EmailViewSet().ApplicationApproved(adopter)
                sent += 1
            except Exception as e:
                self.stderr.write(f"Failed for {adopter.primary_email}: {e}")
                failed += 1

        self.stdout.write(f"Done: {sent} sent, {failed} failed")

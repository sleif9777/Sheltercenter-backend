from django.core import mail
from django.core.mail import EmailMessage
from django.test import SimpleTestCase, override_settings

from email_templates.views import EmailViewSet

from .base import SmokeTestCase


def allowlist(*patterns: str) -> override_settings:
    return override_settings(
        EMAIL_BACKEND="email_templates.backends.AllowlistEmailBackend",
        EMAIL_ALLOWLIST_INNER_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_ALLOWLIST=list(patterns),
    )


@allowlist("dev@example.invalid", "dev+*@example.invalid")
class AllowlistBackendTests(SimpleTestCase):
    """Outside prod, only allowlisted addresses receive mail."""

    def test_strips_recipients_not_on_the_allowlist(self) -> None:
        EmailMessage(
            subject="Hello",
            body="Body",
            to=["Dev <DEV+test@example.invalid>", "adopter@example.invalid"],
            cc=["adoptions@example.invalid", "dev@example.invalid"],
            bcc=["other@example.invalid"],
        ).send()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ["Dev <DEV+test@example.invalid>"])
        self.assertEqual(message.cc, ["dev@example.invalid"])
        self.assertEqual(message.bcc, [])

    def test_drops_message_with_no_allowlisted_recipients(self) -> None:
        with self.assertLogs("email_templates.backends", level="WARNING"):
            sent = EmailMessage(subject="Hello", body="Body", to=["adopter@example.invalid"]).send()
        self.assertEqual(sent, 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_pattern_does_not_match_lookalike_domain(self) -> None:
        EmailMessage(subject="Hello", body="Body", to=["dev+x@example.invalid.evil"]).send()
        self.assertEqual(len(mail.outbox), 0)


@allowlist("test-recipient@example.invalid")
class AllowlistEmailServiceTests(SmokeTestCase):
    def test_adopter_cc_is_dropped(self) -> None:
        """The test-recipient redirect only covers `to`; the allowlist also catches the CCs."""
        EmailViewSet().CalendarAccessRestored(self.adopter)
        message = mail.outbox[-1]
        self.assertEqual(message.to, ["test-recipient@example.invalid"])
        self.assertNotIn(self.adopter.primary_email, message.cc)
        self.assertNotIn("adoptions@savinggracenc.org", message.cc)

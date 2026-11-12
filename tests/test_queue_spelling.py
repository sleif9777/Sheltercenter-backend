from django.core import mail
from django.test import SimpleTestCase

from email_templates.views import EmailViewSet
from utils.TextUtils import fix_queue_spelling

from .base import SmokeTestCase


class FixQueueSpellingTests(SimpleTestCase):
    def test_corrects_que_keeping_case(self) -> None:
        self.assertEqual(fix_queue_spelling("You are #3 in the que."), "You are #3 in the queue.")
        self.assertEqual(fix_queue_spelling("Que position"), "Queue position")
        self.assertEqual(fix_queue_spelling("THE QUE"), "THE QUEUE")

    def test_corrects_inside_html(self) -> None:
        self.assertEqual(
            fix_queue_spelling("<p>in the <b>que</b></p>"), "<p>in the <b>queue</b></p>"
        )

    def test_leaves_other_words_alone(self) -> None:
        text = "queue queued queues quest unique qué"
        self.assertEqual(fix_queue_spelling(text), text)


class QueueSpellingEmailTests(SmokeTestCase):
    def test_staff_message_is_corrected(self) -> None:
        EmailViewSet().GenericMessage(
            self.adopter_user, "Your que spot", "<p>You are first in que</p>"
        )

        message = mail.outbox[-1]
        self.assertTrue(message.subject.endswith("Your queue spot"))
        self.assertIn("first in queue", message.alternatives[0][0])

    def test_ready_to_roll_message_is_corrected(self) -> None:
        EmailViewSet().ReadyToRoll(self.pending_adoption, "<p>No que today</p>")

        self.assertIn("No queue today", mail.outbox[-1].alternatives[0][0])

    def test_adopter_message_to_adoptions_is_unchanged(self) -> None:
        EmailViewSet().GenericMessage(self.adopter_user, "Hi", "<p>que</p>", to_adoptions=True)

        self.assertIn("<p>que</p>", mail.outbox[-1].alternatives[0][0])

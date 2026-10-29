"""The Message Adoptions chatbot: gating, the daily cap, and handing unanswered questions to staff.

The Anthropic client is replaced with a fake, so no request leaves the machine.
"""

import datetime
import io
import json
from types import SimpleNamespace
from unittest import mock

import anthropic
from django.core import mail
from django.core.management import CommandError, call_command
from django.utils import timezone

from appointment_bases.enums import AppointmentTypes
from appointments.models import Appointment
from bookings.enums import BookingStatus
from bookings.models import Booking
from chatbot.enums import BacklogStatus
from chatbot.models import ChatbotInteraction, PolicyEntry

from .base import SmokeTestCase


def fake_response(**reply: object) -> SimpleNamespace:
    body = {
        "category": "other",
        "cited_policies": [],
        "answer": "",
        "needs_staff": True,
        "reason": "Not covered.",
        "offer_appointment_id": 0,
        "offer_cancel": False,
        "awaiting_reply": False,
    } | reply
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[SimpleNamespace(type="text", text=json.dumps(body))],
        usage=SimpleNamespace(input_tokens=120, cache_read_input_tokens=None, output_tokens=40),
    )


class ChatbotTests(SmokeTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.adopter.chatbot_enabled = True
        self.adopter.save()
        PolicyEntry.objects.create(
            slug="no-holds", title="No holds", body="We never hold dogs. First come, first served."
        )

        patcher = mock.patch("chatbot.services.anthropic.Anthropic")
        self.create = patcher.start().return_value.beta.messages.create
        self.addCleanup(patcher.stop)

    def ask(self, question: str = "Can you hold Biscuit for me?", expected: int = 200) -> dict:
        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/Ask/", {"adopterID": self.adopter.id, "question": question}, format="json"
        )
        self.assertStatus(resp, expected)
        return resp.json()

    def test_status_reports_flag_and_remaining_questions(self) -> None:
        with mock.patch.object(ChatbotInteraction, "DAILY_QUESTION_CAP", 5):
            resp = self.client_for(self.adopter_user).get(
                "/Chatbot/GetStatus/", {"adopterID": self.adopter.id}
            )
        self.assertStatus(resp, 200)
        self.assertEqual(resp.json(), {"enabled": True, "questionsRemaining": 5})

    def test_status_without_a_cap(self) -> None:
        with mock.patch.object(ChatbotInteraction, "DAILY_QUESTION_CAP", None):
            resp = self.client_for(self.adopter_user).get(
                "/Chatbot/GetStatus/", {"adopterID": self.adopter.id}
            )
        self.assertStatus(resp, 200)
        self.assertEqual(resp.json(), {"enabled": True, "questionsRemaining": None})

    def test_status_is_private_to_the_adopter(self) -> None:
        resp = self.client_for(self.adopter_user).get(
            "/Chatbot/GetStatus/", {"adopterID": self.other_adopter.id}
        )
        self.assertStatus(resp, 403)

    def test_adopters_without_the_flag_cannot_ask(self) -> None:
        self.adopter.chatbot_enabled = False
        self.adopter.save()

        self.ask(expected=403)
        self.create.assert_not_called()

    def test_grounded_answer_is_returned(self) -> None:
        self.create.return_value = fake_response(
            category="adoption_process",
            cited_policies=["no-holds"],
            needs_staff=False,
            answer="We don't hold dogs.",
        )

        with mock.patch.object(ChatbotInteraction, "DAILY_QUESTION_CAP", 5):
            body = self.ask()

        self.assertFalse(body["sentToStaff"])
        self.assertEqual(body["answer"], "We don't hold dogs.")
        self.assertEqual(body["questionsRemaining"], 4)
        self.assertEqual(len(mail.outbox), 0)
        interaction = ChatbotInteraction.objects.get()
        self.assertEqual(interaction.cited_policies, ["no-holds"])
        self.assertIsNone(interaction.backlog_status)
        self.assertEqual(interaction.input_tokens, 120)

    def test_answer_keeps_only_links_from_policies(self) -> None:
        PolicyEntry.objects.filter(slug="no-holds").update(
            body="We never hold dogs. Track them on your [watchlist](/watchlist/)."
        )
        self.create.return_value = fake_response(
            cited_policies=["no-holds"],
            needs_staff=False,
            answer=(
                "Use your [watchlist](/watchlist/). See [our FAQ](/faq/) or "
                "[this site](https://example.invalid/)."
            ),
        )

        body = self.ask()

        self.assertEqual(
            body["answer"], "Use your [watchlist](/watchlist/). See our FAQ or this site."
        )

    def test_prompt_carries_policies_and_adopter_details(self) -> None:
        self.create.return_value = fake_response()

        self.ask("When is my appointment?")

        kwargs = self.create.call_args.kwargs
        self.assertIn('<policy id="no-holds" title="No holds">', kwargs["system"][0]["text"])
        user_message = kwargs["messages"][0]["content"]
        self.assertIn("First name: Avery", user_message)
        self.assertIn(self.booked_appt.instant_display, user_message)
        self.assertIn("<question>\nWhen is my appointment?\n</question>", user_message)
        self.assertIn("Other adults listed on their application: none on file", user_message)

    def test_prompt_has_the_time_and_recent_appointments(self) -> None:
        missed = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=timezone.now() - datetime.timedelta(days=2)
        )
        Booking.create_active(self.adopter, missed).mark_status(BookingStatus.NOSHOW)
        self.create.return_value = fake_response()

        self.ask("Sorry I missed it!")

        user_message = self.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(f"Now: {timezone.localtime().strftime('%A, %B %-d, %Y')}, ", user_message)
        self.assertIn(
            f"Other appointments in the last 14 days: {missed.instant_display}, no show",
            user_message,
        )
        self.assertIn(
            f"Approved until: {self.adopter.approved_until.strftime('%B %-d, %Y')}", user_message
        )

    def test_eval_command_reports_passes_and_failures(self) -> None:
        self.create.return_value = fake_response()
        out = io.StringIO()

        call_command("chatbot_eval", "--case", "thank-you", stdout=out)
        self.assertIn("PASS  thank-you only", out.getvalue())

        with self.assertRaises(CommandError):
            call_command("chatbot_eval", "--case", "no-show", stdout=out)
        self.assertIn("expected answer, got staff", out.getvalue())
        self.assertEqual(ChatbotInteraction.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_prompt_lists_other_adults_on_the_application(self) -> None:
        self.adopter.co_applicants = "Sam Adopter"
        self.adopter.save()
        self.create.return_value = fake_response()

        self.ask("Can my partner come instead?")

        user_message = self.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn("Other adults listed on their application: Sam Adopter", user_message)

    def test_unanswerable_question_goes_to_staff_and_backlog(self) -> None:
        self.create.return_value = fake_response(category="specific_dog")

        body = self.ask("Is Biscuit good with cats?")

        self.assertTrue(body["sentToStaff"])
        self.assertEqual(body["answer"], "")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Is Biscuit good with cats?", mail.outbox[0].body)
        interaction = ChatbotInteraction.objects.get()
        self.assertTrue(interaction.bot_escalated)
        self.assertEqual(interaction.backlog_status, BacklogStatus.OPEN)
        self.assertEqual(interaction.category, "specific_dog")

    def test_partly_answered_message_shows_answer_and_goes_to_staff(self) -> None:
        self.create.return_value = fake_response(
            category="appointments",
            cited_policies=["no-holds"],
            answer="We don't hold dogs.",
            needs_staff=True,
            reason="Answered the hold question; booking needs staff.",
        )

        body = self.ask("Can you hold Biscuit and book me for Friday?")

        self.assertTrue(body["sentToStaff"])
        self.assertEqual(body["answer"], "We don't hold dogs.")
        interaction = ChatbotInteraction.objects.get()
        self.assertTrue(interaction.bot_escalated)
        self.assertEqual(interaction.backlog_status, BacklogStatus.OPEN)
        self.assertEqual(interaction.bot_reason, "Answered the hold question; booking needs staff.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Can you hold Biscuit and book me for Friday?", mail.outbox[0].body)
        self.assertNotIn("hold dogs.", mail.outbox[0].body)

    def test_send_to_staff_after_a_partial_answer_does_not_email_twice(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"], answer="We don't hold dogs.", needs_staff=True
        )
        interaction_id = self.ask()["interactionID"]

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/SendToStaff/", {"interactionID": interaction_id}, format="json"
        )

        self.assertStatus(resp, 204)
        self.assertEqual(len(mail.outbox), 1)

    def test_answer_without_a_real_citation_is_never_shown(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["made-up-policy"], needs_staff=False, answer="Sure, we'll hold him!"
        )

        body = self.ask()

        self.assertTrue(body["sentToStaff"])
        self.assertEqual(body["answer"], "")
        self.assertEqual(ChatbotInteraction.objects.get().backlog_status, BacklogStatus.OPEN)
        self.assertEqual(len(mail.outbox), 1)

    def test_empty_knowledge_base_skips_the_model(self) -> None:
        PolicyEntry.objects.update(is_active=False)

        body = self.ask()

        self.assertTrue(body["sentToStaff"])
        self.create.assert_not_called()
        self.assertEqual(ChatbotInteraction.objects.get().backlog_status, BacklogStatus.OPEN)
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_request_goes_to_staff_but_not_the_backlog(self) -> None:
        self.create.side_effect = anthropic.AnthropicError("down")

        with self.assertLogs("chatbot.services", level="ERROR"):
            body = self.ask()

        self.assertTrue(body["sentToStaff"])
        self.assertIsNone(ChatbotInteraction.objects.get().backlog_status)
        self.assertEqual(len(mail.outbox), 1)

    def test_refusal_goes_to_staff(self) -> None:
        response = fake_response(cited_policies=["no-holds"], needs_staff=False, answer="x")
        response.stop_reason = "refusal"
        self.create.return_value = response

        with self.assertLogs("chatbot.services", level="WARNING"):
            body = self.ask()

        self.assertTrue(body["sentToStaff"])
        self.assertEqual(len(mail.outbox), 1)

    @mock.patch.object(ChatbotInteraction, "DAILY_QUESTION_CAP", 3)
    def test_daily_cap(self) -> None:
        self.create.return_value = fake_response()
        for _ in range(3):
            self.ask()

        body = self.ask(expected=429)

        self.assertEqual(body, {"questionsRemaining": 0})
        self.assertEqual(self.create.call_count, 3)

    @mock.patch.object(ChatbotInteraction, "DAILY_QUESTION_CAP", None)
    def test_no_cap(self) -> None:
        self.create.return_value = fake_response()
        for _ in range(8):
            body = self.ask()

        self.assertIsNone(body["questionsRemaining"])
        self.assertEqual(self.create.call_count, 8)

    def test_question_length_limit(self) -> None:
        self.ask("x" * (ChatbotInteraction.MAX_QUESTION_LENGTH + 1), expected=400)
        self.create.assert_not_called()

    def test_prompt_lists_open_times_of_the_same_type(self) -> None:
        soon = Appointment.objects.create(
            type=AppointmentTypes.ADULTS, instant=timezone.now() + datetime.timedelta(hours=1)
        )
        puppies = Appointment.objects.create(
            type=AppointmentTypes.PUPPIES, instant=self.open_appt.instant
        )
        self.create.return_value = fake_response()

        self.ask("Can I come an hour later?")

        user_message = self.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(f"[{self.open_appt.id}]", user_message)
        self.assertNotIn(f"[{soon.id}]", user_message, "inside the 2-hour cutoff")
        self.assertNotIn(f"[{puppies.id}]", user_message, "a different appointment type")

    def ask_for_open_appt(self, offer_id: int | None = None) -> dict:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"],
            answer="That time is open, so you can switch with the button below.",
            needs_staff=False,
            offer_appointment_id=offer_id or self.open_appt.id,
        )
        return self.ask("Can I come an hour later?")

    def accept(self, interaction_id: int, user: object = None) -> object:
        return self.client_for(user or self.adopter_user).post(
            "/Chatbot/AcceptOffer/", {"interactionID": interaction_id}, format="json"
        )

    def test_offers_an_open_time_and_moves_the_appointment(self) -> None:
        body = self.ask_for_open_appt()
        self.assertIsNotNone(body["offer"])

        resp = self.accept(body["interactionID"])

        self.assertStatus(resp, 200)
        self.assertEqual(self.adopter.get_current_appointment(), self.open_appt)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.RESCHEDULED)
        self.assertEqual(resp.json()["currentAppt"]["ID"], self.open_appt.id)
        self.assertEqual(len(mail.outbox), 1, "the usual rescheduled email to the adopter")
        self.assertIsNotNone(ChatbotInteraction.objects.get().offer_accepted_instant)
        self.assertStatus(self.accept(body["interactionID"]), 409)

    def test_never_offers_a_time_that_is_not_open(self) -> None:
        taken = Appointment.objects.create(
            type=AppointmentTypes.ADULTS,
            instant=self.open_appt.instant + datetime.timedelta(hours=1),
        )
        Booking.create_active(self.other_adopter, taken)

        body = self.ask_for_open_appt(offer_id=taken.id)

        self.assertIsNone(body["offer"])
        self.assertIsNone(ChatbotInteraction.objects.get().offered_appointment)

    def test_offer_fails_if_the_time_is_taken_before_accepting(self) -> None:
        body = self.ask_for_open_appt()
        Booking.create_active(self.other_adopter, self.open_appt)

        self.assertStatus(self.accept(body["interactionID"]), 409)
        self.assertEqual(self.adopter.get_current_appointment(), self.booked_appt)

    def test_offer_can_only_be_accepted_by_its_adopter(self) -> None:
        body = self.ask_for_open_appt()

        self.assertStatus(self.accept(body["interactionID"], self.other_adopter.user_profile), 403)
        self.assertEqual(self.adopter.get_current_appointment(), self.booked_appt)

    def ask_to_cancel(self) -> dict:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"],
            answer="You can cancel with the button below.",
            needs_staff=False,
            offer_cancel=True,
        )
        return self.ask("Please cancel my appointment.")

    def test_offers_to_cancel_and_cancels(self) -> None:
        body = self.ask_to_cancel()
        self.assertIsNotNone(body["offerCancel"])
        client = self.client_for(self.adopter_user)

        resp = client.post(
            "/Chatbot/AcceptCancellation/", {"interactionID": body["interactionID"]}, format="json"
        )

        self.assertStatus(resp, 200)
        self.booking.refresh_from_db()
        self.assertEqual(self.booking.status, BookingStatus.CANCELLED)
        self.assertIsNone(self.adopter.get_current_appointment())
        self.assertEqual(len(mail.outbox), 1, "the usual cancellation email to the adopter")
        again = client.post(
            "/Chatbot/AcceptCancellation/", {"interactionID": body["interactionID"]}, format="json"
        )
        self.assertStatus(again, 409)
        self.assertEqual(len(mail.outbox), 1)

    def test_cancellation_is_private_to_the_adopter(self) -> None:
        body = self.ask_to_cancel()

        resp = self.client_for(self.other_adopter.user_profile).post(
            "/Chatbot/AcceptCancellation/", {"interactionID": body["interactionID"]}, format="json"
        )

        self.assertStatus(resp, 403)
        self.assertEqual(self.adopter.get_current_appointment(), self.booked_appt)

    def test_no_cancel_offer_without_an_appointment(self) -> None:
        self.booking.mark_status(BookingStatus.CANCELLED)

        body = self.ask_to_cancel()

        self.assertIsNone(body["offerCancel"])
        self.assertFalse(ChatbotInteraction.objects.get().offered_cancellation)

    def test_reply_continues_the_conversation(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"],
            answer="Which day would you like?",
            needs_staff=False,
            awaiting_reply=True,
        )
        first = self.ask("I want to reschedule")
        self.assertTrue(first["awaitingReply"])
        self.create.return_value = fake_response()

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/Ask/",
            {
                "adopterID": self.adopter.id,
                "question": "Friday please",
                "previousInteractionID": first["interactionID"],
            },
            format="json",
        )

        self.assertStatus(resp, 200)
        user_message = self.create.call_args.kwargs["messages"][0]["content"]
        self.assertIn(
            "<earlier_messages>\nAdopter: I want to reschedule\nYou: Which day would you like?\n",
            user_message,
        )
        self.assertIn("<question>\nFriday please\n</question>", user_message)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0].alternatives[0][0]
        self.assertIn("<p>I want to reschedule</p><p>Friday please</p>", email)

    def test_reply_must_follow_the_adopters_own_message(self) -> None:
        theirs = ChatbotInteraction.objects.create(adopter=self.other_adopter, question="q")

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/Ask/",
            {"adopterID": self.adopter.id, "question": "hi", "previousInteractionID": theirs.id},
            format="json",
        )

        self.assertStatus(resp, 404)
        self.create.assert_not_called()

    def test_no_follow_up_question_alongside_an_offer(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"],
            answer="That time is open.",
            needs_staff=False,
            offer_appointment_id=self.open_appt.id,
            awaiting_reply=True,
        )

        body = self.ask("Can I come an hour later?")

        self.assertIsNotNone(body["offer"])
        self.assertFalse(body["awaitingReply"])

    def test_staff_email_uses_the_message_as_written(self) -> None:
        self.create.return_value = fake_response()

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/Ask/",
            {
                "adopterID": self.adopter.id,
                "question": "Hello there",
                "message": "<p>Hello <strong>there</strong></p>",
            },
            format="json",
        )

        self.assertStatus(resp, 200)
        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("<p>Hello <strong>there</strong></p>", html)

    def test_question_is_escaped_in_staff_email(self) -> None:
        self.create.return_value = fake_response()

        self.ask("<b>hi</b>\nsecond line")

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("<p>&lt;b&gt;hi&lt;/b&gt;</p><p>second line</p>", html)

    def test_send_to_staff_after_an_answer(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"], needs_staff=False, answer="We don't hold dogs."
        )
        interaction_id = self.ask()["interactionID"]
        client = self.client_for(self.adopter_user)

        for _ in range(2):
            resp = client.post(
                "/Chatbot/SendToStaff/", {"interactionID": interaction_id}, format="json"
            )
            self.assertStatus(resp, 204)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Can you hold Biscuit for me?", mail.outbox[0].body)
        self.assertNotIn("hold dogs.", mail.outbox[0].body)
        self.assertTrue(ChatbotInteraction.objects.get().adopter_escalated)

    def test_send_to_staff_is_private_to_the_adopter(self) -> None:
        interaction = ChatbotInteraction.objects.create(adopter=self.other_adopter, question="q")

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/SendToStaff/", {"interactionID": interaction.id}, format="json"
        )

        self.assertStatus(resp, 403)

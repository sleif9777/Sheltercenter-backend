"""The Message Adoptions chatbot: gating, the daily cap, and handing unanswered questions to staff.

The Anthropic client is replaced with a fake, so no request leaves the machine.
"""

import json
from types import SimpleNamespace
from unittest import mock

import anthropic
from django.core import mail

from chatbot.enums import BacklogStatus
from chatbot.models import ChatbotInteraction, PolicyEntry

from .base import SmokeTestCase


def fake_response(**reply: object) -> SimpleNamespace:
    body = {"category": "other", "cited_policies": [], "can_answer": False, "answer": ""} | reply
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
        resp = self.client_for(self.adopter_user).get(
            "/Chatbot/GetStatus/", {"adopterID": self.adopter.id}
        )
        self.assertStatus(resp, 200)
        self.assertEqual(
            resp.json(),
            {"enabled": True, "questionsRemaining": ChatbotInteraction.DAILY_QUESTION_CAP},
        )

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
            can_answer=True,
            answer="We don't hold dogs.",
        )

        body = self.ask()

        self.assertTrue(body["answered"])
        self.assertEqual(body["answer"], "We don't hold dogs.")
        self.assertEqual(body["questionsRemaining"], ChatbotInteraction.DAILY_QUESTION_CAP - 1)
        self.assertEqual(len(mail.outbox), 0)
        interaction = ChatbotInteraction.objects.get()
        self.assertEqual(interaction.cited_policies, ["no-holds"])
        self.assertIsNone(interaction.backlog_status)
        self.assertEqual(interaction.input_tokens, 120)

    def test_prompt_carries_policies_and_adopter_details(self) -> None:
        self.create.return_value = fake_response()

        self.ask("When is my appointment?")

        kwargs = self.create.call_args.kwargs
        self.assertIn('<policy id="no-holds" title="No holds">', kwargs["system"][0]["text"])
        user_message = kwargs["messages"][0]["content"]
        self.assertIn("First name: Avery", user_message)
        self.assertIn(self.booked_appt.instant_display, user_message)
        self.assertIn("<question>\nWhen is my appointment?\n</question>", user_message)

    def test_unanswerable_question_goes_to_staff_and_backlog(self) -> None:
        self.create.return_value = fake_response(category="specific_dog")

        body = self.ask("Is Biscuit good with cats?")

        self.assertFalse(body["answered"])
        self.assertEqual(body["answer"], "")
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Is Biscuit good with cats?", mail.outbox[0].body)
        interaction = ChatbotInteraction.objects.get()
        self.assertTrue(interaction.bot_escalated)
        self.assertEqual(interaction.backlog_status, BacklogStatus.OPEN)
        self.assertEqual(interaction.category, "specific_dog")

    def test_answer_without_a_real_citation_is_never_shown(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["made-up-policy"], can_answer=True, answer="Sure, we'll hold him!"
        )

        body = self.ask()

        self.assertFalse(body["answered"])
        self.assertEqual(body["answer"], "")
        self.assertEqual(ChatbotInteraction.objects.get().backlog_status, BacklogStatus.OPEN)
        self.assertEqual(len(mail.outbox), 1)

    def test_empty_knowledge_base_skips_the_model(self) -> None:
        PolicyEntry.objects.update(is_active=False)

        body = self.ask()

        self.assertFalse(body["answered"])
        self.create.assert_not_called()
        self.assertEqual(ChatbotInteraction.objects.get().backlog_status, BacklogStatus.OPEN)
        self.assertEqual(len(mail.outbox), 1)

    def test_failed_request_goes_to_staff_but_not_the_backlog(self) -> None:
        self.create.side_effect = anthropic.AnthropicError("down")

        with self.assertLogs("chatbot.services", level="ERROR"):
            body = self.ask()

        self.assertFalse(body["answered"])
        self.assertIsNone(ChatbotInteraction.objects.get().backlog_status)
        self.assertEqual(len(mail.outbox), 1)

    def test_refusal_goes_to_staff(self) -> None:
        response = fake_response(cited_policies=["no-holds"], can_answer=True, answer="x")
        response.stop_reason = "refusal"
        self.create.return_value = response

        with self.assertLogs("chatbot.services", level="WARNING"):
            body = self.ask()

        self.assertFalse(body["answered"])
        self.assertEqual(len(mail.outbox), 1)

    def test_daily_cap(self) -> None:
        self.create.return_value = fake_response()
        for _ in range(ChatbotInteraction.DAILY_QUESTION_CAP):
            self.ask()

        body = self.ask(expected=429)

        self.assertEqual(body, {"questionsRemaining": 0})
        self.assertEqual(self.create.call_count, ChatbotInteraction.DAILY_QUESTION_CAP)

    def test_question_length_limit(self) -> None:
        self.ask("x" * (ChatbotInteraction.MAX_QUESTION_LENGTH + 1), expected=400)
        self.create.assert_not_called()

    def test_question_is_escaped_in_staff_email(self) -> None:
        self.create.return_value = fake_response()

        self.ask("<b>hi</b>\nsecond line")

        html = mail.outbox[0].alternatives[0][0]
        self.assertIn("&lt;b&gt;hi&lt;/b&gt;<br>second line", html)

    def test_send_to_staff_after_an_answer(self) -> None:
        self.create.return_value = fake_response(
            cited_policies=["no-holds"], can_answer=True, answer="We don't hold dogs."
        )
        interaction_id = self.ask()["interactionID"]
        client = self.client_for(self.adopter_user)

        for _ in range(2):
            resp = client.post(
                "/Chatbot/SendToStaff/", {"interactionID": interaction_id}, format="json"
            )
            self.assertStatus(resp, 204)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("hold dogs.", mail.outbox[0].body)
        self.assertTrue(ChatbotInteraction.objects.get().adopter_escalated)

    def test_send_to_staff_is_private_to_the_adopter(self) -> None:
        interaction = ChatbotInteraction.objects.create(adopter=self.other_adopter, question="q")

        resp = self.client_for(self.adopter_user).post(
            "/Chatbot/SendToStaff/", {"interactionID": interaction.id}, format="json"
        )

        self.assertStatus(resp, 403)

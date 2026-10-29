from django.core.management.base import BaseCommand, CommandError, CommandParser

from chatbot.evals import ANSWER, CASES, PARTIAL, STAFF, EvalCase
from chatbot.models import ChatbotInteraction, PolicyEntry
from chatbot.services import OPEN_TIME_ID, ChatbotService


class Command(BaseCommand):
    help = (
        "Run the saved chatbot scenarios against the live model and current policies. Nothing is "
        "saved and no email is sent, but each case is a real API call."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--case", help="Only run cases whose name contains this text.")

    def handle(self, *args: object, **options: object) -> None:
        knowledge_base = PolicyEntry.compile_knowledge_base()
        if not knowledge_base:
            raise CommandError("There are no active policies to test against.")

        cases = [c for c in CASES if str(options["case"] or "").lower() in c.name.lower()]
        service = ChatbotService()
        failures = 0
        input_tokens = cache_read_tokens = output_tokens = 0

        for case in cases:
            # Unsaved, so it only collects token counts
            interaction = ChatbotInteraction()
            reply = service._get_reply(
                interaction, knowledge_base, service.user_message(case.details, case.message)
            )
            answer = service.shown_answer(reply, knowledge_base)
            outcome = STAFF if not answer else PARTIAL if reply and reply.needs_staff else ANSWER
            # Mirrors ask(): only a full answer can offer a time, and only one listed as open
            open_ids = {int(i) for line in case.details for i in OPEN_TIME_ID.findall(line)}
            offer = reply.offer_appointment_id if reply and outcome == ANSWER else 0
            offer = offer if offer in open_ids else None
            problems = self.problems(case, outcome, answer, offer)
            failures += bool(problems)
            input_tokens += interaction.input_tokens
            cache_read_tokens += interaction.cache_read_tokens
            output_tokens += interaction.output_tokens

            style = self.style.ERROR if problems else self.style.SUCCESS
            self.stdout.write(style(f"{'FAIL' if problems else 'PASS'}  {case.name}"))
            for problem in problems:
                self.stdout.write(f"      {problem}")
            self.stdout.write(
                f"      outcome: {outcome}" + (f", offers [{offer}]" if offer else "")
            )
            if reply is not None:
                self.stdout.write(f"      cited: {', '.join(reply.cited_policies) or 'none'}")
                self.stdout.write(f"      reason: {reply.reason}")
            if answer:
                self.stdout.write(f"      answer: {answer}")

        self.stdout.write(
            f"\n{len(cases) - failures}/{len(cases)} passed. Tokens: {input_tokens} input, "
            f"{cache_read_tokens} cache read, {output_tokens} output."
        )
        if failures:
            raise CommandError(f"{failures} case(s) failed.")

    @staticmethod
    def problems(case: EvalCase, outcome: str, answer: str, offer: int | None) -> list[str]:
        problems = []
        if outcome not in case.expected:
            problems.append(f"expected {' or '.join(sorted(case.expected))}, got {outcome}")
        if offer != case.offer:
            problems.append(f"expected offer {case.offer}, got {offer}")
        for text in case.mentions:
            if answer and text.lower() not in answer.lower():
                problems.append(f'answer doesn\'t mention "{text}"')
        words = len(answer.split())
        if case.max_words and words > case.max_words:
            problems.append(f"answer is {words} words, over {case.max_words}")
        return problems

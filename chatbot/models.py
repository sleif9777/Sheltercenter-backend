import hashlib

from django.conf import settings
from django.db import models
from django.utils import timezone

from adopters.models import Adopter
from appointments.models import Appointment

from .enums import BacklogStatus, InteractionReview


class PolicyEntry(models.Model):
    """One shelter policy or FAQ topic the chatbot may answer from.

    Active entries are compiled, in slug order, into the knowledge base sent with every question. The
    slug is the stable handle used to update an entry over time.
    """

    slug = models.SlugField(max_length=100, unique=True)
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    created_instant = models.DateTimeField(auto_now_add=True)
    updated_instant = models.DateTimeField(auto_now=True)

    @classmethod
    def compile_knowledge_base(cls) -> str:
        entries = cls.objects.filter(is_active=True).order_by("slug")
        return "\n\n".join(
            f'<policy id="{entry.slug}" title="{entry.title}">\n{entry.body.strip()}\n</policy>'
            for entry in entries
        )

    @classmethod
    def knowledge_base_version(cls, knowledge_base: str) -> str:
        return hashlib.sha256(knowledge_base.encode()).hexdigest()[:12]

    def __str__(self) -> str:
        return self.title

    class Meta:
        verbose_name = "policy entry"
        verbose_name_plural = "policy entries"
        ordering = ["slug"]


class ChatbotInteraction(models.Model):
    """One adopter question and the chatbot's reply, kept for staff review and evals.

    An answer must cite at least one policy entry; an uncited answer is never shown to the adopter.
    Whatever the chatbot can't answer goes to staff as a regular message and joins the backlog of
    questions the knowledge base can't answer yet, until a policy entry covers it or it's dismissed.
    A partly answered message shows the adopter its answer and still goes to staff.
    """

    # Past these, the adopter is sent to the regular Message Adoptions form. None means no daily cap,
    # which is only for testing on one account: set it back to 5 before enabling more adopters.
    DAILY_QUESTION_CAP: int | None = None
    MAX_QUESTION_LENGTH = 1000

    created_instant = models.DateTimeField(auto_now_add=True)
    # Kept when the adopter is deleted so the question stays usable as an eval case
    adopter = models.ForeignKey(
        Adopter, null=True, on_delete=models.SET_NULL, related_name="chatbot_interactions"
    )
    question = models.TextField()
    # The adopter's message as they wrote it, formatting included, for the email to staff
    message_html = models.TextField(default="", blank=True)
    answer = models.TextField(default="", blank=True)
    category = models.CharField(default="", max_length=50, blank=True)
    # The chatbot's one-sentence account of what it answered and what it left for staff
    bot_reason = models.TextField(default="", blank=True)
    # Slugs of the policy entries the answer relied on
    cited_policies = models.JSONField(default=list, blank=True)

    # An open time the chatbot offered to move the adopter's appointment to
    offered_appointment = models.ForeignKey(
        Appointment, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    # The chatbot offered to cancel the adopter's current appointment
    offered_cancellation = models.BooleanField(default=False)
    # When the adopter accepted either offer; after that, neither can be accepted again
    offer_accepted_instant = models.DateTimeField(null=True, blank=True)

    # The chatbot handed the question to staff instead of answering
    bot_escalated = models.BooleanField(default=False)
    # The adopter sent the question to staff after seeing the answer
    adopter_escalated = models.BooleanField(default=False)

    # Only set for questions the chatbot couldn't answer
    backlog_status = models.IntegerField(choices=BacklogStatus.choices, null=True, blank=True)
    resolved_by_policy = models.ForeignKey(
        PolicyEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_questions",
    )

    model = models.CharField(default="", max_length=50, blank=True)
    knowledge_base_version = models.CharField(default="", max_length=12, blank=True)
    input_tokens = models.IntegerField(default=0)
    cache_read_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)

    review = models.IntegerField(choices=InteractionReview.choices, null=True, blank=True)
    review_notes = models.TextField(default="", blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    @classmethod
    def questions_remaining_today(cls, adopter: Adopter) -> int | None:
        if cls.DAILY_QUESTION_CAP is None:
            return None

        asked = cls.objects.filter(
            adopter=adopter, created_instant__date=timezone.localdate()
        ).count()
        return max(cls.DAILY_QUESTION_CAP - asked, 0)

    def __str__(self) -> str:
        return self.question[:80]

    class Meta:
        verbose_name = "chatbot interaction"
        ordering = ["-created_instant"]

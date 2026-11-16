from enum import Enum

from django.db import models


class InteractionReview(models.IntegerChoices, Enum):
    GOOD = 0, "Good"
    WRONG = 1, "Wrong answer"
    SHOULD_HAVE_ESCALATED = 2, "Should have escalated"
    SHOULD_NOT_HAVE_ESCALATED = 3, "Escalated unnecessarily"


class BacklogStatus(models.IntegerChoices, Enum):
    OPEN = 0, "Open"
    ANSWERED = 1, "Answered by a policy"
    DISMISSED = 2, "Dismissed"


class InteractionSource(models.IntegerChoices, Enum):
    CHATBOT = 0, "Chatbot"
    # Written in the regular Message Adoptions form and sent straight to staff, with no chatbot reply.
    # Kept only to grow the backlog from real adopter questions.
    MESSAGE_FORM = 1, "Message Adoptions form"

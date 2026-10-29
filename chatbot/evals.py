"""Real messages adopters have sent, with the adopter details at the time and what the chatbot should do.

Run them against the live model and the current policies with `python manage.py chatbot_eval`. Add a
case whenever the chatbot gets a message wrong, or a new kind of message comes in.
"""

from dataclasses import dataclass, field

# What the adopter ends up seeing: a full answer, a partial answer with the message also sent to
# staff, or just the "sent to our team" confirmation
ANSWER, PARTIAL, STAFF = "answer", "partial", "staff"


@dataclass
class EvalCase:
    name: str
    message: str
    details: list[str]
    # Any of these outcomes passes
    expected: set[str]
    # Each must appear in the shown answer, ignoring case
    mentions: list[str] = field(default_factory=list)


def details(
    now: str,
    appointment: str = "none booked",
    recent: str = "none",
    calendar: str = "open",
    co_applicants: str = "none on file (this doesn't mean nobody else is listed)",
    adoption: str = "none",
) -> list[str]:
    return [
        f"Now: {now}",
        "First name: Jamie",
        f"Current appointment: {appointment}",
        f"Other appointments in the last 14 days: {recent}",
        f"Calendar access: {calendar}",
        f"Other adults listed on their application: {co_applicants}",
        f"Adoption in progress: {adoption}",
    ]


CASES = [
    EvalCase(
        name="no-show apology",
        message="I thought this was for tomorrow Oct 24, my bad!",
        details=details("Friday, October 23, 2026, 6:40 PM", recent="Oct 23, 04:00 PM, no show"),
        expected={ANSWER},
        mentions=["Book New Appointment"],
    ),
    EvalCase(
        name="earlier slot, before the booking cutoff",
        message=(
            "Hi. I'm wondering if my 4:30 spot is still available? I canceled to book 6:00, but my "
            "daughter got home sooner than expected."
        ),
        details=details(
            "Wednesday, October 28, 2026, 1:45 PM",
            appointment="Oct 28, 06:00 PM",
            recent="Oct 28, 04:30 PM, cancelled",
        ),
        expected={ANSWER},
        mentions=["See Open Appointments", "Cancel My Appointment"],
    ),
    EvalCase(
        name="earlier slot, inside the booking cutoff",
        message=(
            "Hi. I'm wondering if my 4:30 spot is still available? I canceled to book 6:00, but my "
            "daughter got home sooner than expected."
        ),
        details=details(
            "Wednesday, October 28, 2026, 3:10 PM",
            appointment="Oct 28, 06:00 PM",
            recent="Oct 28, 04:30 PM, cancelled",
        ),
        expected={PARTIAL, STAFF},
    ),
    EvalCase(
        name="co-applicant listed",
        message=(
            "Hi, not sure if I listed my husbands name on the adoption application. He is Chris "
            "Porter. He will be the person able to go next Wednesday in hopes of getting oatmeal. "
            "Please let me know if I need to do anything."
        ),
        details=details(
            "Wednesday, October 28, 2026, 9:15 AM",
            appointment="Nov 04, 05:30 PM",
            co_applicants="Chris Porter",
        ),
        expected={ANSWER},
        mentions=["ID"],
    ),
    EvalCase(
        name="relative not listed",
        message="Can my sister Jane come to my appointment instead of me and adopt?",
        details=details(
            "Wednesday, October 28, 2026, 9:15 AM",
            appointment="Nov 04, 05:30 PM",
            co_applicants="Chris Porter",
        ),
        expected={ANSWER},
        mentions=["application"],
    ),
    EvalCase(
        name="asks to hold a dog",
        message="Can you hold Oatmeal for me until Saturday? I really want him.",
        details=details("Wednesday, October 28, 2026, 9:15 AM", appointment="Oct 31, 01:00 PM"),
        expected={ANSWER, PARTIAL},
        mentions=["watchlist"],
    ),
    EvalCase(
        name="surrender",
        message="I need to bring back the dog I adopted last month, he isn't working out.",
        details=details("Wednesday, October 28, 2026, 9:15 AM"),
        expected={STAFF},
    ),
    EvalCase(
        name="thank-you only",
        message="Thank you so much!!",
        details=details("Wednesday, October 28, 2026, 9:15 AM", appointment="Oct 31, 01:00 PM"),
        expected={STAFF},
    ),
]

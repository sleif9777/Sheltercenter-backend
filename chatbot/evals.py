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
    # Longest acceptable answer, for messages that only need a short reply
    max_words: int | None = None
    # The open time (its id in the details) the chatbot should offer to move the appointment to
    offer: int | None = None
    # Whether the chatbot should offer to cancel the current appointment
    offer_cancel: bool = False
    # Whether the answer should ask the adopter for one more detail; None doesn't check
    asks_follow_up: bool | None = None
    # Whether the chatbot should mark the adopter as bringing their own dog
    bringing_dog: bool = False


def details(
    now: str,
    appointment: str = "none booked",
    open_times: str = "none",
    recent: str = "none",
    approved_until: str = "October 20, 2027",
    calendar: str = "open",
    co_applicants: str = "none on file (this doesn't mean nobody else is listed)",
    adoption: str = "none",
    watchlist: str = "none",
    dogs_named: str = "none",
) -> list[str]:
    return [
        f"Now: {now}",
        "First name: Jamie",
        f"Current appointment: {appointment}",
        f"Open times you can offer to move their current appointment to: {open_times}",
        f"Other appointments in the last 14 days: {recent}",
        f"Approved until: {approved_until}",
        f"Calendar access: {calendar}",
        f"Other adults listed on their application: {co_applicants}",
        f"Adoption in progress: {adoption}",
        f"Dogs on their watchlist: {watchlist}",
        f"Other dogs named in their message: {dogs_named}",
    ]


EARLIER_SLOT = (
    "Hi. I'm wondering if my 4:30 spot is still available? I canceled to book 6:00, but my daughter "
    "got home sooner than expected."
)

CASES = [
    EvalCase(
        name="no-show apology",
        message="I thought this was for tomorrow Oct 24, my bad!",
        details=details("Friday, October 23, 2026, 6:40 PM", recent="Oct 23, 04:00 PM, no show"),
        expected={ANSWER},
        mentions=["Book New Appointment"],
        max_words=60,
    ),
    EvalCase(
        name="no-show apology the records don't show",
        message="I'm sorry I missed my appointment! I thought it was for Friday.",
        details=details("Wednesday, October 28, 2026, 9:05 PM", appointment="Nov 04, 05:30 PM"),
        expected={ANSWER},
        max_words=60,
    ),
    EvalCase(
        name="booking more than two weeks ahead",
        message=(
            "I wasn't sure how long the adoption process would take so I submitted my application "
            "a few days ago. I am happy I have been approved. I want to schedule an appointment in "
            "November. We have a family event in Colorado that we are attending (planned several "
            "months ago) and will be there from Nov. 11 - 16. I read in the information you sent "
            "that a dog cannot be held. So it would be best for me to schedule a visit for when we "
            "return. I saw that the schedule is only done 2 weeks out. I am checking to make sure "
            "that it will be okay for me to schedule my visit when your calendar is updated. Look "
            "forward to meeting the dogs! Thank you."
        ),
        details=details("Monday, October 26, 2026, 8:20 PM"),
        expected={ANSWER},
        max_words=60,
    ),
    EvalCase(
        name="booking ahead, but approval runs out first",
        message="I'm traveling until mid-January. Can I book a visit for when I get back?",
        details=details("Monday, October 26, 2026, 8:20 PM", approved_until="December 17, 2026"),
        expected={ANSWER},
    ),
    EvalCase(
        name="earlier slot, before the booking cutoff",
        message=EARLIER_SLOT,
        details=details(
            "Wednesday, October 28, 2026, 1:45 PM",
            appointment="Oct 28, 06:00 PM",
            open_times="Wed Oct 28: 4:30 PM [501], 5:00 PM [502]; Thu Oct 29: 12:00 PM [503]",
            recent="Oct 28, 04:30 PM, cancelled",
        ),
        expected={ANSWER},
        offer=501,
    ),
    EvalCase(
        name="earlier slot, before the cutoff but taken",
        message=EARLIER_SLOT,
        details=details(
            "Wednesday, October 28, 2026, 1:45 PM",
            appointment="Oct 28, 06:00 PM",
            open_times="Wed Oct 28: 5:00 PM [502]; Thu Oct 29: 12:00 PM [503]",
            recent="Oct 28, 04:30 PM, cancelled",
        ),
        expected={ANSWER},
    ),
    EvalCase(
        name="earlier slot, inside the booking cutoff",
        message=EARLIER_SLOT,
        details=details(
            "Wednesday, October 28, 2026, 3:10 PM",
            appointment="Oct 28, 06:00 PM",
            open_times="Thu Oct 29: 12:00 PM [503]",
            recent="Oct 28, 04:30 PM, cancelled",
        ),
        expected={PARTIAL, STAFF},
    ),
    EvalCase(
        name="move to an open time on another day",
        message="Can I reschedule for 1pm on 11/5",
        details=details(
            "Wednesday, October 28, 2026, 10:00 PM",
            appointment="Nov 04, 05:30 PM",
            open_times="Thu Nov 5: 1:00 PM [601], 1:30 PM [602]; Fri Nov 6: 12:00 PM [603]",
        ),
        expected={ANSWER},
        offer=601,
        max_words=60,
    ),
    EvalCase(
        name="reschedule without a time",
        message="I want to reschedule my appointment",
        details=details(
            "Wednesday, October 28, 2026, 10:00 PM",
            appointment="Nov 04, 05:30 PM",
            open_times="Wed Nov 4: 3:00 PM [701], 4:00 PM [702]; Thu Nov 5: 1:00 PM [703]",
        ),
        expected={ANSWER},
        asks_follow_up=True,
        max_words=60,
    ),
    EvalCase(
        name="time without a date",
        message="I want to reschedule for 3pm",
        details=details(
            "Wednesday, October 28, 2026, 10:00 PM",
            appointment="Nov 04, 05:30 PM",
            open_times="Wed Nov 4: 3:00 PM [701], 4:00 PM [702]; Thu Nov 5: 1:00 PM [703], 3:00 PM [704]",
        ),
        expected={ANSWER},
        offer=701,
        max_words=60,
    ),
    EvalCase(
        name="move to a time outside operating hours",
        message="Can I move my appointment to 9:30am on Thursday 11/5?",
        details=details(
            "Wednesday, October 28, 2026, 10:00 PM",
            appointment="Nov 04, 05:30 PM",
            open_times="Thu Nov 5: 1:00 PM [601], 1:30 PM [602]; Fri Nov 6: 12:00 PM [603]",
        ),
        expected={ANSWER},
        mentions=["1"],
        max_words=60,
    ),
    EvalCase(
        name="cancel request",
        message="Something came up and I can't make it Saturday. Please cancel my appointment, sorry!",
        details=details("Wednesday, October 28, 2026, 9:15 AM", appointment="Oct 31, 01:00 PM"),
        expected={ANSWER},
        offer_cancel=True,
        max_words=60,
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
        name="bringing own dog",
        message="I will be bringing our dog with us to our appointment",
        details=details("Tuesday, November 17, 2026, 7:15 PM", appointment="Nov 19, 02:00 PM"),
        expected={ANSWER},
        mentions=["leash"],
        bringing_dog=True,
    ),
    EvalCase(
        name="booked again to bring own dog, with thanks",
        message=(
            "Thank you for the warm welcome today. I have scheduled another appointment for Friday "
            "(11/27) to bring my dog Ziggy. I look forward to visiting then.\nAll best wishes,\nKristin"
        ),
        details=details(
            "Monday, November 23, 2026, 7:25 PM",
            appointment="Nov 27, 01:00 PM",
            recent="Nov 23, 03:00 PM, completed",
        ),
        expected={ANSWER},
        mentions=["leash"],
        bringing_dog=True,
    ),
    EvalCase(
        name="asks whether they can bring their dog",
        message="Am I allowed to bring my dog to meet the dogs at my appointment?",
        details=details("Tuesday, November 17, 2026, 7:15 PM", appointment="Nov 19, 02:00 PM"),
        expected={ANSWER},
        mentions=["leash"],
    ),
    EvalCase(
        name="notified if an adopted dog is returned",
        message=(
            "Hello! We were going to come today as we were interested in Loretta, but saw she got "
            "adopted (yay!). Is there a way to be contacted if a dog is ever brought back to Saving "
            "Grace? Or is it just best to keep an eye on the site? I'm guessing the watchlist is "
            "only for available dogs, so I wanted to check. Thank you!"
        ),
        details=details("Tuesday, November 17, 2026, 7:58 AM", appointment="Nov 17, 02:00 PM"),
        expected={ANSWER},
        mentions=["website"],
    ),
    EvalCase(
        name="visit a chosen dog before pickup",
        message=(
            "Hi! Loretta is not ready to come home yet, and I'd love to come see her while she gets "
            "over her cold and sees the vet. Could I have access to the appointment calendar? "
            "Thanks! Amy"
        ),
        details=details(
            "Tuesday, November 17, 2026, 8:16 AM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
            adoption="Loretta, status Needs Well Check",
        ),
        expected={ANSWER},
        mentions=["Visit My Dog"],
    ),
    EvalCase(
        name="pickup time for a dog that's ready",
        message="Hi, please let me know if ok to pick up Madison tomorrow 11/18 between 1:30 - 2?",
        details=details(
            "Tuesday, November 17, 2026, 6:21 PM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
            adoption="Madison, status Ready to Roll",
        ),
        expected={ANSWER, PARTIAL},
        mentions=["Pick Up My Dog"],
    ),
    EvalCase(
        name="is a listed dog still available",
        message="Is turquoise still available?",
        details=details(
            "Thursday, November 19, 2026, 1:15 PM", dogs_named="Turquoise (Hound Mix): available"
        ),
        expected={ANSWER},
        mentions=["Turquoise"],
        max_words=80,
    ),
    EvalCase(
        name="dog no longer on the website",
        message=(
            "Is Dallas still available for adoption? I don't see his post anymore under available "
            "for adoption."
        ),
        details=details(
            "Friday, November 20, 2026, 1:26 PM",
            dogs_named="Dallas (Shepherd Mix): no longer available",
        ),
        expected={ANSWER},
        mentions=["no longer available"],
        max_words=80,
    ),
    EvalCase(
        name="neutered, adult weight and availability",
        message=(
            "Hey, Thanks for accepting my application. Still curious about Kenan. Has he been "
            "neutered? Whats his expected weight? His foster parents described him wonderfully. I "
            "realize he may not still be available. But doesnt hurt to inquire. Thanks, Tiffany"
        ),
        details=details(
            "Thursday, November 19, 2026, 11:00 AM",
            dogs_named="Kenan (Labrador Retriever Mix): available",
        ),
        expected={ANSWER},
        mentions=["spayed or neutered"],
    ),
    # Staff-only by choice: no policy will ever answer these, so they must keep going to staff
    EvalCase(
        name="staff only: one dog's vaccinations",
        message="Has Betsy received any of her vaccinations?",
        details=details(
            "Wednesday, November 18, 2026, 10:42 AM",
            appointment="Nov 19, 02:00 PM",
            dogs_named="Betsy (Terrier Mix): available",
        ),
        expected={STAFF},
    ),
    EvalCase(
        name="staff only: adopted dog's medication",
        message=(
            "Hello,\nWhile looking through Shelly's medical record I noticed that she is due for "
            "more Panacur Liquid starting on the 23rd. This didn't come up during the adoption "
            "process so I have a few questions. Was this treatment started as a curative or "
            "preventative? There are other animals potentially in close contact so I need to know "
            "if we need to separate her/take extra precautions cleaning her waste. Was this "
            "something that was supposed to come with her prednisone or does it need to be "
            "supplied externally?\nThanks!"
        ),
        details=details(
            "Wednesday, November 18, 2026, 2:42 PM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
        ),
        expected={STAFF},
    ),
    EvalCase(
        name="staff only: calendar locked by a wrong adoption",
        message=(
            "Hi,\nI was accidentally sent an email saying I adopted a dog last Friday, and now I am "
            "unable to schedule an appointment for myself, because it is is considering me as having "
            "already adopted!\nCan you help?\nThanks!"
        ),
        details=details(
            "Monday, November 16, 2026, 2:59 PM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
        ),
        expected={STAFF},
    ),
    EvalCase(
        name="staff only: chosen dog's health and size",
        message=(
            "Hey there! We're extremely excited to bring Greyson home, and were wondering if there "
            "were any updates concerning his health. Is there any chance we could go ahead and "
            "schedule visits for 11/24 and 11/25 at ~1pm?\nAlso, We're looking at crates for "
            "Greyson. Is there any chance y'all have his height and length so we can buy a crate he "
            "can be comfy in?"
        ),
        details=details(
            "Tuesday, November 17, 2026, 1:23 PM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
            adoption="Greyson, status Needs Spay/Neuter",
        ),
        expected={PARTIAL, STAFF},
    ),
    EvalCase(
        name="staff only: one dog's age in the bio",
        message=(
            "When I first saw Phoenix the bio said he was 2 and now it said he is 7. Can you please "
            "let me know what his age is?"
        ),
        details=details(
            "Tuesday, November 24, 2026, 5:28 PM", dogs_named="Phoenix (Boxer Mix): available"
        ),
        expected={STAFF},
    ),
    EvalCase(
        name="staff only: update on a chosen dog's vet visit",
        message=(
            "Hi\nI am just reaching out to see if there is any update on the adoption process for "
            "Sherbert? Wasn't sure if a vet has been able to see him yet or not.\nThank you"
        ),
        details=details(
            "Wednesday, November 25, 2026, 11:58 AM",
            calendar="restricted, because they have chosen a dog or completed an adoption",
            adoption="Sherbert, status Needs Well Check",
        ),
        expected={STAFF},
    ),
    EvalCase(
        name="thank-you only",
        message="Thank you so much!!",
        details=details("Wednesday, October 28, 2026, 9:15 AM", appointment="Oct 31, 01:00 PM"),
        expected={STAFF},
    ),
]

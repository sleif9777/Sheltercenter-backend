import mimetypes
import os
import sys

import requests
from adopters.models import Adopter
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from environment_settings.models import EnvironmentSettings


class EmailService:
    _GENERIC_COMMENTS: frozenset[str] = frozenset({"dog", "dogs", "a dog", "any dog", "any"})
    _MAX_COMMENT_LENGTH: int = 50

    @staticmethod
    def subject_with_comments(base: str, comments: str | None) -> str:
        cleaned = (comments or "").strip()
        if not cleaned:
            return base
        if cleaned.lower() in EmailService._GENERIC_COMMENTS:
            return base
        if len(cleaned) > EmailService._MAX_COMMENT_LENGTH:
            return base
        return f"{base} (Interested in: {cleaned})"

    def __init__(self, title, template_path, context, recipients: str | list[str], attachments=None, adopter: Adopter=None):
        attachments = attachments or []

        self.subject = title
        self.attachments = attachments
        self.adopter = adopter

        self.content_html = render_to_string(
            f"email_templates/{template_path}.html",
            context
        )
        self.content_plain = strip_tags(self.content_html)

        environment = EnvironmentSettings.objects.get(pk=1)
        
        if isinstance(recipients, str):
            recipients = [recipients]

        if environment.use_production_email:
            self.recipients = recipients
        else:
            self.recipients = [environment.test_recipient_email]
            self.subject = f"[TEST EMAIL] {self.subject}"

    # TODO: deprecate always_send
    def send(self, always_send=False, cc_adoptions=True):
        cc_list = []

        if cc_adoptions:
            cc_list.append("adoptions@savinggracenc.org")

        if self.adopter:
            cc_list.append(self.adopter.primary_email)
        
        try:
            sender = os.environ.get("MAILGUN_SENDER")
            
            msg = EmailMultiAlternatives(
                subject=self.subject,
                body=self.content_plain,
                from_email=sender,
                to=self.recipients,
                cc=cc_list if len(cc_list) > 0 else None,
                reply_to=[self.adopter.primary_email] if self.adopter else ["adoptions@savinggracenc.org"],
            )

            msg.attach_alternative(self.content_html, "text/html")

            for attachment in self.attachments:
                if isinstance(attachment, tuple):
                    path_or_url, desired_filename = attachment
                else:
                    path_or_url, desired_filename = attachment, None

                if path_or_url.startswith(("http://", "https://")):
                    response = requests.get(path_or_url)
                    response.raise_for_status()
                    filename = desired_filename or path_or_url.split("?")[0].split("/")[-1]
                    mime_type = response.headers.get(
                        "Content-Type",
                        mimetypes.guess_type(filename)[0] or "application/octet-stream",
                    )
                    msg.attach(filename, response.content, mime_type)
                else:
                    if desired_filename:
                        mime_type = mimetypes.guess_type(path_or_url)[0] or "application/octet-stream"
                        with open(path_or_url, "rb") as f:
                            msg.attach(desired_filename, f.read(), mime_type)
                    else:
                        msg.attach_file(path_or_url)

            msg.send()
        except Exception as e:
            if hasattr(e, 'response'):
                print("Mailgun response body:", e.response.text)
            sys.stdout.write(self.style.ERROR(f"Failed to send email: {e}"))
            raise
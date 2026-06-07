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
                if attachment.startswith(("http://", "https://")):
                    response = requests.get(attachment)
                    response.raise_for_status()
                    filename = attachment.split("?")[0].split("/")[-1]
                    mime_type = response.headers.get(
                        "Content-Type",
                        mimetypes.guess_type(filename)[0] or "application/octet-stream",
                    )
                    msg.attach(filename, response.content, mime_type)
                else:
                    msg.attach_file(attachment)

            msg.send()
        except Exception as e:
            if hasattr(e, 'response'):
                print("Mailgun response body:", e.response.text)
            sys.stdout.write(self.style.ERROR(f"Failed to send email: {e}"))
            raise
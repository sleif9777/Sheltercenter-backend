import os
from posixpath import basename
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.mime.image import MIMEImage

from environment_settings.enums import EnvironmentType
from environment_settings.models import EnvironmentSettings


class EmailService:
    def __init__(self, title, template_path, context, recipients, attachments=None):
        attachments = attachments or []

        self.subject = title
        self.attachments = attachments

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
        environment = EnvironmentSettings.objects.get(pk=1)
        sender = (os.environ.get("MAILGUN_SENDER")
                  if environment.use_production_email
                  else os.environ.get("MAILGUN_SENDER"))
        
        msg = EmailMultiAlternatives(
            subject=self.subject,
            body=self.content_plain,
            from_email=sender,
            to=self.recipients,
            cc=["adoptions@savinggracenc.org"] if cc_adoptions else None,
            reply_to=["adoptions@savinggracenc.org"],
        )

        msg.attach_alternative(self.content_html, "text/html")

        for attachment in self.attachments:
            msg.attach_file(attachment)

        msg.send()
